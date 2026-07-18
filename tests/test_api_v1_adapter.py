import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

from fastapi.routing import APIRoute

from bbi_os.api import v1
from bbi_os.app import create_app
from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.cockpit.client_management import ClientManagementApiHandler
from bbi_os.observability import Observability, set_observability
from bbi_os.settings import reset_settings_cache
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


EXPECTED_CUSTOM_ROUTES = {
    ("GET", "/"),
    ("GET", "/health"),
    ("POST", "/cockpit/create-client"),
    ("GET", "/cockpit/client/{client_id}"),
    ("GET", "/cockpit/clients/search"),
    ("POST", "/cockpit/test-pipeline"),
    ("GET", "/v1/tasks"),
    ("POST", "/v1/tasks"),
    ("GET", "/v1/tasks/{task_id}"),
    ("PATCH", "/v1/tasks/{task_id}"),
    ("DELETE", "/v1/tasks/{task_id}"),
    ("GET", "/clients"),
    ("POST", "/clients"),
    ("GET", "/v1/clients"),
    ("POST", "/v1/clients"),
}


class FakeRequest:
    def __init__(self, path: str = "/", headers: Optional[Dict[str, str]] = None) -> None:
        self.url = SimpleNamespace(path=path)
        self.headers = headers or {}


def response_body(response: Any) -> Dict[str, Any]:
    return json.loads(response.body.decode("utf-8"))


class V1AdapterTests(unittest.TestCase):
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
        v1._client_handler.cache_clear()
        self.previous_observer = set_observability(Observability())
        self.authenticator = Authenticator(
            {
                "admin-token": UserIdentity(
                    "admin-1", "admin", "admin", "2026-07-02T00:00:00Z"
                )
            }
        )
        self.task_service = TaskService(JsonTaskRepository(self.root / "tasks.json"))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()
        os.environ.pop("BBIOS_DATA_DIR", None)
        os.environ.pop("BBIOS_AUTH_TOKENS", None)
        reset_settings_cache()
        v1._task_service.cache_clear()
        v1._client_handler.cache_clear()

    def test_canonical_app_registers_v1_adapter_routes_once(self) -> None:
        app = create_app()
        custom_routes = {
            (method, route.path)
            for route in app.routes
            if isinstance(route, APIRoute)
            for method in route.methods
            if method not in {"HEAD", "OPTIONS"}
        }
        self.assertTrue(EXPECTED_CUSTOM_ROUTES.issubset(custom_routes))
        for expected in EXPECTED_CUSTOM_ROUTES:
            self.assertEqual(1, sum(1 for route in custom_routes if route == expected))

    def test_task_adapter_matches_handler_success_contract(self) -> None:
        headers = {"Authorization": "Bearer admin-token"}
        payload = {
            "title": "Adapter task",
            "description": "Preserve the handler contract",
            "status": "pending",
        }
        expected_status, expected_body = v1._dispatch_task(
            "POST",
            "/v1/tasks",
            headers,
            payload,
            service=self.task_service,
            authenticator=self.authenticator,
        )
        response = v1.create_task(FakeRequest(headers=headers), payload)
        self.assertEqual(expected_status, response.status_code)
        body = response_body(response)
        self.assertEqual(expected_body["status"], body["status"])
        self.assertEqual(expected_body["data"]["title"], body["data"]["title"])
        self.assertEqual(
            {"request_id", "status", "data", "execution_summary"},
            set(body),
        )

    def test_task_adapter_preserves_failure_status_and_body(self) -> None:
        response = v1.create_task(
            FakeRequest(headers={"Authorization": "Bearer admin-token"}),
            {"title": "Incomplete"},
        )
        body = response_body(response)
        self.assertEqual(400, response.status_code)
        self.assertEqual("failure", body["status"])
        self.assertEqual("VALIDATION_ERROR", body["data"]["error"]["code"])

    def test_task_adapter_exposes_crud_routes(self) -> None:
        headers = {"Authorization": "Bearer admin-token"}
        create = v1.create_task(
            FakeRequest(headers=headers),
            {
                "title": "CRUD task",
                "description": "Exercise every route",
                "status": "pending",
            },
        )
        task_id = response_body(create)["data"]["id"]

        listing = v1.list_tasks(FakeRequest(headers=headers))
        self.assertEqual(200, listing.status_code)
        self.assertEqual([task_id], [item["id"] for item in response_body(listing)["data"]])

        retrieved = v1.get_task(task_id, FakeRequest(headers=headers))
        self.assertEqual(200, retrieved.status_code)
        self.assertEqual(task_id, response_body(retrieved)["data"]["id"])

        updated = v1.update_task(
            task_id, FakeRequest(headers=headers), {"status": "complete"}
        )
        self.assertEqual(200, updated.status_code)
        self.assertEqual("complete", response_body(updated)["data"]["status"])

        deleted = v1.delete_task(task_id, FakeRequest(headers=headers))
        self.assertEqual(200, deleted.status_code)
        self.assertEqual({}, response_body(deleted)["data"])

        missing = v1.get_task(task_id, FakeRequest(headers=headers))
        self.assertEqual(404, missing.status_code)
        self.assertEqual("TASK_NOT_FOUND", response_body(missing)["data"]["error"]["code"])

    def test_task_adapter_delegates_to_handler_lifecycle(self) -> None:
        response = v1.create_task(
            FakeRequest(),
            {"title": "Denied", "description": "No token", "status": "pending"},
        )
        body = response_body(response)
        self.assertEqual(401, response.status_code)
        self.assertEqual("UNAUTHORIZED", body["data"]["error"]["code"])

    def test_clients_adapter_preserves_frontend_compatible_create_and_list(self) -> None:
        create = v1.create_client(
            FakeRequest("/clients"),
            {"name": "Pilot Client", "plan": "Pro"},
        )
        self.assertEqual(201, create.status_code)
        created_body = response_body(create)
        self.assertEqual("success", created_body["status"])
        self.assertEqual("Pilot Client", created_body["data"]["name"])

        listing = v1.list_clients(FakeRequest("/clients"))
        self.assertEqual(200, listing.status_code)
        self.assertEqual("Pilot Client", response_body(listing)["data"][0]["name"])

        versioned_listing = v1.list_clients(FakeRequest("/v1/clients"))
        self.assertEqual(200, versioned_listing.status_code)
        self.assertEqual("Pilot Client", response_body(versioned_listing)["data"][0]["name"])

    def test_clients_adapter_preserves_error_contract(self) -> None:
        response = v1.create_client(FakeRequest("/clients"), {"name": "", "plan": "Pro"})
        body = response_body(response)
        self.assertEqual(400, response.status_code)
        self.assertEqual("failure", body["status"])
        self.assertEqual("INVALID_CLIENT", body["data"]["error"]["code"])

        versioned = v1.create_client(
            FakeRequest("/v1/clients"), {"name": "Bad", "plan": "Unknown"}
        )
        self.assertEqual(400, versioned.status_code)
        self.assertEqual("INVALID_CLIENT", response_body(versioned)["data"]["error"]["code"])

    def test_clients_adapter_delegates_to_client_management_handler(self) -> None:
        class RecordingHandler:
            def __init__(self) -> None:
                self.calls = []

            def handle(self, method: str, entity_id: Any, request: Any) -> None:
                self.calls.append((method, entity_id, request._body()))
                request._respond(200, {"status": "success", "data": {"ok": True}})

        handler = RecordingHandler()
        status, body = v1._dispatch_handler(
            handler, "POST", "/clients", None, {}, {"name": "Tracked"}
        )
        self.assertEqual(200, status)
        self.assertEqual({"ok": True}, body["data"])
        self.assertEqual([("POST", None, {"name": "Tracked"})], handler.calls)

    def test_runtime_client_handler_uses_existing_handler_type(self) -> None:
        self.assertIsInstance(v1._runtime_client_handler(), ClientManagementApiHandler)


if __name__ == "__main__":
    unittest.main()
