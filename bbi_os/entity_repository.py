import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, List, Optional, Protocol

from bbi_os.domain import BaseEntity
from bbi_os.observability import get_observability


class EntityRepository(Protocol):
    entity_type: str

    def list(self) -> List[BaseEntity]: ...

    def get(self, entity_id: str) -> Optional[BaseEntity]: ...

    def exists(self, entity_id: str) -> bool: ...

    def count(self) -> int: ...

    def save(self, entity: BaseEntity) -> BaseEntity: ...

    def delete(self, entity_id: str) -> bool: ...


class JsonEntityRepository:
    """Generic, isolated JSON storage for future entity domains."""

    def __init__(self, entity_type: str, path: Path) -> None:
        if not entity_type:
            raise ValueError("Entity type is required")
        self.entity_type = entity_type
        self.path = path
        self._lock = threading.RLock()

    def list(self) -> List[BaseEntity]:
        with self._lock:
            entities = [BaseEntity.from_record(record) for record in self._read().values()]
            for entity in entities:
                self._event("entity_retrieved", entity.entity_id)
            return entities

    def get(self, entity_id: str) -> Optional[BaseEntity]:
        with self._lock:
            record = self._read().get(entity_id)
            if record is None:
                return None
            entity = BaseEntity.from_record(record)
            self._event("entity_retrieved", entity_id)
            return entity

    def exists(self, entity_id: str) -> bool:
        with self._lock:
            return entity_id in self._read()

    def count(self) -> int:
        with self._lock:
            return len(self._read())

    def save(self, entity: BaseEntity) -> BaseEntity:
        self._validate_type(entity)
        with self._lock:
            records = self._read()
            event_type = "entity_updated" if entity.entity_id in records else "entity_created"
            records[entity.entity_id] = entity.to_record()
            self._write(records)
            self._event(event_type, entity.entity_id)
            return entity

    def delete(self, entity_id: str) -> bool:
        with self._lock:
            records = self._read()
            if entity_id not in records:
                return False
            del records[entity_id]
            self._write(records)
            self._event("entity_deleted", entity_id)
            return True

    def _validate_type(self, entity: BaseEntity) -> None:
        if entity.entity_type != self.entity_type:
            raise ValueError(
                f"Entity type '{entity.entity_type}' cannot be stored in "
                f"'{self.entity_type}' repository"
            )

    def _event(self, event_type: str, entity_id: str) -> None:
        get_observability().log(
            "INFO",
            event_type,
            event_type.replace("_", " ").capitalize(),
            {
                "event_type": event_type,
                "entity_type": self.entity_type,
                "entity_id": entity_id,
            },
        )

    def _read(self) -> Dict[str, Dict[str, object]]:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid entity data in {self.path}")
        return data

    def _write(self, records: Dict[str, Dict[str, object]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(records, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise


class EntityRepositoryRouter:
    def __init__(self) -> None:
        self._repositories: Dict[str, EntityRepository] = {}

    def register(self, repository: EntityRepository) -> None:
        if repository.entity_type in self._repositories:
            raise ValueError(f"Repository already registered for '{repository.entity_type}'")
        self._repositories[repository.entity_type] = repository

    def repository_for(self, entity_type: str) -> EntityRepository:
        try:
            return self._repositories[entity_type]
        except KeyError as error:
            raise KeyError(f"No repository registered for '{entity_type}'") from error

