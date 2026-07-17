
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
