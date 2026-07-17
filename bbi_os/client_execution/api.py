from typing import Any, Dict, Optional
from urllib.parse import urlparse

from bbi_os.client_execution.errors import (
    ConcurrentExecution,
    ExecutionAuthenticationFailed,
    ExecutionClientNotFound,
    ExecutionNotFound,
    InvalidExecutionRequest,
)
from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.client_execution.service import ClientExecutionService
from bbi_os.observability import current_request_id
from bbi_os.response_contract import record_error, response_envelope
from bbi_os.task_management.api import error_response, success_response


class ClientExecutionApiHandler:
    def __init__(self, service: ClientExecutionService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        parts = [part for part in urlparse(request.path).path.split("/") if part]
        try:
            if method == "POST" and entity_id == "execute" and len(parts) == 3:
                record = self.service.start(request._body())
                if record.state == "FAILED":
                    self._execution_failure(request, record)
                else:
                    request._respond(
                        201,
                        success_response(
                            self._data(record), "Client execution processed"
                        ),
                    )
                return
            if method == "POST" and entity_id == "schedule-execution" and len(parts) == 3:
                record = self.service.schedule(request._body())
                request._respond(
                    201,
                    success_response(self._data(record), "Client execution scheduled"),
                )
                return
            if method == "GET" and entity_id == "execution-status" and len(parts) == 4:
                record = self.service.status(parts[3])
                request._respond(
                    200,
                    success_response(self._data(record), "Client execution status retrieved"),
                )
                return
            request._route_not_found()
        except InvalidExecutionRequest as error:
            self._error(request, 400, "INVALID_EXECUTION_REQUEST", str(error))
        except ExecutionAuthenticationFailed:
            self._error(request, 401, "UNAUTHORIZED", "Authentication required")
        except ExecutionClientNotFound:
            self._error(request, 404, "CLIENT_NOT_FOUND", "Client not found")
        except ExecutionNotFound:
            self._error(request, 404, "EXECUTION_NOT_FOUND", "Execution not found")
        except ConcurrentExecution:
            self._error(
                request,
                409,
                "CONCURRENT_EXECUTION",
                "A client execution is already running",
            )
        except Exception:
            self._error(
                request, 500, "CLIENT_EXECUTION_FAILED", "Client execution failed"
            )

    @staticmethod
    def _data(record: ClientExecutionRecord) -> Dict[str, Any]:
        return {
            "execution_id": record.execution_id,
            "client_id": record.client_id,
            "status": record.state.lower(),
            "workflow_instance_id": record.workflow_instance_id,
            "execution_state": record.state,
            "failure_step": record.failure_step,
            "error_reason": record.error_reason,
            "rollback_actions": list(record.rollback_actions),
            "output": dict(record.output),
            "transitions": [item.__dict__ for item in record.transitions],
        }

    @classmethod
    def _execution_failure(
        cls, request: Any, record: ClientExecutionRecord
    ) -> None:
        code = "CLIENT_EXECUTION_FAILED"
        message = "Client execution failed"
        record_error(code, message)
        request._log_error(code, message)
        data = cls._data(record)
        data["error"] = {"code": code, "message": message}
        request._respond(
            422, response_envelope(current_request_id(), "failure", data)
        )

    @staticmethod
    def _error(request: Any, status: int, code: str, message: str) -> None:
        request._log_error(code, message)
        request._respond(status, error_response(code, message))
