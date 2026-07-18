from datetime import datetime
from typing import Any, Dict, List
import uuid

from bbi_os.client_execution.models import ClientExecutionRecord
from bbi_os.observability import get_observability


class CockpitService:

    def __init__(
        self,
        clients: Any = None,
        executions: Any = None,
        system_overview_dashboard: Any = None,
        client_view_dashboard: Any = None,
        execution_monitor_dashboard: Any = None,
        monetization_dashboard: Any = None,
        workflow_control_dashboard: Any = None,
        workflow_controls: Any = None,
        usage_insights: Any = None,
        performance_metrics: Any = None,
    ):
        self.clients = {}
        self.executions = []
        self._client_repository = clients
        self._execution_repository = executions
        self._system_overview_dashboard = system_overview_dashboard
        self._client_view_dashboard = client_view_dashboard
        self._execution_monitor_dashboard = execution_monitor_dashboard
        self._monetization_dashboard = monetization_dashboard
        self._workflow_control_dashboard = workflow_control_dashboard
        self._workflow_controls = workflow_controls
        self._usage_insights = usage_insights
        self._performance_metrics = performance_metrics

    def validate_client(self, name, plan):
        if not name or name.strip() == "":
            return "Client name is required"

        if not plan or plan.strip() == "":
            return "Plan is required"

        return None

    def create_client(self, name: str, plan: str):

        error = self.validate_client(name, plan)
        if error:
            return {"status": "error", "message": error}

        client_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        client = {
            "client_id": client_id,
            "client_name": name,
            "plan": plan,
            "created_at": created_at
        }

        self.clients[client_id] = client

        self.log_event("client_created", client_id)

        return {
            "status": "success",
            "client": client
        }

    def get_client(self, client_id: str):

        client = self.clients.get(client_id)

        if not client:
            return {
                "status": "error",
                "message": "Client not found"
            }

        self.log_event("client_retrieved", client_id)

        return {
            "status": "success",
            "client": client
        }

    def search_clients(self, name: str = "", plan: str = ""):

        results = []

        for client in self.clients.values():

            if name and name.lower() not in client["client_name"].lower():
                continue

            if plan and plan.lower() != client["plan"].lower():
                continue

            results.append(client)

        self.log_event("client_search", "system")

        return {
            "status": "success",
            "results": results
        }

    def log_event(self, event_type, client_id):

        self.executions.append({
            "event": event_type,
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    def test_pipeline(self):

        self.log_event("pipeline_test", "system")

        return {
            "status": "ok",
            "message": "pipeline executed"
        }

    def system_overview(self):
        self._require_rich("system_overview", self._system_overview_dashboard)
        records = self._execution_records()
        data = self._system_overview_dashboard.render(records)
        self._record_view("system_overview")
        return data

    def client(self, client_id):
        self._require_rich("client", self._client_view_dashboard)
        data = self._client_view_dashboard.render(
            client_id, self._execution_records_for_client(client_id)
        )
        self._record_view("client", {"client_id": client_id})
        return data

    def execution_monitor(self):
        self._require_rich("execution_monitor", self._execution_monitor_dashboard)
        data = self._execution_monitor_dashboard.render(self._execution_records())
        self._record_view("execution_monitor")
        return data

    def usage(self):
        self._require_rich("usage", self._monetization_dashboard)
        client_ids = self._client_ids()
        data = self._monetization_dashboard.usage(client_ids)
        if self._usage_insights is not None:
            data["insights"] = self._usage_insights.calculate(
                client_ids, self._execution_records()
            )
        self._record_view("usage")
        return data

    def billing(self):
        self._require_rich("billing", self._monetization_dashboard)
        data = self._monetization_dashboard.billing(self._client_ids())
        self._record_view("billing")
        return data

    def workflow_control(self):
        self._require_rich("workflow_control", self._workflow_control_dashboard)
        records = [
            record for record in self._execution_records()
            if record.state in {"PENDING", "RUNNING", "WAITING_EXTERNAL", "COMPENSATING"}
        ]
        data = self._workflow_control_dashboard.render(records)
        self._record_view("workflow_control")
        return data

    def execute(self, data):
        self._require_rich("execute", self._workflow_controls)
        result = self._workflow_controls.execute(data)
        self._record_view("workflow_execute", {"client_id": result.get("client_id", "")})
        return result

    def retry(self, execution_id):
        self._require_rich("retry", self._workflow_controls)
        result = self._workflow_controls.retry(execution_id)
        self._record_view("workflow_retry", {"execution_id": execution_id})
        return result

    def cancel(self, execution_id):
        self._require_rich("cancel", self._workflow_controls)
        self._workflow_controls.cancel(execution_id)
        self._record_view("workflow_cancel", {"execution_id": execution_id})

    def _client_ids(self) -> List[str]:
        self._require_rich("clients", self._client_repository)
        return [client.entity_id for client in self._client_repository.list()]

    def _execution_records(self) -> List[ClientExecutionRecord]:
        self._require_rich("executions", self._execution_repository)
        records = self._execution_repository._read()
        return [
            ClientExecutionRecord.from_dict(item)
            for item in records.values()
        ]

    def _execution_records_for_client(self, client_id: str) -> List[ClientExecutionRecord]:
        if hasattr(self._execution_repository, "list_for_client"):
            return self._execution_repository.list_for_client(client_id)
        return [
            record for record in self._execution_records()
            if record.client_id == client_id
        ]

    @staticmethod
    def _require_rich(name: str, dependency: Any) -> None:
        if dependency is None:
            raise RuntimeError(f"Cockpit {name} is unavailable without rich dependencies")

    @staticmethod
    def _record_view(view: str, metadata: Dict[str, Any] = None) -> None:
        details = {"view": view}
        if metadata:
            details.update(metadata)
        get_observability().log(
            "INFO",
            "cockpit_view_rendered",
            "Cockpit view rendered",
            details,
        )
