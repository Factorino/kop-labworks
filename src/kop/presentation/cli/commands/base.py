from abc import abstractmethod
from typing import Protocol


# The CLI counterpart of an application `Interactor`: one command, one request,
# one response, and no idea how any of it reaches a terminal.
class CliCommand[RequestData, ResponseData](Protocol):
    @abstractmethod
    async def execute(self, request: RequestData) -> ResponseData: ...
