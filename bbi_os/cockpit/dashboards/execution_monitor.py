from typing import Any, Dict, Iterable

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.cockpit.models import CockpitEventStore
from bbi_os.workflows.repository import WorkflowRepository


class ExecutionMonitorDashboard:
    def __init__(self, workflows: WorkflowRepository, events: CockpitEventStore) -> None:
        self.workflows = workflows
        self.events = events

    def render(self, records: Iterable[ClientExecutionRecord]) -> Dict[str, Any]:
        return {"executions": [self._execution(record) for record in records]}

    def _execution(self, record: ClientExecutionRecord) -> Dict[str, Any]:
        instance = (
            self.workflows.get_instance(record.workflow_instance_id)
            if record.workflow_instance_id
            else None
        )
        return {
            **record.to_dict(),
            "step_history": [step.__dict__ for step in instance.step_history]
            if instance
            else [],
            "connector_calls": [
                event
                for event in self.events.list("external_request", record.client_id)
                if event.get("metadata", {}).get("workflow_instance_id")
                == record.workflow_instance_id
            ],
        }

