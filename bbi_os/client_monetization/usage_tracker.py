import json
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from bbi_os.client_monetization.models import UsageEvent


class UsageTracker:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def record(self, event: UsageEvent) -> UsageEvent:
        with self._lock:
            events = self._read()
            events[event.usage_event_id] = event.to_dict()
            self._write(events)
        return event

    def for_client(self, client_id: str) -> List[UsageEvent]:
        with self._lock:
            events = [
                UsageEvent.from_dict(item)
                for item in self._read().values()
                if item.get("client_id") == client_id
            ]
        return sorted(events, key=lambda event: (event.timestamp, event.usage_event_id))

    def total_units(self, client_id: str) -> int:
        return sum(event.usage_units for event in self.for_client(client_id))

    def recent_count(self, client_id: str, minutes: int = 1) -> int:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return sum(
            1
            for event in self.for_client(client_id)
            if datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")) >= threshold
        )

    def _read(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid usage data in {self.path}")
        return data

    def _write(self, events: Dict[str, Dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(events, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
