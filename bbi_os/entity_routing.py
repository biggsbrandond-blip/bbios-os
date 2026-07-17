from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse


@dataclass(frozen=True)
class EntityRoute:
    entity_type: str
    handler: Any
    entity_id: Optional[str] = None
    subpath: Tuple[str, ...] = ()


class EntityRouteRegistry:
    """Resolves versioned entity paths without coupling the core API to future domains."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Any] = {}

    def register(self, path_name: str, handler: Any) -> None:
        if not path_name or "/" in path_name:
            raise ValueError("Entity path name must be one URL segment")
        if path_name in self._handlers:
            raise ValueError(f"Route already registered for '{path_name}'")
        self._handlers[path_name] = handler

    def resolve(self, path: str) -> Optional[EntityRoute]:
        parts = [part for part in urlparse(path).path.split("/") if part]
        if len(parts) < 2 or parts[0] != "v1":
            return None
        handler = self._handlers.get(parts[1])
        if handler is None:
            return None
        return EntityRoute(
            entity_type=parts[1],
            handler=handler,
            entity_id=parts[2] if len(parts) >= 3 else None,
            subpath=tuple(parts[3:]) if len(parts) > 3 else (),
        )
