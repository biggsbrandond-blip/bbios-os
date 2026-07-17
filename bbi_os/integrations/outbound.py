import json
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from bbi_os.integrations.models import (
    ConnectorDefinition,
    ExternalRequestFailed,
    ExternalTimeoutError,
)
from bbi_os.integrations.registry import IntegrationRegistry
from bbi_os.integrations.validation import validate_schema
from bbi_os.integrations.workflow import current_workflow_instance_id
from bbi_os.observability import get_observability
from bbi_os.workflows.engine import ActionResult


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    body: bytes
    content_type: str = "application/json"


class HttpTransport(Protocol):
    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout_seconds: float,
    ) -> TransportResponse: ...


class UrllibHttpTransport:
    def send(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout_seconds: float,
    ) -> TransportResponse:
        request = Request(url, data=body, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                response_body = response.read(1_048_577)
                if len(response_body) > 1_048_576:
                    raise ExternalRequestFailed("External response exceeded size limit")
                return TransportResponse(
                    response.status,
                    response_body,
                    response.headers.get_content_type(),
                )
        except HTTPError as error:
            return TransportResponse(
                error.code,
                error.read(1_048_577),
                error.headers.get_content_type() if error.headers else "text/plain",
            )


class OutboundRequestEngine:
    def __init__(
        self,
        registry: IntegrationRegistry,
        transport: Optional[HttpTransport] = None,
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
    ) -> None:
        if timeout_seconds <= 0 or not 0 <= max_retries <= 3:
            raise ValueError("Invalid outbound timeout or retry configuration")
        self.registry = registry
        self.transport = transport or UrllibHttpTransport()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def execute(
        self,
        connector_id: str,
        method: str = "GET",
        path: str = "",
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        workflow_instance_id: str = "",
    ) -> Dict[str, Any]:
        connector = self.registry.get_connector(connector_id, version)
        method = method.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ExternalRequestFailed("Unsupported external HTTP method")
        request_body = body or {}
        validate_schema(
            request_body, connector.request_schema, ExternalRequestFailed, "request"
        )
        encoded_body = None
        if method not in {"GET", "DELETE"}:
            encoded_body = json.dumps(request_body).encode("utf-8")
            if len(encoded_body) > 262_144:
                raise ExternalRequestFailed("External request exceeded size limit")
        endpoint = self._endpoint(connector, path, query or {})
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        self._apply_credentials(connector, headers)

        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                response = self.transport.send(
                    method, endpoint, headers, encoded_body, self.timeout_seconds
                )
                latency_ms = (time.perf_counter() - started) * 1000
                if response.status_code >= 500 and attempt < self.max_retries:
                    self._log(
                        connector,
                        endpoint,
                        "retrying",
                        latency_ms,
                        workflow_instance_id,
                        response.status_code,
                        attempt + 1,
                    )
                    continue
                if not 200 <= response.status_code < 300:
                    self._log(
                        connector,
                        endpoint,
                        "failure",
                        latency_ms,
                        workflow_instance_id,
                        response.status_code,
                        attempt + 1,
                    )
                    raise ExternalRequestFailed(
                        f"External service returned HTTP {response.status_code}"
                    )
                normalized = self._normalize(response)
                validate_schema(
                    normalized["data"],
                    connector.response_schema,
                    ExternalRequestFailed,
                    "response",
                )
                self._log(
                    connector,
                    endpoint,
                    "success",
                    latency_ms,
                    workflow_instance_id,
                    response.status_code,
                    attempt + 1,
                )
                return normalized
            except (TimeoutError, socket.timeout) as error:
                latency_ms = (time.perf_counter() - started) * 1000
                if attempt < self.max_retries:
                    self._log(
                        connector,
                        endpoint,
                        "retrying",
                        latency_ms,
                        workflow_instance_id,
                        None,
                        attempt + 1,
                    )
                    continue
                self._log(
                    connector,
                    endpoint,
                    "timeout",
                    latency_ms,
                    workflow_instance_id,
                    None,
                    attempt + 1,
                )
                raise ExternalTimeoutError("External request timed out") from error
            except URLError as error:
                latency_ms = (time.perf_counter() - started) * 1000
                if attempt < self.max_retries:
                    continue
                self._log(
                    connector,
                    endpoint,
                    "failure",
                    latency_ms,
                    workflow_instance_id,
                    None,
                    attempt + 1,
                )
                raise ExternalRequestFailed("External service was unavailable") from error
        raise ExternalRequestFailed("External request failed")

    def _endpoint(
        self, connector: ConnectorDefinition, path: str, query: Dict[str, Any]
    ) -> str:
        base = connector.base_url.rstrip("/") + "/"
        endpoint = urljoin(base, path.lstrip("/"))
        base_parts = urlparse(base)
        endpoint_parts = urlparse(endpoint)
        base_path = base_parts.path.rstrip("/") + "/"
        if (
            endpoint_parts.scheme != base_parts.scheme
            or endpoint_parts.netloc != base_parts.netloc
            or not endpoint_parts.path.startswith(base_path)
        ):
            raise ExternalRequestFailed("External path escaped connector base_url")
        if query:
            endpoint = f"{endpoint}?{urlencode(query, doseq=True)}"
        return endpoint

    @staticmethod
    def _apply_credentials(
        connector: ConnectorDefinition, headers: Dict[str, str]
    ) -> None:
        if connector.auth_method == "none":
            return
        credential = os.environ.get(connector.credential_env or "")
        if not credential:
            raise ExternalRequestFailed("Connector credential is not configured")
        if connector.auth_method == "api_key":
            headers["X-API-Key"] = credential
        elif connector.auth_method == "bearer_token":
            headers["Authorization"] = f"Bearer {credential}"

    @staticmethod
    def _normalize(response: TransportResponse) -> Dict[str, Any]:
        try:
            data = json.loads(response.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = response.body.decode("utf-8", errors="replace")
        return {
            "status_code": response.status_code,
            "content_type": response.content_type,
            "data": data,
        }

    @staticmethod
    def _log(
        connector: ConnectorDefinition,
        endpoint: str,
        status: str,
        latency_ms: float,
        workflow_instance_id: str,
        status_code: Optional[int],
        attempt: int,
    ) -> None:
        safe_endpoint = endpoint.split("?", 1)[0]
        get_observability().log(
            "ERROR" if status in {"failure", "timeout"} else "INFO",
            "external_request",
            "External request completed",
            {
                "connector_id": connector.connector_id,
                "workflow_instance_id": workflow_instance_id,
                "external_endpoint": safe_endpoint,
                "status": status,
                "status_code": status_code,
                "latency_ms": round(latency_ms, 3),
                "attempt": attempt,
            },
        )


class ConnectorWorkflowAction:
    def __init__(self, outbound: OutboundRequestEngine) -> None:
        self.outbound = outbound

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        return ActionResult(
            self.outbound.execute(
                connector_id=inputs["connector_id"],
                version=inputs.get("version"),
                method=inputs.get("method", "GET"),
                path=inputs.get("path", ""),
                body=inputs.get("body", {}),
                query=inputs.get("query", {}),
                workflow_instance_id=inputs.get("workflow_instance_id")
                or current_workflow_instance_id(),
            )
        )

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        return None
