from typing import Any, Optional

from bbi_os.client_pipeline.errors import (
    InvalidClientRequest,
    InvalidRequestType,
    PipelineAuthenticationFailed,
    PipelineExecutionFailed,
    PipelineWorkflowNotFound,
)
from bbi_os.client_pipeline.service import ClientPipelineService
from bbi_os.task_management.api import error_response, success_response


class ClientPipelineApiHandler:
    def __init__(self, service: ClientPipelineService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        if method != "POST" or entity_id != "request":
            request._route_not_found()
            return
        try:
            result = self.service.process(request._body())
            request._respond(
                201,
                success_response(result.to_dict(), "Client request completed"),
            )
        except InvalidRequestType:
            self._error(
                request,
                400,
                "INVALID_REQUEST_TYPE",
                "Unsupported client request type",
            )
        except InvalidClientRequest as error:
            self._error(request, 400, "VALIDATION_ERROR", str(error))
        except PipelineAuthenticationFailed:
            self._error(request, 401, "UNAUTHORIZED", "Authentication required")
        except PipelineWorkflowNotFound:
            self._error(request, 404, "WORKFLOW_NOT_FOUND", "Workflow not found")
        except PipelineExecutionFailed:
            self._error(
                request,
                422,
                "PIPELINE_EXECUTION_FAILED",
                "Client pipeline execution failed",
            )
        except Exception:
            self._error(
                request,
                500,
                "PIPELINE_EXECUTION_FAILED",
                "Client pipeline execution failed",
            )

    @staticmethod
    def _error(
        request: Any, status: int, code: str, message: str
    ) -> None:
        request._log_error(code, message)
        request._respond(status, error_response(code, message))
