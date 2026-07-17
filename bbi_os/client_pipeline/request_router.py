from bbi_os.client_pipeline.models import ClientRequest
from bbi_os.client_pipeline.templates.registry import (
    ClientTemplateRegistry,
    TemplateRoute,
)


class ClientRequestRouter:
    def __init__(self, templates: ClientTemplateRegistry) -> None:
        self.templates = templates

    def route(self, request: ClientRequest) -> TemplateRoute:
        return self.templates.resolve(request.type)

