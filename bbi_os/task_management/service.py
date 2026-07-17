from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from bbi_os.observability import get_observability
from bbi_os.task_management.errors import TaskNotFoundError, ValidationError
from bbi_os.task_management.repository import JsonTaskRepository, Task


VALID_STATUSES = {"pending", "in-progress", "complete"}
UPDATABLE_FIELDS = {"title", "description", "status"}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TaskService:
    def __init__(self, repository: JsonTaskRepository) -> None:
        self.repository = repository

    def create(self, data: Dict[str, Any]) -> Task:
        self._validate_fields(data, required=UPDATABLE_FIELDS)
        now = _timestamp()
        task: Task = {
            "id": str(uuid4()),
            "title": data["title"],
            "description": data["description"],
            "status": data["status"],
            "created_at": now,
            "updated_at": now,
        }
        saved_task = self.repository.save(task)
        get_observability().task_event("task_created", saved_task["id"])
        return saved_task

    def list(self) -> List[Task]:
        return self.repository.list()

    def get(self, task_id: str) -> Task:
        task = self._find(task_id)
        get_observability().task_event("task_retrieved", task_id)
        return task

    def _find(self, task_id: str) -> Task:
        task = self.repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' was not found")
        return task

    def update(self, task_id: str, data: Dict[str, Any]) -> Task:
        if not data:
            raise ValidationError("At least one field is required")
        self._validate_fields(data, required=set())
        task = self._find(task_id)
        task.update(data)
        task["updated_at"] = _timestamp()
        saved_task = self.repository.save(task)
        get_observability().task_event("task_updated", task_id)
        return saved_task

    def delete(self, task_id: str) -> None:
        if not self.repository.delete(task_id):
            raise TaskNotFoundError(f"Task '{task_id}' was not found")
        get_observability().task_event("task_deleted", task_id)

    @staticmethod
    def _validate_fields(data: Dict[str, Any], required: set) -> None:
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object")
        unknown = set(data) - UPDATABLE_FIELDS
        if unknown:
            raise ValidationError(f"Unknown field(s): {', '.join(sorted(unknown))}")
        missing = required - set(data)
        if missing:
            raise ValidationError(f"Missing field(s): {', '.join(sorted(missing))}")
        for field in ("title", "description"):
            if field in data and not isinstance(data[field], str):
                raise ValidationError(f"'{field}' must be a string")
        if "status" in data and data["status"] not in VALID_STATUSES:
            raise ValidationError("'status' must be pending, in-progress, or complete")
