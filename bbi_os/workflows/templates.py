import json
import os
import re
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from bbi_os.observability import get_observability
from bbi_os.workflows.engine import WorkflowEngine
from bbi_os.workflows.models import WorkflowInstance, WorkflowStep


class InvalidWorkflowTemplate(Exception):
    pass


class TemplateNotFound(Exception):
    pass


class TemplateVersionNotFound(TemplateNotFound):
    pass


@dataclass(frozen=True)
class WorkflowTemplate:
    template_id: str
    name: str
    description: str
    version: str
    parameter_schema: Dict[str, Any]
    step_blueprint: List[Dict[str, Any]]

    def validate(self) -> None:
        if not self.template_id or not self.name or not self.description or not self.version:
            raise InvalidWorkflowTemplate(
                "Template ID, name, description, and version are required"
            )
        if not isinstance(self.parameter_schema, dict) or not isinstance(
            self.step_blueprint, list
        ):
            raise InvalidWorkflowTemplate("Template schema and step blueprint are invalid")
        if not self.step_blueprint:
            raise InvalidWorkflowTemplate("Template must include at least one step")
        try:
            steps = [WorkflowStep.from_dict(step) for step in self.step_blueprint]
        except Exception as error:
            raise InvalidWorkflowTemplate("Template contains an invalid step") from error
        if len({step.step_id for step in steps}) != len(steps):
            raise InvalidWorkflowTemplate("Template step IDs must be unique")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowTemplate":
        try:
            template = cls(
                template_id=data["template_id"],
                name=data["name"],
                description=data["description"],
                version=data["version"],
                parameter_schema=dict(data.get("parameter_schema", {})),
                step_blueprint=list(data["step_blueprint"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidWorkflowTemplate("Invalid workflow template") from error
        template.validate()
        return template


class WorkflowTemplateRepository:
    def __init__(self, templates_path: Path, lineage_path: Path) -> None:
        self.templates_path = templates_path
        self.lineage_path = lineage_path
        self._lock = threading.RLock()

    def create(self, template: WorkflowTemplate) -> WorkflowTemplate:
        key = self._key(template.template_id, template.version)
        with self._lock:
            records = self._read(self.templates_path)
            if key in records:
                raise InvalidWorkflowTemplate("Template version already exists")
            records[key] = template.to_dict()
            self._write(self.templates_path, records)
        return template

    def list(self) -> List[WorkflowTemplate]:
        with self._lock:
            records = self._read(self.templates_path)
        return [WorkflowTemplate.from_dict(record) for record in records.values()]

    def get(self, reference: str, version: Optional[str] = None) -> WorkflowTemplate:
        templates = self.list()
        exact = [template for template in templates if template.template_id == reference]
        matches = exact or [template for template in templates if template.name == reference]
        if not matches:
            raise TemplateNotFound(f"Template '{reference}' was not found")
        template_ids = {template.template_id for template in matches}
        if len(template_ids) > 1:
            raise InvalidWorkflowTemplate("Template name is ambiguous; use template_id")
        if version is not None:
            for template in matches:
                if template.version == version:
                    return template
            raise TemplateVersionNotFound(
                f"Template '{reference}' version '{version}' was not found"
            )
        return max(matches, key=lambda template: self._version_key(template.version))

    def save_lineage(self, instance_id: str, lineage: Dict[str, Any]) -> None:
        with self._lock:
            records = self._read(self.lineage_path)
            records[instance_id] = lineage
            self._write(self.lineage_path, records)

    def get_lineage(self, instance_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._read(self.lineage_path).get(instance_id)

    @staticmethod
    def _key(template_id: str, version: str) -> str:
        return f"{template_id}:{version}"

    @staticmethod
    def _version_key(version: str) -> Tuple[Any, ...]:
        return tuple(
            (1, int(part)) if part.isdigit() else (0, part.lower())
            for part in re.split(r"([0-9]+)", version)
            if part
        )

    @staticmethod
    def _read(path: Path) -> Dict[str, Dict[str, Any]]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as data_file:
            data = json.load(data_file)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid template data in {path}")
        return data

    @staticmethod
    def _write(path: Path, records: Dict[str, Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as data_file:
                json.dump(records, data_file, indent=2, sort_keys=True)
                data_file.write("\n")
                data_file.flush()
                os.fsync(data_file.fileno())
            os.replace(temporary_path, path)
        except Exception:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise


class WorkflowTemplateService:
    _placeholder = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def __init__(
        self, repository: WorkflowTemplateRepository, engine: WorkflowEngine
    ) -> None:
        self.repository = repository
        self.engine = engine

    def create(self, data: Dict[str, Any]) -> WorkflowTemplate:
        template = self.repository.create(WorkflowTemplate.from_dict(data))
        self._event("workflow_template_created", template, "", {})
        return template

    def list(self) -> List[WorkflowTemplate]:
        return self.repository.list()

    def get(self, reference: str, version: Optional[str] = None) -> WorkflowTemplate:
        return self.repository.get(reference, version)

    def execute(
        self,
        reference: str,
        parameters: Dict[str, Any],
        version: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[WorkflowInstance, Dict[str, Any]]:
        template = self.get(reference, version)
        self._validate_parameters(template.parameter_schema, parameters)
        resolved_steps = self._bind(template.step_blueprint, parameters)
        resolved_workflow_id = (
            f"template:{template.template_id}:{template.version}:{uuid4()}"
        )
        self.engine.create_definition(
            {
                "workflow_id": resolved_workflow_id,
                "name": template.name,
                "description": template.description,
                "trigger_type": "manual",
                "steps": resolved_steps,
                "input_schema": template.parameter_schema,
                "output_schema": None,
            }
        )
        instance = self.engine.trigger(resolved_workflow_id, input_data or {})
        lineage = {
            "template_id": template.template_id,
            "workflow_version": template.version,
            "workflow_instance_id": instance.workflow_instance_id,
            "resolved_workflow_id": resolved_workflow_id,
            "parameter_bindings": dict(parameters),
        }
        self.repository.save_lineage(instance.workflow_instance_id, lineage)
        self._event(
            "workflow_template_executed",
            template,
            instance.workflow_instance_id,
            parameters,
        )
        return instance, lineage

    @classmethod
    def _bind(cls, value: Any, parameters: Dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {key: cls._bind(item, parameters) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._bind(item, parameters) for item in value]
        if not isinstance(value, str):
            return value
        exact = cls._placeholder.fullmatch(value)
        if exact:
            return cls._parameter(parameters, exact.group(1))
        return cls._placeholder.sub(
            lambda match: str(cls._parameter(parameters, match.group(1))), value
        )

    @staticmethod
    def _parameter(parameters: Dict[str, Any], name: str) -> Any:
        try:
            return parameters[name]
        except KeyError as error:
            raise InvalidWorkflowTemplate(
                f"Missing template parameter: {name}"
            ) from error

    @staticmethod
    def _validate_parameters(schema: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        if not isinstance(parameters, dict):
            raise InvalidWorkflowTemplate("Parameter bindings must be an object")
        required = schema.get("required", [])
        missing = [name for name in required if name not in parameters]
        if missing:
            raise InvalidWorkflowTemplate(
                f"Missing template parameter(s): {', '.join(sorted(missing))}"
            )
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
        }
        for name, rules in schema.get("properties", {}).items():
            if name in parameters and rules.get("type") in type_map:
                expected = type_map[rules["type"]]
                if not isinstance(parameters[name], expected):
                    raise InvalidWorkflowTemplate(
                        f"Template parameter '{name}' must be {rules['type']}"
                    )

    @staticmethod
    def _event(
        event_type: str,
        template: WorkflowTemplate,
        instance_id: str,
        parameters: Dict[str, Any],
    ) -> None:
        get_observability().log(
            "INFO",
            event_type,
            event_type.replace("_", " ").capitalize(),
            {
                "event_type": event_type,
                "template_id": template.template_id,
                "workflow_version": template.version,
                "workflow_instance_id": instance_id,
                "parameter_bindings": dict(parameters),
            },
        )
