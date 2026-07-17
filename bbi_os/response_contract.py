import time
from contextvars import ContextVar, Token
from typing import Any, Dict, Optional


_execution_state: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "execution_summary_state", default=None
)


def begin_execution_summary() -> Token:
    return _execution_state.set(
        {
            "started": time.perf_counter(),
            "workflow_instance_id": "",
            "steps_completed": [],
            "external_calls": [],
            "errors": [],
        }
    )


def end_execution_summary(token: Token) -> None:
    _execution_state.reset(token)


def record_event(event: str, metadata: Dict[str, Any]) -> None:
    state = _execution_state.get()
    if state is None:
        return
    workflow_instance_id = metadata.get("workflow_instance_id")
    if workflow_instance_id:
        state["workflow_instance_id"] = workflow_instance_id
    if event == "workflow_step_completed":
        step_id = metadata.get("step_id")
        if step_id and step_id not in state["steps_completed"]:
            state["steps_completed"].append(step_id)
    if event in {"external_request", "webhook_invocation"}:
        external_call = {
            key: metadata.get(key)
            for key in (
                "connector_id",
                "external_endpoint",
                "status",
                "status_code",
                "latency_ms",
            )
            if key in metadata
        }
        if external_call not in state["external_calls"]:
            state["external_calls"].append(external_call)
    if event == "request_error":
        record_error(
            str(metadata.get("error_code", "INTERNAL_ERROR")),
            str(metadata.get("error_message", "Request failed")),
        )


def record_error(code: str, message: str) -> None:
    state = _execution_state.get()
    if state is None:
        return
    error = {"code": code, "message": message}
    if error not in state["errors"]:
        state["errors"].append(error)


def execution_summary() -> Dict[str, Any]:
    state = _execution_state.get()
    if state is None:
        return {
            "workflow_instance_id": "",
            "duration_ms": 0,
            "steps_completed": [],
            "external_calls": [],
            "errors": [],
        }
    return {
        "workflow_instance_id": state["workflow_instance_id"],
        "duration_ms": round((time.perf_counter() - state["started"]) * 1000, 3),
        "steps_completed": list(state["steps_completed"]),
        "external_calls": list(state["external_calls"]),
        "errors": list(state["errors"]),
    }


def response_envelope(
    request_id: str, status: str, data: Any
) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "status": status,
        "data": data,
        "execution_summary": execution_summary(),
    }

