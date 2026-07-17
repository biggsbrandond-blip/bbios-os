from bbi_os.client_pipeline.errors import (
    PipelineExecutionFailed,
    PipelineWorkflowNotFound,
)
from bbi_os.client_pipeline.models import ClientPipelineResult, ClientRequest
from bbi_os.client_pipeline.templates.registry import TemplateRoute
from bbi_os.workflows.templates import (
    TemplateNotFound,
    WorkflowTemplateService,
)


class ClientPipelineEngine:
    """Transforms a routed client request into an existing template execution."""

    def __init__(self, templates: WorkflowTemplateService) -> None:
        self.templates = templates

    def execute(
        self, request: ClientRequest, route: TemplateRoute
    ) -> ClientPipelineResult:
        try:
            template = self.templates.get(route.template_id, route.version)
            parameters = dict(request.payload)
            parameters.setdefault("user_id", request.user_id)
            workflow_input = dict(request.payload)
            workflow_input.setdefault("user_id", request.user_id)
            instance, lineage = self.templates.execute(
                template.template_id,
                parameters,
                template.version,
                workflow_input,
            )
        except TemplateNotFound as error:
            raise PipelineWorkflowNotFound("Mapped workflow template was not found") from error
        except Exception as error:
            raise PipelineExecutionFailed("Client pipeline execution failed") from error
        if instance.execution_status != "completed":
            raise PipelineExecutionFailed("Client pipeline workflow failed")
        return ClientPipelineResult(
            request_type=request.type,
            workflow_template_id=lineage["template_id"],
            workflow_version=lineage["workflow_version"],
            workflow_instance_id=instance.workflow_instance_id,
            status=instance.execution_status,
            output=dict(instance.output_data),
        )

