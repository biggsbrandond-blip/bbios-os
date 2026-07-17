from dataclasses import asdict, dataclass
from typing import Any, Dict

from bbi_os.client_monetization.errors import InvalidUsageEvent


USAGE_EVENT_TYPES = {"workflow_execution", "onboarding", "connector_call"}


@dataclass(frozen=True)
class ClientPlan:
    plan_id: str
    execution_limit: int
    connector_access: bool
    workflow_complexity_limit: int
    rate_limit_per_minute: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsageEventRequest:
    client_id: str
    event_type: str
    usage_units: int
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageEventRequest":
        if not isinstance(data, dict):
            raise InvalidUsageEvent("Usage event must be an object")
        try:
            event = cls(
                client_id=data["client_id"],
                event_type=data["event_type"],
                usage_units=data["usage_units"],
                metadata=data.get("metadata", {}),
            )
        except KeyError as error:
            raise InvalidUsageEvent("Usage event is missing required fields") from error
        if not isinstance(event.client_id, str) or not event.client_id:
            raise InvalidUsageEvent("client_id must be a non-empty string")
        if event.event_type not in USAGE_EVENT_TYPES:
            raise InvalidUsageEvent("Unsupported usage event type")
        if (
            not isinstance(event.usage_units, int)
            or isinstance(event.usage_units, bool)
            or event.usage_units <= 0
        ):
            raise InvalidUsageEvent("usage_units must be a positive integer")
        if not isinstance(event.metadata, dict):
            raise InvalidUsageEvent("metadata must be an object")
        return event


@dataclass(frozen=True)
class UsageEvent:
    usage_event_id: str
    client_id: str
    event_type: str
    usage_units: int
    estimated_cost: float
    metadata: Dict[str, Any]
    timestamp: str
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageEvent":
        return cls(**data)


@dataclass(frozen=True)
class BillingSummary:
    client_id: str
    total_usage_units: int
    estimated_cost: float
    usage_breakdown: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
