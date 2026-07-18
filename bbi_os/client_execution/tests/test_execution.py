import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.client_execution.api import ClientExecutionApiHandler
from bbi_os.client_execution.engine import ClientExecutionEngine
from bbi_os.client_execution.errors import ConcurrentExecution
from bbi_os.client_execution.executor import ClientWorkflowExecutor
from bbi_os.client_execution.models import ClientExecutionRequest
from bbi_os.client_execution.registry import ExecutionTypeRegistry
from bbi_os.client_execution.router import ClientExecutionRouter
from bbi_os.client_execution.service import ClientExecutionService
from bbi_os.client_execution.state import ExecutionStateRepository
from bbi_os.domain import BaseEntity
from bbi_os.entity_repository import JsonEntityRepository
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.integrations.models import ConnectorDefinition
from bbi_os.integrations.outbound import (
    ConnectorWorkflowAction,
    OutboundRequestEngine,
    TransportResponse,
)
from bbi_os.integrations.registry import IntegrationRegistry
from bbi_os.integrations.workflow import IntegrationWorkflowEngine
from bbi_os.observability import Observability, set_observability, timestamp
from bbi_os.task_management.api import TaskRequestHandler
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService
from bbi_os.workflows.actions import TaskWorkflowActions
from bbi_os.workflows.engine import ActionResult, WorkflowActionRegistry
from bbi_os.workflows.repository import WorkflowRepository
from bbi_os.workflows.templates import (
    WorkflowTemplateRepository,
    WorkflowTemplateService,
)


class FailureAction:
    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        raise RuntimeError("deliberate workflow failure")

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        return None


class BlockingAction:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        self.started.set()
        self.release.wait(timeout=2)
        return ActionResult({"released": True})

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        return None


class FailingTransport:
    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout_seconds: float,
    ) -> TransportResponse:
        return TransportResponse(503, b'{"error":"unavailable"}')


class ClientExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))
        self.clients = JsonEntityRepository("client", root / "clients.json")
        now = timestamp()
        self.client = BaseEntity(
            "client-1",
            "client",
            now,
            now,
            {"client_name": "Acme", "onboarding_status": "complete"},
        )
        self.clients.save(self.client)
        self.task_service = TaskService(JsonTaskRepository(root / "tasks.json"))
        self.blocking = BlockingAction()
        actions = WorkflowActionRegistry()
        actions.register(
            "entity_operation", "tasks", TaskWorkflowActions(self.task_service)
        )
        actions.register("function_call", "failure", FailureAction())
        actions.register("function_call", "blocking", self.blocking)
        integration_registry = IntegrationRegistry(root / "integrations.json")
        integration_registry.create_connector(
            ConnectorDefinition(
                connector_id="failing",
                name="Failing connector",
                type="http_api",
                base_url="https://external.example.test/api",
                auth_method="none",
                request_schema={"type": "object"},
                response_schema={"type": "object"},
            )
        )
        outbound = OutboundRequestEngine(
            integration_registry, FailingTransport(), max_retries=0
        )
        actions.register("function_call", "connector", ConnectorWorkflowAction(outbound))
        workflow_engine = IntegrationWorkflowEngine(
            WorkflowRepository(root / "workflows.json", root / "workflow_instances.json"),
            actions,
        )
        templates = WorkflowTemplateService(
            WorkflowTemplateRepository(root / "templates.json", root / "lineage.json"),
            workflow_engine,
        )
        self._create_templates(templates)
        self.state = ExecutionStateRepository(root / "executions.json")
        self.engine = ClientExecutionEngine(
            ClientWorkflowExecutor(templates), self.state
        )
        self.service = ClientExecutionService(
            self.clients,
            ClientExecutionRouter(ExecutionTypeRegistry()),
            self.engine,
            self.state,
        )
        self.api = ClientExecutionApiHandler(self.service)
        self.authenticator = Authenticator(
            {"user-token": UserIdentity("user-1", "operator", "user", "start")}
        )
        self.routes = EntityRouteRegistry()
        self.routes.register("tasks", "tasks")
        self.routes.register("client", self.api)
        self.responses: List[Tuple[int, Dict[str, Any]]] = []

    def tearDown(self) -> None:
        self.blocking.release.set()
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def _create_templates(self, templates: WorkflowTemplateService) -> None:
        templates.create(self._template("happy", [self._task_step()]))
        templates.create(
            self._template(
                "workflow-failure",
                [
                    self._task_step(),
                    {
                        "step_id": "fail",
                        "step_name": "Fail",
                        "action_type": "function_call",
                        "target_entity": "failure",
                    },
                ],
            )
        )
        templates.create(
            self._template(
                "connector-failure",
                [
                    self._task_step(),
                    {
                        "step_id": "external",
                        "step_name": "External",
                        "action_type": "function_call",
                        "target_entity": "connector",
                        "input_mapping": {
                            "connector_id": "failing",
                            "method": "POST",
                            "path": "execute",
                            "body": {},
                        },
                    },
                ],
            )
        )
        templates.create(
            self._template(
                "blocking",
                [
                    {
                        "step_id": "block",
                        "step_name": "Block",
                        "action_type": "function_call",
                        "target_entity": "blocking",
                    }
                ],
            )
        )

    @staticmethod
    def _task_step() -> Dict[str, Any]:
        return {
            "step_id": "create_task",
            "step_name": "Create task",
            "action_type": "entity_operation",
            "target_entity": "tasks",
            "input_mapping": {
                "operation": "create",
                "title": "Execute ${client_id}",
                "description": "COS-002 execution",
                "status": "pending",
            },
            "output_mapping": {"task_id": "$result.id"},
        }

    @staticmethod
    def _template(template_id: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "template_id": template_id,
            "name": template_id,
            "description": "COS-002 test template",
            "version": "v1",
            "parameter_schema": {
                "required": ["client_id"],
                "properties": {"client_id": {"type": "string"}},
            },
            "step_blueprint": steps,
        }

    def request(
        self, workflow_id: str, execution_type: str = "one_time"
    ) -> Dict[str, Any]:
        return {
            "client_id": self.client.entity_id,
            "execution_type": execution_type,
            "workflow_id": workflow_id,
            "input": {},
        }

    def call(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = path
        handler.command = method
        handler.service = self.task_service
        handler.authenticator = self.authenticator
        handler.route_registry = self.routes
        handler.headers = {"Authorization": "Bearer user-token"}
        handler._body = lambda: body or {}

        def respond(status: int, response: Dict[str, Any]) -> None:
            handler._response_status = status
            self.responses.append((status, response))

        handler._respond = respond
        getattr(handler, f"do_{method}")()
        return self.responses[-1]

    def test_happy_path_execution_and_response_contract(self) -> None:
        status, response = self.call(
            "POST", "/v1/client/execute", self.request("happy")
        )
        self.assertEqual(201, status)
        self.assertEqual(
            {"request_id", "status", "data", "execution_summary"}, set(response)
        )
        self.assertEqual("success", response["status"])
        self.assertEqual("completed", response["data"]["status"])
        self.assertEqual("COMPLETED", response["data"]["execution_state"])
        self.assertEqual(
            response["data"]["workflow_instance_id"],
            response["execution_summary"]["workflow_instance_id"],
        )
        self.assertEqual(["create_task"], response["execution_summary"]["steps_completed"])

    def test_workflow_failure_records_compensation(self) -> None:
        status, response = self.call(
            "POST", "/v1/client/execute", self.request("workflow-failure")
        )
        self.assertEqual(422, status)
        execution = response["data"]
        self.assertEqual("FAILED", execution["execution_state"])
        self.assertEqual("fail", execution["failure_step"])
        self.assertEqual(["create_task"], execution["rollback_actions"])
        self.assertEqual([], self.task_service.list())
        self.assertTrue(response["execution_summary"]["errors"])

    def test_connector_failure_enters_waiting_and_compensation_states(self) -> None:
        _, response = self.call(
            "POST", "/v1/client/execute", self.request("connector-failure")
        )
        states = [item["state"] for item in response["data"]["transitions"]]
        self.assertEqual(
            ["PENDING", "RUNNING", "WAITING_EXTERNAL", "COMPENSATING", "FAILED"],
            states,
        )
        self.assertEqual("external", response["data"]["failure_step"])
        self.assertEqual(1, len(response["execution_summary"]["external_calls"]))

    def test_invalid_client_is_rejected(self) -> None:
        request = self.request("happy")
        request["client_id"] = "missing"
        status, response = self.call("POST", "/v1/client/execute", request)
        self.assertEqual(404, status)
        self.assertEqual("CLIENT_NOT_FOUND", response["data"]["error"]["code"])

    def test_concurrent_execution_for_same_client_is_rejected(self) -> None:
        request = ClientExecutionRequest.from_dict(self.request("blocking"))
        results: List[Any] = []

        def run() -> None:
            results.append(self.engine.execute(request))

        worker = threading.Thread(target=run)
        worker.start()
        self.assertTrue(self.blocking.started.wait(timeout=1))
        with self.assertRaises(ConcurrentExecution):
            self.engine.execute(request)
        self.blocking.release.set()
        worker.join(timeout=2)
        self.assertEqual("COMPLETED", results[0].state)

    def test_state_transitions_and_observability_are_complete(self) -> None:
        _, response = self.call(
            "POST", "/v1/client/execute", self.request("happy")
        )
        self.assertEqual(
            ["PENDING", "RUNNING", "COMPLETED"],
            [item["state"] for item in response["data"]["transitions"]],
        )
        records = [json.loads(line) for line in self.stream.getvalue().splitlines()]
        transitions = [
            item
            for item in records
            if item["event"] == "client_execution_state_changed"
        ]
        self.assertEqual(["RUNNING", "COMPLETED"], [item["metadata"]["execution_state"] for item in transitions])
        self.assertTrue(all(item["request_id"] for item in transitions))
        self.assertTrue(
            all(item["metadata"]["client_id"] == "client-1" for item in transitions)
        )

    def test_scheduled_execution_remains_pending_and_status_is_retrievable(self) -> None:
        status, scheduled = self.call(
            "POST",
            "/v1/client/schedule-execution",
            self.request("happy", "scheduled"),
        )
        self.assertEqual(201, status)
        self.assertEqual("PENDING", scheduled["data"]["execution_state"])
        status, retrieved = self.call(
            "GET", "/v1/client/execution-status/client-1"
        )
        self.assertEqual(200, status)
        self.assertEqual(
            scheduled["data"]["execution_id"], retrieved["data"]["execution_id"]
        )

    def test_state_repository_lists_all_execution_records(self) -> None:
        first = self.engine.schedule(
            ClientExecutionRequest.from_dict(self.request("happy", "scheduled"))
        )
        second = self.engine.schedule(
            ClientExecutionRequest.from_dict(self.request("happy", "recurring"))
        )

        records = self.state.list()

        self.assertEqual(
            {first.execution_id, second.execution_id},
            {record.execution_id for record in records},
        )
        self.assertTrue(all(hasattr(record, "to_dict") for record in records))


if __name__ == "__main__":
    unittest.main()
