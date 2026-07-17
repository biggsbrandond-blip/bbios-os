import io
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bbi_os.auth import Authenticator, UserIdentity
from bbi_os.client_monetization.api import ClientMonetizationApiHandler
from bbi_os.client_monetization.metering_observer import UsageSignalMeter
from bbi_os.client_monetization.pricing_engine import PricingEngine
from bbi_os.client_monetization.registry import ClientPlanRegistry
from bbi_os.client_monetization.service import ClientMonetizationService
from bbi_os.client_monetization.usage_tracker import UsageTracker
from bbi_os.domain import BaseEntity
from bbi_os.entity_repository import JsonEntityRepository
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.observability import (
    Observability,
    begin_request,
    end_request,
    set_observability,
    set_request_identity,
    timestamp,
)
from bbi_os.task_management.api import TaskRequestHandler
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService


class FailingMonetizationService:
    def record_automatic(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("billing storage unavailable")


class ClientMonetizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.clients = JsonEntityRepository("client", root / "clients.json")
        now = timestamp()
        for client_id in ("client-1", "client-2"):
            self.clients.save(
                BaseEntity(client_id, "client", now, now, {"client_name": client_id})
            )
        self.plans = ClientPlanRegistry(root / "plans.json")
        self.usage = UsageTracker(root / "usage.json")
        self.service = ClientMonetizationService(
            self.clients, self.plans, self.usage, PricingEngine()
        )
        self.stream = io.StringIO()
        self.observer = Observability(self.stream)
        self.previous_observer = set_observability(self.observer)
        self.api = ClientMonetizationApiHandler(self.service)
        self.task_service = TaskService(JsonTaskRepository(root / "tasks.json"))
        self.authenticator = Authenticator(
            {"user-token": UserIdentity("user-1", "operator", "user", "start")}
        )
        self.routes = EntityRouteRegistry()
        self.routes.register("tasks", "tasks")
        self.routes.register("client", self.api)
        self.responses: List[Tuple[int, Dict[str, Any]]] = []

    def tearDown(self) -> None:
        set_observability(self.previous_observer)
        self.temporary_directory.cleanup()

    def call(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        handler = TaskRequestHandler.__new__(TaskRequestHandler)
        handler.path = path
        handler.command = method
        handler.service = self.task_service
        handler.authenticator = self.authenticator
        handler.route_registry = self.routes
        handler.headers = {"Authorization": "Bearer user-token"}
        handler._body = lambda: body or {}

        def respond(status: int, response: Dict[str, Any]) -> None:
            handler._response_status = status
            self.responses.append((status, response))

        handler._respond = respond
        getattr(handler, f"do_{method}")()
        return self.responses[-1]

    def test_usage_tracking_correctness_and_plan_lookup(self) -> None:
        status, plan = self.call("GET", "/v1/client/plan/client-1")
        self.assertEqual(200, status)
        self.assertEqual("basic", plan["data"]["plan_id"])
        status, response = self.call(
            "POST",
            "/v1/client/usage-event",
            {
                "client_id": "client-1",
                "event_type": "workflow_execution",
                "usage_units": 3,
                "metadata": {"workflow_steps": 2},
            },
        )
        self.assertEqual(201, status)
        self.assertEqual(3, response["data"]["usage_units"])
        metrics = self.call("GET", "/v1/client/usage/client-1")[1]["data"]
        self.assertEqual(3, metrics["total_usage_units"])
        self.assertEqual(0.30, metrics["estimated_cost"])

    def test_plan_enforcement_connector_and_usage_limits(self) -> None:
        status, response = self.call(
            "POST",
            "/v1/client/usage-event",
            {
                "client_id": "client-1",
                "event_type": "connector_call",
                "usage_units": 1,
                "metadata": {},
            },
        )
        self.assertEqual(403, status)
        self.assertEqual("CONNECTOR_ACCESS_DENIED", response["data"]["error"]["code"])

        self.call(
            "POST",
            "/v1/client/usage-event",
            {
                "client_id": "client-1",
                "event_type": "workflow_execution",
                "usage_units": 100,
                "metadata": {},
            },
        )
        status, response = self.call(
            "POST",
            "/v1/client/usage-event",
            {
                "client_id": "client-1",
                "event_type": "workflow_execution",
                "usage_units": 1,
                "metadata": {},
            },
        )
        self.assertEqual(429, status)
        self.assertEqual("PLAN_LIMIT_EXCEEDED", response["data"]["error"]["code"])

    def test_billing_aggregation_accuracy(self) -> None:
        self.service.record_automatic("client-1", "workflow_execution", 2, {})
        self.service.record_automatic("client-1", "connector_call", 1, {})
        self.service.record_automatic("client-1", "onboarding", 1, {})
        summary = self.call(
            "POST", "/v1/client/billing-summary", {"client_id": "client-1"}
        )[1]["data"]
        self.assertEqual(4, summary["total_usage_units"])
        self.assertEqual(0.45, summary["estimated_cost"])
        self.assertEqual(
            {"workflows": 2, "connectors": 1, "onboarding": 1},
            summary["usage_breakdown"],
        )

    def test_cos002_observability_events_are_metered(self) -> None:
        self.observer.add_listener(UsageSignalMeter(self.service))
        token = begin_request("2026-07-02T00:00:00Z")
        set_request_identity("user-1", "user")
        try:
            self.observer.log(
                "INFO",
                "workflow_step_completed",
                "Step completed",
                {"step_id": "one", "workflow_instance_id": "instance-1"},
            )
            self.observer.log(
                "INFO",
                "workflow_step_completed",
                "Step completed",
                {"step_id": "two", "workflow_instance_id": "instance-1"},
            )
            self.observer.log(
                "INFO",
                "external_request",
                "External request completed",
                {
                    "connector_id": "crm",
                    "workflow_instance_id": "instance-1",
                    "status": "success",
                },
            )
            self.observer.log(
                "INFO",
                "client_execution_completed",
                "Execution complete",
                {
                    "client_id": "client-1",
                    "execution_id": "execution-1",
                    "workflow_instance_id": "instance-1",
                    "execution_state": "COMPLETED",
                },
            )
        finally:
            end_request(token)
        events = self.usage.for_client("client-1")
        self.assertEqual(
            [("workflow_execution", 3), ("connector_call", 1)],
            [(event.event_type, event.usage_units) for event in events],
        )

    def test_monetization_failure_cannot_break_execution_signal(self) -> None:
        observer = Observability(io.StringIO())
        observer.add_listener(UsageSignalMeter(FailingMonetizationService()))
        record = observer.log(
            "INFO",
            "client_execution_completed",
            "Execution complete",
            {
                "client_id": "client-1",
                "workflow_instance_id": "instance-1",
                "execution_state": "COMPLETED",
            },
        )
        self.assertEqual("client_execution_completed", record["event"])

    def test_multi_client_usage_is_strictly_separated(self) -> None:
        self.service.record_automatic("client-1", "workflow_execution", 2, {})
        self.service.record_automatic("client-2", "onboarding", 1, {})
        first = self.service.billing.generate("client-1")
        second = self.service.billing.generate("client-2")
        self.assertEqual(2, first.total_usage_units)
        self.assertEqual({"workflows": 2, "connectors": 0, "onboarding": 0}, first.usage_breakdown)
        self.assertEqual(1, second.total_usage_units)
        self.assertEqual({"workflows": 0, "connectors": 0, "onboarding": 1}, second.usage_breakdown)

    def test_pro_plan_allows_connector_usage(self) -> None:
        self.plans.assign("client-1", "pro")
        status, response = self.call(
            "POST",
            "/v1/client/usage-event",
            {
                "client_id": "client-1",
                "event_type": "connector_call",
                "usage_units": 2,
                "metadata": {},
            },
        )
        self.assertEqual(201, status)
        self.assertEqual(0.08, response["data"]["estimated_cost"])


if __name__ == "__main__":
    unittest.main()
