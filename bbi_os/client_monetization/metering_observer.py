import threading
from typing import Any, Dict

from bbi_os.client_monetization.service import ClientMonetizationService


class UsageSignalMeter:
    """Failure-isolated adapter from existing observability events to usage records."""

    def __init__(self, service: ClientMonetizationService) -> None:
        self.service = service
        self._lock = threading.Lock()
        self._requests: Dict[str, Dict[str, int]] = {}

    def __call__(self, record: Dict[str, Any]) -> None:
        request_id = record.get("request_id", "system")
        event = record.get("event")
        metadata = record.get("metadata", {})
        if event not in {
            "workflow_step_completed",
            "external_request",
            "client_execution_completed",
            "client_execution_recorded",
            "client_onboarding_completed",
        }:
            return
        with self._lock:
            counters = self._requests.setdefault(
                request_id, {"steps": 0, "connectors": 0}
            )
            if event == "workflow_step_completed":
                counters["steps"] += 1
                return
            if event == "external_request":
                counters["connectors"] += 1
                return
            if event == "client_execution_completed" or (
                event == "client_execution_recorded"
                and metadata.get("execution_state") == "FAILED"
            ):
                snapshot = dict(counters)
                self._requests.pop(request_id, None)
                client_id = metadata.get("client_id", "")
                workflow_instance_id = metadata.get("workflow_instance_id", "")
                execution_id = metadata.get("execution_id", "")
            elif event == "client_onboarding_completed":
                snapshot = dict(counters)
                self._requests.pop(request_id, None)
                client_id = metadata.get("entity_id", "")
                workflow_instance_id = metadata.get("workflow_instance_id", "")
                execution_id = metadata.get("onboarding_request_id", "")
                self._safe_record(
                    client_id,
                    "onboarding",
                    1,
                    {
                        "workflow_instance_id": workflow_instance_id,
                        "onboarding_request_id": execution_id,
                    },
                )
                if snapshot["connectors"]:
                    self._safe_record(
                        client_id,
                        "connector_call",
                        snapshot["connectors"],
                        {"workflow_instance_id": workflow_instance_id},
                    )
                return
            else:
                return

        self._safe_record(
            client_id,
            "workflow_execution",
            1 + snapshot["steps"],
            {
                "workflow_instance_id": workflow_instance_id,
                "execution_id": execution_id,
                "workflow_steps": snapshot["steps"],
                "execution_state": metadata.get("execution_state"),
            },
        )
        if snapshot["connectors"]:
            self._safe_record(
                client_id,
                "connector_call",
                snapshot["connectors"],
                {"workflow_instance_id": workflow_instance_id},
            )

    def _safe_record(
        self,
        client_id: str,
        event_type: str,
        usage_units: int,
        metadata: Dict[str, Any],
    ) -> None:
        try:
            self.service.record_automatic(
                client_id, event_type, usage_units, metadata
            )
        except Exception:
            # Monetization failures must never affect COS-001/COS-002 execution.
            return
