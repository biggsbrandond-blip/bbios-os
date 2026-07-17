class MonetizationError(Exception):
    pass


class MonetizationClientNotFound(MonetizationError):
    pass


class InvalidUsageEvent(MonetizationError):
    pass


class PlanLimitExceeded(MonetizationError):
    pass


class ConnectorAccessDenied(MonetizationError):
    pass


class MonetizationAuthenticationFailed(MonetizationError):
    pass

