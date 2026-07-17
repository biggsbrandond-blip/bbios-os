from typing import Any, Dict, Iterable

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.cockpit.models import CockpitEventStore


class SystemHealthEngine:
    def __init__(self, events: CockpitEventStore) -> None:
        self.events = events

    def calculate(self, records: Iterable[ClientExecutionRecord]) -> Dict[str, Any]:
        items = list(records)
        terminal = [item for item in items if item.state in {"COMPLETED", "FAILED"}]
        completed = sum(item.state == "COMPLETED" for item in terminal)
        connector_events = self.events.list("external_request")
        connector_failures = sum(
            event.get("metadata", {}).get("status") == "failure"
            for event in connector_events
        )
        return {
            "status": "degraded" if any(item.state == "FAILED" for item in items) else "healthy",
            "workflow_success_rate": round(completed / len(terminal), 4) if terminal else 1.0,
            "connector_failure_rate": round(connector_failures / len(connector_events), 4)
            if connector_events
            else 0.0,
            "running_executions": sum(
                item.state in {"RUNNING", "WAITING_EXTERNAL", "COMPENSATING"}
                for item in items
            ),
            "queued_executions": sum(item.state == "PENDING" for item in items),
        }

