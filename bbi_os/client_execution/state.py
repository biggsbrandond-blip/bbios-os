import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.client_execution.errors import ClientExecutionError
from bbi_os.client_execution.models import StateTransition
from bbi_os.observability import get_observability, timestamp


STATE_TRANSITIONS = {
    "PENDING": {"RUNNING"},
    "RUNNING": {"WAITING_EXTERNAL", "COMPENSATING", "COMPLETED"},
    "WAITING_EXTERNAL": {"RUNNING", "COMPENSATING"},
    "COMPENSATING": {"FAILED"},
    "FAILED": set(),
    "COMPLETED": set(),
}


class ExecutionStateMachine:
    def __init__(self, repository: "ExecutionStateRepository") -> None:
        self.repository = repository

    def transition(
        self, record: ClientExecutionRecord, next_state: str
    ) -> ClientExecutionRecord:
        if next_state not in STATE_TRANSITIONS.get(record.state, set()):
            raise ClientExecutionError(
                f"Invalid execution transition: {record.state} -> {next_state}"
            )
        previous = record.state
        now = timestamp()
        record.state = next_state
        record.updated_at = now
        record.transitions.append(StateTransition(next_state, now))
        self.repository.save(record)
        get_observability().log(
            "ERROR" if next_state == "FAILED" else "INFO",
            "client_execution_state_changed",
            "Client execution state changed",
            {
                "event_type": "client_execution_state_changed",
                "client_id": record.client_id,
                "execution_id": record.execution_id,
                "workflow_instance_id": record.workflow_instance_id,
                "previous_state": previous,
                "execution_state": next_state,
            },
        )
        return record


class ExecutionStateRepository:
    """Atomic, thread-safe COS-002 execution state persistence."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def save(self, record: ClientExecutionRecord) -> ClientExecutionRecord:
        with self._lock:
            records = self._read()
            records[record.execution_id] = record.to_dict()
            self._write(records)
        return record

    def get(self, execution_id: str) -> Optional[ClientExecutionRecord]:
        with self._lock:
            item = self._read().get(execution_id)
        return ClientExecutionRecord.from_dict(item) if item else None

    def latest_for_client(self, client_id: str) -> Optional[ClientExecutionRecord]:
        with self._lock:
            matches = [
                ClientExecutionRecord.from_dict(item)
                for item in self._read().values()
                if item.get("client_id") == client_id
            ]
        return max(matches, key=lambda item: item.created_at) if matches else None

    def list_for_client(self, client_id: str) -> List[ClientExecutionRecord]:
        with self._lock:
            return [
                ClientExecutionRecord.from_dict(item)
                for item in self._read().values()
                if item.get("client_id") == client_id
            ]

    def _read(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid execution state in {self.path}")
        return data

    def _write(self, records: Dict[str, Dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(records, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
