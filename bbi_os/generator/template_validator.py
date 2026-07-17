from bbi_os.generator.template_contract import (
    REQUIRED_TEMPLATE_FIELDS,
    REQUIRED_ARCHITECTURE_FIELDS
)

class TemplateValidationError(Exception):
    pass

class TemplateValidator:

    def validate(self, template: dict):
        self._validate_root(template)
        self._validate_architecture(template["architecture"])
        self._validate_endpoints(template["architecture"])

    def _validate_root(self, template):
        for key, expected_type in REQUIRED_TEMPLATE_FIELDS.items():
            if key not in template:
                raise TemplateValidationError(f"Missing required field: {key}")
            if not isinstance(template[key], expected_type):
                raise TemplateValidationError(f"Invalid type for {key}")

    def _validate_architecture(self, architecture):
        for key, expected_type in REQUIRED_ARCHITECTURE_FIELDS.items():
            if key not in architecture:
                raise TemplateValidationError(f"Missing architecture field: {key}")
            if not isinstance(architecture[key], expected_type):
                raise TemplateValidationError(f"Invalid type: {key}")

    def _validate_endpoints(self, architecture):
        endpoints = architecture.get("endpoints", [])

        if not isinstance(endpoints, list):
            raise TemplateValidationError("endpoints must be a list")

        for ep in endpoints:
            if "path" not in ep or "method" not in ep:
                raise TemplateValidationError(f"Bad endpoint: {ep}")
