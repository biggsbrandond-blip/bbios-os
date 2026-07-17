import io
import tempfile
import unittest
from pathlib import Path

from bbi_os.client_execution.models import ClientExecutionRecord, ClientExecutionRequest
from bbi_os.client_execution.state import ExecutionStateRepository
from bbi_os.client_monetization.pricing_engine import PricingEngine
from bbi_os.client_monetization.registry import ClientPlanRegistry
from bbi_os.client_monetization.service import ClientMonetizationService
from bbi_os.client_monetization.usage_tracker import UsageTracker
from bbi_os.cockpit.analytics.performance_metrics import PerformanceMetricsEngine
from bbi_os.cockpit.analytics.system_health import SystemHealthEngine
from bbi_os.cockpit.analytics.usage_insights import UsageInsightsEngine
from bbi_os.cockpit.api import CockpitApiHandler
from bbi_os.cockpit.controls.client_controls import ClientControls
from bbi_os.cockpit.controls.execution_controls import ExecutionControls
from bbi_os.cockpit.controls.workflow_controls import WorkflowControls
from bbi_os.cockpit.dashboards.client_view import ClientViewDashboard
from bbi_os.cockpit.dashboards.execution_monitor import ExecutionMonitorDashboard
from bbi_os.cockpit.dashboards.monetization_view import MonetizationDashboard
from bbi_os.cockpit.dashboards.system_overview import SystemOverviewDashboard
from bbi_os.cockpit.dashboards.workflow_control import WorkflowControlDashboard
from bbi_os.cockpit.models import CockpitControlError, CockpitEventStore
from bbi_os.cockpit.service import CockpitService
from bbi_os.domain import BaseEntity
from bbi_os.entity_repository import JsonEntityRepository
from bbi_os.observability import (
    Observability,
    begin_request,
    end_request,
    set_observability,
    set_request_identity,
    timestamp,
)
from bbi_os.workflows.repository import WorkflowRepository


class StubTemplates:
    def list(self):
        return []

    def get(self, reference, version=None):
        raise LookupError(reference)


class StubExecutionService:
    def __init__(self, state_repository):
        self.state_repository = state_repository
        self.requests = []

    def start(self, data):
        self.requests.append(dict(data))
        request = ClientExecutionRequest.from_dict(data)
        record = ClientExecutionRecord.new(f"execution-{len(self.requests)}", request)
        record.state = "COMPLETED"
        self.state_repository.save(record)
        return record


class FakeRequest:
    def __init__(self, path, body=None):
        self.path = path
        self.body = body or {}
        self.response = None
        self.error = None
        self.not_found = False

    def _body(self):
        return dict(self.body)

    def _respond(self, status, body):
        self.response = (status, body)

    def _log_error(self, code, message):
        self.error = (code, message)

    def _route_not_found(self):
        self.not_found = True


class CockpitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.observer = Observability(io.StringIO())
        self.events = CockpitEventStore()
        self.observer.add_listener(self.events)
        self.previous_observer = set_observability(self.observer)
        self.token = begin_request()
        set_request_identity("operator-1", "admin")
        self.clients = JsonEntityRepository("client", root / "clients.json")
        for client_id in ("client-1", "client-2"):
            now = timestamp()
            self.clients.save(
                BaseEntity(client_id, "client", now, now, {"name": client_id})
            )
        self.executions = ExecutionStateRepository(root / "executions.json")
        self.workflow_repository = WorkflowRepository(
            root / "workflows.json", root / "instances.json"
        )
        self.monetization = ClientMonetizationService(
            self.clients,
            ClientPlanRegistry(root / "plans.json"),
            UsageTracker(root / "usage.json"),
            PricingEngine(),
        )
        self.execution_service = StubExecutionService(self.executions)
        self.execution_controls = ExecutionControls(self.execution_service)
        self.client_controls = ClientControls(self.execution_controls)
        self.templates = StubTemplates()
        self.workflow_controls = WorkflowControls(
            self.execution_controls, self.templates
        )
        self.service = CockpitService(
            self.clients,
            self.executions,
            SystemOverviewDashboard(
                self.clients, SystemHealthEngine(self.events), self.events
            ),
            ClientViewDashboard(
                self.clients, self.monetization, self.client_controls, self.events
            ),
            ExecutionMonitorDashboard(self.workflow_repository, self.events),
            MonetizationDashboard(self.monetization),
            WorkflowControlDashboard(self.templates, self.executions),
            self.workflow_controls,
            UsageInsightsEngine(self.monetization),
            PerformanceMetricsEngine(self.observer),
        )

    def tearDown(self):
        end_request(self.token)
        set_observability(self.previous_observer)
        self.temporary.cleanup()

    def _record(self, client_id="client-1", state="COMPLETED"):
        request = ClientExecutionRequest(
            client_id, "one_time", "template-1", {}
        )
        record = ClientExecutionRecord.new(
            f"{client_id}-{state.lower()}", request
        )
        record.state = state
        self.executions.save(record)
        return record

    def test_system_overview_aggregates_clients_and_execution_states(self):
        self._record(state="RUNNING")
        self._record("client-2", "FAILED")
        overview = self.service.system_overview()
        self.assertEqual(2, overview["active_clients"])
        self.assertEqual(1, overview["running_workflows"])
        self.assertEqual({"RUNNING": 1, "FAILED": 1}, overview["execution_states"])
        self.assertEqual("degraded", overview["system_health"]["status"])

    def test_client_view_combines_cos001_cos002_and_cos003(self):
        self._record()
        self.monetization.track(
            {
                "client_id": "client-1",
                "event_type": "workflow_execution",
                "usage_units": 2,
                "metadata": {},
            }
        )
        view = self.service.client("client-1")
        self.assertEqual("client-1", view["client"]["entity_id"])
        self.assertEqual(1, len(view["executions"]))
        self.assertEqual(2, view["usage"]["total_usage_units"])

    def test_execution_control_routes_start_through_cos002_service(self):
        result = self.service.execute(
            {"client_id": "client-1", "workflow_id": "template-1", "input": {}}
        )
        self.assertEqual("COMPLETED", result["state"])
        self.assertEqual("client-1", self.execution_service.requests[0]["client_id"])

    def test_workflow_cancel_is_safe_and_does_not_mutate_state(self):
        record = self._record(state="RUNNING")
        before = self.executions.get(record.execution_id).to_dict()
        with self.assertRaises(CockpitControlError):
            self.service.cancel(record.execution_id)
        self.assertEqual(before, self.executions.get(record.execution_id).to_dict())

    def test_observability_records_request_trace_for_cockpit_action(self):
        self.service.system_overview()
        event = self.events.list("cockpit_view_rendered")[-1]
        self.assertNotEqual("", event["request_id"])
        self.assertEqual("operator-1", event["user_id"])

    def test_billing_dashboard_aggregates_clients_accurately(self):
        for client_id in ("client-1", "client-2"):
            self.monetization.track(
                {
                    "client_id": client_id,
                    "event_type": "workflow_execution",
                    "usage_units": 2,
                    "metadata": {},
                }
            )
        billing = self.service.billing()
        self.assertEqual(4, billing["total_usage_units"])
        self.assertEqual(0.4, billing["estimated_cost"])

    def test_read_only_views_do_not_change_persisted_execution_state(self):
        self._record()
        before = self.executions.path.read_bytes()
        self.service.system_overview()
        self.service.execution_monitor()
        self.service.usage()
        self.assertEqual(before, self.executions.path.read_bytes())

    def test_required_api_surfaces_return_standardized_contracts(self):
        self._record()
        handler = CockpitApiHandler(self.service)
        requests = [
            ("system-overview", "/v1/cockpit/system-overview"),
            ("client", "/v1/cockpit/client/client-1"),
            ("executions", "/v1/cockpit/executions"),
            ("usage", "/v1/cockpit/usage"),
            ("billing-summary", "/v1/cockpit/billing-summary"),
        ]
        for entity_id, path in requests:
            request = FakeRequest(path)
            handler.handle("GET", entity_id, request)
            self.assertEqual(200, request.response[0])
            self.assertEqual(
                {"request_id", "status", "data", "execution_summary"},
                set(request.response[1]),
            )
        execute = FakeRequest(
            "/v1/cockpit/workflow/execute",
            {"client_id": "client-1", "workflow_id": "template-1", "input": {}},
        )
        handler.handle("POST", "workflow", execute)
        self.assertEqual(201, execute.response[0])


if __name__ == "__main__":
    unittest.main()
