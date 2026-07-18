from typing import Any
from urllib.parse import urlparse

from bbi_os.cockpit.models import CockpitControlError
from bbi_os.cockpit.service import CockpitService
from bbi_os.task_management.api import error_response, success_response


class CockpitApiHandler:
    """Internal cockpit adapter for versioned handler-style routes."""

    def __init__(self, service: CockpitService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: str, request: Any) -> None:
        try:
            if method == "GET" and entity_id == "system-overview":
                self._ok(request, self.service.system_overview(), "System overview retrieved")
                return
            if method == "GET" and entity_id == "client":
                client_id = self._subpath(request, 3)
                if not client_id:
                    request._route_not_found()
                    return
                self._ok(request, self.service.client(client_id), "Client view retrieved")
                return
            if method == "GET" and entity_id == "executions":
                self._ok(request, self.service.execution_monitor(), "Executions retrieved")
                return
            if method == "GET" and entity_id == "usage":
                self._ok(request, self.service.usage(), "Usage retrieved")
                return
            if method == "GET" and entity_id == "billing-summary":
                self._ok(request, self.service.billing(), "Billing summary retrieved")
                return
            if (
                method == "GET"
                and entity_id == "workflow"
                and self._subpath(request, 3) == "control"
            ):
                self._ok(
                    request,
                    self.service.workflow_control(),
                    "Workflow control retrieved",
                )
                return
            if (
                method == "POST"
                and entity_id == "workflow"
                and self._subpath(request, 3) == "execute"
            ):
                self._created(
                    request,
                    self.service.execute(request._body()),
                    "Workflow execution started",
                )
                return
            if (
                method == "POST"
                and entity_id == "workflow"
                and self._subpath(request, 3) == "retry"
            ):
                execution_id = self._subpath(request, 4)
                if not execution_id:
                    request._route_not_found()
                    return
                self._ok(request, self.service.retry(execution_id), "Workflow retried")
                return
            if (
                method == "POST"
                and entity_id == "workflow"
                and self._subpath(request, 3) == "cancel"
            ):
                execution_id = self._subpath(request, 4)
                if not execution_id:
                    request._route_not_found()
                    return
                self.service.cancel(execution_id)
                self._ok(request, {}, "Workflow cancelled")
                return
            request._route_not_found()
        except CockpitControlError as error:
            self._error(request, 400, "COCKPIT_CONTROL_ERROR", str(error))

    @staticmethod
    def _ok(request: Any, data: Any, message: str) -> None:
        request._respond(200, success_response(data, message))

    @staticmethod
    def _created(request: Any, data: Any, message: str) -> None:
        request._respond(201, success_response(data, message))

    @staticmethod
    def _error(request: Any, status: int, code: str, message: str) -> None:
        request._log_error(code, message)
        request._respond(status, error_response(code, message))

    @staticmethod
    def _subpath(request: Any, index: int) -> str:
        parts = [part for part in urlparse(request.path).path.split("/") if part]
        return parts[index] if len(parts) > index else ""
