from typing import Any, Dict

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.client_execution.service import ClientExecutionService
from bbi_os.cockpit.models import CockpitControlError, WorkflowControlRequest


class ExecutionControls:
    """Delegates every executable command to COS-002."""

    def __init__(self, service: ClientExecutionService) -> None:
        self.service = service

    def start(self, data: Dict[str, Any]) -> ClientExecutionRecord:
        request = WorkflowControlRequest.from_dict(data)
        return self.service.start(
            {
                "client_id": request.client_id,
                "execution_type": request.execution_type,
                "workflow_id": request.workflow_id,
                "input": request.input,
            }
        )

    def retry(self, execution_id: str) -> ClientExecutionRecord:
        record = self._get_execution(execution_id)
        if record is None:
            raise CockpitControlError("Execution was not found")
        if record.state != "FAILED":
            raise CockpitControlError("Only failed executions can be retried")
        return self.service.start(
            {
                "client_id": record.client_id,
                "execution_type": "one_time",
                "workflow_id": record.workflow_id,
                "input": dict(record.input_data),
            }
        )

    def pause(self, execution_id: str) -> None:
        self._unsupported(execution_id, "Pause")

    def cancel(self, execution_id: str) -> None:
        self._unsupported(execution_id, "Cancel")

    def inspect(self, execution_id: str) -> ClientExecutionRecord:
        record = self._get_execution(execution_id)
        if record is None:
            raise CockpitControlError("Execution was not found")
        return record

    def _get_execution(self, execution_id: str) -> ClientExecutionRecord | None:
        lookup = getattr(self.service, "get_execution", None)
        if lookup is not None:
            return lookup(execution_id)
        return self.service.state_repository.get(execution_id)

    def _unsupported(self, execution_id: str, command: str) -> None:
        self.inspect(execution_id)
        raise CockpitControlError(
            f"{command} is unavailable because COS-002 has no corresponding state transition"
        )

