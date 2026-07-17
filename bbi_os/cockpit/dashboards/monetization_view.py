from collections import Counter
from typing import Any, Dict, Iterable

from bbi_os.client_monetization.service import ClientMonetizationService


class MonetizationDashboard:
    def __init__(self, monetization: ClientMonetizationService) -> None:
        self.monetization = monetization

    def usage(self, client_ids: Iterable[str]) -> Dict[str, Any]:
        clients = [self.monetization.metrics(client_id) for client_id in client_ids]
        return {
            "clients": clients,
            "plan_breakdown": dict(Counter(item["plan"] for item in clients)),
            "execution_volume": sum(
                item["usage_breakdown"]["workflows"] for item in clients
            ),
            "connector_usage": sum(
                item["usage_breakdown"]["connectors"] for item in clients
            ),
        }

    def billing(self, client_ids: Iterable[str]) -> Dict[str, Any]:
        summaries = [
            self.monetization.billing_summary(client_id) for client_id in client_ids
        ]
        return {
            "clients": summaries,
            "total_usage_units": sum(item["total_usage_units"] for item in summaries),
            "estimated_cost": round(sum(item["estimated_cost"] for item in summaries), 2),
        }

