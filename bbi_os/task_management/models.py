from dataclasses import dataclass
from typing import Any, Dict

from bbi_os.task_management.errors import ValidationError


VALID_STATUSES = {"pending", "in-progress", "complete"}
UPDATABLE_FIELDS = {"title", "description", "status"}
_UNSET = object()


def validate_task_fields(data: Dict[str, Any], required: set[str]) -> None:
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


@dataclass(frozen=True)
class TaskCreateRequest:
    title: str
    description: str
    status: str

    def __post_init__(self) -> None:
        validate_task_fields(self.to_dict(), required=UPDATABLE_FIELDS)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskCreateRequest":
        validate_task_fields(data, required=UPDATABLE_FIELDS)
        return cls(
            title=data["title"],
            description=data["description"],
            status=data["status"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "status": self.status,
        }


@dataclass(frozen=True)
class TaskUpdateRequest:
    title: Any = _UNSET
    description: Any = _UNSET
    status: Any = _UNSET

    def __post_init__(self) -> None:
        data = self.to_dict()
        if not data:
            raise ValidationError("At least one field is required")
        validate_task_fields(data, required=set())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskUpdateRequest":
        if not data:
            raise ValidationError("At least one field is required")
        validate_task_fields(data, required=set())
        return cls(
            title=data.get("title", _UNSET),
            description=data.get("description", _UNSET),
            status=data.get("status", _UNSET),
        )

    def to_dict(self) -> Dict[str, Any]:
        values = {
            "title": self.title,
            "description": self.description,
            "status": self.status,
        }
        return {key: value for key, value in values.items() if value is not _UNSET}
