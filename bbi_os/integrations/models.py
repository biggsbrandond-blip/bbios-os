from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse


CONNECTOR_TYPES = {"http_api", "webhook", "external_service"}
AUTH_METHODS = {"api_key", "bearer_token", "none"}


class InvalidConnector(Exception):
    pass


class ConnectorNotFound(Exception):
    pass


class ExternalRequestFailed(Exception):
    pass


class ExternalTimeoutError(ExternalRequestFailed):
    pass


class WebhookValidationFailed(Exception):
    pass


@dataclass(frozen=True)
class ConnectorDefinition:
    connector_id: str
    name: str
    type: str
    base_url: str
    auth_method: str
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]
    version: str = "v1"
    credential_env: Optional[str] = None

    def validate(self) -> None:
        if not self.connector_id or not self.name or not self.version:
            raise InvalidConnector("Connector ID, name, and version are required")
        if self.type not in CONNECTOR_TYPES:
            raise InvalidConnector(f"Unsupported connector type: {self.type}")
        if self.auth_method not in AUTH_METHODS:
            raise InvalidConnector(f"Unsupported authentication method: {self.auth_method}")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise InvalidConnector("Connector base_url must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.fragment:
            raise InvalidConnector("Connector base_url cannot contain credentials or fragments")
        if self.auth_method != "none" and not self.credential_env:
            raise InvalidConnector("Authenticated connectors require credential_env")
        if self.credential_env and not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.credential_env
        ):
            raise InvalidConnector("credential_env must be a valid environment variable name")
        if not isinstance(self.request_schema, dict) or not isinstance(
            self.response_schema, dict
        ):
            raise InvalidConnector("Connector schemas must be objects")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConnectorDefinition":
        try:
            connector = cls(
                connector_id=data["connector_id"],
                name=data["name"],
                type=data["type"],
                base_url=data["base_url"],
                auth_method=data["auth_method"],
                request_schema=dict(data.get("request_schema", {})),
                response_schema=dict(data.get("response_schema", {})),
                version=data.get("version", "v1"),
                credential_env=data.get("credential_env"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidConnector("Invalid connector definition") from error
        connector.validate()
        return connector


@dataclass(frozen=True)
class WebhookRegistration:
    webhook_id: str
    workflow_id: str
    payload_schema: Dict[str, Any]
    secret_env: Optional[str] = None
    connector_id: Optional[str] = None

    def validate(self) -> None:
        if not self.webhook_id or not self.workflow_id:
            raise WebhookValidationFailed("Webhook ID and workflow ID are required")
        if not isinstance(self.payload_schema, dict):
            raise WebhookValidationFailed("Webhook payload schema must be an object")
        if self.secret_env and not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.secret_env
        ):
            raise WebhookValidationFailed(
                "secret_env must be a valid environment variable name"
            )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookRegistration":
        try:
            registration = cls(
                webhook_id=data["webhook_id"],
                workflow_id=data["workflow_id"],
                payload_schema=dict(data.get("payload_schema", {})),
                secret_env=data.get("secret_env"),
                connector_id=data.get("connector_id"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise WebhookValidationFailed("Invalid webhook registration") from error
        registration.validate()
        return registration
