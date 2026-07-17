import os
import yaml


class TemplateRegistry:
    """
    Discovers and loads YAML templates from bbi_os/templates
    """

    def __init__(self, template_dir="bbi_os/templates"):
        self.template_dir = template_dir

    def list_templates(self):
        return [
            f for f in os.listdir(self.template_dir)
            if f.endswith(".yaml")
        ]

    def load_template(self, name: str):
        path = os.path.join(self.template_dir, name)

        if not os.path.exists(path):
            raise Exception(f"Template not found: {name}")

        with open(path, "r") as f:
            return yaml.safe_load(f)

    def load_all(self):
        templates = {}

        for file in self.list_templates():
            path = os.path.join(self.template_dir, file)

            with open(path, "r") as f:
                templates[file] = yaml.safe_load(f)

        return templates
