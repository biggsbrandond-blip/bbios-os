from typing import Any, Dict, List

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.client_monetization.service import ClientMonetizationService
from bbi_os.cockpit.controls.client_controls import ClientControls
from bbi_os.cockpit.models import CockpitControlError, CockpitEventStore


class ClientViewDashboard:
    def __init__(
        self,
        clients: Any,
        monetization: ClientMonetizationService,
        controls: ClientControls,
        events: CockpitEventStore,
    ) -> None:
        self.clients = clients
        self.monetization = monetization
        self.controls = controls
        self.events = events

    def render(
        self, client_id: str, records: List[ClientExecutionRecord]
    ) -> Dict[str, Any]:
        client = self.clients.get(client_id)
        if client is None:
            raise CockpitControlError("Client was not found")
        return {
            "client": client.to_record(),
            "status": "locked" if self.controls.is_locked(client_id) else "active",
            "executions": [record.to_dict() for record in records],
            "active_workflows": [
                record.to_dict()
                for record in records
                if record.state in {"PENDING", "RUNNING", "WAITING_EXTERNAL"}
            ],
            "usage": self.monetization.metrics(client_id),
            "billing": self.monetization.billing_summary(client_id),
            "logs": self.events.list(client_id=client_id)[-100:],
        }

