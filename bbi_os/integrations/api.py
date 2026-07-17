from typing import Any, Optional
from urllib.parse import urlparse

from bbi_os.integrations.models import (
    ConnectorDefinition,
    ConnectorNotFound,
    ExternalRequestFailed,
    ExternalTimeoutError,
    InvalidConnector,
    WebhookValidationFailed,
)
from bbi_os.integrations.outbound import OutboundRequestEngine
from bbi_os.integrations.registry import IntegrationRegistry
from bbi_os.integrations.webhooks import WebhookService
from bbi_os.task_management.api import error_response, success_response


class ConnectorApiHandler:
    def __init__(
        self, registry: IntegrationRegistry, outbound: OutboundRequestEngine
    ) -> None:
        self.registry = registry
        self.outbound = outbound

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        parts = [part for part in urlparse(request.path).path.split("/") if part]
        subresource = parts[3] if len(parts) == 4 else None
        try:
            if method == "POST" and entity_id is None:
                connector = self.registry.create_connector(
                    ConnectorDefinition.from_dict(request._body())
                )
                request._respond(
                    201, success_response(connector.to_dict(), "Connector created")
                )
                return
            if method == "GET" and entity_id is None:
                connectors = [item.to_dict() for item in self.registry.list_connectors()]
                request._respond(
                    200, success_response(connectors, "Connectors retrieved")
                )
                return
            if method == "POST" and entity_id and subresource == "test":
                body = request._body()
                result = self.outbound.execute(
                    entity_id,
                    method=body.get("method", "GET"),
                    path=body.get("path", ""),
                    body=body.get("body", {}),
                    query=body.get("query", {}),
                    version=body.get("version"),
                )
                request._respond(
                    200, success_response(result, "Connector test completed")
                )
                return
            request._route_not_found()
        except InvalidConnector as error:
            request._log_error("INVALID_CONNECTOR", str(error))
            request._respond(400, error_response("INVALID_CONNECTOR", str(error)))
        except ConnectorNotFound:
            request._log_error("CONNECTOR_NOT_FOUND", "Connector not found")
            request._respond(
                404, error_response("CONNECTOR_NOT_FOUND", "Connector not found")
            )
        except ExternalTimeoutError:
            request._log_error("TIMEOUT_ERROR", "External request timed out")
            request._respond(
                504, error_response("TIMEOUT_ERROR", "External request timed out")
            )
        except ExternalRequestFailed:
            request._log_error("EXTERNAL_REQUEST_FAILED", "External request failed")
            request._respond(
                502,
                error_response("EXTERNAL_REQUEST_FAILED", "External request failed"),
            )
        except Exception:
            request._log_error("EXTERNAL_REQUEST_FAILED", "External request failed")
            request._respond(
                500,
                error_response("EXTERNAL_REQUEST_FAILED", "External request failed"),
            )


class WebhookApiHandler:
    def __init__(self, service: WebhookService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        try:
            if method == "POST" and entity_id == "register":
                registration = self.service.register(request._body())
                request._respond(
                    201, success_response(registration.to_dict(), "Webhook registered")
                )
                return
            if method == "POST" and entity_id == "invoke":
                body = request._body()
                instance = self.service.invoke(
                    body["webhook_id"],
                    body.get("payload", {}),
                    request.headers.get("X-Webhook-Signature"),
                )
                if instance.execution_status == "failed":
                    request._respond(
                        422,
                        error_response(
                            "EXTERNAL_REQUEST_FAILED", "Webhook workflow failed"
                        ),
                    )
                else:
                    request._respond(
                        201,
                        success_response(instance.to_dict(), "Webhook invoked"),
                    )
                return
            request._route_not_found()
        except (WebhookValidationFailed, KeyError) as error:
            message = str(error) if isinstance(error, WebhookValidationFailed) else "Invalid webhook request"
            request._log_error("WEBHOOK_VALIDATION_FAILED", message)
            request._respond(
                400, error_response("WEBHOOK_VALIDATION_FAILED", message)
            )
        except Exception:
            request._log_error("EXTERNAL_REQUEST_FAILED", "Webhook execution failed")
            request._respond(
                500,
                error_response("EXTERNAL_REQUEST_FAILED", "Webhook execution failed"),
            )
