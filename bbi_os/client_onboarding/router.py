from bbi_os.client_onboarding.models import OnboardingRequest
from bbi_os.client_onboarding.registry import OnboardingRegistry, OnboardingRoute


class OnboardingRouter:
    def __init__(self, registry: OnboardingRegistry) -> None:
        self.registry = registry

    def route(self, request: OnboardingRequest) -> OnboardingRoute:
        return self.registry.resolve(request.request_type)

