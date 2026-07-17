class TaskError(Exception):
    """Base exception for task operations."""


class TaskNotFoundError(TaskError):
    """Raised when a task ID does not exist."""


class ValidationError(TaskError):
    """Raised when task input is invalid."""

