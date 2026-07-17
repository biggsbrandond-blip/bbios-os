import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.task_management.api import (
    TaskRequestHandler,
    error_response,
    success_response,
)
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class TaskApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        data_file = Path(self.temporary_directory.name) / "tasks.json"
        self.service = TaskService(JsonTaskRepository(data_file))
        self.authenticator = Authenticator(
            {
                "admin-test-token": UserIdentity(
                    "admin-test", "admin", "admin", "2026-07-02T00:00:00Z"
                )
            }
        )
        self.responses: List[Tuple[int, Dict[str, Any]]] = []

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def handler(self, path: str) -> TaskRequestHandler:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = path
        handler.service = self.service
        handler.authenticator = self.authenticator
        handler.headers = {"Authorization": "Bearer admin-test-token"}
        handler._respond = lambda status, body: self.responses.append((status, body))
        handler.log_error = lambda *args: None
        return handler

    def test_only_versioned_task_routes_are_recognized(self) -> None:
        self.assertEqual(("tasks", None), self.handler("/v1/tasks")._route())
        self.assertEqual(("tasks", "task-id"), self.handler("/v1/tasks/task-id")._route())
        self.assertIsNone(self.handler("/tasks")._route())
        self.assertIsNone(self.handler("/v2/tasks")._route())

    def test_crud_endpoints_return_consistent_success_envelopes(self) -> None:
        create = self.handler("/v1/tasks")
        create._body = lambda: {
            "title": "API task",
            "description": "Test the contract",
            "status": "pending",
        }
        create.do_POST()
        status, body = self.responses[-1]
        self.assertEqual(201, status)
        self.assertEqual(
            {"request_id", "status", "data", "execution_summary"}, set(body)
        )
        self.assertEqual("success", body["status"])
        self.assertTrue(body["request_id"])
        self.assertEqual(
            {
                "workflow_instance_id",
                "duration_ms",
                "steps_completed",
                "external_calls",
                "errors",
            },
            set(body["execution_summary"]),
        )
        task_id = body["data"]["id"]

        self.handler("/v1/tasks").do_GET()
        self.assertEqual([body["data"]], self.responses[-1][1]["data"])

        self.handler(f"/v1/tasks/{task_id}").do_GET()
        self.assertEqual(task_id, self.responses[-1][1]["data"]["id"])

        update = self.handler(f"/v1/tasks/{task_id}")
        update._body = lambda: {"status": "complete"}
        update.do_PATCH()
        self.assertEqual("complete", self.responses[-1][1]["data"]["status"])

        self.handler(f"/v1/tasks/{task_id}").do_DELETE()
        self.assertEqual(200, self.responses[-1][0])
        self.assertEqual("success", self.responses[-1][1]["status"])
        self.assertEqual({}, self.responses[-1][1]["data"])
        self.assertEqual([], self.service.list())

    def test_validation_and_not_found_errors_are_structured(self) -> None:
        create = self.handler("/v1/tasks")
        create._body = lambda: {"title": "Incomplete"}
        create.do_POST()
        status, body = self.responses[-1]
        self.assertEqual(400, status)
        self.assertEqual("failure", body["status"])
        self.assertEqual({"code", "message"}, set(body["data"]["error"]))
        self.assertEqual("VALIDATION_ERROR", body["data"]["error"]["code"])
        self.assertEqual(
            "VALIDATION_ERROR", body["execution_summary"]["errors"][0]["code"]
        )
        self.assertTrue(body["request_id"])

        self.handler("/v1/tasks/missing").do_GET()
        self.assertEqual(404, self.responses[-1][0])
        self.assertEqual(
            "TASK_NOT_FOUND", self.responses[-1][1]["data"]["error"]["code"]
        )

    def test_unknown_route_and_internal_error_do_not_leak_details(self) -> None:
        self.handler("/tasks").do_GET()
        self.assertEqual(404, self.responses[-1][0])
        self.assertEqual(
            "ROUTE_NOT_FOUND", self.responses[-1][1]["data"]["error"]["code"]
        )

        handler = self.handler("/v1/tasks")
        handler.service.list = lambda: (_ for _ in ()).throw(RuntimeError("secret detail"))
        handler.do_GET()
        self.assertEqual(500, self.responses[-1][0])
        self.assertEqual(
            "INTERNAL_ERROR", self.responses[-1][1]["data"]["error"]["code"]
        )


if __name__ == "__main__":
    unittest.main()
