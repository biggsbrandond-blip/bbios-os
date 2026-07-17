import hashlib
import hmac
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.integrations.api import ConnectorApiHandler, WebhookApiHandler
from bbi_os.integrations.models import (
    ConnectorDefinition,
    ExternalRequestFailed,
    ExternalTimeoutError,
)
from bbi_os.integrations.outbound import (
    ConnectorWorkflowAction,
    OutboundRequestEngine,
    TransportResponse,
)
from bbi_os.integrations.registry import IntegrationRegistry
from bbi_os.integrations.webhooks import WebhookService
from bbi_os.integrations.workflow import IntegrationWorkflowEngine
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


class FakeTransport:
    def __init__(self, results: List[Any]) -> None:
        self.results = list(results)
        self.calls: List[Dict[str, Any]] = []

    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout_seconds: float,
    ) -> TransportResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout_seconds,
            }
        )
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class CaptureAction:
    def __init__(self) -> None:
        self.inputs: List[Dict[str, Any]] = []

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        self.inputs.append(dict(inputs))
        return ActionResult(dict(inputs))

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        return None


def connector(version: str = "v1", auth_method: str = "none") -> ConnectorDefinition:
    return ConnectorDefinition(
        connector_id="weather",
        name="Weather API",
        type="http_api",
        base_url="https://api.example.test/v1",
        auth_method=auth_method,
        credential_env="WEATHER_API_TOKEN" if auth_method != "none" else None,
        version=version,
        request_schema={"type": "object"},
        response_schema={
            "type": "object",
            "required": ["temperature"],
            "properties": {"temperature": {"type": "number"}},
        },
    )


class IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.registry = IntegrationRegistry(self.root / "integrations.json")
        self.stream = io.StringIO()
        self.previous_observer = set_observability(Observability(self.stream))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()
        os.environ.pop("WEATHER_API_TOKEN", None)
        os.environ.pop("WEBHOOK_SECRET", None)

    def records(self) -> List[Dict[str, Any]]:
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_connector_registry_is_versioned_and_retrievable(self) -> None:
        self.registry.create_connector(connector("v1"))
        self.registry.create_connector(connector("v2"))
        self.assertEqual(2, len(self.registry.list_connectors()))
        self.assertEqual("v2", self.registry.get_connector("weather").version)
        self.assertEqual("v1", self.registry.get_connector("weather", "v1").version)

    def test_external_call_normalizes_response_and_uses_environment_credential(self) -> None:
        os.environ["WEATHER_API_TOKEN"] = "secret-token"
        self.registry.create_connector(connector(auth_method="bearer_token"))
        transport = FakeTransport(
            [TransportResponse(200, b'{"temperature":72}', "application/json")]
        )
        outbound = OutboundRequestEngine(
            self.registry, transport, timeout_seconds=2, max_retries=1
        )
        result = outbound.execute(
            "weather", path="current", query={"city": "Boston"}
        )
        self.assertEqual(72, result["data"]["temperature"])
        self.assertEqual("Bearer secret-token", transport.calls[0]["headers"]["Authorization"])
        self.assertEqual(2, transport.calls[0]["timeout"])
        self.assertNotIn("secret-token", self.stream.getvalue())

    def test_bounded_retry_and_timeout_mapping(self) -> None:
        self.registry.create_connector(connector())
        retry_transport = FakeTransport(
            [
                TransportResponse(503, b"{}"),
                TransportResponse(200, b'{"temperature":65}'),
            ]
        )
        result = OutboundRequestEngine(
            self.registry, retry_transport, max_retries=1
        ).execute("weather")
        self.assertEqual(65, result["data"]["temperature"])
        self.assertEqual(2, len(retry_transport.calls))

        timeout_transport = FakeTransport([TimeoutError(), TimeoutError()])
        with self.assertRaises(ExternalTimeoutError):
            OutboundRequestEngine(
                self.registry, timeout_transport, max_retries=1
            ).execute("weather")
        self.assertEqual(2, len(timeout_transport.calls))

    def test_outbound_path_and_response_validation_fail_safely(self) -> None:
        self.registry.create_connector(connector())
        outbound = OutboundRequestEngine(
            self.registry, FakeTransport([TransportResponse(200, b"{}")])
        )
        with self.assertRaises(ExternalRequestFailed):
            outbound.execute("weather", path="../private")
        with self.assertRaises(ExternalRequestFailed):
            outbound.execute("weather")

    def test_observability_contains_external_correlation_and_latency(self) -> None:
        self.registry.create_connector(connector())
        transport = FakeTransport(
            [TransportResponse(200, b'{"temperature":70}')]
        )
        outbound = OutboundRequestEngine(self.registry, transport)
        token = begin_request("2026-07-02T00:00:00Z")
        set_request_identity("user-1", "user")
        try:
            outbound.execute("weather", workflow_instance_id="instance-1")
        finally:
            end_request(token)
        record = next(
            item for item in self.records() if item["event"] == "external_request"
        )
        self.assertEqual("weather", record["metadata"]["connector_id"])
        self.assertEqual("instance-1", record["metadata"]["workflow_instance_id"])
        self.assertEqual("success", record["metadata"]["status"])
        self.assertGreaterEqual(record["metadata"]["latency_ms"], 0)
        self.assertNotIn("?", record["metadata"]["external_endpoint"])
        self.assertEqual("user-1", record["user_id"])
        self.assertTrue(record["request_id"])

    def test_workflow_passes_external_response_to_following_step(self) -> None:
        self.registry.create_connector(connector())
        outbound = OutboundRequestEngine(
            self.registry,
            FakeTransport([TransportResponse(200, b'{"temperature":81}')]),
        )
        capture = CaptureAction()
        actions = WorkflowActionRegistry()
        actions.register("function_call", "connector", ConnectorWorkflowAction(outbound))
        actions.register("entity_operation", "tasks", capture)
        engine = IntegrationWorkflowEngine(
            WorkflowRepository(self.root / "definitions.json", self.root / "instances.json"),
            actions,
        )
        engine.create_definition(
            {
                "workflow_id": "external-flow",
                "name": "External flow",
                "description": "Use external data",
                "trigger_type": "manual",
                "steps": [
                    {
                        "step_id": "weather",
                        "step_name": "Get weather",
                        "action_type": "function_call",
                        "target_entity": "connector",
                        "input_mapping": {
                            "connector_id": "weather",
                        },
                    },
                    {
                        "step_id": "update_task",
                        "step_name": "Update task",
                        "action_type": "entity_operation",
                        "target_entity": "tasks",
                        "input_mapping": {
                            "temperature": "$steps.weather.data.temperature"
                        },
                    },
                ],
            }
        )
        instance = engine.trigger("external-flow", {})
        self.assertEqual("completed", instance.execution_status)
        self.assertEqual(81, capture.inputs[0]["temperature"])
        external_log = next(
            item for item in self.records() if item["event"] == "external_request"
        )
        self.assertEqual(
            instance.workflow_instance_id,
            external_log["metadata"]["workflow_instance_id"],
        )

    def test_signed_webhook_triggers_mapped_workflow(self) -> None:
        capture = CaptureAction()
        actions = WorkflowActionRegistry()
        actions.register("function_call", "capture", capture)
        engine = WorkflowEngine(
            WorkflowRepository(self.root / "definitions.json", self.root / "instances.json"),
            actions,
        )
        engine.create_definition(
            {
                "workflow_id": "webhook-flow",
                "name": "Webhook flow",
                "description": "Triggered externally",
                "trigger_type": "manual",
                "steps": [
                    {
                        "step_id": "capture",
                        "step_name": "Capture",
                        "action_type": "function_call",
                        "target_entity": "capture",
                        "input_mapping": {"event": "$input.event"},
                    }
                ],
            }
        )
        service = WebhookService(self.registry, engine)
        service.register(
            {
                "webhook_id": "incoming",
                "workflow_id": "webhook-flow",
                "secret_env": "WEBHOOK_SECRET",
                "payload_schema": {
                    "type": "object",
                    "required": ["event"],
                    "properties": {"event": {"type": "string"}},
                },
            }
        )
        os.environ["WEBHOOK_SECRET"] = "webhook-secret"
        payload = {"event": "created"}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(b"webhook-secret", encoded, hashlib.sha256).hexdigest()
        instance = service.invoke("incoming", payload, f"sha256={signature}")
        self.assertEqual("completed", instance.execution_status)
        self.assertEqual("created", capture.inputs[0]["event"])
        self.assertEqual("webhook-flow", self.registry.workflow_mappings()[0]["workflow_id"])
        webhook_log = next(
            item for item in self.records() if item["event"] == "webhook_invocation"
        )
        self.assertEqual(instance.workflow_instance_id, webhook_log["metadata"]["workflow_instance_id"])


class IntegrationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.registry = IntegrationRegistry(root / "integrations.json")
        self.transport = FakeTransport(
            [TransportResponse(200, b'{"temperature":68}')]
        )
        outbound = OutboundRequestEngine(self.registry, self.transport)
        actions = WorkflowActionRegistry()
        actions.register("function_call", "capture", CaptureAction())
        engine = WorkflowEngine(
            WorkflowRepository(root / "definitions.json", root / "instances.json"),
            actions,
        )
        engine.create_definition(
            {
                "workflow_id": "hook-flow",
                "name": "Hook",
                "description": "Hook flow",
                "trigger_type": "manual",
                "steps": [
                    {
                        "step_id": "capture",
                        "step_name": "Capture",
                        "action_type": "function_call",
                        "target_entity": "capture",
                        "input_mapping": {"event": "$input.event"},
                    }
                ],
            }
        )
        self.routes = EntityRouteRegistry()
        self.routes.register("tasks", "tasks")
        self.routes.register("connectors", ConnectorApiHandler(self.registry, outbound))
        self.routes.register("webhooks", WebhookApiHandler(WebhookService(self.registry, engine)))
        self.task_service = TaskService(JsonTaskRepository(root / "tasks.json"))
        self.authenticator = Authenticator(
            {"admin-token": UserIdentity("admin-1", "admin", "admin", "start")}
        )
        self.responses: List[Tuple[int, Dict[str, Any]]] = []
        self.previous_observer = set_observability(Observability(io.StringIO()))

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def call(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = path
        handler.command = method
        handler.service = self.task_service
        handler.authenticator = self.authenticator
        handler.route_registry = self.routes
        handler.headers = {"Authorization": "Bearer admin-token", **(headers or {})}
        handler._body = lambda: body or {}

        def respond(status: int, response: Dict[str, Any]) -> None:
            handler._response_status = status
            self.responses.append((status, response))

        handler._respond = respond
        getattr(handler, f"do_{method}")()
        return self.responses[-1]

    def test_connector_and_webhook_api_routes(self) -> None:
        self.assertEqual(
            201,
            self.call("POST", "/v1/connectors", connector().to_dict())[0],
        )
        self.assertEqual(1, len(self.call("GET", "/v1/connectors")[1]["data"]))
        self.assertEqual(
            200,
            self.call("POST", "/v1/connectors/weather/test", {"path": "current"})[0],
        )
        self.assertEqual(
            201,
            self.call(
                "POST",
                "/v1/webhooks/register",
                {
                    "webhook_id": "api-hook",
                    "workflow_id": "hook-flow",
                    "payload_schema": {"type": "object", "required": ["event"]},
                },
            )[0],
        )
        status, response = self.call(
            "POST",
            "/v1/webhooks/invoke",
            {"webhook_id": "api-hook", "payload": {"event": "ready"}},
        )
        self.assertEqual(201, status)
        self.assertEqual("completed", response["data"]["execution_status"])


if __name__ == "__main__":
    unittest.main()
