import json
import sys
import threading
import time
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Callable, Dict, IO, List, Optional
from uuid import uuid4

from bbi_os.response_contract import record_event


REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 128

_request_context: ContextVar[Dict[str, str]] = ContextVar(
    "request_context",
    default={
        "request_id": "system",
        "user_id": "system",
        "role": "system",
        "request_timestamp": "",
    },
)


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def current_request_id() -> str:
    return _request_context.get()["request_id"]


def current_request_context() -> Dict[str, str]:
    return dict(_request_context.get())


def _is_valid_request_id(value: str) -> bool:
    return (
        bool(value)
        and len(value) <= MAX_REQUEST_ID_LENGTH
        and all(character.isprintable() and not character.isspace() for character in value)
    )


def normalize_request_id(request_id: Optional[str] = None) -> str:
    if request_id is not None:
        normalized = request_id.strip()
        if _is_valid_request_id(normalized):
            return normalized
    return str(uuid4())


def begin_request(
    request_timestamp: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Token:
    return _request_context.set(
        {
            "request_id": normalize_request_id(request_id),
            "user_id": "anonymous",
            "role": "readonly",
            "request_timestamp": request_timestamp or timestamp(),
        }
    )


def set_request_identity(user_id: str, role: str) -> None:
    context = current_request_context()
    context.update({"user_id": user_id, "role": role})
    _request_context.set(context)


def end_request(token: Token) -> None:
    _request_context.reset(token)


class PerformanceMetrics:
    """Thread-safe, process-local request timing aggregation."""

    def __init__(self, slow_request_ms: float = 500.0) -> None:
        self.slow_request_ms = slow_request_ms
        self._lock = threading.Lock()
        self._endpoints: Dict[str, Dict[str, float]] = {}

    def record(self, endpoint: str, duration_ms: float) -> Dict[str, Any]:
        with self._lock:
            metric = self._endpoints.setdefault(endpoint, {"count": 0, "total_ms": 0.0})
            metric["count"] += 1
            metric["total_ms"] += duration_ms
            return {
                "endpoint": endpoint,
                "duration_ms": round(duration_ms, 3),
                "average_duration_ms": round(metric["total_ms"] / metric["count"], 3),
                "request_count": int(metric["count"]),
                "slow": duration_ms > self.slow_request_ms,
                "slow_request_threshold_ms": self.slow_request_ms,
            }

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                endpoint: {
                    "request_count": int(metric["count"]),
                    "average_duration_ms": round(
                        metric["total_ms"] / metric["count"], 3
                    ),
                }
                for endpoint, metric in self._endpoints.items()
            }


class Observability:
    """Emits structured JSON logs and owns internal performance metrics."""

    def __init__(
        self,
        stream: Optional[IO[str]] = None,
        slow_request_ms: float = 500.0,
    ) -> None:
        self.stream = stream or sys.stdout
        self.metrics = PerformanceMetrics(slow_request_ms)
        self._lock = threading.Lock()
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def log(
        self,
        level: str,
        event: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = current_request_context()
        record = {
            "timestamp": timestamp(),
            "level": level.upper(),
            "event": event,
            "request_id": context["request_id"],
            "user_id": context["user_id"],
            "role": context["role"],
            "message": message,
            "metadata": metadata or {},
        }
        record_event(event, record["metadata"])
        with self._lock:
            self.stream.write(json.dumps(record, sort_keys=True) + "\n")
            self.stream.flush()
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(record)
            except Exception:
                # Observability consumers must never interrupt system execution.
                continue
        return record

    def add_listener(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def task_event(self, event_type: str, entity_id: str) -> Dict[str, Any]:
        return self.log(
            "INFO",
            event_type,
            event_type.replace("_", " ").capitalize(),
            {"event_type": event_type, "entity_id": entity_id},
        )

    def record_request(self, endpoint: str, duration_ms: float) -> Dict[str, Any]:
        return self.metrics.record(endpoint, duration_ms)


_observer = Observability()


def get_observability() -> Observability:
    return _observer


def set_observability(observer: Observability) -> Observability:
    """Replace the process observer and return the previous instance (primarily for tests)."""
    global _observer
    previous = _observer
    _observer = observer
    return previous
