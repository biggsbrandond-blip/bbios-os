from typing import Any, Optional
from urllib.parse import urlparse

from bbi_os.client_monetization.errors import (
    ConnectorAccessDenied,
    InvalidUsageEvent,
    MonetizationAuthenticationFailed,
    MonetizationClientNotFound,
    PlanLimitExceeded,
)
from bbi_os.client_monetization.service import ClientMonetizationService
from bbi_os.task_management.api import error_response, success_response


class ClientMonetizationApiHandler:
    def __init__(self, service: ClientMonetizationService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        parts = [part for part in urlparse(request.path).path.split("/") if part]
        try:
            if method == "GET" and entity_id == "plan" and len(parts) == 4:
                request._respond(
                    200,
                    success_response(
                        self.service.get_plan(parts[3]), "Client plan retrieved"
                    ),
                )
                return
            if method == "POST" and entity_id == "usage-event" and len(parts) == 3:
                event = self.service.track(request._body())
                request._respond(
                    201, success_response(event.to_dict(), "Usage event recorded")
                )
                return
            if method == "GET" and entity_id == "usage" and len(parts) == 4:
                request._respond(
                    200,
                    success_response(
                        self.service.metrics(parts[3]), "Usage metrics retrieved"
                    ),
                )
                return
            if method == "POST" and entity_id == "billing-summary" and len(parts) == 3:
                body = request._body()
                request._respond(
                    200,
                    success_response(
                        self.service.billing_summary(body["client_id"]),
                        "Billing summary generated",
                    ),
                )
                return
            request._route_not_found()
        except (InvalidUsageEvent, KeyError) as error:
            message = str(error) if isinstance(error, InvalidUsageEvent) else "client_id is required"
            self._error(request, 400, "INVALID_USAGE_EVENT", message)
        except MonetizationAuthenticationFailed:
            self._error(request, 401, "UNAUTHORIZED", "Authentication required")
        except MonetizationClientNotFound:
            self._error(request, 404, "CLIENT_NOT_FOUND", "Client not found")
        except ConnectorAccessDenied:
            self._error(request, 403, "CONNECTOR_ACCESS_DENIED", "Connector access denied")
        except PlanLimitExceeded as error:
            self._error(request, 429, "PLAN_LIMIT_EXCEEDED", str(error))
        except Exception:
            self._error(
                request, 500, "MONETIZATION_ERROR", "Monetization request failed"
            )

    @staticmethod
    def _error(request: Any, status: int, code: str, message: str) -> None:
        request._log_error(code, message)
        request._respond(status, error_response(code, message))
