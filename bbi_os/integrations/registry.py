import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bbi_os.integrations.models import (
    ConnectorDefinition,
    ConnectorNotFound,
    InvalidConnector,
    WebhookRegistration,
    WebhookValidationFailed,
)


class IntegrationRegistry:
    """Persistent versioned connectors, webhook registrations, and workflow mappings."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def create_connector(self, connector: ConnectorDefinition) -> ConnectorDefinition:
        key = f"{connector.connector_id}:{connector.version}"
        with self._lock:
            data = self._read()
            if key in data["connectors"]:
                raise InvalidConnector("Connector version already exists")
            data["connectors"][key] = connector.to_dict()
            self._write(data)
        return connector

    def list_connectors(self) -> List[ConnectorDefinition]:
        return [
            ConnectorDefinition.from_dict(record)
            for record in self._read()["connectors"].values()
        ]

    def get_connector(
        self, connector_id: str, version: Optional[str] = None
    ) -> ConnectorDefinition:
        matches = [
            connector
            for connector in self.list_connectors()
            if connector.connector_id == connector_id
        ]
        if version:
            matches = [connector for connector in matches if connector.version == version]
        if not matches:
            raise ConnectorNotFound(f"Connector '{connector_id}' was not found")
        return max(matches, key=lambda connector: self._version_key(connector.version))

    def register_webhook(self, webhook: WebhookRegistration) -> WebhookRegistration:
        with self._lock:
            data = self._read()
            if webhook.webhook_id in data["webhooks"]:
                raise WebhookValidationFailed("Webhook ID already exists")
            if webhook.connector_id:
                self.get_connector(webhook.connector_id)
            data["webhooks"][webhook.webhook_id] = webhook.to_dict()
            mapping = {
                "connector_id": webhook.connector_id,
                "workflow_id": webhook.workflow_id,
                "webhook_id": webhook.webhook_id,
            }
            data["workflow_mappings"].append(mapping)
            self._write(data)
        return webhook

    def get_webhook(self, webhook_id: str) -> WebhookRegistration:
        record = self._read()["webhooks"].get(webhook_id)
        if record is None:
            raise WebhookValidationFailed("Webhook registration was not found")
        return WebhookRegistration.from_dict(record)

    def workflow_mappings(self) -> List[Dict[str, Any]]:
        return list(self._read()["workflow_mappings"])

    @staticmethod
    def _version_key(version: str) -> Tuple[Any, ...]:
        return tuple(
            (1, int(part)) if part.isdigit() else (0, part.lower())
            for part in re.split(r"([0-9]+)", version)
            if part
        )

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"connectors": {}, "webhooks": {}, "workflow_mappings": []}
        with self.path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid integration data in {self.path}")
        data.setdefault("connectors", {})
        data.setdefault("webhooks", {})
        data.setdefault("workflow_mappings", [])
        return data

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(self.path.parent), prefix=f".{self.path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(data, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, self.path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise
