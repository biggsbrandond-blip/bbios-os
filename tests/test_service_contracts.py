import unittest
from typing import Any, Dict, List

from bbi_os.client_execution.models import ClientExecutionRecord, StateTransition
from bbi_os.client_execution.service import ClientExecutionService
from bbi_os.client_monetization.models import BillingSummary, ClientPlan
from bbi_os.client_monetization.service import ClientMonetizationService
from bbi_os.cockpit.controls.execution_controls import ExecutionControls
from bbi_os.cockpit.models import CockpitControlError
from bbi_os.domain import BaseEntity
from bbi_os.observability import begin_request, end_request, set_request_identity


def _execution(execution_id: str, state: str = "FAILED") -> ClientExecutionRecord:
    return ClientExecutionRecord(
        execution_id=execution_id,
        client_id="client-1",
        execution_type="one_time",
        workflow_id="workflow-1",
        input_data={"key": "value"},
        state=state,
        transitions=[StateTransition(state, "2026-01-01T00:00:00Z")],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


class FakeExecutionService:
    def __init__(self, record: ClientExecutionRecord | None) -> None:
        self.record = record
        self.lookups: List[str] = []
        self.starts: List[Dict[str, Any]] = []

    @property
    def state_repository(self) -> object:
        raise AssertionError("controls must use the public service lookup contract")

    def get_execution(self, execution_id: str) -> ClientExecutionRecord | None:
        self.lookups.append(execution_id)
        return self.record

    def start(self, data: Dict[str, Any]) -> ClientExecutionRecord:
        self.starts.append(data)
        return _execution("retry-1", "PENDING")


class FakeClients:
    def get(self, client_id: str) -> BaseEntity | None:
        if client_id != "client-1":
            return None
        return BaseEntity(
            "client-1",
            "client",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:00:00Z",
            {"client_name": "Acme"},
        )


class FakePlans:
    def plan_for(self, client_id: str) -> ClientPlan:
        return ClientPlan("pro", 100, True, 10, 10)


class FakeUsage:
    def __init__(self) -> None:
        self.events: List[Any] = []

    def record(self, event: Any) -> Any:
        self.events.append(event)
        return event


class FakePricing:
    def estimate(self, plan: ClientPlan, event_type: str, usage_units: int) -> float:
        return 12.34


class FakeEnforcer:
    def __init__(self) -> None:
        self.calls: List[Any] = []

    def enforce(self, plan: ClientPlan, event: Any) -> None:
        self.calls.append((plan, event))


class FakeBilling:
    def __init__(self) -> None:
        self.client_ids: List[str] = []

    def generate(self, client_id: str) -> BillingSummary:
        self.client_ids.append(client_id)
        return BillingSummary(client_id, 7, 12.34, {"workflows": 7})


class ServiceContractTests(unittest.TestCase):
    def test_execution_controls_use_public_execution_service_lookup(self) -> None:
        service = FakeExecutionService(_execution("execution-1"))
        controls = ExecutionControls(service)  # type: ignore[arg-type]

        self.assertEqual("execution-1", controls.inspect("execution-1").execution_id)
        retried = controls.retry("execution-1")

        self.assertEqual("retry-1", retried.execution_id)
        self.assertEqual(["execution-1", "execution-1"], service.lookups)
        self.assertEqual(
            [
                {
                    "client_id": "client-1",
                    "execution_type": "one_time",
                    "workflow_id": "workflow-1",
                    "input": {"key": "value"},
                }
            ],
            service.starts,
        )

    def test_execution_controls_preserve_missing_execution_error(self) -> None:
        controls = ExecutionControls(FakeExecutionService(None))  # type: ignore[arg-type]

        with self.assertRaisesRegex(CockpitControlError, "Execution was not found"):
            controls.inspect("missing")

    def test_client_execution_service_exposes_public_execution_lookup(self) -> None:
        class StateRepository:
            def get(self, execution_id: str) -> ClientExecutionRecord | None:
                return _execution(execution_id)

        service = ClientExecutionService(
            FakeClients(), object(), object(), StateRepository()  # type: ignore[arg-type]
        )

        self.assertEqual("execution-42", service.get_execution("execution-42").execution_id)

    def test_monetization_service_honors_injected_helpers(self) -> None:
        enforcer = FakeEnforcer()
        billing = FakeBilling()
        service = ClientMonetizationService(
            FakeClients(),  # type: ignore[arg-type]
            FakePlans(),  # type: ignore[arg-type]
            FakeUsage(),  # type: ignore[arg-type]
            FakePricing(),  # type: ignore[arg-type]
            enforcer,
            billing,
        )
        token = begin_request("request-1")
        set_request_identity("user-1", "user")
        try:
            usage = service.track(
                {
                    "client_id": "client-1",
                    "event_type": "workflow_execution",
                    "usage_units": 2,
                    "metadata": {},
                }
            )
            summary = service.billing_summary("client-1")
        finally:
            end_request(token)

        self.assertEqual(12.34, usage.estimated_cost)
        self.assertEqual(1, len(enforcer.calls))
        self.assertEqual({"workflows": 7}, summary["usage_breakdown"])
        self.assertEqual(["client-1"], billing.client_ids)


if __name__ == "__main__":
    unittest.main()
