import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from bbi_os.integrations.models import (
    WebhookRegistration,
    WebhookValidationFailed,
)
from bbi_os.integrations.registry import IntegrationRegistry
from bbi_os.integrations.validation import validate_schema
from bbi_os.observability import get_observability
from bbi_os.workflows.engine import WorkflowEngine
from bbi_os.workflows.models import WorkflowInstance


class WebhookService:
    def __init__(self, registry: IntegrationRegistry, engine: WorkflowEngine) -> None:
        self.registry = registry
        self.engine = engine

    def register(self, data: Dict[str, Any]) -> WebhookRegistration:
        return self.registry.register_webhook(WebhookRegistration.from_dict(data))

    def invoke(
        self, webhook_id: str, payload: Any, signature: Optional[str] = None
    ) -> WorkflowInstance:
        started = time.perf_counter()
        registration = self.registry.get_webhook(webhook_id)
        try:
            sanitized = self._sanitize(payload)
            validate_schema(
                sanitized,
                registration.payload_schema,
                WebhookValidationFailed,
                "webhook payload",
            )
            self._validate_signature(registration, sanitized, signature)
            instance = self.engine.trigger(registration.workflow_id, sanitized)
            status = "success" if instance.execution_status == "completed" else "failure"
            self._log(
                registration,
                instance.workflow_instance_id,
                status,
                (time.perf_counter() - started) * 1000,
            )
            return instance
        except Exception:
            self._log(
                registration,
                "",
                "failure",
                (time.perf_counter() - started) * 1000,
            )
            raise

    @classmethod
    def _sanitize(cls, value: Any, depth: int = 0) -> Any:
        if depth > 10:
            raise WebhookValidationFailed("Webhook payload exceeded nesting limit")
        if isinstance(value, dict):
            if len(value) > 200:
                raise WebhookValidationFailed("Webhook payload has too many fields")
            sanitized: Dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str) or not key or len(key) > 128 or key.startswith("__"):
                    raise WebhookValidationFailed("Webhook payload contains an invalid field")
                sanitized[key] = cls._sanitize(item, depth + 1)
            if len(json.dumps(sanitized).encode("utf-8")) > 65_536:
                raise WebhookValidationFailed("Webhook payload exceeded size limit")
            return sanitized
        if isinstance(value, list):
            if len(value) > 1000:
                raise WebhookValidationFailed("Webhook payload list is too large")
            return [cls._sanitize(item, depth + 1) for item in value]
        if isinstance(value, str):
            if len(value) > 4096:
                raise WebhookValidationFailed("Webhook payload string is too large")
            return value
        if value is None or isinstance(value, (bool, int, float)):
            return value
        raise WebhookValidationFailed("Webhook payload contains an unsupported value")

    @staticmethod
    def _validate_signature(
        registration: WebhookRegistration,
        payload: Any,
        signature: Optional[str],
    ) -> None:
        if not registration.secret_env:
            return
        secret = os.environ.get(registration.secret_env)
        if not secret:
            raise WebhookValidationFailed("Webhook secret is not configured")
        if not signature:
            raise WebhookValidationFailed("Webhook signature is required")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), encoded, hashlib.sha256).hexdigest()
        supplied = signature.removeprefix("sha256=")
        if not hmac.compare_digest(expected, supplied):
            raise WebhookValidationFailed("Webhook signature is invalid")

    @staticmethod
    def _log(
        registration: WebhookRegistration,
        instance_id: str,
        status: str,
        latency_ms: float,
    ) -> None:
        get_observability().log(
            "ERROR" if status == "failure" else "INFO",
            "webhook_invocation",
            "Webhook invocation completed",
            {
                "connector_id": registration.connector_id or "",
                "webhook_id": registration.webhook_id,
                "workflow_instance_id": instance_id,
                "external_endpoint": f"/v1/webhooks/invoke:{registration.webhook_id}",
                "status": status,
                "latency_ms": round(latency_ms, 3),
            },
        )

