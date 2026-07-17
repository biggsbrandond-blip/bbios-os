from datetime import datetime
import uuid


class CockpitService:

    def __init__(self):
        self.clients = {}
        self.executions = []

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
