import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict

from bbi_os.client_monetization.models import ClientPlan
from bbi_os.client_monetization.plans import DEFAULT_PLANS


class ClientPlanRegistry:
    """Persistent client plan assignments over immutable plan definitions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def plan_for(self, client_id: str) -> ClientPlan:
        assignments = self._read()
        return DEFAULT_PLANS[assignments.get(client_id, "basic")]

    def assign(self, client_id: str, plan_id: str) -> ClientPlan:
        if plan_id not in DEFAULT_PLANS:
            raise ValueError(f"Unknown plan: {plan_id}")
        with self._lock:
            assignments = self._read()
            assignments[client_id] = plan_id
            self._write(assignments)
        return DEFAULT_PLANS[plan_id]

    def _read(self) -> Dict[str, str]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid plan assignments in {self.path}")
        return data

    def _write(self, assignments: Dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(assignments, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise

