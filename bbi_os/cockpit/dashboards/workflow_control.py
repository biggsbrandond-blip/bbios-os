from typing import Any, Dict

from bbi_os.client_execution.state import ExecutionStateRepository
from bbi_os.workflows.templates import WorkflowTemplateService


class WorkflowControlDashboard:
    def __init__(
        self, templates: WorkflowTemplateService, executions: ExecutionStateRepository
    ) -> None:
        self.templates = templates
        self.executions = executions

    def render(self, active_records: Any) -> Dict[str, Any]:
        return {
            "active_workflows": [record.to_dict() for record in active_records],
            "templates": [template.to_dict() for template in self.templates.list()],
            "execution_queue": [
                record.to_dict() for record in active_records if record.state == "PENDING"
            ],
        }

