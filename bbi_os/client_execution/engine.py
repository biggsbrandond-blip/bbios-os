import threading
from typing import Dict
from uuid import uuid4

from bbi_os.client_execution.errors import ConcurrentExecution
from bbi_os.client_execution.executor import ClientWorkflowExecutor
from bbi_os.client_execution.models import (
    ClientExecutionRecord,
    ClientExecutionRequest,
)
from bbi_os.client_execution.state import (
    ExecutionStateMachine,
    ExecutionStateRepository,
)


class ClientExecutionEngine:
    def __init__(
        self,
        executor: ClientWorkflowExecutor,
        state_repository: ExecutionStateRepository,
    ) -> None:
        self.executor = executor
        self.state_repository = state_repository
        self.state_machine = ExecutionStateMachine(state_repository)
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def schedule(self, request: ClientExecutionRequest) -> ClientExecutionRecord:
        record = ClientExecutionRecord.new(str(uuid4()), request)
        self.state_repository.save(record)
        return record

    def execute(self, request: ClientExecutionRequest) -> ClientExecutionRecord:
        client_lock = self._client_lock(request.client_id)
        if not client_lock.acquire(blocking=False):
            raise ConcurrentExecution("A client execution is already running")
        try:
            record = ClientExecutionRecord.new(str(uuid4()), request)
            self.state_repository.save(record)
            self.state_machine.transition(record, "RUNNING")
            try:
                resolved = self.executor.resolve(
                    request.workflow_id, request.client_id, request.input
                )
                if resolved.uses_external_connector:
                    self.state_machine.transition(record, "WAITING_EXTERNAL")
                instance = self.executor.execute(
                    resolved, request.client_id, request.input
                )
                record.workflow_instance_id = instance.workflow_instance_id
                record.output = dict(instance.output_data)
                self.state_repository.save(record)
                if record.state == "WAITING_EXTERNAL" and instance.execution_status == "completed":
                    self.state_machine.transition(record, "RUNNING")
                if instance.execution_status == "completed":
                    self.state_machine.transition(record, "COMPLETED")
                    return record
                self._record_failure(record, instance)
                return record
            except Exception:
                record.error_reason = "Execution could not be completed"
                self.state_repository.save(record)
                self.state_machine.transition(record, "COMPENSATING")
                self.state_machine.transition(record, "FAILED")
                return record
        finally:
            client_lock.release()

    def _record_failure(self, record: ClientExecutionRecord, instance: object) -> None:
        history = getattr(instance, "step_history", [])
        failed_steps = [step for step in history if step.status == "failed"]
        rolled_back = [step.step_id for step in history if step.status == "rolled_back"]
        record.failure_step = failed_steps[-1].step_id if failed_steps else None
        record.error_reason = "Workflow step failed"
        record.rollback_actions = rolled_back
        self.state_repository.save(record)
        self.state_machine.transition(record, "COMPENSATING")
        self.state_machine.transition(record, "FAILED")

    def _client_lock(self, client_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(client_id, threading.Lock())
