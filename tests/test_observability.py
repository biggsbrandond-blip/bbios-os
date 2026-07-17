import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import UUID

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.observability import Observability, set_observability
from bbi_os.task_management.api import TaskRequestHandler
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class ObservabilityTests(unittest.TestCase):
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
        self.stream = io.StringIO()
        self.observer = Observability(self.stream)
        self.previous_observer = set_observability(self.observer)
        self.responses: List[Tuple[int, Dict[str, Any]]] = []

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def handler(self, path: str) -> TaskRequestHandler:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = path
        handler.service = self.service
        handler.authenticator = self.authenticator
        handler.headers = {"Authorization": "Bearer admin-test-token"}

        def respond(status: int, body: Dict[str, Any]) -> None:
            handler._response_status = status
            self.responses.append((status, body))

        handler._respond = respond
        return handler

    def records(self) -> List[Dict[str, Any]]:
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_request_id_is_generated_and_propagated_through_all_layers(self) -> None:
        handler = self.handler("/v1/tasks")
        handler._body = lambda: {
            "title": "Observable task",
            "description": "Trace this request",
            "status": "pending",
        }
        handler.do_POST()

        records = self.records()
        request_ids = {record["request_id"] for record in records}
        self.assertEqual(1, len(request_ids))
        request_id = request_ids.pop()
        self.assertEqual(str(UUID(request_id)), request_id)
        self.assertIn("request_started", {record["event"] for record in records})
        self.assertIn("repository_task_saved", {record["event"] for record in records})
        self.assertIn("task_created", {record["event"] for record in records})
        self.assertIn("request_completed", {record["event"] for record in records})

    def test_task_events_contain_entity_and_request_correlation(self) -> None:
        create = self.handler("/v1/tasks")
        create._body = lambda: {
            "title": "Event task",
            "description": "Track events",
            "status": "pending",
        }
        create.do_POST()
        task_id = self.responses[-1][1]["data"]["id"]
        self.handler(f"/v1/tasks/{task_id}").do_GET()
        update = self.handler(f"/v1/tasks/{task_id}")
        update._body = lambda: {"status": "complete"}
        update.do_PATCH()
        self.handler(f"/v1/tasks/{task_id}").do_DELETE()

        events = {
            record["event"]: record
            for record in self.records()
            if record["event"].startswith("task_")
        }
        self.assertEqual(
            {"task_created", "task_retrieved", "task_updated", "task_deleted"},
            set(events),
        )
        for event_type, record in events.items():
            self.assertEqual(event_type, record["metadata"]["event_type"])
            self.assertEqual(task_id, record["metadata"]["entity_id"])
            self.assertTrue(record["timestamp"])
            self.assertTrue(record["request_id"])
            self.assertEqual("admin-test", record["user_id"])
            self.assertEqual("admin", record["role"])

    def test_error_log_is_traceable_without_changing_api_error(self) -> None:
        self.handler("/v1/tasks/missing").do_GET()

        error = next(record for record in self.records() if record["event"] == "request_error")
        self.assertEqual("ERROR", error["level"])
        self.assertEqual("TASK_NOT_FOUND", error["metadata"]["error_code"])
        self.assertEqual("Task not found", error["metadata"]["error_message"])
        self.assertTrue(error["metadata"]["error_timestamp"])
        self.assertTrue(error["metadata"]["context"])
        self.assertTrue(error["request_id"])
        self.assertEqual(
            "TASK_NOT_FOUND", self.responses[-1][1]["data"]["error"]["code"]
        )

    def test_completion_log_and_metrics_include_performance_timing(self) -> None:
        self.handler("/v1/tasks").do_GET()

        completion = next(
            record for record in self.records() if record["event"] == "request_completed"
        )
        metadata = completion["metadata"]
        self.assertGreaterEqual(metadata["duration_ms"], 0)
        self.assertGreaterEqual(metadata["average_duration_ms"], 0)
        self.assertTrue(metadata["started_at"])
        self.assertTrue(metadata["ended_at"])
        snapshot = self.observer.metrics.snapshot()
        self.assertEqual(1, snapshot["/v1/tasks"]["request_count"])

    def test_slow_request_emits_warning(self) -> None:
        set_observability(Observability(self.stream, slow_request_ms=-1))
        self.handler("/v1/tasks").do_GET()
        warning = next(record for record in self.records() if record["event"] == "slow_request")
        self.assertEqual("WARNING", warning["level"])


if __name__ == "__main__":
    unittest.main()
