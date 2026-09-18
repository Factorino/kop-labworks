import asyncio
from typing import ClassVar, override

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine
import structlog

from kop.application.interfaces.system.dependency_probe import IDependencyProbe


_logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(__name__)


class SADatabaseProbe(IDependencyProbe):
    name: ClassVar[str] = "database"

    def __init__(self, engine: AsyncEngine, timeout_seconds: float) -> None:
        self._engine: AsyncEngine = engine
        self._timeout_seconds: float = timeout_seconds

    @override
    async def is_available(self) -> bool:
        # Own connection: the probe must not open a transaction a request inherits.
        try:
            async with (
                asyncio.timeout(self._timeout_seconds),
                self._engine.connect() as connection,
            ):
                await connection.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError):
            await _logger.awarning("readiness.dependency_unavailable", dependency=self.name)
            return False
        return True
