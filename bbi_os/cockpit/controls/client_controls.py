import threading
from typing import Any, Dict

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.cockpit.controls.execution_controls import ExecutionControls
from bbi_os.cockpit.models import CockpitControlError


class ClientControls:
    """Controls cockpit-originated execution access without changing client records."""

    def __init__(self, executions: ExecutionControls) -> None:
        self.executions = executions
        self._locked = set()
        self._guard = threading.Lock()

    def trigger(self, data: Dict[str, Any]) -> ClientExecutionRecord:
        client_id = data.get("client_id", "")
        if self.is_locked(client_id):
            raise CockpitControlError("Client execution is locked in the cockpit")
        return self.executions.start(data)

    def lock(self, client_id: str) -> None:
        with self._guard:
            self._locked.add(client_id)

    def unlock(self, client_id: str) -> None:
        with self._guard:
            self._locked.discard(client_id)

    def is_locked(self, client_id: str) -> bool:
        with self._guard:
            return client_id in self._locked

