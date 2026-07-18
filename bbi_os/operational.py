import time
from typing import Any

from bbi_os.observability import (
    REQUEST_ID_HEADER,
    begin_request,
    end_request,
    get_observability,
    normalize_request_id,
    timestamp,
)


def install_operational_middleware(application: Any) -> None:
    @application.middleware("http")
    async def correlation_id_middleware(request: Any, call_next: Any) -> Any:
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        started_at = timestamp()
        token = begin_request(started_at, request_id=request_id)
        started = time.perf_counter()
        observer = get_observability()
        endpoint = request.url.path
        method = request.method
        observer.log(
            "INFO",
            "fastapi_request_started",
            "FastAPI request started",
            {"method": method, "endpoint": endpoint, "started_at": started_at},
        )
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            observer.log(
                "INFO",
                "fastapi_request_completed",
                "FastAPI request completed",
                {
                    "method": method,
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "started_at": started_at,
                    "ended_at": timestamp(),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                },
            )
            return response
        finally:
            end_request(token)
