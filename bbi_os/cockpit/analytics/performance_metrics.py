from datetime import datetime
from typing import Any, Dict, Iterable

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.observability import Observability


class PerformanceMetricsEngine:
    def __init__(self, observability: Observability) -> None:
        self.observability = observability

    def calculate(self, records: Iterable[ClientExecutionRecord]) -> Dict[str, Any]:
        items = list(records)
        durations = [self._duration(item) for item in items]
        return {
            "average_workflow_duration_ms": round(sum(durations) / len(durations), 3)
            if durations
            else 0.0,
            "failure_frequency": sum(item.state == "FAILED" for item in items),
            "compensation_frequency": sum(
                any(transition.state == "COMPENSATING" for transition in item.transitions)
                for item in items
            ),
            "endpoint_metrics": self.observability.metrics.snapshot(),
        }

    @staticmethod
    def _duration(record: ClientExecutionRecord) -> float:
        start = datetime.fromisoformat(record.created_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(record.updated_at.replace("Z", "+00:00"))
        return max((end - start).total_seconds() * 1000, 0.0)

