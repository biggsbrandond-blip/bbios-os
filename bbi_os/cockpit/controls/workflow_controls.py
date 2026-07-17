from typing import Any, Dict

from bbi_os.cockpit.controls.execution_controls import ExecutionControls
from bbi_os.cockpit.models import CockpitControlError
from bbi_os.workflows.templates import WorkflowTemplateService


class WorkflowControls:
    def __init__(
        self, executions: ExecutionControls, templates: WorkflowTemplateService
    ) -> None:
        self.executions = executions
        self.templates = templates

    def select_template(self, reference: str, version: str = "") -> Dict[str, Any]:
        return self.templates.get(reference, version or None).to_dict()

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.executions.start(data).to_dict()

    def retry(self, execution_id: str) -> Dict[str, Any]:
        return self.executions.retry(execution_id).to_dict()

    def cancel(self, execution_id: str) -> None:
        self.executions.cancel(execution_id)

    def history(self, execution_id: str) -> Dict[str, Any]:
        return self.executions.inspect(execution_id).to_dict()

    @staticmethod
    def deploy_template() -> None:
        raise CockpitControlError(
            "Template deployment is unavailable because the cockpit cannot define templates"
        )
