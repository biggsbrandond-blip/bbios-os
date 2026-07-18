from typing import Any, Dict, Optional
from uuid import uuid4

from bbi_os.client_monetization.billing import BillingSummaryGenerator
from bbi_os.client_monetization.errors import (
    MonetizationAuthenticationFailed,
    MonetizationClientNotFound,
)
from bbi_os.client_monetization.metering import PlanEnforcer
from bbi_os.client_monetization.models import UsageEvent, UsageEventRequest
from bbi_os.client_monetization.pricing_engine import PricingEngine
from bbi_os.client_monetization.registry import ClientPlanRegistry
from bbi_os.client_monetization.usage_tracker import UsageTracker
from bbi_os.entity_repository import EntityRepository
from bbi_os.observability import current_request_context, get_observability, timestamp


class ClientMonetizationService:
    def __init__(
        self,
        clients: EntityRepository,
        plans: ClientPlanRegistry,
        usage: UsageTracker,
        pricing: PricingEngine,
        enforcer: Optional[PlanEnforcer] = None,
        billing: Optional[BillingSummaryGenerator] = None,
    ) -> None:
        self.clients = clients
        self.plans = plans
        self.usage = usage
        self.pricing = pricing
        self.enforcer = enforcer or PlanEnforcer(usage)
        self.billing = billing or BillingSummaryGenerator(usage)

    def get_plan(self, client_id: str) -> Dict[str, Any]:
        self._validate_client(client_id, require_auth=True)
        return self.plans.plan_for(client_id).to_dict()

    def track(self, data: Dict[str, Any]) -> UsageEvent:
        event = UsageEventRequest.from_dict(data)
        self._validate_client(event.client_id, require_auth=True)
        return self._record(event, source="api", enforce_limits=True)

    def record_automatic(
        self,
        client_id: str,
        event_type: str,
        usage_units: int,
        metadata: Dict[str, Any],
    ) -> UsageEvent:
        self._validate_client(client_id, require_auth=False)
        request = UsageEventRequest(client_id, event_type, usage_units, metadata)
        return self._record(request, source="system", enforce_limits=False)

    def metrics(self, client_id: str) -> Dict[str, Any]:
        self._validate_client(client_id, require_auth=True)
        events = self.usage.for_client(client_id)
        summary = self.billing.generate(client_id)
        return {
            "client_id": client_id,
            "plan": self.plans.plan_for(client_id).plan_id,
            "event_count": len(events),
            "total_usage_units": summary.total_usage_units,
            "estimated_cost": summary.estimated_cost,
            "usage_breakdown": summary.usage_breakdown,
        }

    def billing_summary(self, client_id: str) -> Dict[str, Any]:
        self._validate_client(client_id, require_auth=True)
        return self.billing.generate(client_id).to_dict()

    def _record(
        self,
        request: UsageEventRequest,
        source: str,
        enforce_limits: bool,
    ) -> UsageEvent:
        plan = self.plans.plan_for(request.client_id)
        if enforce_limits:
            self.enforcer.enforce(plan, request)
        event = UsageEvent(
            usage_event_id=str(uuid4()),
            client_id=request.client_id,
            event_type=request.event_type,
            usage_units=request.usage_units,
            estimated_cost=self.pricing.estimate(
                plan, request.event_type, request.usage_units
            ),
            metadata=dict(request.metadata),
            timestamp=timestamp(),
            source=source,
        )
        self.usage.record(event)
        get_observability().log(
            "INFO",
            "client_usage_recorded",
            "Client usage recorded",
            {
                "event_type": "client_usage_recorded",
                "client_id": request.client_id,
                "usage_event_type": request.event_type,
                "usage_units": request.usage_units,
                "estimated_cost": event.estimated_cost,
                "source": source,
            },
        )
        return event

    def _validate_client(self, client_id: str, require_auth: bool) -> None:
        if require_auth and current_request_context()["user_id"] in {
            "anonymous",
            "system",
            "",
        }:
            raise MonetizationAuthenticationFailed("Authentication required")
        if self.clients.get(client_id) is None:
            raise MonetizationClientNotFound("Client not found")

