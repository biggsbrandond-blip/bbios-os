from bbi_os.client_monetization.models import BillingSummary
from bbi_os.client_monetization.usage_tracker import UsageTracker


class BillingSummaryGenerator:
    def __init__(self, usage: UsageTracker) -> None:
        self.usage = usage

    def generate(self, client_id: str) -> BillingSummary:
        events = self.usage.for_client(client_id)
        breakdown = {"workflows": 0, "connectors": 0, "onboarding": 0}
        mapping = {
            "workflow_execution": "workflows",
            "connector_call": "connectors",
            "onboarding": "onboarding",
        }
        for event in events:
            breakdown[mapping[event.event_type]] += event.usage_units
        return BillingSummary(
            client_id=client_id,
            total_usage_units=sum(event.usage_units for event in events),
            estimated_cost=round(sum(event.estimated_cost for event in events), 2),
            usage_breakdown=breakdown,
        )
