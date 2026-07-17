import yaml
import os


# -------------------------
# TEMPLATE VALIDATION CORE
# -------------------------
class TemplateValidationError(Exception):
    pass


class TemplateValidator:

    def validate(self, template: dict):
        self.validate_root(template)
        self.validate_architecture(template)

    def validate_root(self, template):
        required = ["name", "version", "architecture", "rules", "future_modules"]

        for key in required:
            if key not in template:
                raise TemplateValidationError(f"Missing required field: {key}")

    def validate_architecture(self, template):
        arch = template.get("architecture", {})

        required_arch = [
            "api_layer",
            "router_layer",
            "service_layer",
            "state_layer",
            "endpoints"
        ]

        for key in required_arch:
            if key not in arch:
                raise TemplateValidationError(f"Missing architecture field: {key}")

        if not isinstance(arch.get("endpoints", []), list):
            raise TemplateValidationError("endpoints must be a list")


# -------------------------
# GENERATOR CORE
# -------------------------
class BBIOSGeneratorV2:

    def __init__(self, template_path: str):
        self.template_path = template_path
        self.template = self.load_template()
        self.validator = TemplateValidator()

    # -------------------------
    # LOAD TEMPLATE
    # -------------------------
    def load_template(self):
        with open(self.template_path, "r") as f:
            return yaml.safe_load(f) or {}

    # -------------------------
    # ENTRY POINT
    # -------------------------
    def generate(self):
        # 🔒 VALIDATION GATE (NO PATCHING NEEDED EVER AGAIN)
        self.validator.validate(self.template)

        output = self.build_files()
        self.write_output(output)

    # -------------------------
    # FILE BUILDERS
    # -------------------------
    def build_files(self):
        return {
            "api.py": self.build_api(),
            "router.py": self.build_router(),
            "service.py": self.build_service()
        }

    # -------------------------
    # API LAYER
    # -------------------------
    def build_api(self):
        name = self.template.get("name", "BBIOS System")
        version = self.template.get("version", "0.1")

        return f"""
from fastapi import FastAPI
from bbi_os.cockpit.router import router

app = FastAPI(
    title="{name}",
    version="{version}"
)

app.include_router(router, prefix="/cockpit")
"""

    # -------------------------
    # ROUTER LAYER
    # -------------------------
    def build_router(self):
        endpoints = self.template["architecture"]["endpoints"]

        routes = ""

        for ep in endpoints:
            path = ep.get("path", "/")
            method = ep.get("method", "get").lower()
            etype = ep.get("type", "generic")

            routes += f"""

@router.{method}("{path}")
def endpoint():
    return {{"status": "{etype}"}}
"""

        return f"""
from fastapi import APIRouter
from bbi_os.cockpit.service import CockpitService

router = APIRouter()
service = CockpitService()

{routes}
"""

    # -------------------------
    # SERVICE LAYER
    # -------------------------
    def build_service(self):
        return """
class CockpitService:
    def __init__(self):
        self.clients = []
        self.executions = []

    def create_client(self, name: str, plan: str):
        client = {
            "name": name,
            "plan": plan
        }
        self.clients.append(client)
        return {"status": "success", "client": client}

    def test_pipeline(self):
        execution = {
            "status": "ok",
            "message": "pipeline executed"
        }
        self.executions.append(execution)
        return execution
"""

    # -------------------------
    # WRITE OUTPUT
    # -------------------------
    def write_output(self, files: dict, output_dir="generated_system"):
        os.makedirs(output_dir, exist_ok=True)

        for name, content in files.items():
            with open(os.path.join(output_dir, name), "w") as f:
                f.write(content)

        print("\n✔ BBIOS GENERATION COMPLETE")
        print(f"Output: {output_dir}")


# -------------------------
# RUNNER
# -------------------------
if __name__ == "__main__":
    gen = BBIOSGeneratorV2(
        "bbi_os/templates/cockpit_template_v0_1.yaml"
    )
    gen.generate()
