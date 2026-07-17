from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple
from uuid import uuid4

from bbi_os.observability import get_observability, timestamp
from bbi_os.workflows.models import (
    InvalidWorkflowDefinition,
    StepExecution,
    WorkflowDefinition,
    WorkflowExecutionError,
    WorkflowInstance,
    WorkflowNotFound,
    WorkflowStep,
    WorkflowStepError,
)
from bbi_os.workflows.repository import WorkflowRepository


@dataclass
class ActionResult:
    output: Dict[str, Any]
    rollback_data: Optional[Dict[str, Any]] = None


class ActionHandler(Protocol):
    def execute(self, inputs: Dict[str, Any]) -> ActionResult: ...

    def rollback(self, rollback_data: Dict[str, Any]) -> None: ...


class WorkflowActionRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[Tuple[str, str], ActionHandler] = {}

    def register(self, action_type: str, target_entity: str, handler: ActionHandler) -> None:
        key = (action_type, target_entity)
        if key in self._handlers:
            raise ValueError(f"Action handler already registered for {key}")
        self._handlers[key] = handler

    def handler_for(self, action_type: str, target_entity: str) -> ActionHandler:
        try:
            return self._handlers[(action_type, target_entity)]
        except KeyError as error:
            raise WorkflowStepError(
                f"No action handler for {action_type}:{target_entity}"
            ) from error


class WorkflowEngine:
    def __init__(
        self, repository: WorkflowRepository, actions: WorkflowActionRegistry
    ) -> None:
        self.repository = repository
        self.actions = actions

    def create_definition(self, data: Dict[str, Any]) -> WorkflowDefinition:
        definition = WorkflowDefinition.from_dict(data)
        return self.repository.save_definition(definition)

    def trigger(self, workflow_id: str, input_data: Dict[str, Any]) -> WorkflowInstance:
        definition = self._definition(workflow_id)
        if definition.trigger_type != "manual":
            raise WorkflowExecutionError("Event-based workflows cannot be triggered manually")
        instance = WorkflowInstance.new(str(uuid4()), workflow_id, dict(input_data))
        self.repository.save_instance(instance)
        return self._execute(definition, instance)

    def retry(self, instance_id: str) -> WorkflowInstance:
        instance = self.get_status(instance_id)
        if instance.execution_status != "failed":
            raise WorkflowExecutionError("Only failed workflows can be retried")
        instance.current_step_index = 0
        instance.execution_status = "pending"
        instance.step_history = []
        instance.output_data = {}
        instance.updated_at = timestamp()
        self.repository.save_instance(instance)
        return self._execute(self._definition(instance.workflow_id), instance)

    def get_status(self, instance_id: str) -> WorkflowInstance:
        instance = self.repository.get_instance(instance_id)
        if instance is None:
            raise WorkflowNotFound(f"Workflow instance '{instance_id}' was not found")
        return instance

    def get_history(self, instance_id: str) -> List[StepExecution]:
        return self.get_status(instance_id).step_history

    def _definition(self, workflow_id: str) -> WorkflowDefinition:
        definition = self.repository.get_definition(workflow_id)
        if definition is None:
            raise WorkflowNotFound(f"Workflow '{workflow_id}' was not found")
        return definition

    def _execute(
        self, definition: WorkflowDefinition, instance: WorkflowInstance
    ) -> WorkflowInstance:
        instance.execution_status = "running"
        instance.updated_at = timestamp()
        self.repository.save_instance(instance)
        self._event("workflow_execution_started", definition, instance, "", "running")
        context: Dict[str, Any] = {
            "input": instance.input_data,
            "steps": {},
            "output": instance.output_data,
        }
        completed: List[Tuple[WorkflowStep, ActionHandler, ActionResult, StepExecution]] = []

        for index, step in enumerate(definition.steps):
            instance.current_step_index = index
            history = StepExecution(step.step_id, step.step_name, "running", timestamp())
            instance.step_history.append(history)
            instance.updated_at = timestamp()
            self.repository.save_instance(instance)
            self._event("workflow_step_started", definition, instance, step.step_id, "running")
            try:
                inputs = self._resolve_mapping(step.input_mapping, context)
                handler = self.actions.handler_for(step.action_type, step.target_entity)
                result = handler.execute(inputs)
                if not isinstance(result.output, dict):
                    raise WorkflowStepError("Workflow action output must be an object")
                context["steps"][step.step_id] = result.output
                mapped_output = self._resolve_mapping(
                    step.output_mapping, {**context, "result": result.output}
                )
                context["output"].update(mapped_output)
                history.status = "completed"
                history.output = result.output
                history.ended_at = timestamp()
                completed.append((step, handler, result, history))
                instance.current_step_index = index + 1
                instance.output_data = context["output"]
                instance.updated_at = timestamp()
                self.repository.save_instance(instance)
                self._event(
                    "workflow_step_completed", definition, instance, step.step_id, "completed"
                )
            except Exception as error:
                history.status = "failed"
                history.error = str(error)
                history.ended_at = timestamp()
                instance.execution_status = "failed"
                instance.updated_at = timestamp()
                self.repository.save_instance(instance)
                self._event("workflow_step_failed", definition, instance, step.step_id, "failed")
                self._rollback(definition, instance, completed)
                self._event("workflow_execution_failed", definition, instance, step.step_id, "failed")
                return instance

        instance.execution_status = "completed"
        instance.updated_at = timestamp()
        self.repository.save_instance(instance)
        self._event("workflow_execution_completed", definition, instance, "", "completed")
        return instance

    def _rollback(
        self,
        definition: WorkflowDefinition,
        instance: WorkflowInstance,
        completed: List[Tuple[WorkflowStep, ActionHandler, ActionResult, StepExecution]],
    ) -> None:
        for step, handler, result, history in reversed(completed):
            if result.rollback_data is None:
                continue
            try:
                handler.rollback(result.rollback_data)
                history.status = "rolled_back"
                self._event(
                    "workflow_step_rolled_back",
                    definition,
                    instance,
                    step.step_id,
                    "rolled_back",
                )
            except Exception:
                history.status = "rollback_failed"
                self._event(
                    "workflow_step_rollback_failed",
                    definition,
                    instance,
                    step.step_id,
                    "rollback_failed",
                )
        instance.updated_at = timestamp()
        self.repository.save_instance(instance)

    @classmethod
    def _resolve_mapping(
        cls, mapping: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {key: cls._resolve(value, context) for key, value in mapping.items()}

    @classmethod
    def _resolve(cls, value: Any, context: Dict[str, Any]) -> Any:
        if not isinstance(value, str) or not value.startswith("$"):
            return value
        current: Any = context
        for part in value[1:].split("."):
            if not isinstance(current, dict) or part not in current:
                raise WorkflowStepError(f"Unable to resolve mapping: {value}")
            current = current[part]
        return current

    @staticmethod
    def _event(
        event_type: str,
        definition: WorkflowDefinition,
        instance: WorkflowInstance,
        step_id: str,
        status: str,
    ) -> None:
        get_observability().log(
            "ERROR" if status in {"failed", "rollback_failed"} else "INFO",
            event_type,
            event_type.replace("_", " ").capitalize(),
            {
                "event_type": event_type,
                "workflow_id": definition.workflow_id,
                "workflow_instance_id": instance.workflow_instance_id,
                "step_id": step_id,
                "execution_status": status,
            },
        )
