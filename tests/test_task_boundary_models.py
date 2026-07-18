import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

from bbi_os.api import v1
from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.observability import Observability, set_observability
from bbi_os.settings import reset_settings_cache
from bbi_os.task_management.errors import ValidationError
from bbi_os.task_management.models import TaskCreateRequest, TaskUpdateRequest
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class FakeRequest:
    def __init__(self, headers: Optional[Dict[str, str]] = None) -> None:
        self.headers = headers or {}


def response_body(response: Any) -> Dict[str, Any]:
    return json.loads(response.body.decode("utf-8"))


class TaskBoundaryModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        os.environ["BBIOS_DATA_DIR"] = str(self.root)
        os.environ["BBIOS_AUTH_TOKENS"] = json.dumps(
            {
                "admin-token": {
                    "user_id": "admin-1",
                    "username": "admin",
                    "role": "admin",
                    "created_at": "2026-07-02T00:00:00Z",
                }
            }
        )
        reset_settings_cache()
        v1._task_service.cache_clear()
        self.previous_observer = set_observability(Observability())
        self.authenticator = Authenticator(
            {
                "admin-token": UserIdentity(
                    "admin-1", "admin", "admin", "2026-07-02T00:00:00Z"
                )
            }
        )

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()
        os.environ.pop("BBIOS_DATA_DIR", None)
        os.environ.pop("BBIOS_AUTH_TOKENS", None)
        reset_settings_cache()
        v1._task_service.cache_clear()

    def test_task_create_request_accepts_valid_payload(self) -> None:
        request = TaskCreateRequest.from_dict(
            {"title": "Typed", "description": "Boundary", "status": "pending"}
        )

        self.assertEqual("Typed", request.title)
        self.assertEqual(
            {"title": "Typed", "description": "Boundary", "status": "pending"},
            request.to_dict(),
        )

    def test_task_create_request_preserves_missing_required_error(self) -> None:
        with self.assertRaisesRegex(
            ValidationError, "Missing field\\(s\\): description, status"
        ):
            TaskCreateRequest.from_dict({"title": "Typed"})

    def test_task_update_request_accepts_optional_fields(self) -> None:
        request = TaskUpdateRequest.from_dict({"status": "complete"})

        self.assertEqual({"status": "complete"}, request.to_dict())

    def test_task_update_request_preserves_empty_update_error(self) -> None:
        with self.assertRaisesRegex(ValidationError, "At least one field is required"):
            TaskUpdateRequest.from_dict({})

    def test_task_service_preserves_dict_create_and_update_callers(self) -> None:
        service = TaskService(JsonTaskRepository(self.root / "tasks.json"))

        created = service.create(
            {"title": "Dict", "description": "Existing callers", "status": "pending"}
        )
        updated = service.update(created["id"], {"status": "complete"})

        self.assertEqual("Dict", created["title"])
        self.assertEqual("complete", updated["status"])

    def test_typed_create_matches_legacy_dict_persistence_shape(self) -> None:
        data = {
            "title": "Equivalent",
            "description": "Same persisted record",
            "status": "pending",
        }
        expected = self._create_with_input("legacy.json", data)
        actual = self._create_with_input("typed.json", TaskCreateRequest.from_dict(data))

        self.assertEqual(expected, actual)
        self.assertEqual(
            expected,
            self._stored_record("typed.json", expected["id"]),
        )

    def test_typed_update_matches_legacy_dict_result_shape(self) -> None:
        base = {"title": "Update", "description": "Before", "status": "pending"}
        legacy = TaskService(JsonTaskRepository(self.root / "legacy-update.json"))
        typed = TaskService(JsonTaskRepository(self.root / "typed-update.json"))
        with patch("bbi_os.task_management.service.uuid4", return_value="task-1"), patch(
            "bbi_os.task_management.service._timestamp",
            side_effect=[
                "2026-07-18T00:00:00Z",
                "2026-07-18T00:00:00Z",
                "2026-07-18T00:00:00Z",
                "2026-07-18T00:00:00Z",
            ],
        ):
            legacy_created = legacy.create(base)
            typed_created = typed.create(TaskCreateRequest.from_dict(base))

        with patch(
            "bbi_os.task_management.service._timestamp",
            return_value="2026-07-18T00:01:00Z",
        ):
            legacy_updated = legacy.update(legacy_created["id"], {"status": "complete"})
            typed_updated = typed.update(
                typed_created["id"], TaskUpdateRequest.from_dict({"status": "complete"})
            )

        self.assertEqual(legacy_updated, typed_updated)

    def test_fastapi_adapter_still_returns_handler_envelope(self) -> None:
        service = TaskService(JsonTaskRepository(self.root / "adapter.json"))
        response = v1.create_task(
            FakeRequest({"Authorization": "Bearer admin-token"}),
            {"title": "Adapter", "description": "Envelope", "status": "pending"},
        )
        direct_status, direct_body = v1._dispatch_task(
            "POST",
            "/v1/tasks",
            {"Authorization": "Bearer admin-token"},
            {"title": "Adapter", "description": "Envelope", "status": "pending"},
            service=service,
            authenticator=self.authenticator,
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(201, direct_status)
        self.assertEqual(
            {"request_id", "status", "data", "execution_summary"},
            set(response_body(response)),
        )
        self.assertEqual("success", direct_body["status"])

    def _create_with_input(self, file_name: str, data: Any) -> Dict[str, Any]:
        service = TaskService(JsonTaskRepository(self.root / file_name))
        with patch("bbi_os.task_management.service.uuid4", return_value="task-1"), patch(
            "bbi_os.task_management.service._timestamp",
            return_value="2026-07-18T00:00:00Z",
        ):
            return service.create(data)

    def _stored_record(self, file_name: str, task_id: str) -> Dict[str, Any]:
        with (self.root / file_name).open(encoding="utf-8") as data_file:
            return json.load(data_file)[task_id]


if __name__ == "__main__":
    unittest.main()
