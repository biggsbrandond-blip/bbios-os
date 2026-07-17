from dataclasses import dataclass
from typing import Dict, List

from bbi_os.client_onboarding.errors import InvalidOnboardingType
from bbi_os.workflows.templates import (
    TemplateNotFound,
    WorkflowTemplateService,
)


@dataclass(frozen=True)
class OnboardingRoute:
    request_type: str
    template_id: str
    version: str


class OnboardingRegistry:
    def __init__(self) -> None:
        self._routes: Dict[str, OnboardingRoute] = {}

    def register(
        self, request_type: str, template_id: str, version: str = "v1"
    ) -> OnboardingRoute:
        if not request_type or not template_id or not version:
            raise ValueError("Onboarding route fields are required")
        if request_type in self._routes:
            raise ValueError(f"Onboarding type '{request_type}' is already registered")
        route = OnboardingRoute(request_type, template_id, version)
        self._routes[request_type] = route
        return route

    def resolve(self, request_type: str) -> OnboardingRoute:
        try:
            return self._routes[request_type]
        except KeyError as error:
            raise InvalidOnboardingType(
                f"Unsupported onboarding request type: {request_type}"
            ) from error

    def list(self) -> List[OnboardingRoute]:
        return list(self._routes.values())


def default_onboarding_registry() -> OnboardingRegistry:
    registry = OnboardingRegistry()
    registry.register("basic_onboarding", "onboarding_template_v1")
    registry.register("premium_onboarding", "onboarding_template_v2")
    registry.register("enterprise_onboarding", "onboarding_template_v3")
    return registry


def install_default_onboarding_templates(
    templates: WorkflowTemplateService,
) -> None:
    for template_id in (
        "onboarding_template_v1",
        "onboarding_template_v2",
        "onboarding_template_v3",
    ):
        try:
            templates.get(template_id, "v1")
            continue
        except TemplateNotFound:
            pass
        templates.create(
            {
                "template_id": template_id,
                "name": template_id.replace("_", " ").title(),
                "description": "COS-001 automated client onboarding workflow",
                "version": "v1",
                "parameter_schema": {
                    "required": [
                        "client_name",
                        "user_id",
                        "user_role",
                        "payload",
                        "external_connector_id",
                    ],
                    "properties": {
                        "client_name": {"type": "string"},
                        "user_id": {"type": "string"},
                        "user_role": {"type": "string"},
                        "payload": {"type": "object"},
                        "external_connector_id": {"type": "string"},
                    },
                },
                "step_blueprint": _default_steps(),
            }
        )


def _default_steps() -> List[Dict[str, object]]:
    return [
        {
            "step_id": "validate_client",
            "step_name": "Validate Client",
            "action_type": "entity_operation",
            "target_entity": "onboarding",
            "input_mapping": {
                "operation": "validate_client",
                "client_name": "${client_name}",
            },
        },
        {
            "step_id": "create_client",
            "step_name": "Create Client Entity",
            "action_type": "entity_operation",
            "target_entity": "onboarding",
            "input_mapping": {
                "operation": "create_client",
                "client_name": "${client_name}",
                "payload": "${payload}",
            },
            "output_mapping": {
                "client_entity_id": "$result.client_entity_id"
            },
        },
        {
            "step_id": "assign_role",
            "step_name": "Assign User Role",
            "action_type": "entity_operation",
            "target_entity": "onboarding",
            "input_mapping": {
                "operation": "assign_user_role",
                "client_entity_id": "$steps.create_client.client_entity_id",
                "user_id": "${user_id}",
                "role": "${user_role}",
            },
        },
        {
            "step_id": "create_task",
            "step_name": "Create Task Set",
            "action_type": "entity_operation",
            "target_entity": "tasks",
            "input_mapping": {
                "operation": "create",
                "title": "Onboard ${client_name}",
                "description": "Client onboarding for ${client_name}",
                "status": "pending",
            },
            "output_mapping": {"task_id": "$result.id"},
        },
        {
            "step_id": "external_setup",
            "step_name": "Call External Setup API",
            "action_type": "entity_operation",
            "target_entity": "onboarding",
            "input_mapping": {
                "operation": "external_setup",
                "connector_id": "${external_connector_id}",
                "client_entity_id": "$steps.create_client.client_entity_id",
                "client_name": "${client_name}",
            },
            "output_mapping": {
                "external_setup": "$result.external_setup"
            },
        },
        {
            "step_id": "complete",
            "step_name": "Confirm Onboarding Complete",
            "action_type": "entity_operation",
            "target_entity": "onboarding",
            "input_mapping": {
                "operation": "complete_onboarding",
                "client_entity_id": "$steps.create_client.client_entity_id",
                "task_id": "$steps.create_task.id",
                "user_id": "${user_id}",
            },
            "output_mapping": {
                "onboarding_entity_id": "$result.onboarding_entity_id",
                "client_entity_id": "$result.client_entity_id",
                "status": "$result.status",
            },
        },
    ]
