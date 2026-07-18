import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from bbi_os.auth import (
    AuthenticationRequired,
    Authenticator,
    Forbidden,
    InvalidToken,
)
from bbi_os.entity_routing import EntityRouteRegistry
from bbi_os.observability import (
    REQUEST_ID_HEADER,
    begin_request,
    current_request_id,
    end_request,
    get_observability,
    set_request_identity,
    timestamp,
)
from bbi_os.response_contract import (
    begin_execution_summary,
    end_execution_summary,
    execution_summary,
    record_error,
    response_envelope,
)
from bbi_os.task_management.errors import TaskNotFoundError, ValidationError
from bbi_os.task_management.service import TaskService


def success_response(data: Any, message: str = "") -> Dict[str, Any]:
    return response_envelope(current_request_id(), "success", data)


def error_response(code: str, message: str) -> Dict[str, Any]:
    record_error(code, message)
    return response_envelope(
        current_request_id(),
        "failure",
        {"error": {"code": code, "message": message}},
    )


class TaskRequestHandler(BaseHTTPRequestHandler):
    service: TaskService
    authenticator = Authenticator()
    route_registry = EntityRouteRegistry()
    route_registry.register("tasks", "tasks")

    def do_GET(self) -> None:
        self._observe_request("GET", self._get)

    def _get(self) -> None:
        if self._dispatch_entity("GET"):
            return
        route = self._route()
        if route == ("tasks", None):
            self._execute(
                lambda: self._respond(
                    200, success_response(self.service.list(), "Tasks retrieved")
                )
            )
        elif route and route[0] == "tasks" and route[1]:
            self._execute(
                lambda: self._respond(
                    200, success_response(self.service.get(route[1]), "Task retrieved")
                )
            )
        else:
            self._route_not_found()

    def do_POST(self) -> None:
        self._observe_request("POST", self._post)

    def _post(self) -> None:
        if self._dispatch_entity("POST"):
            return
        if self._route() != ("tasks", None):
            self._route_not_found()
            return
        self._execute(
            lambda: self._respond(
                201, success_response(self.service.create(self._body()), "Task created")
            )
        )

    def do_PATCH(self) -> None:
        self._observe_request("PATCH", self._patch)

    def _patch(self) -> None:
        if self._dispatch_entity("PATCH"):
            return
        route = self._route()
        if not route or route[0] != "tasks" or not route[1]:
            self._route_not_found()
            return
        self._execute(
            lambda: self._respond(
                200,
                success_response(
                    self.service.update(route[1], self._body()), "Task updated"
                ),
            )
        )

    def do_DELETE(self) -> None:
        self._observe_request("DELETE", self._delete)

    def _delete(self) -> None:
        if self._dispatch_entity("DELETE"):
            return
        route = self._route()
        if not route or route[0] != "tasks" or not route[1]:
            self._route_not_found()
            return

        def delete() -> None:
            self.service.delete(route[1])
            self._respond(200, success_response({}, "Task deleted"))

        self._execute(delete)

    def _execute(self, action: Any) -> None:
        try:
            action()
        except ValidationError as error:
            self._log_error("VALIDATION_ERROR", str(error))
            self._respond(400, error_response("VALIDATION_ERROR", str(error)))
        except TaskNotFoundError:
            self._log_error("TASK_NOT_FOUND", "Task not found")
            self._respond(404, error_response("TASK_NOT_FOUND", "Task not found"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._log_error("INVALID_JSON", "Request body must contain valid JSON")
            self._respond(
                400,
                error_response(
                    "INVALID_JSON", "Request body must contain valid JSON"
                ),
            )
        except Exception:
            self._log_error("INTERNAL_ERROR", "An unexpected error occurred")
            self._respond(
                500,
                error_response(
                    "INTERNAL_ERROR", "An unexpected error occurred"
                ),
            )

    def _observe_request(self, method: str, action: Any) -> None:
        observer = get_observability()
        endpoint = urlparse(self.path).path
        started_at = timestamp()
        token = begin_request(started_at, request_id=self.headers.get(REQUEST_ID_HEADER))
        summary_token = begin_execution_summary()
        started = time.perf_counter()
        self._response_status = None
        identity = self._authenticate_request()
        observer.log(
            "INFO",
            "request_started",
            "Request started",
            {"method": method, "endpoint": endpoint, "started_at": started_at},
        )
        try:
            if identity is None:
                self._log_error("INVALID_TOKEN", "Invalid authentication token")
                self._respond(
                    401,
                    error_response("INVALID_TOKEN", "Invalid authentication token"),
                )
            elif self._authorize_request(identity[0], identity[1], method):
                action()
        finally:
            ended_at = timestamp()
            duration_ms = (time.perf_counter() - started) * 1000
            performance = observer.record_request(endpoint, duration_ms)
            metadata = {
                "method": method,
                "endpoint": endpoint,
                "status": self._response_status,
                "started_at": started_at,
                "ended_at": ended_at,
                **performance,
            }
            observer.log("INFO", "request_completed", "Request completed", metadata)
            if performance["slow"]:
                observer.log("WARNING", "slow_request", "Slow request detected", metadata)
            end_execution_summary(summary_token)
            end_request(token)

    def _authenticate_request(self) -> Optional[Tuple[Any, bool]]:
        if self.route_registry.resolve(self.path) is None:
            return self.authenticator.authenticate({})
        try:
            user, authenticated = self.authenticator.authenticate(self.headers)
            set_request_identity(user.user_id, user.role)
            return user, authenticated
        except InvalidToken:
            return None

    def _authorize_request(self, user: Any, authenticated: bool, method: str) -> bool:
        if self.route_registry.resolve(self.path) is None:
            return True
        try:
            self.authenticator.authorize(user, authenticated, method)
            return True
        except AuthenticationRequired:
            self._log_error("UNAUTHORIZED", "Authentication required")
            self._respond(401, error_response("UNAUTHORIZED", "Authentication required"))
        except Forbidden:
            self._log_error("FORBIDDEN", "Insufficient permissions")
            self._respond(403, error_response("FORBIDDEN", "Insufficient permissions"))
        return False

    def _dispatch_entity(self, method: str) -> bool:
        route = self._resolved_entity_route()
        if route is None or route.handler == "tasks":
            return False
        self._execute(lambda: route.handler.handle(method, route.entity_id, self))
        return True

    def _resolved_entity_route(self) -> Any:
        path = urlparse(self.path).path
        if path == "/clients":
            path = "/v1/clients"
        return self.route_registry.resolve(path)

    def _log_error(self, error_code: str, error_message: str) -> None:
        get_observability().log(
            "ERROR",
            "request_error",
            "Request failed",
            {
                "error_code": error_code,
                "error_message": error_message,
                "error_timestamp": timestamp(),
                "context": {
                    "method": getattr(self, "command", ""),
                    "endpoint": urlparse(self.path).path,
                },
            },
        )

    def _body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValidationError("Invalid Content-Length") from error
        raw_body = self.rfile.read(length)
        return json.loads(raw_body.decode("utf-8"))

    def _route(self) -> Optional[Tuple[str, Optional[str]]]:
        route = self.route_registry.resolve(self.path)
        if route is None or route.handler != "tasks" or route.subpath:
            return None
        return "tasks", route.entity_id

    def _route_not_found(self) -> None:
        self._log_error("ROUTE_NOT_FOUND", "Route not found")
        self._respond(404, error_response("ROUTE_NOT_FOUND", "Route not found"))

    def _respond(self, status: int, body: Any) -> None:
        self._response_status = status
        if not isinstance(body, dict) or not {
            "request_id",
            "status",
            "data",
            "execution_summary",
        }.issubset(body):
            body = response_envelope(
                current_request_id(),
                "success" if 200 <= status < 400 else "failure",
                body,
            )
        else:
            body = dict(body)
            body["request_id"] = current_request_id()
            body["status"] = "success" if 200 <= status < 400 else "failure"
            body["execution_summary"] = execution_summary()
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:
        get_observability().log(
            "INFO", "http_access", "HTTP access", {"detail": format % args}
        )


def run_server(
    service: TaskService,
    host: str,
    port: int,
    authenticator: Optional[Authenticator] = None,
    route_registry: Optional[EntityRouteRegistry] = None,
) -> None:
    handler = type(
        "ConfiguredTaskRequestHandler",
        (TaskRequestHandler,),
        {
            "service": service,
            "authenticator": authenticator or Authenticator(),
            "route_registry": route_registry or TaskRequestHandler.route_registry,
        },
    )
    server = ThreadingHTTPServer((host, port), handler)
    get_observability().log(
        "INFO",
        "server_started",
        "BBIOS OS task API started",
        {"host": host, "port": port},
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        get_observability().log("INFO", "server_stopping", "BBIOS OS task API stopping")
    finally:
        server.server_close()
