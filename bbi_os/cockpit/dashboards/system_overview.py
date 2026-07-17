from typing import Any, Dict, List

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.cockpit.analytics.system_health import SystemHealthEngine
from bbi_os.cockpit.models import CockpitEventStore


class SystemOverviewDashboard:
    def __init__(self, clients: Any, health: SystemHealthEngine, events: CockpitEventStore) -> None:
        self.clients = clients
        self.health = health
        self.events = events

    def render(self, records: List[ClientExecutionRecord]) -> Dict[str, Any]:
        errors = [event for event in self.events.list() if event.get("level") == "ERROR"]
        connectors = self.events.list("external_request")
        return {
            "active_clients": len(self.clients.list()),
            "running_workflows": sum(
                item.state in {"RUNNING", "WAITING_EXTERNAL", "COMPENSATING"}
                for item in records
            ),
            "execution_states": self._states(records),
            "system_health": self.health.calculate(records),
            "recent_errors": errors[-20:],
            "connector_activity": connectors[-20:],
        }

    @staticmethod
    def _states(records: List[ClientExecutionRecord]) -> Dict[str, int]:
        states: Dict[str, int] = {}
        for record in records:
            states[record.state] = states.get(record.state, 0) + 1
        return states

