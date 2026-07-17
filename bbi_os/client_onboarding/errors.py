class OnboardingError(Exception):
    pass


class InvalidOnboardingRequest(OnboardingError):
    pass


class InvalidOnboardingType(OnboardingError):
    pass


class OnboardingWorkflowNotFound(OnboardingError):
    pass


class OnboardingExecutionFailed(OnboardingError):
    pass


class OnboardingAuthenticationFailed(OnboardingError):
    pass

