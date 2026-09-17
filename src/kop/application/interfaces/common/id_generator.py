from abc import abstractmethod
from collections.abc import Hashable
from typing import Protocol


class IIdGenerator[IdT: Hashable](Protocol):
    @abstractmethod
    def generate(self) -> IdT: ...
