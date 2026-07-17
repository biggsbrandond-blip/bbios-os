import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.observability import (
    Observability,
    begin_request,
    end_request,
    set_observability,
    set_request_identity,
)
from bbi_os.task_management.api import TaskRequestHandler
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService
from bbi_os.workflows.api import WorkflowApiHandler
from bbi_os.workflows.engine import ActionResult, WorkflowActionRegistry, WorkflowEngine
from bbi_os.workflows.repository import WorkflowRepository


class MemoryAction:
    def __init__(self, name: str, order: List[str], fail: bool = False) -> None:
        self.name = name
        self.order = order
        self.fail = fail
        self.entities: Dict[str, Dict[str, Any]] = {}

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        self.order.append(self.name)
        if self.fail:
            raise RuntimeError("deliberate step failure")
        operation = inputs.get("operation", "echo")
        if operation == "create":
            entity_id = inputs["entity_id"]
            output = dict(inputs)
            self.entities[entity_id] = output
            return ActionResult(output, {"entity_id": entity_id})
        return ActionResult(dict(inputs))

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        self.order.append(f"rollback:{self.name}")
        self.entities.pop(rollback_data["entity_id"], None)


def definition(steps: List[Dict[str, Any]], workflow_id: str = "workflow-1") -> Dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "name": "Test workflow",
        "description": "Exercise orchestration",
        "trigger_type": "manual",
        "steps": steps,
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
    }


class WorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.repository = WorkflowRepository(
            self.root / "definitions.json", self.root / "instances.json"
        )
        self.actions = WorkflowActionRegistry()
        self.engine = WorkflowEngine(self.repository, self.actions)
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def test_workflow_creation_and_ordered_output_passing(self) -> None:
        order: List[str] = []
        first = MemoryAction("tasks", order)
        second = MemoryAction("users", order)
        self.actions.register("entity_operation", "tasks", first)
        self.actions.register("entity_operation", "users", second)
        self.engine.create_definition(
            definition(
                [
                    {
                        "step_id": "create_task",
                        "step_name": "Create task",
                        "action_type": "entity_operation",
                        "target_entity": "tasks",
                        "input_mapping": {
                            "operation": "create",
                            "entity_id": "$input.task_id",
                        },
                        "output_mapping": {"task_id": "$result.entity_id"},
                    },
                    {
                        "step_id": "read_user",
                        "step_name": "Read user",
                        "action_type": "entity_operation",
                        "target_entity": "users",
                        "input_mapping": {
                            "operation": "echo",
                            "task_id": "$steps.create_task.entity_id",
                            "user_id": "$input.user_id",
                        },
                        "output_mapping": {"user_id": "$result.user_id"},
                    },
                ]
            )
        )

        instance = self.engine.trigger(
            "workflow-1", {"task_id": "task-1", "user_id": "user-1"}
        )
        self.assertEqual("completed", instance.execution_status)
        self.assertEqual(["tasks", "users"], order)
        self.assertEqual({"task_id": "task-1", "user_id": "user-1"}, instance.output_data)
        self.assertEqual(["completed", "completed"], [step.status for step in instance.step_history])

    def test_failure_halts_and_rolls_back_completed_reversible_steps(self) -> None:
        order: List[str] = []
        creator = MemoryAction("creator", order)
        failure = MemoryAction("failure", order, fail=True)
        self.actions.register("entity_operation", "tasks", creator)
        self.actions.register("function_call", "failure", failure)
        self.engine.create_definition(
            definition(
                [
                    {
                        "step_id": "create",
                        "step_name": "Create",
                        "action_type": "entity_operation",
                        "target_entity": "tasks",
                        "input_mapping": {"operation": "create", "entity_id": "task-1"},
                    },
                    {
                        "step_id": "fail",
                        "step_name": "Fail",
                        "action_type": "function_call",
                        "target_entity": "failure",
                    },
                ]
            )
        )

        instance = self.engine.trigger("workflow-1", {})
        self.assertEqual("failed", instance.execution_status)
        self.assertEqual(["creator", "failure", "rollback:creator"], order)
        self.assertEqual({}, creator.entities)
        self.assertEqual(["rolled_back", "failed"], [step.status for step in instance.step_history])

    def test_failed_instance_can_retry_from_clean_state(self) -> None:
        order: List[str] = []
        action = MemoryAction("retryable", order, fail=True)
        self.actions.register("function_call", "retryable", action)
        self.engine.create_definition(
            definition(
                [
                    {
                        "step_id": "retry",
                        "step_name": "Retry",
                        "action_type": "function_call",
                        "target_entity": "retryable",
                    }
                ]
            )
        )
        failed = self.engine.trigger("workflow-1", {})
        action.fail = False
        completed = self.engine.retry(failed.workflow_instance_id)
        self.assertEqual("completed", completed.execution_status)
        self.assertEqual(1, len(completed.step_history))

    def test_workflow_state_survives_repository_restart(self) -> None:
        action = MemoryAction("task", [])
        self.actions.register("entity_operation", "tasks", action)
        self.engine.create_definition(
            definition(
                [
                    {
                        "step_id": "one",
                        "step_name": "One",
                        "action_type": "entity_operation",
                        "target_entity": "tasks",
                        "input_mapping": {"value": "$input.value"},
                    }
                ]
            )
        )
        instance = self.engine.trigger("workflow-1", {"value": "persisted"})
        restarted = WorkflowRepository(
            self.root / "definitions.json", self.root / "instances.json"
        )
        loaded = restarted.get_instance(instance.workflow_instance_id)
        self.assertEqual(instance.to_dict(), loaded.to_dict())

    def test_observability_tracks_every_step_with_execution_context(self) -> None:
        self.actions.register("entity_operation", "tasks", MemoryAction("task", []))
        self.engine.create_definition(
            definition(
                [
                    {
                        "step_id": "observed",
                        "step_name": "Observed",
                        "action_type": "entity_operation",
                        "target_entity": "tasks",
                    }
                ]
            )
        )
        token = begin_request("2026-07-02T00:00:00Z")
        set_request_identity("user-1", "user")
        try:
            instance = self.engine.trigger("workflow-1", {})
        finally:
            end_request(token)
        records = [json.loads(line) for line in self.stream.getvalue().splitlines()]
        step_records = [record for record in records if "workflow_step_" in record["event"]]
        self.assertEqual(2, len(step_records))
        for record in step_records:
            metadata = record["metadata"]
            self.assertEqual("workflow-1", metadata["workflow_id"])
            self.assertEqual(instance.workflow_instance_id, metadata["workflow_instance_id"])
            self.assertEqual("observed", metadata["step_id"])
            self.assertTrue(metadata["execution_status"])
            self.assertEqual("user-1", record["user_id"])
            self.assertTrue(record["request_id"])


class WorkflowApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.repository = WorkflowRepository(root / "definitions.json", root / "instances.json")
        actions = WorkflowActionRegistry()
        actions.register("entity_operation", "tasks", MemoryAction("tasks", []))
        self.engine = WorkflowEngine(self.repository, actions)
        self.service = TaskService(JsonTaskRepository(root / "tasks.json"))
        self.authenticator = Authenticator(
            {"admin-token": UserIdentity("admin-1", "admin", "admin", "start")}
        )
        self.routes = EntityRouteRegistry()
        self.routes.register("tasks", "tasks")
        self.routes.register("workflows", WorkflowApiHandler(self.engine, "definitions"))
        self.routes.register(
            "workflow-executions", WorkflowApiHandler(self.engine, "executions")
        )
        self.routes.register("workflow-history", WorkflowApiHandler(self.engine, "history"))
        self.responses: List[Tuple[int, Dict[str, Any]]] = []
        self.previous_observer = set_observability(Observability(io.StringIO()))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def call(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Dict[str, Any]]:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = path
        handler.command = method
        handler.service = self.service
        handler.authenticator = self.authenticator
        handler.route_registry = self.routes
        handler.headers = {"Authorization": "Bearer admin-token"}
        handler._body = lambda: body or {}

        def respond(status: int, response: Dict[str, Any]) -> None:
            handler._response_status = status
            self.responses.append((status, response))

        handler._respond = respond
        getattr(handler, f"do_{method}")()
        return self.responses[-1]

    def test_definition_trigger_status_and_history_endpoints(self) -> None:
        workflow = definition(
            [
                {
                    "step_id": "api-step",
                    "step_name": "API step",
                    "action_type": "entity_operation",
                    "target_entity": "tasks",
                    "input_mapping": {"value": "$input.value"},
                    "output_mapping": {"value": "$result.value"},
                }
            ]
        )
        self.assertEqual(201, self.call("POST", "/v1/workflows", workflow)[0])
        status, response = self.call(
            "POST",
            "/v1/workflow-executions",
            {"workflow_id": "workflow-1", "input": {"value": "done"}},
        )
        self.assertEqual(201, status)
        instance_id = response["data"]["workflow_instance_id"]
        self.assertEqual(
            "completed",
            self.call("GET", f"/v1/workflow-executions/{instance_id}")[1]["data"][
                "execution_status"
            ],
        )
        history = self.call("GET", f"/v1/workflow-history/{instance_id}")[1]["data"]
        self.assertEqual(["api-step"], [step["step_id"] for step in history])

    def test_invalid_definition_uses_standard_error_contract(self) -> None:
        status, body = self.call("POST", "/v1/workflows", {"name": "invalid"})
        self.assertEqual(400, status)
        self.assertEqual("failure", body["status"])
        self.assertEqual(
            "INVALID_WORKFLOW_DEFINITION", body["data"]["error"]["code"]
        )


if __name__ == "__main__":
    unittest.main()
