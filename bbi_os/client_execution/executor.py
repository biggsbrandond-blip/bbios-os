from dataclasses import dataclass
from typing import Any, Dict

from bbi_os.client_execution.errors import ExecutionWorkflowNotFound
from bbi_os.workflows.models import WorkflowInstance
from bbi_os.workflows.templates import (
    TemplateNotFound,
    WorkflowTemplate,
    WorkflowTemplateService,
)


@dataclass(frozen=True)
class ResolvedClientExecution:
    template: WorkflowTemplate
    parameters: Dict[str, Any]
    uses_external_connector: bool


class ClientWorkflowExecutor:
    """Delegates template instantiation and execution to Sprint 006/005."""

    def __init__(self, templates: WorkflowTemplateService) -> None:
        self.templates = templates

    def resolve(
        self, workflow_id: str, client_id: str, input_data: Dict[str, Any]
    ) -> ResolvedClientExecution:
        try:
            template = self.templates.get(workflow_id)
        except TemplateNotFound as error:
            raise ExecutionWorkflowNotFound("Workflow template was not found") from error
        parameters = dict(input_data)
        parameters.setdefault("client_id", client_id)
        uses_external = any(
            step.get("target_entity") == "connector"
            or step.get("step_id") == "external_setup"
            for step in template.step_blueprint
        )
        return ResolvedClientExecution(template, parameters, uses_external)

    def execute(
        self,
        resolved: ResolvedClientExecution,
        client_id: str,
        input_data: Dict[str, Any],
    ) -> WorkflowInstance:
        workflow_input = dict(input_data)
        workflow_input.setdefault("client_id", client_id)
        instance, _ = self.templates.execute(
            resolved.template.template_id,
            resolved.parameters,
            resolved.template.version,
            workflow_input,
        )
        return instance

