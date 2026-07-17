import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.client_onboarding.api import OnboardingApiHandler
from bbi_os.client_onboarding.onboarding_engine import (
    OnboardingEngine,
    OnboardingWorkflowActions,
)
from bbi_os.client_onboarding.registry import (
    default_onboarding_registry,
    install_default_onboarding_templates,
)
from bbi_os.client_onboarding.router import OnboardingRouter
from bbi_os.client_onboarding.service import OnboardingService
from bbi_os.entity_repository import EntityRepositoryRouter, JsonEntityRepository
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.integrations.models import ConnectorDefinition
from bbi_os.integrations.outbound import OutboundRequestEngine, TransportResponse
from bbi_os.integrations.registry import IntegrationRegistry
from bbi_os.integrations.workflow import IntegrationWorkflowEngine
from bbi_os.observability import Observability, set_observability
from bbi_os.task_management.api import TaskRequestHandler
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService
from bbi_os.workflows.actions import TaskWorkflowActions
from bbi_os.workflows.engine import WorkflowActionRegistry
from bbi_os.workflows.repository import WorkflowRepository
from bbi_os.workflows.templates import (
    WorkflowTemplateRepository,
    WorkflowTemplateService,
)


class SetupTransport:
    def __init__(self) -> None:
        self.fail = False
        self.calls: List[Dict[str, Any]] = []

    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout_seconds: float,
    ) -> TransportResponse:
        self.calls.append({"method": method, "url": url, "body": body})
        if self.fail:
            return TransportResponse(503, b'{"error":"unavailable"}')
        return TransportResponse(200, b'{"account_id":"crm-1"}')


class ClientOnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))
        self.task_service = TaskService(JsonTaskRepository(root / "tasks.json"))
        self.client_repository = JsonEntityRepository(
            "client", root / "clients.json"
        )
        self.onboarding_repository = JsonEntityRepository(
            "onboarding", root / "onboarding.json"
        )
        repositories = EntityRepositoryRouter()
        repositories.register(self.client_repository)
        repositories.register(self.onboarding_repository)
        integration_registry = IntegrationRegistry(root / "integrations.json")
        integration_registry.create_connector(
            ConnectorDefinition(
                connector_id="crm",
                name="CRM",
                type="http_api",
                base_url="https://crm.example.test/v1",
                auth_method="none",
                request_schema={"type": "object"},
                response_schema={"type": "object"},
            )
        )
        self.transport = SetupTransport()
        outbound = OutboundRequestEngine(
            integration_registry, self.transport, max_retries=0
        )
        actions = WorkflowActionRegistry()
        actions.register(
            "entity_operation", "tasks", TaskWorkflowActions(self.task_service)
        )
        actions.register(
            "entity_operation",
            "onboarding",
            OnboardingWorkflowActions(repositories, outbound),
        )
        self.workflow_repository = WorkflowRepository(
            root / "workflows.json", root / "instances.json"
        )
        engine = IntegrationWorkflowEngine(self.workflow_repository, actions)
        templates = WorkflowTemplateService(
            WorkflowTemplateRepository(root / "templates.json", root / "lineage.json"),
            engine,
        )
        install_default_onboarding_templates(templates)
        service = OnboardingService(
            OnboardingRouter(default_onboarding_registry()),
            OnboardingEngine(templates),
        )
        self.api = OnboardingApiHandler(service)
        self.authenticator = Authenticator(
            {"user-token": UserIdentity("user-1", "operator", "user", "start")}
        )
        self.routes = EntityRouteRegistry()
        self.routes.register("tasks", "tasks")
        self.routes.register("client", self.api)
        self.responses: List[Tuple[int, Dict[str, Any]]] = []

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def call(
        self, body: Dict[str, Any], token: str = "user-token"
    ) -> Tuple[int, Dict[str, Any]]:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = "/v1/client/onboarding"
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

    @staticmethod
    def request(
        request_type: str = "basic_onboarding", payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "user_id": "user-1",
            "client_name": "Acme Corporation",
            "request_type": request_type,
            "payload": payload or {},
        }

    def records(self) -> List[Dict[str, Any]]:
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_valid_onboarding_executes_complete_flow(self) -> None:
        status, response = self.call(self.request())
        self.assertEqual(201, status)
        data = response["data"]
        self.assertEqual("completed", data["status"])
        self.assertTrue(data["client_entity_id"])
        self.assertTrue(data["onboarding_entity_id"])
        self.assertTrue(data["task_id"])
        self.assertEqual("skipped", data["output"]["external_setup"])
        self.assertEqual(
            data["workflow_instance_id"],
            response["execution_summary"]["workflow_instance_id"],
        )
        self.assertEqual(
            [
                "validate_client",
                "create_client",
                "assign_role",
                "create_task",
                "external_setup",
                "complete",
            ],
            response["execution_summary"]["steps_completed"],
        )

    def test_invalid_request_type_returns_error(self) -> None:
        status, response = self.call(self.request("unknown"))
        self.assertEqual(400, status)
        self.assertEqual(
            "INVALID_ONBOARDING_TYPE", response["data"]["error"]["code"]
        )

    def test_authentication_failure_blocks_onboarding(self) -> None:
        status, response = self.call(self.request(), token="invalid")
        self.assertEqual(401, status)
        self.assertEqual("INVALID_TOKEN", response["data"]["error"]["code"])
        self.assertEqual([], self.client_repository.list())

    def test_workflow_executes_six_steps_in_order(self) -> None:
        _, response = self.call(self.request())
        instance = self.workflow_repository.get_instance(
            response["data"]["workflow_instance_id"]
        )
        self.assertEqual(
            [
                "validate_client",
                "create_client",
                "assign_role",
                "create_task",
                "external_setup",
                "complete",
            ],
            [step.step_id for step in instance.step_history],
        )
        self.assertTrue(all(step.status == "completed" for step in instance.step_history))

    def test_entities_are_created_and_linked_to_workflow(self) -> None:
        _, response = self.call(self.request())
        data = response["data"]
        client = self.client_repository.get(data["client_entity_id"])
        onboarding = self.onboarding_repository.get(data["onboarding_entity_id"])
        self.assertEqual("Acme Corporation", client.metadata["client_name"])
        self.assertEqual("user-1", client.metadata["assigned_user_id"])
        self.assertEqual("user", client.metadata["assigned_role"])
        self.assertEqual("complete", client.metadata["onboarding_status"])
        self.assertEqual(data["client_entity_id"], onboarding.metadata["client_entity_id"])
        self.assertEqual(
            data["workflow_instance_id"], onboarding.metadata["workflow_instance_id"]
        )
        self.assertEqual(data["task_id"], onboarding.metadata["task_id"])

    def test_observability_has_end_to_end_onboarding_trace(self) -> None:
        _, response = self.call(self.request())
        event = next(
            record
            for record in self.records()
            if record["event"] == "client_onboarding_completed"
        )
        data = response["data"]
        self.assertTrue(event["metadata"]["onboarding_request_id"])
        self.assertEqual("user-1", event["user_id"])
        self.assertTrue(event["request_id"])
        self.assertEqual(data["workflow_template_id"], event["metadata"]["workflow_id"])
        self.assertEqual(data["workflow_instance_id"], event["metadata"]["workflow_instance_id"])
        self.assertEqual(data["client_entity_id"], event["metadata"]["entity_id"])
        self.assertEqual("completed", event["metadata"]["status"])
        self.assertGreaterEqual(event["metadata"]["duration_ms"], 0)

    def test_connector_failure_fails_and_compensates_entities(self) -> None:
        self.transport.fail = True
        status, response = self.call(
            self.request(payload={"external_connector_id": "crm"})
        )
        self.assertEqual(422, status)
        self.assertEqual(
            "ONBOARDING_EXECUTION_FAILED", response["data"]["error"]["code"]
        )
        self.assertEqual([], self.client_repository.list())
        self.assertEqual([], self.onboarding_repository.list())
        self.assertEqual([], self.task_service.list())


if __name__ == "__main__":
    unittest.main()
