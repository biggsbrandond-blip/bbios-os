from bbi_os.client_execution.models import ClientExecutionRequest
from bbi_os.client_execution.registry import ExecutionMode, ExecutionTypeRegistry


class ClientExecutionRouter:
    def __init__(self, registry: ExecutionTypeRegistry) -> None:
        self.registry = registry

    def route(self, request: ClientExecutionRequest) -> ExecutionMode:
        return self.registry.resolve(request.execution_type)
