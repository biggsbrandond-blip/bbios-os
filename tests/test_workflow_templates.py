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
from bbi_os.workflows.engine import ActionResult, WorkflowActionRegistry, WorkflowEngine
from bbi_os.workflows.repository import WorkflowRepository
from bbi_os.workflows.template_api import WorkflowTemplateApiHandler
from bbi_os.workflows.templates import (
    InvalidWorkflowTemplate,
    WorkflowTemplateRepository,
    WorkflowTemplateService,
)


class CapturingAction:
    def __init__(self) -> None:
        self.inputs: List[Dict[str, Any]] = []

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        self.inputs.append(dict(inputs))
        return ActionResult(dict(inputs))

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        return None


def template(version: str = "v1", title: str = "${title}") -> Dict[str, Any]:
    return {
        "template_id": "task-template",
        "name": "Reusable task",
        "description": "Parameterized task workflow",
        "version": version,
        "parameter_schema": {
            "required": ["title", "priority"],
            "properties": {
                "title": {"type": "string"},
                "priority": {"type": "integer"},
            },
        },
        "step_blueprint": [
            {
                "step_id": "create",
                "step_name": "Create task",
                "action_type": "entity_operation",
                "target_entity": "tasks",
                "input_mapping": {
                    "title": title,
                    "priority": "${priority}",
                    "label": "Task: ${title}",
                },
                "output_mapping": {"title": "$result.title"},
            }
        ],
    }


class WorkflowTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        workflow_repository = WorkflowRepository(
            self.root / "definitions.json", self.root / "instances.json"
        )
        self.action = CapturingAction()
        actions = WorkflowActionRegistry()
        actions.register("entity_operation", "tasks", self.action)
        self.engine = WorkflowEngine(workflow_repository, actions)
        self.repository = WorkflowTemplateRepository(
            self.root / "templates.json", self.root / "lineage.json"
        )
        self.service = WorkflowTemplateService(self.repository, self.engine)
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def test_template_creation_is_immutable_per_version(self) -> None:
        created = self.service.create(template())
        self.assertEqual("task-template", created.template_id)
        with self.assertRaises(InvalidWorkflowTemplate):
            self.service.create(template())
        self.assertEqual(1, len(self.service.list()))

    def test_parameters_are_injected_without_losing_native_types(self) -> None:
        self.service.create(template())
        instance, lineage = self.service.execute(
            "task-template", {"title": "Review", "priority": 3}
        )
        self.assertEqual("completed", instance.execution_status)
        self.assertEqual(
            {"title": "Review", "priority": 3, "label": "Task: Review"},
            self.action.inputs[-1],
        )
        self.assertEqual(3, self.action.inputs[-1]["priority"])
        self.assertEqual("v1", lineage["workflow_version"])

    def test_latest_and_explicit_older_versions_coexist(self) -> None:
        self.service.create(template("v1", "v1:${title}"))
        self.service.create(template("v2", "v2:${title}"))
        self.assertEqual("v2", self.service.get("task-template").version)
        self.assertEqual("v1", self.service.get("Reusable task", "v1").version)

        old_instance, old_lineage = self.service.execute(
            "task-template", {"title": "Old", "priority": 1}, version="v1"
        )
        new_instance, new_lineage = self.service.execute(
            "task-template", {"title": "New", "priority": 2}, version="v2"
        )
        self.assertEqual("completed", old_instance.execution_status)
        self.assertEqual("v1:Old", self.action.inputs[-2]["title"])
        self.assertEqual("v2:New", self.action.inputs[-1]["title"])
        self.assertEqual("v1", old_lineage["workflow_version"])
        self.assertEqual("v2", new_lineage["workflow_version"])

    def test_each_execution_clones_definition_and_preserves_template(self) -> None:
        created = self.service.create(template())
        first, first_lineage = self.service.execute(
            created.template_id, {"title": "One", "priority": 1}
        )
        second, second_lineage = self.service.execute(
            created.template_id, {"title": "Two", "priority": 2}
        )
        self.assertNotEqual(first.workflow_id, second.workflow_id)
        self.assertNotEqual(
            first_lineage["resolved_workflow_id"], second_lineage["resolved_workflow_id"]
        )
        self.assertEqual(template(), self.service.get(created.template_id, "v1").to_dict())

    def test_lineage_persists_and_observability_tracks_bindings(self) -> None:
        self.service.create(template())
        token = begin_request("2026-07-02T00:00:00Z")
        set_request_identity("user-1", "user")
        try:
            instance, lineage = self.service.execute(
                "task-template", {"title": "Trace", "priority": 5}
            )
        finally:
            end_request(token)
        self.assertEqual(lineage, self.repository.get_lineage(instance.workflow_instance_id))
        records = [json.loads(line) for line in self.stream.getvalue().splitlines()]
        event = next(
            record for record in records if record["event"] == "workflow_template_executed"
        )
        self.assertEqual("task-template", event["metadata"]["template_id"])
        self.assertEqual("v1", event["metadata"]["workflow_version"])
        self.assertEqual(instance.workflow_instance_id, event["metadata"]["workflow_instance_id"])
        self.assertEqual(
            {"title": "Trace", "priority": 5},
            event["metadata"]["parameter_bindings"],
        )
        self.assertEqual("user-1", event["user_id"])
        self.assertTrue(event["request_id"])


class WorkflowTemplateApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        action = CapturingAction()
        actions = WorkflowActionRegistry()
        actions.register("entity_operation", "tasks", action)
        engine = WorkflowEngine(
            WorkflowRepository(root / "definitions.json", root / "instances.json"),
            actions,
        )
        service = WorkflowTemplateService(
            WorkflowTemplateRepository(root / "templates.json", root / "lineage.json"),
            engine,
        )
        self.api = WorkflowTemplateApiHandler(service)
        self.task_service = TaskService(JsonTaskRepository(root / "tasks.json"))
        self.authenticator = Authenticator(
            {"admin-token": UserIdentity("admin-1", "admin", "admin", "start")}
        )
        self.routes = EntityRouteRegistry()
        self.routes.register("tasks", "tasks")
        self.routes.register("workflow-templates", self.api)
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
        handler.service = self.task_service
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

    def test_template_api_lifecycle_and_exact_execute_route(self) -> None:
        self.assertEqual(201, self.call("POST", "/v1/workflow-templates", template())[0])
        self.assertEqual(1, len(self.call("GET", "/v1/workflow-templates")[1]["data"]))
        self.assertEqual(
            "v1",
            self.call("GET", "/v1/workflow-templates/task-template?version=v1")[1][
                "data"
            ]["version"],
        )
        status, response = self.call(
            "POST",
            "/v1/workflow-templates/task-template/execute",
            {"version": "v1", "parameters": {"title": "API", "priority": 7}},
        )
        self.assertEqual(201, status)
        self.assertEqual("completed", response["data"]["execution_status"])
        self.assertEqual("v1", response["data"]["template_lineage"]["workflow_version"])


if __name__ == "__main__":
    unittest.main()
