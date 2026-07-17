from typing import Any, Dict, List
from uuid import uuid4

from bbi_os.client_monetization.registry import ClientPlanRegistry
from bbi_os.domain import BaseEntity
from bbi_os.entity_repository import EntityRepository
from bbi_os.observability import get_observability, timestamp


CLIENT_PLANS = {
    "Basic": "basic",
    "Pro": "pro",
    "Enterprise": "enterprise",
    "Custom": "custom",
}


class InvalidClient(Exception):
    pass


class ClientManagementService:
    """Creates and reads clients without owning execution or billing behavior."""

    def __init__(
        self, clients: EntityRepository, plans: ClientPlanRegistry
    ) -> None:
        self.clients = clients
        self.plans = plans

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise InvalidClient("Client request must be an object")
        name = data.get("name")
        plan = data.get("plan")
        if not isinstance(name, str) or not name.strip():
            raise InvalidClient("Client name is required")
        if plan not in CLIENT_PLANS:
            raise InvalidClient("Plan must be Basic, Pro, Enterprise, or Custom")
        client_id = str(uuid4())
        created_at = timestamp()
        entity = BaseEntity(
            entity_id=client_id,
            entity_type="client",
            created_at=created_at,
            updated_at=created_at,
            metadata={"name": name.strip()},
        )
        self.clients.save(entity)
        try:
            self.plans.assign(client_id, CLIENT_PLANS[plan])
        except Exception:
            self.clients.delete(client_id)
            raise
        client = self._client(entity)
        get_observability().log(
            "INFO",
            "client_created",
            "Client created",
            {
                "event_type": "client_created",
                "client_id": client_id,
                "entity_id": client_id,
                "plan": CLIENT_PLANS[plan],
            },
        )
        return client

    def list(self) -> List[Dict[str, Any]]:
        clients = [self._client(entity) for entity in self.clients.list()]
        return sorted(clients, key=lambda item: (item["created_at"], item["id"]))

    def _client(self, entity: BaseEntity) -> Dict[str, Any]:
        metadata = entity.metadata
        plan = self.plans.plan_for(entity.entity_id).plan_id
        return {
            "id": entity.entity_id,
            "name": metadata.get("name") or metadata.get("client_name") or entity.entity_id,
            "plan": plan.capitalize(),
            "created_at": entity.created_at,
        }


class ClientManagementApiHandler:
    def __init__(self, service: ClientManagementService) -> None:
        self.service = service

    def handle(self, method: str, entity_id: Any, request: Any) -> None:
        from bbi_os.task_management.api import error_response, success_response

        try:
            if method == "GET" and entity_id is None:
                request._respond(
                    200, success_response(self.service.list(), "Clients retrieved")
                )
                return
            if method == "POST" and entity_id is None:
                request._respond(
                    201,
                    success_response(
                        self.service.create(request._body()), "Client created"
                    ),
                )
                return
            request._route_not_found()
        except InvalidClient as error:
            request._log_error("INVALID_CLIENT", str(error))
            request._respond(400, error_response("INVALID_CLIENT", str(error)))
        except Exception:
            request._log_error("CLIENT_PERSISTENCE_ERROR", "Client request failed")
            request._respond(
                500,
                error_response("CLIENT_PERSISTENCE_ERROR", "Client request failed"),
            )
