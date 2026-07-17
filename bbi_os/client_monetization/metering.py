from bbi_os.client_monetization.errors import (
    ConnectorAccessDenied,
    PlanLimitExceeded,
)
from bbi_os.client_monetization.models import ClientPlan, UsageEventRequest
from bbi_os.client_monetization.usage_tracker import UsageTracker


class PlanEnforcer:
    def __init__(self, usage: UsageTracker) -> None:
        self.usage = usage

    def enforce(self, plan: ClientPlan, event: UsageEventRequest) -> None:
        if event.event_type == "connector_call" and not plan.connector_access:
            raise ConnectorAccessDenied("Client plan does not allow connector usage")
        if self.usage.total_units(event.client_id) + event.usage_units > plan.execution_limit:
            raise PlanLimitExceeded("Client plan usage limit exceeded")
        workflow_steps = event.metadata.get("workflow_steps", 0)
        if (
            event.event_type == "workflow_execution"
            and isinstance(workflow_steps, int)
            and workflow_steps > plan.workflow_complexity_limit
        ):
            raise PlanLimitExceeded("Workflow complexity exceeds client plan")
        if self.usage.recent_count(event.client_id) >= plan.rate_limit_per_minute:
            raise PlanLimitExceeded("Client plan rate limit exceeded")

