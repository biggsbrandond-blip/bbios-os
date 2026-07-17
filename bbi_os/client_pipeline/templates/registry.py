from dataclasses import dataclass
from typing import Dict, List, Optional

from bbi_os.client_pipeline.errors import InvalidRequestType


@dataclass(frozen=True)
class TemplateRoute:
    request_type: str
    template_id: str
    version: Optional[str] = None


class ClientTemplateRegistry:
    """Extensible request-type to workflow-template mapping."""

    def __init__(self) -> None:
        self._routes: Dict[str, TemplateRoute] = {}

    def register(
        self, request_type: str, template_id: str, version: Optional[str] = None
    ) -> TemplateRoute:
        if not request_type or not template_id:
            raise ValueError("Request type and template ID are required")
        if request_type in self._routes:
            raise ValueError(f"Request type '{request_type}' is already registered")
        route = TemplateRoute(request_type, template_id, version)
        self._routes[request_type] = route
        return route

    def resolve(self, request_type: str) -> TemplateRoute:
        try:
            return self._routes[request_type]
        except KeyError as error:
            raise InvalidRequestType(
                f"Unsupported client request type: {request_type}"
            ) from error

    def list(self) -> List[TemplateRoute]:
        return list(self._routes.values())

