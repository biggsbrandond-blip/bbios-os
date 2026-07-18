import unittest

from fastapi import FastAPI
from fastapi.routing import APIRoute

from bbi_os.app import app as canonical_app
from bbi_os.app import create_app
from bbi_os.cockpit.api import app as cockpit_legacy_app
from bbi_os.cockpit.api import create_app as cockpit_legacy_factory
from bbi_os.cockpit.router import ClientRequest
from bbi_os.__main__ import app as main_legacy_app
from bbi_os.__main__ import create_app as main_legacy_factory


EXPECTED_CUSTOM_ROUTES = {
    ("GET", "/"),
    ("GET", "/health"),
    ("POST", "/cockpit/create-client"),
    ("GET", "/cockpit/client/{client_id}"),
    ("GET", "/cockpit/clients/search"),
    ("POST", "/cockpit/test-pipeline"),
}


def custom_routes(app: FastAPI):
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }


def route_endpoint(app: FastAPI, method: str, path: str):
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == path
            and method in route.methods
        ):
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


class RuntimeContractTests(unittest.TestCase):
    def test_canonical_factory_returns_fastapi_instance(self) -> None:
        application = create_app()

        self.assertIsInstance(application, FastAPI)

    def test_legacy_app_imports_reference_canonical_app(self) -> None:
        self.assertIs(canonical_app, main_legacy_app)
        self.assertIs(canonical_app, cockpit_legacy_app)
        self.assertIs(create_app, main_legacy_factory)
        self.assertIs(create_app, cockpit_legacy_factory)

    def test_expected_custom_routes_remain_registered(self) -> None:
        self.assertEqual(EXPECTED_CUSTOM_ROUTES, custom_routes(canonical_app))

    def test_application_metadata_uses_settings_defaults(self) -> None:
        self.assertEqual("BBIOS OS", canonical_app.title)
        self.assertEqual("1.0", canonical_app.version)
        self.assertEqual("BBIOS Unified System", canonical_app.description)

    def test_existing_fastapi_endpoint_behavior_is_preserved(self) -> None:
        health = route_endpoint(canonical_app, "GET", "/health")
        create_client = route_endpoint(
            canonical_app, "POST", "/cockpit/create-client"
        )
        get_client = route_endpoint(canonical_app, "GET", "/cockpit/client/{client_id}")

        self.assertEqual({"status": "ok"}, health())
        created = create_client(ClientRequest(client_name="Runtime Client", plan="premium"))
        self.assertEqual("success", created["status"])
        client_id = created["client"]["client_id"]

        retrieved = get_client(client_id)
        self.assertEqual("success", retrieved["status"])
        self.assertEqual(client_id, retrieved["client"]["client_id"])


if __name__ == "__main__":
    unittest.main()
