import time
from threading import Lock
from typing import Any

from bbi_os.observability import (
    REQUEST_ID_HEADER,
    begin_request,
    end_request,
    get_observability,
    normalize_request_id,
    timestamp,
)


class OperationalMetrics:
    def __init__(self) -> None:
        self._started_at = time.monotonic()
        self._lock = Lock()
        self._requests_received = 0
        self._requests_completed = 0
        self._requests_failed = 0
        self._total_duration_ms = 0.0

    def record_received(self) -> None:
        with self._lock:
            self._requests_received += 1

    def record_completed(self, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self._requests_completed += 1
            if status_code >= 500:
                self._requests_failed += 1
            self._total_duration_ms += duration_ms

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            average_duration = (
                self._total_duration_ms / self._requests_completed
                if self._requests_completed
                else 0.0
            )
            return {
                "requests_received": self._requests_received,
                "requests_completed": self._requests_completed,
                "requests_failed": self._requests_failed,
                "average_duration_ms": round(average_duration, 3),
                "uptime_seconds": round(time.monotonic() - self._started_at, 3),
            }


_operational_metrics = OperationalMetrics()


def get_operational_metrics() -> OperationalMetrics:
    return _operational_metrics


def install_operational_middleware(application: Any) -> None:
    @application.middleware("http")
    async def correlation_id_middleware(request: Any, call_next: Any) -> Any:
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        started_at = timestamp()
        token = begin_request(started_at, request_id=request_id)
        started = time.perf_counter()
        observer = get_observability()
        metrics = get_operational_metrics()
        endpoint = request.url.path
        method = request.method
        metrics.record_received()
        observer.log(
            "INFO",
            "fastapi_request_started",
            "FastAPI request started",
            {"method": method, "endpoint": endpoint, "started_at": started_at},
        )
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            metrics.record_completed(response.status_code, duration_ms)
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
                    "duration_ms": duration_ms,
                },
            )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 3)
            metrics.record_completed(500, duration_ms)
            raise
        finally:
            end_request(token)
