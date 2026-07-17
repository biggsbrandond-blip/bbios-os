from typing import Any, Optional

from bbi_os.task_management.api import error_response, success_response
from bbi_os.workflows.engine import WorkflowEngine
from bbi_os.workflows.models import (
    InvalidWorkflowDefinition,
    WorkflowExecutionError,
    WorkflowNotFound,
)


class WorkflowApiHandler:
    def __init__(self, engine: WorkflowEngine, resource: str) -> None:
        self.engine = engine
        self.resource = resource

    def handle(self, method: str, entity_id: Optional[str], request: Any) -> None:
        try:
            if self.resource == "definitions" and method == "POST" and entity_id is None:
                definition = self.engine.create_definition(request._body())
                request._respond(
                    201, success_response(definition.to_dict(), "Workflow created")
                )
                return
            if self.resource == "executions" and method == "POST" and entity_id is None:
                body = request._body()
                instance = self.engine.trigger(body["workflow_id"], body.get("input", {}))
                if instance.execution_status == "failed":
                    request._log_error("WORKFLOW_STEP_FAILED", "Workflow step failed")
                    request._respond(
                        422,
                        error_response("WORKFLOW_STEP_FAILED", "Workflow step failed"),
                    )
                else:
                    request._respond(
                        201,
                        success_response(instance.to_dict(), "Workflow completed"),
                    )
                return
            if self.resource == "executions" and method == "GET" and entity_id:
                instance = self.engine.get_status(entity_id)
                request._respond(
                    200, success_response(instance.to_dict(), "Workflow status retrieved")
                )
                return
            if self.resource == "history" and method == "GET" and entity_id:
                history = [step.__dict__ for step in self.engine.get_history(entity_id)]
                request._respond(
                    200, success_response(history, "Workflow history retrieved")
                )
                return
            request._route_not_found()
        except InvalidWorkflowDefinition as error:
            request._log_error("INVALID_WORKFLOW_DEFINITION", str(error))
            request._respond(
                400, error_response("INVALID_WORKFLOW_DEFINITION", str(error))
            )
        except KeyError:
            request._log_error(
                "INVALID_WORKFLOW_DEFINITION", "Required workflow input is missing"
            )
            request._respond(
                400,
                error_response(
                    "INVALID_WORKFLOW_DEFINITION", "Required workflow input is missing"
                ),
            )
        except WorkflowNotFound:
            request._log_error("WORKFLOW_NOT_FOUND", "Workflow not found")
            request._respond(404, error_response("WORKFLOW_NOT_FOUND", "Workflow not found"))
        except WorkflowExecutionError:
            request._log_error("WORKFLOW_EXECUTION_FAILED", "Workflow execution failed")
            request._respond(
                422,
                error_response("WORKFLOW_EXECUTION_FAILED", "Workflow execution failed"),
            )
        except Exception:
            request._log_error("WORKFLOW_EXECUTION_FAILED", "Workflow execution failed")
            request._respond(
                500,
                error_response("WORKFLOW_EXECUTION_FAILED", "Workflow execution failed"),
            )
