from abc import abstractmethod
from datetime import datetime
from typing import Protocol


class IClock(Protocol):
    # Always timezone-aware UTC.
    @abstractmethod
    def now(self) -> datetime: ...
