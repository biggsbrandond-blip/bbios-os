from dataclasses import asdict, dataclass
from typing import Any, Dict

from bbi_os.client_onboarding.errors import InvalidOnboardingRequest


@dataclass(frozen=True)
class OnboardingRequest:
    user_id: str
    client_name: str
    request_type: str
    payload: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OnboardingRequest":
        if not isinstance(data, dict):
            raise InvalidOnboardingRequest("Onboarding request must be an object")
        try:
            request = cls(
                user_id=data["user_id"],
                client_name=data["client_name"],
                request_type=data["request_type"],
                payload=data["payload"],
            )
        except KeyError as error:
            raise InvalidOnboardingRequest(
                "Onboarding request is missing required fields"
            ) from error
        for field_name in ("user_id", "client_name", "request_type"):
            value = getattr(request, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidOnboardingRequest(
                    f"Onboarding {field_name} must be a non-empty string"
                )
        if not isinstance(request.payload, dict):
            raise InvalidOnboardingRequest("Onboarding payload must be an object")
        return request


@dataclass(frozen=True)
class OnboardingResult:
    onboarding_request_id: str
    client_entity_id: str
    onboarding_entity_id: str
    workflow_template_id: str
    workflow_instance_id: str
    task_id: str
    status: str
    output: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

