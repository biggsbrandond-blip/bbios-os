class ClientExecutionError(Exception):
    pass


class InvalidExecutionRequest(ClientExecutionError):
    pass


class ExecutionClientNotFound(ClientExecutionError):
    pass


class ExecutionWorkflowNotFound(ClientExecutionError):
    pass


class ExecutionFailed(ClientExecutionError):
    pass


class ExecutionNotFound(ClientExecutionError):
    pass


class ConcurrentExecution(ClientExecutionError):
    pass


class ExecutionAuthenticationFailed(ClientExecutionError):
    pass

