from typing import Any, Dict
from uuid import uuid4

from bbi_os.client_onboarding.errors import (
    InvalidOnboardingRequest,
    OnboardingExecutionFailed,
    OnboardingWorkflowNotFound,
)
from bbi_os.client_onboarding.models import OnboardingRequest, OnboardingResult
from bbi_os.client_onboarding.registry import OnboardingRoute
from bbi_os.domain import BaseEntity
from bbi_os.entity_repository import EntityRepositoryRouter
from bbi_os.integrations.outbound import OutboundRequestEngine
from bbi_os.integrations.workflow import current_workflow_instance_id
from bbi_os.observability import current_request_context, timestamp
from bbi_os.workflows.engine import ActionResult
from bbi_os.workflows.templates import TemplateNotFound, WorkflowTemplateService


class OnboardingWorkflowActions:
    """COS-specific entity operations backed by Sprint 004 repositories."""

    def __init__(
        self,
        repositories: EntityRepositoryRouter,
        outbound: OutboundRequestEngine,
    ) -> None:
        self.repositories = repositories
        self.outbound = outbound

    def execute(self, inputs: Dict[str, Any]) -> ActionResult:
        operation = inputs.get("operation")
        if operation == "validate_client":
            client_name = inputs.get("client_name", "")
            if not isinstance(client_name, str) or not client_name.strip():
                raise InvalidOnboardingRequest("Client name is required")
            return ActionResult({"validated": True, "client_name": client_name.strip()})
        if operation == "create_client":
            entity = BaseEntity(
                entity_id=str(uuid4()),
                entity_type="client",
                created_at=timestamp(),
                updated_at=timestamp(),
                metadata={
                    "client_name": inputs["client_name"],
                    "payload": dict(inputs.get("payload", {})),
                    "onboarding_status": "in-progress",
                },
            )
            self.repositories.repository_for("client").save(entity)
            return ActionResult(
                {"client_entity_id": entity.entity_id},
                {"operation": "delete_client", "entity_id": entity.entity_id},
            )
        if operation == "assign_user_role":
            context = current_request_context()
            if inputs["user_id"] != context["user_id"]:
                raise InvalidOnboardingRequest("Assigned user does not match request identity")
            repository = self.repositories.repository_for("client")
            existing = repository.get(inputs["client_entity_id"])
            if existing is None:
                raise InvalidOnboardingRequest("Client entity was not found")
            previous = existing.to_record()
            metadata = dict(existing.metadata)
            metadata.update(
                {"assigned_user_id": context["user_id"], "assigned_role": context["role"]}
            )
            updated = BaseEntity(
                existing.entity_id,
                existing.entity_type,
                existing.created_at,
                timestamp(),
                metadata,
            )
            repository.save(updated)
            return ActionResult(
                {
                    "client_entity_id": updated.entity_id,
                    "user_id": context["user_id"],
                    "role": context["role"],
                },
                {"operation": "restore_client", "record": previous},
            )
        if operation == "external_setup":
            connector_id = inputs.get("connector_id", "")
            if not connector_id:
                return ActionResult({"external_setup": "skipped"})
            response = self.outbound.execute(
                connector_id=connector_id,
                method="POST",
                path=inputs.get("path", "setup"),
                body={
                    "client_entity_id": inputs["client_entity_id"],
                    "client_name": inputs["client_name"],
                },
                workflow_instance_id=current_workflow_instance_id(),
            )
            return ActionResult({"external_setup": "completed", "response": response})
        if operation == "complete_onboarding":
            now = timestamp()
            onboarding = BaseEntity(
                entity_id=str(uuid4()),
                entity_type="onboarding",
                created_at=now,
                updated_at=now,
                metadata={
                    "client_entity_id": inputs["client_entity_id"],
                    "task_id": inputs["task_id"],
                    "user_id": inputs["user_id"],
                    "workflow_instance_id": current_workflow_instance_id(),
                    "status": "complete",
                },
            )
            self.repositories.repository_for("onboarding").save(onboarding)
            client_repository = self.repositories.repository_for("client")
            client = client_repository.get(inputs["client_entity_id"])
            if client is None:
                raise InvalidOnboardingRequest("Client entity was not found")
            metadata = dict(client.metadata)
            metadata["onboarding_status"] = "complete"
            client_repository.save(
                BaseEntity(
                    client.entity_id,
                    client.entity_type,
                    client.created_at,
                    now,
                    metadata,
                )
            )
            return ActionResult(
                {
                    "onboarding_entity_id": onboarding.entity_id,
                    "client_entity_id": client.entity_id,
                    "status": "complete",
                },
                {"operation": "delete_onboarding", "entity_id": onboarding.entity_id},
            )
        raise InvalidOnboardingRequest(f"Unsupported onboarding operation: {operation}")

    def rollback(self, rollback_data: Dict[str, Any]) -> None:
        operation = rollback_data["operation"]
        if operation == "delete_client":
            self.repositories.repository_for("client").delete(rollback_data["entity_id"])
        elif operation == "restore_client":
            self.repositories.repository_for("client").save(
                BaseEntity.from_record(rollback_data["record"])
            )
        elif operation == "delete_onboarding":
            self.repositories.repository_for("onboarding").delete(
                rollback_data["entity_id"]
            )


class OnboardingEngine:
    def __init__(self, templates: WorkflowTemplateService) -> None:
        self.templates = templates

    def execute(
        self,
        onboarding_request_id: str,
        request: OnboardingRequest,
        route: OnboardingRoute,
    ) -> OnboardingResult:
        try:
            template = self.templates.get(route.template_id, route.version)
            parameters = {
                "client_name": request.client_name.strip(),
                "user_id": request.user_id,
                "user_role": current_request_context()["role"],
                "payload": dict(request.payload),
                "external_connector_id": request.payload.get(
                    "external_connector_id", ""
                ),
            }
            instance, lineage = self.templates.execute(
                template.template_id,
                parameters,
                template.version,
                {**request.payload, **parameters},
            )
        except TemplateNotFound as error:
            raise OnboardingWorkflowNotFound(
                "Onboarding workflow template was not found"
            ) from error
        except Exception as error:
            raise OnboardingExecutionFailed("Onboarding execution failed") from error
        if instance.execution_status != "completed":
            raise OnboardingExecutionFailed("Onboarding workflow failed")
        output = dict(instance.output_data)
        return OnboardingResult(
            onboarding_request_id=onboarding_request_id,
            client_entity_id=output["client_entity_id"],
            onboarding_entity_id=output["onboarding_entity_id"],
            workflow_template_id=lineage["template_id"],
            workflow_instance_id=instance.workflow_instance_id,
            task_id=output["task_id"],
            status="completed",
            output=output,
        )
