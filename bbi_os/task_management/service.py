from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from bbi_os.observability import get_observability
from bbi_os.persistence import TaskRecord, TaskRepository
from bbi_os.task_management.errors import TaskNotFoundError, ValidationError
from bbi_os.task_management.models import (
    TaskCreateRequest,
    TaskUpdateRequest,
    UPDATABLE_FIELDS,
    VALID_STATUSES,
    validate_task_fields,
)


TaskCreateInput = Dict[str, Any] | TaskCreateRequest
TaskUpdateInput = Dict[str, Any] | TaskUpdateRequest


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def create(self, data: TaskCreateInput) -> TaskRecord:
        request = (
            data if isinstance(data, TaskCreateRequest)
            else TaskCreateRequest.from_dict(data)
        )
        return self.create_task(request)

    def create_task(self, request: TaskCreateRequest) -> TaskRecord:
        now = _timestamp()
        task: TaskRecord = {
            "id": str(uuid4()),
            "title": request.title,
            "description": request.description,
            "status": request.status,
            "created_at": now,
            "updated_at": now,
        }
        saved_task = self.repository.save(task)
        get_observability().task_event("task_created", saved_task["id"])
        return saved_task

    def list(self) -> List[TaskRecord]:
        return self.repository.list()

    def get(self, task_id: str) -> TaskRecord:
        task = self._find(task_id)
        get_observability().task_event("task_retrieved", task_id)
        return task

    def _find(self, task_id: str) -> TaskRecord:
        task = self.repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task '{task_id}' was not found")
        return task

    def update(self, task_id: str, data: TaskUpdateInput) -> TaskRecord:
        request = (
            data if isinstance(data, TaskUpdateRequest)
            else TaskUpdateRequest.from_dict(data)
        )
        return self.update_task(task_id, request)

    def update_task(self, task_id: str, request: TaskUpdateRequest) -> TaskRecord:
        task = self._find(task_id)
        task.update(request.to_dict())
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
        validate_task_fields(data, required=required)
