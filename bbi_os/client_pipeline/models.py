from dataclasses import asdict, dataclass
from typing import Any, Dict

from bbi_os.client_pipeline.errors import InvalidClientRequest


@dataclass(frozen=True)
class ClientRequest:
    type: str
    payload: Dict[str, Any]
    user_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientRequest":
        if not isinstance(data, dict):
            raise InvalidClientRequest("Client request must be an object")
        try:
            request = cls(
                type=data["type"],
                payload=data["payload"],
                user_id=data["user_id"],
            )
        except KeyError as error:
            raise InvalidClientRequest("Client request is missing required fields") from error
        if not isinstance(request.type, str) or not request.type:
            raise InvalidClientRequest("Client request type must be a non-empty string")
        if not isinstance(request.payload, dict):
            raise InvalidClientRequest("Client request payload must be an object")
        if not isinstance(request.user_id, str) or not request.user_id:
            raise InvalidClientRequest("Client request user_id must be a non-empty string")
        return request


@dataclass(frozen=True)
class ClientPipelineResult:
    request_type: str
    workflow_template_id: str
    workflow_version: str
    workflow_instance_id: str
    status: str
    output: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

