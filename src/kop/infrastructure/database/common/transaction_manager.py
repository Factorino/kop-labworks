from typing import override

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from kop.application.interfaces.common.transaction_manager import (
    AbstractTransactionManager,
)
from kop.domain.errors.base import AppError
from kop.infrastructure.database.common.errors.handler import handle_sqlalchemy_error


_logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(__name__)


class SATransactionManager(AbstractTransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    @override
    async def commit(self) -> None:
        try:
            await self._session.commit()
        # Already translated by the engine's policy, so not a SQLAlchemyError.
        except AppError:
            await self._safe_rollback()
            raise
        except SQLAlchemyError as exception:
            await self._safe_rollback()
            handle_sqlalchemy_error(exception)

    @override
    async def flush(self) -> None:
        try:
            await self._session.flush()
        except AppError:
            await self._safe_rollback()
            raise
        except SQLAlchemyError as exception:
            await self._safe_rollback()
            handle_sqlalchemy_error(exception)

    @override
    async def rollback(self) -> None:
        await self._session.rollback()

    async def _safe_rollback(self) -> None:
        try:
            await self._session.rollback()
        except SQLAlchemyError:
            await _logger.aexception("transaction.rollback_failed")
