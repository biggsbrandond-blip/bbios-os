from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from bbi_os.task_management.api import error_response, success_response
from bbi_os.workflows.templates import (
    InvalidWorkflowTemplate,
    TemplateNotFound,
    TemplateVersionNotFound,
    WorkflowTemplateService,
)


class WorkflowTemplateApiHandler:
    def __init__(self, service: WorkflowTemplateService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        parsed = urlparse(request.path)
        parts = [part for part in parsed.path.split("/") if part]
        subresource = parts[3] if len(parts) == 4 else None
        query_version = parse_qs(parsed.query).get("version", [None])[0]
        try:
            if method == "POST" and entity_id is None:
                template = self.service.create(request._body())
                request._respond(
                    201, success_response(template.to_dict(), "Workflow template created")
                )
                return
            if method == "GET" and entity_id is None:
                templates = [template.to_dict() for template in self.service.list()]
                request._respond(
                    200, success_response(templates, "Workflow templates retrieved")
                )
                return
            if method == "GET" and entity_id and subresource is None:
                template = self.service.get(entity_id, query_version)
                request._respond(
                    200, success_response(template.to_dict(), "Workflow template retrieved")
                )
                return
            if method == "POST" and entity_id and subresource == "execute":
                body = request._body()
                instance, lineage = self.service.execute(
                    entity_id,
                    body.get("parameters", {}),
                    body.get("version") or query_version,
                    body.get("input", {}),
                )
                data = instance.to_dict()
                data["template_lineage"] = lineage
                if instance.execution_status == "failed":
                    request._log_error(
                        "TEMPLATE_EXECUTION_FAILED", "Template execution failed"
                    )
                    request._respond(
                        422,
                        error_response(
                            "TEMPLATE_EXECUTION_FAILED", "Template execution failed"
                        ),
                    )
                else:
                    request._respond(
                        201, success_response(data, "Workflow template executed")
                    )
                return
            request._route_not_found()
        except InvalidWorkflowTemplate as error:
            request._log_error("INVALID_WORKFLOW_TEMPLATE", str(error))
            request._respond(
                400, error_response("INVALID_WORKFLOW_TEMPLATE", str(error))
            )
        except TemplateVersionNotFound:
            request._log_error(
                "TEMPLATE_VERSION_NOT_FOUND", "Workflow template version not found"
            )
            request._respond(
                404,
                error_response(
                    "TEMPLATE_VERSION_NOT_FOUND", "Workflow template version not found"
                ),
            )
        except TemplateNotFound:
            request._log_error("TEMPLATE_NOT_FOUND", "Workflow template not found")
            request._respond(
                404, error_response("TEMPLATE_NOT_FOUND", "Workflow template not found")
            )
        except Exception:
            request._log_error(
                "TEMPLATE_EXECUTION_FAILED", "Template execution failed"
            )
            request._respond(
                500,
                error_response(
                    "TEMPLATE_EXECUTION_FAILED", "Template execution failed"
                ),
            )
