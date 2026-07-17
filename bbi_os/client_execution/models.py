from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from bbi_os.client_execution.errors import InvalidExecutionRequest
from bbi_os.observability import timestamp


EXECUTION_TYPES = {"one_time", "scheduled", "recurring"}


@dataclass(frozen=True)
class ClientExecutionRequest:
    client_id: str
    execution_type: str
    workflow_id: str
    input: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientExecutionRequest":
        if not isinstance(data, dict):
            raise InvalidExecutionRequest("Execution request must be an object")
        try:
            request = cls(
                client_id=data["client_id"],
                execution_type=data["execution_type"],
                workflow_id=data["workflow_id"],
                input=data["input"],
            )
        except KeyError as error:
            raise InvalidExecutionRequest(
                "Execution request is missing required fields"
            ) from error
        if not isinstance(request.client_id, str) or not request.client_id:
            raise InvalidExecutionRequest("client_id must be a non-empty string")
        if request.execution_type not in EXECUTION_TYPES:
            raise InvalidExecutionRequest("Unsupported execution_type")
        if not isinstance(request.workflow_id, str) or not request.workflow_id:
            raise InvalidExecutionRequest("workflow_id must be a non-empty string")
        if not isinstance(request.input, dict):
            raise InvalidExecutionRequest("input must be an object")
        return request


@dataclass(frozen=True)
class StateTransition:
    state: str
    timestamp: str


@dataclass
class ClientExecutionRecord:
    execution_id: str
    client_id: str
    execution_type: str
    workflow_id: str
    input_data: Dict[str, Any]
    state: str
    transitions: List[StateTransition]
    created_at: str
    updated_at: str
    workflow_instance_id: str = ""
    failure_step: Optional[str] = None
    error_reason: Optional[str] = None
    rollback_actions: List[str] = field(default_factory=list)
    output: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def new(
        cls,
        execution_id: str,
        request: ClientExecutionRequest,
    ) -> "ClientExecutionRecord":
        now = timestamp()
        return cls(
            execution_id=execution_id,
            client_id=request.client_id,
            execution_type=request.execution_type,
            workflow_id=request.workflow_id,
            input_data=dict(request.input),
            state="PENDING",
            transitions=[StateTransition("PENDING", now)],
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientExecutionRecord":
        return cls(
            execution_id=data["execution_id"],
            client_id=data["client_id"],
            execution_type=data["execution_type"],
            workflow_id=data["workflow_id"],
            input_data=dict(data.get("input_data", {})),
            state=data["state"],
            transitions=[StateTransition(**item) for item in data.get("transitions", [])],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            workflow_instance_id=data.get("workflow_instance_id", ""),
            failure_step=data.get("failure_step"),
            error_reason=data.get("error_reason"),
            rollback_actions=list(data.get("rollback_actions", [])),
            output=dict(data.get("output", {})),
        )

