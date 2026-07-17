from typing import Dict

from bbi_os.client_monetization.models import ClientPlan


DEFAULT_PLANS: Dict[str, ClientPlan] = {
    "basic": ClientPlan("basic", 100, False, 10, 10),
    "pro": ClientPlan("pro", 1_000, True, 50, 60),
    "enterprise": ClientPlan("enterprise", 10_000, True, 200, 600),
    "custom": ClientPlan("custom", 1_000, True, 100, 120),
}

