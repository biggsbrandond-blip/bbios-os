from dataclasses import dataclass
from typing import Dict

from bbi_os.client_execution.errors import InvalidExecutionRequest


@dataclass(frozen=True)
class ExecutionMode:
    execution_type: str
    immediate: bool


class ExecutionTypeRegistry:
    def __init__(self) -> None:
        self._modes: Dict[str, ExecutionMode] = {
            "one_time": ExecutionMode("one_time", True),
            "scheduled": ExecutionMode("scheduled", False),
            "recurring": ExecutionMode("recurring", False),
        }

    def resolve(self, execution_type: str) -> ExecutionMode:
        try:
            return self._modes[execution_type]
        except KeyError as error:
            raise InvalidExecutionRequest("Unsupported execution_type") from error

