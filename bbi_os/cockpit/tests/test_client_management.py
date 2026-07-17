import io
import tempfile
import unittest
from pathlib import Path

from bbi_os.client_monetization.registry import ClientPlanRegistry
from bbi_os.cockpit.client_management import (
    ClientManagementApiHandler,
    ClientManagementService,
    InvalidClient,
)
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.entity_repository import JsonEntityRepository
from bbi_os.observability import Observability, set_observability
from bbi_os.task_management.api import TaskRequestHandler


class FakeRequest:
    def __init__(self, body=None):
        self.body = body or {}
        self.response = None
        self.error = None

    def _body(self):
        return dict(self.body)

    def _respond(self, status, body):
        self.response = (status, body)

    def _log_error(self, code, message):
        self.error = (code, message)

    def _route_not_found(self):
        raise AssertionError("Unexpected route-not-found response")


class ClientManagementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.previous_observer = set_observability(Observability(io.StringIO()))
        self.service = self._service()

    def tearDown(self):
        set_observability(self.previous_observer)
        self.temporary.cleanup()

    def _service(self):
        return ClientManagementService(
            JsonEntityRepository("client", self.root / "clients.json"),
            ClientPlanRegistry(self.root / "plans.json"),
        )

    def test_create_returns_required_client_fields_and_unique_ids(self):
        first = self.service.create({"name": "Alpha", "plan": "Pro"})
        second = self.service.create({"name": "Beta", "plan": "Basic"})
        self.assertEqual({"id", "name", "plan", "created_at"}, set(first))
        self.assertEqual("Alpha", first["name"])
        self.assertEqual("Pro", first["plan"])
        self.assertNotEqual(first["id"], second["id"])

    def test_clients_persist_across_service_restart(self):
        created = self.service.create({"name": "Persistent Client", "plan": "Enterprise"})
        restarted = self._service()
        self.assertEqual([created], restarted.list())

    def test_empty_name_and_invalid_plan_are_rejected(self):
        with self.assertRaises(InvalidClient):
            self.service.create({"name": "  ", "plan": "Pro"})
        with self.assertRaises(InvalidClient):
            self.service.create({"name": "Alpha", "plan": "Unknown"})
        self.assertEqual([], self.service.list())

    def test_api_create_and_list_return_standard_response_contract(self):
        handler = ClientManagementApiHandler(self.service)
        create = FakeRequest({"name": "API Client", "plan": "Custom"})
        handler.handle("POST", None, create)
        self.assertEqual(201, create.response[0])
        self.assertEqual("API Client", create.response[1]["data"]["name"])
        listing = FakeRequest()
        handler.handle("GET", None, listing)
        self.assertEqual(200, listing.response[0])
        self.assertEqual("Custom", listing.response[1]["data"][0]["plan"])

    def test_unversioned_clients_path_resolves_to_registered_handler(self):
        handler = ClientManagementApiHandler(self.service)
        routes = EntityRouteRegistry()
        routes.register("clients", handler)
        request = type(
            "RouteProbe",
            (),
            {"path": "/clients", "route_registry": routes},
        )()
        route = TaskRequestHandler._resolved_entity_route(request)
        self.assertIs(handler, route.handler)
        self.assertIsNone(route.entity_id)


if __name__ == "__main__":
    unittest.main()
