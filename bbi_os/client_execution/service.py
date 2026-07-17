import time
from typing import Any, Dict

from bbi_os.client_execution.engine import ClientExecutionEngine
from bbi_os.client_execution.errors import (
    ExecutionAuthenticationFailed,
    ExecutionClientNotFound,
    ExecutionNotFound,
    InvalidExecutionRequest,
)
from bbi_os.client_execution.models import (
    ClientExecutionRecord,
    ClientExecutionRequest,
)
from bbi_os.client_execution.router import ClientExecutionRouter
from bbi_os.client_execution.state import ExecutionStateRepository
from bbi_os.entity_repository import EntityRepository
from bbi_os.observability import current_request_context, get_observability


class ClientExecutionService:
    def __init__(
        self,
        clients: EntityRepository,
        router: ClientExecutionRouter,
        engine: ClientExecutionEngine,
        state_repository: ExecutionStateRepository,
    ) -> None:
        self.clients = clients
        self.router = router
        self.engine = engine
        self.state_repository = state_repository

    def start(self, data: Dict[str, Any]) -> ClientExecutionRecord:
        started = time.perf_counter()
        request = ClientExecutionRequest.from_dict(data)
        self._validate_access(request.client_id)
        mode = self.router.route(request)
        record = (
            self.engine.execute(request)
            if mode.immediate
            else self.engine.schedule(request)
        )
        self._event(record, started)
        return record

    def schedule(self, data: Dict[str, Any]) -> ClientExecutionRecord:
        started = time.perf_counter()
        request = ClientExecutionRequest.from_dict(data)
        self._validate_access(request.client_id)
        mode = self.router.route(request)
        if mode.immediate:
            raise InvalidExecutionRequest(
                "schedule-execution requires scheduled or recurring execution_type"
            )
        record = self.engine.schedule(request)
        self._event(record, started)
        return record

    def status(self, client_id: str) -> ClientExecutionRecord:
        self._validate_access(client_id)
        record = self.state_repository.latest_for_client(client_id)
        if record is None:
            raise ExecutionNotFound("Client execution was not found")
        return record

    def _validate_access(self, client_id: str) -> None:
        context = current_request_context()
        if context["user_id"] in {"anonymous", "system", ""}:
            raise ExecutionAuthenticationFailed("Authentication required")
        if self.clients.get(client_id) is None:
            raise ExecutionClientNotFound("Client was not found")

    @staticmethod
    def _event(record: ClientExecutionRecord, started: float) -> None:
        get_observability().log(
            "ERROR" if record.state == "FAILED" else "INFO",
            "client_execution_completed"
            if record.state == "COMPLETED"
            else "client_execution_recorded",
            "Client execution processed",
            {
                "event_type": "client_execution_processed",
                "client_id": record.client_id,
                "execution_id": record.execution_id,
                "workflow_instance_id": record.workflow_instance_id,
                "execution_state": record.state,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "failure_step": record.failure_step,
                "rollback_actions": list(record.rollback_actions),
            },
        )

