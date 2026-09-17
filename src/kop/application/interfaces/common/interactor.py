from abc import abstractmethod
from typing import Protocol


class Interactor[RequestData, ResponseData](Protocol):
    @abstractmethod
    async def execute(self, request: RequestData) -> ResponseData: ...
