from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Self


class AbstractTransactionManager(ABC):
    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def flush(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Self]:
        try:
            yield self
            await self.commit()
        except BaseException:
            await self.rollback()
            raise
