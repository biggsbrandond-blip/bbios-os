from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from bbi_os.auth import Authenticator
from bbi_os.cockpit.client_management import (
    ClientManagementApiHandler,
    ClientManagementService,
)
from bbi_os.entity_repository import JsonEntityRepository
from bbi_os.observability import (
    REQUEST_ID_HEADER,
    begin_request,
    current_request_id,
    end_request,
    get_observability,
    set_request_identity,
    timestamp,
)
from bbi_os.response_contract import begin_execution_summary, end_execution_summary
from bbi_os.settings import get_settings
from bbi_os.task_management.api import TaskRequestHandler, error_response
from bbi_os.task_management.repository import JsonTaskRepository
from bbi_os.task_management.service import TaskService
from bbi_os.client_monetization.registry import ClientPlanRegistry


router = APIRouter()


class AdapterRequest:
    """Small request surface expected by existing handler-style APIs."""

    def __init__(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.command = method
        self.path = path
        self.headers = headers
        self._request_body = body or {}
        self._response: Optional[Tuple[int, Dict[str, Any]]] = None

    def _body(self) -> Dict[str, Any]:
        return dict(self._request_body)

    def _respond(self, status: int, body: Dict[str, Any]) -> None:
        self._response = (status, body)

    def _route_not_found(self) -> None:
        self._log_error("ROUTE_NOT_FOUND", "Route not found")
        self._respond(404, error_response("ROUTE_NOT_FOUND", "Route not found"))

    def _log_error(self, error_code: str, error_message: str) -> None:
        get_observability().log(
            "ERROR",
            "request_error",
            "Request failed",
            {
                "error_code": error_code,
                "error_message": error_message,
                "error_timestamp": timestamp(),
                "context": {"method": self.command, "endpoint": self.path},
            },
        )

    @property
    def response(self) -> Tuple[int, Dict[str, Any]]:
        if self._response is None:
            return 500, error_response("INTERNAL_ERROR", "An unexpected error occurred")
        return self._response


@lru_cache(maxsize=8)
def _task_service(data_dir: str) -> TaskService:
    return TaskService(JsonTaskRepository(Path(data_dir) / "tasks.json"))


@lru_cache(maxsize=8)
def _client_handler(data_dir: str) -> ClientManagementApiHandler:
    service = ClientManagementService(
        JsonEntityRepository("client", Path(data_dir) / "clients.json"),
        ClientPlanRegistry(Path(data_dir) / "plans.json"),
    )
    return ClientManagementApiHandler(service)


def _runtime_task_service() -> TaskService:
    settings = get_settings()
    return _task_service(str(settings.data_dir))


def _runtime_client_handler() -> ClientManagementApiHandler:
    settings = get_settings()
    return _client_handler(str(settings.data_dir))


def _headers(request: Request) -> Mapping[str, str]:
    return request.headers


def _json(status: int, body: Dict[str, Any]) -> JSONResponse:
    return JSONResponse(status_code=status, content=body)


def _dispatch_task(
    method: str,
    path: str,
    headers: Mapping[str, str],
    body: Optional[Dict[str, Any]] = None,
    service: Optional[TaskService] = None,
    authenticator: Optional[Authenticator] = None,
) -> Tuple[int, Dict[str, Any]]:
    handler = TaskRequestHandler.__new__(TaskRequestHandler)
    handler.path = path
    handler.command = method
    handler.service = service or _runtime_task_service()
    handler.authenticator = authenticator or Authenticator.from_environment()
    handler.route_registry = TaskRequestHandler.route_registry
    handler.headers = headers
    handler._body = lambda: body or {}

    captured: Dict[str, Tuple[int, Dict[str, Any]]] = {}

    def respond(status: int, response_body: Dict[str, Any]) -> None:
        handler._response_status = status
        captured["response"] = (status, response_body)

    handler._respond = respond
    getattr(handler, f"do_{method}")()
    return captured.get(
        "response",
        (500, error_response("INTERNAL_ERROR", "An unexpected error occurred")),
    )


def _dispatch_handler(
    handler: Any,
    method: str,
    path: str,
    entity_id: Optional[str],
    headers: Mapping[str, str],
    body: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any]]:
    request_token = begin_request(request_id=headers.get(REQUEST_ID_HEADER))
    summary_token = begin_execution_summary()
    request = AdapterRequest(method, path, headers, body)
    set_request_identity("anonymous", "readonly")
    try:
        handler.handle(method, entity_id, request)
        return request.response
    finally:
        end_execution_summary(summary_token)
        end_request(request_token)


@router.get("/v1/tasks")
def list_tasks(request: Request) -> JSONResponse:
    return _json(*_dispatch_task("GET", "/v1/tasks", _headers(request)))


@router.post("/v1/tasks")
def create_task(
    request: Request,
    body: Dict[str, Any] = Body(default_factory=dict),
) -> JSONResponse:
    return _json(*_dispatch_task("POST", "/v1/tasks", _headers(request), body))


@router.get("/v1/tasks/{task_id}")
def get_task(task_id: str, request: Request) -> JSONResponse:
    return _json(*_dispatch_task("GET", f"/v1/tasks/{task_id}", _headers(request)))


@router.patch("/v1/tasks/{task_id}")
def update_task(
    task_id: str,
    request: Request,
    body: Dict[str, Any] = Body(default_factory=dict),
) -> JSONResponse:
    return _json(
        *_dispatch_task("PATCH", f"/v1/tasks/{task_id}", _headers(request), body)
    )


@router.delete("/v1/tasks/{task_id}")
def delete_task(task_id: str, request: Request) -> JSONResponse:
    return _json(*_dispatch_task("DELETE", f"/v1/tasks/{task_id}", _headers(request)))


@router.get("/clients")
@router.get("/v1/clients")
def list_clients(request: Request) -> JSONResponse:
    return _json(
        *_dispatch_handler(
            _runtime_client_handler(), "GET", request.url.path, None, _headers(request)
        )
    )


@router.post("/clients")
@router.post("/v1/clients")
def create_client(
    request: Request,
    body: Dict[str, Any] = Body(default_factory=dict),
) -> JSONResponse:
    return _json(
        *_dispatch_handler(
            _runtime_client_handler(), "POST", request.url.path, None, _headers(request), body
        )
    )
