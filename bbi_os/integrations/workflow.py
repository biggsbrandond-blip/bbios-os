from contextvars import ContextVar, Token

from bbi_os.workflows.engine import WorkflowEngine
from bbi_os.workflows.models import WorkflowDefinition, WorkflowInstance


_workflow_instance_id: ContextVar[str] = ContextVar(
    "integration_workflow_instance_id", default=""
)


def current_workflow_instance_id() -> str:
    return _workflow_instance_id.get()


class IntegrationWorkflowEngine(WorkflowEngine):
    """Scopes workflow identity for connector actions without changing the core engine."""

    def _execute(
        self, definition: WorkflowDefinition, instance: WorkflowInstance
    ) -> WorkflowInstance:
        token: Token = _workflow_instance_id.set(instance.workflow_instance_id)
        try:
            return super()._execute(definition, instance)
        finally:
            _workflow_instance_id.reset(token)

