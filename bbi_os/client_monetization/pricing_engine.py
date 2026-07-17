from decimal import Decimal, ROUND_HALF_UP

from bbi_os.client_monetization.models import ClientPlan


RATES = {
    "basic": {
        "workflow_execution": Decimal("0.10"),
        "connector_call": Decimal("0.05"),
        "onboarding": Decimal("0.20"),
    },
    "pro": {
        "workflow_execution": Decimal("0.08"),
        "connector_call": Decimal("0.04"),
        "onboarding": Decimal("0.15"),
    },
    "enterprise": {
        "workflow_execution": Decimal("0.05"),
        "connector_call": Decimal("0.02"),
        "onboarding": Decimal("0.10"),
    },
    "custom": {
        "workflow_execution": Decimal("0.08"),
        "connector_call": Decimal("0.03"),
        "onboarding": Decimal("0.15"),
    },
}


class PricingEngine:
    def estimate(self, plan: ClientPlan, event_type: str, usage_units: int) -> float:
        amount = RATES[plan.plan_id][event_type] * usage_units
        return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

