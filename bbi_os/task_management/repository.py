import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from bbi_os.observability import get_observability

Task = Dict[str, Any]


class JsonTaskRepository:
    """Persists tasks in a JSON file, replacing the file atomically on writes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def list(self) -> List[Task]:
        with self._lock:
            tasks = list(self._read().values())
            self._log_operation("repository_tasks_listed")
            return tasks

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            task = self._read().get(task_id)
            self._log_operation("repository_task_read", task_id)
            return task

    def save(self, task: Task) -> Task:
        with self._lock:
            tasks = self._read()
            tasks[task["id"]] = task
            self._write(tasks)
            self._log_operation("repository_task_saved", task["id"])
            return task

    def delete(self, task_id: str) -> bool:
        with self._lock:
            tasks = self._read()
            if task_id not in tasks:
                return False
            del tasks[task_id]
            self._write(tasks)
            self._log_operation("repository_task_deleted", task_id)
            return True

    @staticmethod
    def _log_operation(event: str, entity_id: Optional[str] = None) -> None:
        get_observability().log(
            "DEBUG",
            event,
            "Repository operation completed",
            {"entity_id": entity_id} if entity_id else {},
        )

    def _read(self) -> Dict[str, Task]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid task data in {self.path}")
        return data

    def _write(self, tasks: Dict[str, Task]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(tasks, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
