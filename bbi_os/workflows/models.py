from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from bbi_os.observability import timestamp


TRIGGER_TYPES = {"manual", "event-based"}
ACTION_TYPES = {"entity_operation", "function_call"}
EXECUTION_STATUSES = {"pending", "running", "failed", "completed"}


class InvalidWorkflowDefinition(Exception):
    pass


class WorkflowNotFound(Exception):
    pass


class WorkflowExecutionError(Exception):
    pass


class WorkflowStepError(WorkflowExecutionError):
    pass


@dataclass(frozen=True)
class WorkflowStep:
    step_id: str
    step_name: str
    action_type: str
    target_entity: str
    input_mapping: Dict[str, Any] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.step_id or not self.step_name or not self.target_entity:
            raise InvalidWorkflowDefinition("Step ID, name, and target entity are required")
        if self.action_type not in ACTION_TYPES:
            raise InvalidWorkflowDefinition(f"Unsupported action type: {self.action_type}")
        if not isinstance(self.input_mapping, dict) or not isinstance(self.output_mapping, dict):
            raise InvalidWorkflowDefinition("Step mappings must be objects")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStep":
        try:
            step = cls(
                step_id=data["step_id"],
                step_name=data["step_name"],
                action_type=data["action_type"],
                target_entity=data["target_entity"],
                input_mapping=dict(data.get("input_mapping", {})),
                output_mapping=dict(data.get("output_mapping", {})),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidWorkflowDefinition("Invalid workflow step") from error
        step.validate()
        return step


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    trigger_type: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        if not self.workflow_id or not self.name or not self.description:
            raise InvalidWorkflowDefinition("Workflow ID, name, and description are required")
        if self.trigger_type not in TRIGGER_TYPES:
            raise InvalidWorkflowDefinition(f"Unsupported trigger type: {self.trigger_type}")
        if not self.steps:
            raise InvalidWorkflowDefinition("Workflow must include at least one step")
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise InvalidWorkflowDefinition("Workflow step IDs must be unique")
        for step in self.steps:
            step.validate()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        try:
            definition = cls(
                workflow_id=data["workflow_id"],
                name=data["name"],
                description=data["description"],
                steps=[WorkflowStep.from_dict(step) for step in data["steps"]],
                trigger_type=data["trigger_type"],
                input_schema=data.get("input_schema"),
                output_schema=data.get("output_schema"),
            )
        except (KeyError, TypeError) as error:
            raise InvalidWorkflowDefinition("Invalid workflow definition") from error
        definition.validate()
        return definition


@dataclass
class StepExecution:
    step_id: str
    step_name: str
    status: str
    started_at: str
    ended_at: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class WorkflowInstance:
    workflow_instance_id: str
    workflow_id: str
    current_step_index: int
    execution_status: str
    step_history: List[StepExecution]
    created_at: str
    updated_at: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def new(cls, instance_id: str, workflow_id: str, input_data: Dict[str, Any]) -> "WorkflowInstance":
        now = timestamp()
        return cls(instance_id, workflow_id, 0, "pending", [], now, now, input_data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowInstance":
        return cls(
            workflow_instance_id=data["workflow_instance_id"],
            workflow_id=data["workflow_id"],
            current_step_index=data["current_step_index"],
            execution_status=data["execution_status"],
            step_history=[StepExecution(**step) for step in data.get("step_history", [])],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            input_data=dict(data.get("input_data", {})),
            output_data=dict(data.get("output_data", {})),
        )

