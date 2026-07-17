import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.client_pipeline.api import ClientPipelineApiHandler
from bbi_os.client_pipeline.models import ClientRequest
from bbi_os.client_pipeline.pipeline_engine import ClientPipelineEngine
from bbi_os.client_pipeline.request_router import ClientRequestRouter
from bbi_os.client_pipeline.service import ClientPipelineService
from bbi_os.client_pipeline.templates.registry import ClientTemplateRegistry
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.integrations.models import ConnectorDefinition
from bbi_os.integrations.outbound import (
    ConnectorWorkflowAction,
    OutboundRequestEngine,
    TransportResponse,
)
from bbi_os.integrations.registry import IntegrationRegistry
from bbi_os.integrations.workflow import IntegrationWorkflowEngine
from bbi_os.observability import Observability, set_observability
from bbi_os.task_management.api import TaskRequestHandler
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService
from bbi_os.workflows.engine import ActionResult, WorkflowActionRegistry
from bbi_os.workflows.repository import WorkflowRepository
from bbi_os.workflows.templates import (
    WorkflowTemplateRepository,
    WorkflowTemplateService,
)


class CaptureAction:
    def __init__(self) -> None:
        self.inputs: List[Dict[str, Any]] = []

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        self.inputs.append(dict(inputs))
        return ActionResult(dict(inputs))

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        return None


class StaticTransport:
    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout_seconds: float,
    ) -> TransportResponse:
        return TransportResponse(200, b'{"external_id":"ext-42"}')


class ClientPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.capture = CaptureAction()
        actions = WorkflowActionRegistry()
        actions.register("entity_operation", "tasks", self.capture)
        integration_registry = IntegrationRegistry(root / "integrations.json")
        integration_registry.create_connector(
            ConnectorDefinition(
                connector_id="external",
                name="External service",
                type="http_api",
                base_url="https://external.example.test/api",
                auth_method="none",
                request_schema={"type": "object"},
                response_schema={
                    "type": "object",
                    "required": ["external_id"],
                },
            )
        )
        outbound = OutboundRequestEngine(integration_registry, StaticTransport())
        actions.register("function_call", "connector", ConnectorWorkflowAction(outbound))
        engine = IntegrationWorkflowEngine(
            WorkflowRepository(root / "definitions.json", root / "instances.json"),
            actions,
        )
        self.templates = WorkflowTemplateService(
            WorkflowTemplateRepository(root / "templates.json", root / "lineage.json"),
            engine,
        )
        self.templates.create(self._template("onboarding-template", external=False))
        self.templates.create(self._template("external-template", external=True))
        self.mapping = ClientTemplateRegistry()
        self.mapping.register("onboarding", "onboarding-template", "v1")
        self.mapping.register("external_action", "external-template", "v1")
        self.service = ClientPipelineService(
            ClientRequestRouter(self.mapping), ClientPipelineEngine(self.templates)
        )
        self.api = ClientPipelineApiHandler(self.service)
        self.task_service = TaskService(JsonTaskRepository(root / "tasks.json"))
        self.authenticator = Authenticator(
            {"user-token": UserIdentity("user-1", "client", "user", "start")}
        )
        self.routes = EntityRouteRegistry()
        self.routes.register("tasks", "tasks")
        self.routes.register("client", self.api)
        self.responses: List[Tuple[int, Dict[str, Any]]] = []
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    @staticmethod
    def _template(template_id: str, external: bool) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        if external:
            steps.append(
                {
                    "step_id": "external",
                    "step_name": "Call external service",
                    "action_type": "function_call",
                    "target_entity": "connector",
                    "input_mapping": {
                        "connector_id": "external",
                        "method": "POST",
                        "path": "actions",
                        "body": {"title": "${title}"},
                    },
                }
            )
            task_input = {
                "title": "${title}",
                "external_id": "$steps.external.data.external_id",
            }
        else:
            task_input = {"title": "${title}", "user_id": "${user_id}"}
        steps.append(
            {
                "step_id": "task",
                "step_name": "Process task",
                "action_type": "entity_operation",
                "target_entity": "tasks",
                "input_mapping": task_input,
                "output_mapping": {"title": "$result.title"},
            }
        )
        return {
            "template_id": template_id,
            "name": template_id,
            "description": "Client pipeline template",
            "version": "v1",
            "parameter_schema": {
                "required": ["title", "user_id"],
                "properties": {
                    "title": {"type": "string"},
                    "user_id": {"type": "string"},
                },
            },
            "step_blueprint": steps,
        }

    def call(
        self,
        body: Dict[str, Any],
        token: str = "user-token",
    ) -> Tuple[int, Dict[str, Any]]:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = "/v1/client/request"
        handler.command = "POST"
        handler.service = self.task_service
        handler.authenticator = self.authenticator
        handler.route_registry = self.routes
        handler.headers = {"Authorization": f"Bearer {token}"}
        handler._body = lambda: body

        def respond(status: int, response: Dict[str, Any]) -> None:
            handler._response_status = status
            self.responses.append((status, response))

        handler._respond = respond
        handler.do_POST()
        return self.responses[-1]

    def test_valid_request_executes_selected_workflow(self) -> None:
        status, response = self.call(
            {"type": "onboarding", "payload": {"title": "Welcome"}, "user_id": "user-1"}
        )
        self.assertEqual(201, status)
        self.assertEqual("completed", response["data"]["status"])
        self.assertEqual("onboarding-template", response["data"]["workflow_template_id"])
        self.assertEqual("Welcome", self.capture.inputs[-1]["title"])
        self.assertEqual("user-1", self.capture.inputs[-1]["user_id"])

    def test_invalid_request_type_returns_standard_error(self) -> None:
        status, response = self.call(
            {"type": "unknown", "payload": {}, "user_id": "user-1"}
        )
        self.assertEqual(400, status)
        self.assertEqual("INVALID_REQUEST_TYPE", response["data"]["error"]["code"])

    def test_authentication_failure_blocks_pipeline(self) -> None:
        status, response = self.call(
            {"type": "onboarding", "payload": {"title": "No"}, "user_id": "user-1"},
            token="invalid-token",
        )
        self.assertEqual(401, status)
        self.assertEqual("INVALID_TOKEN", response["data"]["error"]["code"])
        self.assertEqual([], self.capture.inputs)

    def test_authenticated_identity_cannot_be_spoofed(self) -> None:
        status, response = self.call(
            {"type": "onboarding", "payload": {"title": "No"}, "user_id": "user-2"}
        )
        self.assertEqual(401, status)
        self.assertEqual("UNAUTHORIZED", response["data"]["error"]["code"])

    def test_request_router_mapping_is_extensible_and_exact(self) -> None:
        route = ClientRequestRouter(self.mapping).route(
            ClientRequest("external_action", {}, "user-1")
        )
        self.assertEqual("external-template", route.template_id)
        self.assertEqual("v1", route.version)

    def test_full_pipeline_uses_external_response_in_following_step(self) -> None:
        status, response = self.call(
            {
                "type": "external_action",
                "payload": {"title": "Send externally"},
                "user_id": "user-1",
            }
        )
        self.assertEqual(201, status)
        self.assertEqual("ext-42", self.capture.inputs[-1]["external_id"])
        self.assertTrue(response["data"]["workflow_instance_id"])
        summary = response["execution_summary"]
        self.assertEqual(
            response["data"]["workflow_instance_id"],
            summary["workflow_instance_id"],
        )
        self.assertEqual(["external", "task"], summary["steps_completed"])
        self.assertEqual(1, len(summary["external_calls"]))
        self.assertEqual([], summary["errors"])

    def test_observability_emits_complete_pipeline_event(self) -> None:
        self.call(
            {"type": "onboarding", "payload": {"title": "Trace"}, "user_id": "user-1"}
        )
        records = [json.loads(line) for line in self.stream.getvalue().splitlines()]
        event = next(
            record for record in records if record["event"] == "client_pipeline_completed"
        )
        self.assertEqual("user-1", event["user_id"])
        self.assertTrue(event["request_id"])
        self.assertEqual("onboarding-template", event["metadata"]["workflow_template_id"])
        self.assertTrue(event["metadata"]["workflow_instance_id"])
        self.assertEqual("completed", event["metadata"]["status"])
        self.assertGreaterEqual(event["metadata"]["execution_time_ms"], 0)


if __name__ == "__main__":
    unittest.main()
