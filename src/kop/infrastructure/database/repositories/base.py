from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import ColumnElement, Executable, Result, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from kop.infrastructure.database.common.errors.handler import handle_sqlalchemy_errors
from kop.infrastructure.database.models.base import BaseORM


class SABaseRepository[EntityT, ORMT: BaseORM](ABC):
    # Not a ClassVar: a ClassVar cannot carry the type parameter.
    _model: type[ORMT]

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    @abstractmethod
    def _to_domain(self, orm_object: ORMT) -> EntityT:
        raise NotImplementedError

    async def _find(self, *whereclause: ColumnElement[bool]) -> EntityT | None:
        query: Select[tuple[ORMT]] = select(self._model).where(*whereclause)
        result: Result[tuple[ORMT]] = await self._execute(query)
        orm_object: ORMT | None = result.scalars().first()
        return None if orm_object is None else self._to_domain(orm_object)

    async def _exists(self, *whereclause: ColumnElement[bool]) -> bool:
        query: Select[tuple[Any]] = select(self._model.__mapper__.primary_key[0]).where(
            *whereclause,
        )
        result: Result[tuple[Any]] = await self._execute(query)
        return result.first() is not None

    # Only reads pass here; writes surface at commit in the transaction manager.
    @handle_sqlalchemy_errors
    async def _execute(self, statement: Executable) -> Result[Any]:
        result: Result[Any] = await self._session.execute(statement)
        return result
