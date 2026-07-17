import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from bbi_os.workflows.models import WorkflowDefinition, WorkflowInstance


class WorkflowRepository:
    """Atomic JSON persistence for definitions and execution state."""

    def __init__(self, definitions_path: Path, instances_path: Path) -> None:
        self.definitions_path = definitions_path
        self.instances_path = instances_path
        self._lock = threading.RLock()

    def save_definition(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        with self._lock:
            records = self._read(self.definitions_path)
            records[definition.workflow_id] = definition.to_dict()
            self._write(self.definitions_path, records)
        return definition

    def get_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        with self._lock:
            record = self._read(self.definitions_path).get(workflow_id)
        return WorkflowDefinition.from_dict(record) if record else None

    def save_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        with self._lock:
            records = self._read(self.instances_path)
            records[instance.workflow_instance_id] = instance.to_dict()
            self._write(self.instances_path, records)
        return instance

    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        with self._lock:
            record = self._read(self.instances_path).get(instance_id)
        return WorkflowInstance.from_dict(record) if record else None

    @staticmethod
    def _read(path: Path) -> Dict[str, Dict[str, Any]]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid workflow data in {path}")
        return data

    @staticmethod
    def _write(path: Path, records: Dict[str, Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(records, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
