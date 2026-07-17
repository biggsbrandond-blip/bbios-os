from collections import Counter
from typing import Any, Dict, Iterable

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.client_monetization.service import ClientMonetizationService


class UsageInsightsEngine:
    def __init__(self, monetization: ClientMonetizationService) -> None:
        self.monetization = monetization

    def calculate(
        self, client_ids: Iterable[str], records: Iterable[ClientExecutionRecord]
    ) -> Dict[str, Any]:
        executions = list(records)
        workflow_counts = Counter(item.workflow_id for item in executions)
        usage = [self.monetization.metrics(client_id) for client_id in client_ids]
        return {
            "executions_per_client": dict(Counter(item.client_id for item in executions)),
            "top_workflows": [
                {"workflow_id": workflow_id, "executions": count}
                for workflow_id, count in workflow_counts.most_common(10)
            ],
            "estimated_cost": round(sum(item["estimated_cost"] for item in usage), 2),
            "total_usage_units": sum(item["total_usage_units"] for item in usage),
        }

