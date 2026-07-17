from typing import Any, Dict, Optional

from bbi_os.client_onboarding.errors import (
    InvalidOnboardingRequest,
    InvalidOnboardingType,
    OnboardingAuthenticationFailed,
    OnboardingExecutionFailed,
    OnboardingWorkflowNotFound,
)
from bbi_os.client_onboarding.service import OnboardingService
from bbi_os.task_management.api import error_response, success_response


class OnboardingApiHandler:
    def __init__(self, service: OnboardingService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        if method != "POST" or entity_id != "onboarding":
            request._route_not_found()
            return
        try:
            result = self.service.onboard(request._body())
            request._respond(
                201, success_response(result.to_dict(), "Client onboarding completed")
            )
        except InvalidOnboardingRequest as error:
            self._error(request, 400, "INVALID_ONBOARDING_REQUEST", str(error))
        except InvalidOnboardingType:
            self._error(
                request,
                400,
                "INVALID_ONBOARDING_TYPE",
                "Unsupported onboarding request type",
            )
        except OnboardingAuthenticationFailed:
            self._error(request, 401, "UNAUTHORIZED", "Authentication required")
        except OnboardingWorkflowNotFound:
            self._error(
                request,
                404,
                "ONBOARDING_WORKFLOW_NOT_FOUND",
                "Onboarding workflow not found",
            )
        except OnboardingExecutionFailed:
            self._error(
                request,
                422,
                "ONBOARDING_EXECUTION_FAILED",
                "Client onboarding failed",
            )
        except Exception:
            self._error(
                request,
                500,
                "ONBOARDING_EXECUTION_FAILED",
                "Client onboarding failed",
            )

    @staticmethod
    def _error(request: Any, status: int, code: str, message: str) -> None:
        request._log_error(code, message)
        request._respond(status, error_response(code, message))


class ClientApiRouter:
    """Dispatches resources that share the versioned /v1/client boundary."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Any] = {}

    def register(self, resource: str, handler: Any) -> None:
        if resource in self._handlers:
            raise ValueError(f"Client API resource '{resource}' is already registered")
        self._handlers[resource] = handler

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        handler = self._handlers.get(entity_id or "")
        if handler is None:
            request._route_not_found()
            return
        handler.handle(method, entity_id, request)
