import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.domain import BaseEntity, TaskEntity, UserEntity
from bbi_os.entity_repository import EntityRepositoryRouter, JsonEntityRepository
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.observability import (
    Observability,
    begin_request,
    end_request,
    set_observability,
    set_request_identity,
)
from bbi_os.task_management.api import TaskRequestHandler, success_response
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class RecordingEntityHandler:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, Optional[str]]] = []

    def handle(
        self, method: str, entity_id: Optional[str], request: TaskRequestHandler
    ) -> None:
        self.calls.append((method, entity_id))
        request._respond(
            200,
            success_response(
                {"entity_type": "users", "entity_id": entity_id},
                "Entity routed",
            ),
        )


class DomainLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def test_task_entity_preserves_existing_task_schema(self) -> None:
        task = {
            "id": "task-1",
            "title": "Existing task",
            "description": "No schema migration",
            "status": "pending",
            "created_at": "2026-07-02T00:00:00Z",
            "updated_at": "2026-07-02T00:00:00Z",
        }
        entity = TaskEntity.from_task(task)
        self.assertIsInstance(entity, BaseEntity)
        self.assertEqual("task", entity.entity_type)
        self.assertEqual(task, entity.to_task())

    def test_user_identity_has_domain_entity_representation(self) -> None:
        identity = UserIdentity(
            "user-1", "operator", "user", "2026-07-02T00:00:00Z"
        )
        entity = UserEntity.from_identity(identity)
        self.assertEqual("user", entity.entity_type)
        self.assertEqual(identity, entity.to_identity())

    def test_repository_router_keeps_entity_types_isolated(self) -> None:
        tasks = JsonEntityRepository("task", self.root / "entities" / "tasks.json")
        users = JsonEntityRepository("user", self.root / "entities" / "users.json")
        router = EntityRepositoryRouter()
        router.register(tasks)
        router.register(users)
        task = BaseEntity("shared-id", "task", "start", "start", {"title": "Task"})
        user = BaseEntity("shared-id", "user", "start", "start", {"username": "User"})

        router.repository_for("task").save(task)
        router.repository_for("user").save(user)

        self.assertEqual(task, router.repository_for("task").get("shared-id"))
        self.assertEqual(user, router.repository_for("user").get("shared-id"))
        with self.assertRaises(ValueError):
            router.repository_for("task").save(user)
        self.assertNotEqual(tasks.path, users.path)

    def test_route_registry_resolves_correct_entity_handler(self) -> None:
        task_handler = object()
        user_handler = object()
        registry = EntityRouteRegistry()
        registry.register("tasks", task_handler)
        registry.register("users", user_handler)

        task_route = registry.resolve("/v1/tasks/task-1")
        user_route = registry.resolve("/v1/users/user-1")
        self.assertIs(task_handler, task_route.handler)
        self.assertEqual("task-1", task_route.entity_id)
        self.assertIs(user_handler, user_route.handler)
        self.assertEqual("user-1", user_route.entity_id)
        self.assertIsNone(registry.resolve("/v1/projects"))

    def test_registered_entity_handler_inherits_auth_boundary(self) -> None:
        entity_handler = RecordingEntityHandler()
        registry = EntityRouteRegistry()
        registry.register("tasks", "tasks")
        registry.register("users", entity_handler)
        service = TaskService(JsonTaskRepository(self.root / "tasks.json"))
        responses: List[Tuple[int, Dict[str, Any]]] = []

        def request(method: str, token: str = "") -> Tuple[int, Dict[str, Any]]:
            handler = TaskRequestHandler.__new__(TaskRequestHandler)
            handler.path = "/v1/users/user-1"
            handler.command = method
            handler.service = service
            handler.route_registry = registry
            handler.authenticator = Authenticator()
            handler.headers = {"Authorization": f"Bearer {token}"} if token else {}

            def respond(status: int, body: Dict[str, Any]) -> None:
                handler._response_status = status
                responses.append((status, body))

            handler._respond = respond
            getattr(handler, f"do_{method}")()
            return responses[-1]

        self.assertEqual(200, request("GET")[0])
        self.assertEqual([("GET", "user-1")], entity_handler.calls)
        status, body = request("POST")
        self.assertEqual(401, status)
        self.assertEqual("UNAUTHORIZED", body["data"]["error"]["code"])
        self.assertEqual(1, len(entity_handler.calls))

    def test_generic_entity_events_include_full_trace_context(self) -> None:
        repository = JsonEntityRepository("project", self.root / "projects.json")
        entity = BaseEntity("project-1", "project", "start", "start", {})
        token = begin_request("2026-07-02T00:00:00Z")
        set_request_identity("admin-1", "admin")
        try:
            repository.save(entity)
            repository.get(entity.entity_id)
            repository.delete(entity.entity_id)
        finally:
            end_request(token)

        records = [json.loads(line) for line in self.stream.getvalue().splitlines()]
        self.assertEqual(
            {"entity_created", "entity_retrieved", "entity_deleted"},
            {record["event"] for record in records},
        )
        for record in records:
            self.assertEqual("project", record["metadata"]["entity_type"])
            self.assertEqual("project-1", record["metadata"]["entity_id"])
            self.assertEqual(record["event"], record["metadata"]["event_type"])
            self.assertEqual("admin-1", record["user_id"])
            self.assertEqual("admin", record["role"])
            self.assertTrue(record["request_id"])


if __name__ == "__main__":
    unittest.main()
