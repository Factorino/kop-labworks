from abc import abstractmethod
from typing import ClassVar, Protocol


class IDependencyProbe(Protocol):
    name: ClassVar[str]

    @abstractmethod
    async def is_available(self) -> bool: ...
