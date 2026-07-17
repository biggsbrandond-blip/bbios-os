import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List


class CockpitControlError(Exception):
    """A safe control-plane command could not be completed."""


@dataclass(frozen=True)
class WorkflowControlRequest:
    client_id: str
    workflow_id: str
    input: Dict[str, Any]
    execution_type: str = "one_time"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowControlRequest":
        if not isinstance(data, dict):
            raise CockpitControlError("Control request must be an object")
        client_id = data.get("client_id")
        workflow_id = data.get("workflow_id")
        input_data = data.get("input", {})
        execution_type = data.get("execution_type", "one_time")
        if not isinstance(client_id, str) or not client_id:
            raise CockpitControlError("client_id is required")
        if not isinstance(workflow_id, str) or not workflow_id:
            raise CockpitControlError("workflow_id is required")
        if not isinstance(input_data, dict):
            raise CockpitControlError("input must be an object")
        return cls(client_id, workflow_id, input_data, execution_type)


class CockpitEventStore:
    """Bounded, process-local view of existing structured observability events."""

    def __init__(self, limit: int = 2000) -> None:
        self._records: Deque[Dict[str, Any]] = deque(maxlen=limit)
        self._lock = threading.Lock()

    def __call__(self, record: Dict[str, Any]) -> None:
        with self._lock:
            self._records.append(dict(record))

    def list(self, event: str = "", client_id: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            records = list(self._records)
        if event:
            records = [record for record in records if record.get("event") == event]
        if client_id:
            records = [
                record
                for record in records
                if record.get("metadata", {}).get("client_id") == client_id
                or record.get("metadata", {}).get("entity_id") == client_id
            ]
        return records

