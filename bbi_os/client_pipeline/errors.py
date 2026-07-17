class ClientPipelineError(Exception):
    pass


class InvalidClientRequest(ClientPipelineError):
    pass


class InvalidRequestType(ClientPipelineError):
    pass


class PipelineWorkflowNotFound(ClientPipelineError):
    pass


class PipelineExecutionFailed(ClientPipelineError):
    pass


class PipelineAuthenticationFailed(ClientPipelineError):
    pass

