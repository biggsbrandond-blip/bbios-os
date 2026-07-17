from dataclasses import dataclass, field
from typing import Any, Dict

from bbi_os.auth import UserIdentity


@dataclass(frozen=True)
class BaseEntity:
    entity_id: str
    entity_type: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entity_id or not self.entity_type:
            raise ValueError("Entity ID and entity type are required")
        if not isinstance(self.metadata, dict):
            raise ValueError("Entity metadata must be a dictionary")

    def to_record(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "BaseEntity":
        return cls(
            entity_id=record["entity_id"],
            entity_type=record["entity_type"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            metadata=dict(record.get("metadata", {})),
        )


@dataclass(frozen=True)
class TaskEntity(BaseEntity):
    @classmethod
    def from_task(cls, task: Dict[str, Any]) -> "TaskEntity":
        return cls(
            entity_id=task["id"],
            entity_type="task",
            created_at=task["created_at"],
            updated_at=task["updated_at"],
            metadata={
                "title": task["title"],
                "description": task["description"],
                "status": task["status"],
            },
        )

    def to_task(self) -> Dict[str, Any]:
        if self.entity_type != "task":
            raise ValueError("TaskEntity must use the 'task' entity type")
        return {
            "id": self.entity_id,
            "title": self.metadata["title"],
            "description": self.metadata["description"],
            "status": self.metadata["status"],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class UserEntity(BaseEntity):
    @classmethod
    def from_identity(cls, identity: UserIdentity) -> "UserEntity":
        return cls(
            entity_id=identity.user_id,
            entity_type="user",
            created_at=identity.created_at,
            updated_at=identity.created_at,
            metadata={"username": identity.username, "role": identity.role},
        )

    def to_identity(self) -> UserIdentity:
        if self.entity_type != "user":
            raise ValueError("UserEntity must use the 'user' entity type")
        return UserIdentity(
            user_id=self.entity_id,
            username=self.metadata["username"],
            role=self.metadata["role"],
            created_at=self.created_at,
        )

