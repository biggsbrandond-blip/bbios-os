import time
from typing import Any, Dict
from uuid import uuid4

from bbi_os.client_onboarding.errors import (
    OnboardingAuthenticationFailed,
    OnboardingError,
)
from bbi_os.client_onboarding.models import OnboardingRequest, OnboardingResult
from bbi_os.client_onboarding.onboarding_engine import OnboardingEngine
from bbi_os.client_onboarding.router import OnboardingRouter
from bbi_os.observability import current_request_context, get_observability


class OnboardingService:
    def __init__(self, router: OnboardingRouter, engine: OnboardingEngine) -> None:
        self.router = router
        self.engine = engine

    def onboard(self, data: Dict[str, Any]) -> OnboardingResult:
        started = time.perf_counter()
        onboarding_request_id = str(uuid4())
        request = OnboardingRequest.from_dict(data)
        context = current_request_context()
        if context["user_id"] in {"anonymous", "system", ""}:
            self._event(
                "client_onboarding_failed",
                onboarding_request_id,
                request,
                "",
                "",
                "",
                "failed",
                started,
            )
            raise OnboardingAuthenticationFailed("Authentication required")
        if request.user_id != context["user_id"]:
            self._event(
                "client_onboarding_failed",
                onboarding_request_id,
                request,
                "",
                "",
                "",
                "failed",
                started,
            )
            raise OnboardingAuthenticationFailed(
                "Onboarding user_id does not match authenticated user"
            )
        template_id = ""
        try:
            route = self.router.route(request)
            template_id = route.template_id
            result = self.engine.execute(onboarding_request_id, request, route)
            self._event(
                "client_onboarding_completed",
                onboarding_request_id,
                request,
                result.workflow_template_id,
                result.workflow_instance_id,
                result.client_entity_id,
                "completed",
                started,
            )
            return result
        except OnboardingError:
            self._event(
                "client_onboarding_failed",
                onboarding_request_id,
                request,
                template_id,
                "",
                "",
                "failed",
                started,
            )
            raise

    @staticmethod
    def _event(
        event_type: str,
        onboarding_request_id: str,
        request: OnboardingRequest,
        workflow_id: str,
        workflow_instance_id: str,
        entity_id: str,
        status: str,
        started: float,
    ) -> None:
        get_observability().log(
            "ERROR" if status == "failed" else "INFO",
            event_type,
            event_type.replace("_", " ").capitalize(),
            {
                "event_type": event_type,
                "onboarding_request_id": onboarding_request_id,
                "workflow_id": workflow_id,
                "workflow_instance_id": workflow_instance_id,
                "entity_id": entity_id,
                "client_name": request.client_name,
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            },
        )

