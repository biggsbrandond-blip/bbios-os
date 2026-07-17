from typing import Any, Dict

from bbi_os.observability import current_request_context
from bbi_os.task_management.service import TaskService
from bbi_os.workflows.engine import ActionResult
from bbi_os.workflows.models import WorkflowStepError


class TaskWorkflowActions:
    def __init__(self, service: TaskService) -> None:
        self.service = service

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        operation = inputs.get("operation")
        if operation == "create":
            task = self.service.create(
                {
                    "title": inputs["title"],
                    "description": inputs["description"],
                    "status": inputs["status"],
                }
            )
            return ActionResult(task, {"operation": "delete", "task_id": task["id"]})
        if operation == "get":
            return ActionResult(self.service.get(inputs["task_id"]))
        if operation == "update":
            task_id = inputs["task_id"]
            previous = dict(self.service.get(task_id))
            updates = {
                key: value
                for key, value in inputs.items()
                if key in {"title", "description", "status"}
            }
            return ActionResult(
                self.service.update(task_id, updates),
                {"operation": "restore", "task": previous},
            )
        if operation == "delete":
            if current_request_context()["role"] != "admin":
                raise WorkflowStepError("Admin role is required to delete tasks")
            self.service.delete(inputs["task_id"])
            return ActionResult({"task_id": inputs["task_id"], "deleted": True})
        raise WorkflowStepError(f"Unsupported task operation: {operation}")

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        operation = rollback_data["operation"]
        if operation == "delete":
            self.service.delete(rollback_data["task_id"])
        elif operation == "restore":
            task = rollback_data["task"]
            self.service.update(
                task["id"],
                {
                    "title": task["title"],
                    "description": task["description"],
                    "status": task["status"],
                },
            )


class UserWorkflowActions:
    """Read-only access to the user identity already attached to the request."""

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        if inputs.get("operation") != "current":
            raise WorkflowStepError("Only the current user identity is available")
        context = current_request_context()
        return ActionResult(
            {"user_id": context["user_id"], "role": context["role"]}
        )

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        return None

