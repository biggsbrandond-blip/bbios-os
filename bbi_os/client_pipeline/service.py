import time
from typing import Any, Dict

from bbi_os.client_pipeline.errors import (
    ClientPipelineError,
    PipelineAuthenticationFailed,
)
from bbi_os.client_pipeline.models import ClientPipelineResult, ClientRequest
from bbi_os.client_pipeline.pipeline_engine import ClientPipelineEngine
from bbi_os.client_pipeline.request_router import ClientRequestRouter
from bbi_os.observability import current_request_context, get_observability


class ClientPipelineService:
    def __init__(
        self, router: ClientRequestRouter, engine: ClientPipelineEngine
    ) -> None:
        self.router = router
        self.engine = engine

    def process(self, data: Dict[str, Any]) -> ClientPipelineResult:
        started = time.perf_counter()
        request = ClientRequest.from_dict(data)
        context = current_request_context()
        if context["user_id"] in {"anonymous", "system", ""}:
            self._event(
                "client_pipeline_failed", request, "", "", "failed", started
            )
            raise PipelineAuthenticationFailed("Authentication required")
        if request.user_id != context["user_id"]:
            self._event(
                "client_pipeline_failed", request, "", "", "failed", started
            )
            raise PipelineAuthenticationFailed(
                "Client request user_id does not match authenticated user"
            )
        template_id = ""
        instance_id = ""
        try:
            route = self.router.route(request)
            template_id = route.template_id
            result = self.engine.execute(request, route)
            instance_id = result.workflow_instance_id
            self._event(
                "client_pipeline_completed",
                request,
                template_id,
                instance_id,
                "completed",
                started,
            )
            return result
        except ClientPipelineError:
            self._event(
                "client_pipeline_failed",
                request,
                template_id,
                instance_id,
                "failed",
                started,
            )
            raise

    @staticmethod
    def _event(
        event_type: str,
        request: ClientRequest,
        template_id: str,
        instance_id: str,
        status: str,
        started: float,
    ) -> None:
        get_observability().log(
            "ERROR" if status == "failed" else "INFO",
            event_type,
            event_type.replace("_", " ").capitalize(),
            {
                "event_type": event_type,
                "client_request_type": request.type,
                "workflow_template_id": template_id,
                "workflow_instance_id": instance_id,
                "status": status,
                "execution_time_ms": round(
                    (time.perf_counter() - started) * 1000, 3
                ),
            },
        )
