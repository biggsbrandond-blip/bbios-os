import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.observability import Observability, set_observability
from bbi_os.task_management.api import TaskRequestHandler
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        data_file = Path(self.temporary_directory.name) / "tasks.json"
        self.service = TaskService(JsonTaskRepository(data_file))
        created_at = "2026-07-02T00:00:00Z"
        self.users = {
            "admin-token": UserIdentity("admin-id", "admin", "admin", created_at),
            "user-token": UserIdentity("user-id", "member", "user", created_at),
            "readonly-token": UserIdentity(
                "readonly-id", "viewer", "readonly", created_at
            ),
        }
        self.authenticator = Authenticator(self.users)
        self.responses: List[Tuple[int, Dict[str, Any]]] = []
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def handler(
        self, method: str, path: str, token: str = "", body: Dict[str, Any] = None
    ) -> TaskRequestHandler:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = path
        handler.command = method
        handler.service = self.service
        handler.authenticator = self.authenticator
        handler.headers = {"Authorization": f"Bearer {token}"} if token else {}
        handler._body = lambda: body

        def respond(status: int, response_body: Dict[str, Any]) -> None:
            handler._response_status = status
            self.responses.append((status, response_body))

        handler._respond = respond
        return handler

    def call(
        self, method: str, path: str, token: str = "", body: Dict[str, Any] = None
    ) -> Tuple[int, Dict[str, Any]]:
        handler = self.handler(method, path, token, body)
        getattr(handler, f"do_{method}")()
        return self.responses[-1]

    def create_task(self, token: str = "admin-token") -> Dict[str, Any]:
        return self.call(
            "POST",
            "/v1/tasks",
            token,
            {"title": "Secured", "description": "RBAC task", "status": "pending"},
        )[1]["data"]

    def records(self) -> List[Dict[str, Any]]:
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_admin_has_full_access(self) -> None:
        task = self.create_task()
        self.assertEqual(200, self.call("GET", f"/v1/tasks/{task['id']}", "admin-token")[0])
        self.assertEqual(
            200,
            self.call(
                "PATCH", f"/v1/tasks/{task['id']}", "admin-token", {"status": "complete"}
            )[0],
        )
        self.assertEqual(
            200, self.call("DELETE", f"/v1/tasks/{task['id']}", "admin-token")[0]
        )

    def test_user_can_create_read_and_update_but_not_delete(self) -> None:
        task = self.create_task("user-token")
        self.assertEqual(200, self.call("GET", f"/v1/tasks/{task['id']}", "user-token")[0])
        self.assertEqual(
            200,
            self.call(
                "PATCH", f"/v1/tasks/{task['id']}", "user-token", {"status": "complete"}
            )[0],
        )
        status, body = self.call("DELETE", f"/v1/tasks/{task['id']}", "user-token")
        self.assertEqual(403, status)
        self.assertEqual("FORBIDDEN", body["data"]["error"]["code"])

    def test_readonly_can_read_but_authenticated_write_is_forbidden(self) -> None:
        self.assertEqual(200, self.call("GET", "/v1/tasks", "readonly-token")[0])
        status, body = self.call(
            "POST",
            "/v1/tasks",
            "readonly-token",
            {"title": "No", "description": "Denied", "status": "pending"},
        )
        self.assertEqual(403, status)
        self.assertEqual("FORBIDDEN", body["data"]["error"]["code"])

    def test_anonymous_read_is_allowed_but_write_requires_authentication(self) -> None:
        self.assertEqual(200, self.call("GET", "/v1/tasks")[0])
        status, body = self.call(
            "POST",
            "/v1/tasks",
            body={"title": "No", "description": "Denied", "status": "pending"},
        )
        self.assertEqual(401, status)
        self.assertEqual("UNAUTHORIZED", body["data"]["error"]["code"])
        self.assertEqual("Authentication required", body["data"]["error"]["message"])

    def test_unknown_token_is_rejected(self) -> None:
        status, body = self.call("GET", "/v1/tasks", "unknown-token")
        self.assertEqual(401, status)
        self.assertEqual("INVALID_TOKEN", body["data"]["error"]["code"])

    def test_observability_contains_authenticated_user_context(self) -> None:
        self.create_task("user-token")
        records = self.records()
        self.assertTrue(records)
        for record in records:
            self.assertEqual("user-id", record["user_id"])
            self.assertEqual("user", record["role"])
            self.assertTrue(record["request_id"])


if __name__ == "__main__":
    unittest.main()
