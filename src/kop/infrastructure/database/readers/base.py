from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, ClassVar, Final
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Date,
    DateTime,
    Result,
    Select,
    UnaryExpression,
    Uuid,
    asc,
    bindparam,
    desc,
    func,
    select,
    tuple_,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import operators
from sqlalchemy.types import TypeEngine

from kop.application.dto.base import DTO
from kop.application.dto.query.cursor import (
    DEFAULT_CURSOR_PAGINATION,
    CursorPage,
    CursorPagination,
    KeysetSort,
)
from kop.application.dto.query.filter import (
    Filter,
    OperatorList,
    OperatorNull,
    OperatorRange,
    OperatorScalar,
    OperatorStr,
)
from kop.application.dto.query.pagination import (
    DEFAULT_PAGINATION,
    Page,
    PageMeta,
    Pagination,
)
from kop.application.dto.query.sort import Sort, SortDirection
from kop.domain.errors.common import ValidationError
from kop.infrastructure.database.common.errors.handler import handle_sqlalchemy_errors
from kop.infrastructure.database.models.base import BaseORM
from kop.infrastructure.database.models.types import FlagType
from kop.infrastructure.database.readers.cursor import decode_cursor, encode_cursor


type FilterOperator = Callable[[InstrumentedAttribute[Any], Any], ColumnElement[bool]]


def _between(column: InstrumentedAttribute[Any], value: Any) -> ColumnElement[bool]:
    lower, upper = value
    return column.between(lower, upper)


# Negated as a whole: `< lower OR > upper` differs from NOT BETWEEN on NULL.
def _not_between(column: InstrumentedAttribute[Any], value: Any) -> ColumnElement[bool]:
    lower, upper = value
    return ~column.between(lower, upper)


# How the query vocabulary of the application layer is spelled in SQLAlchemy.
# Module constants: no reader overrides them, and both tables are properties of
# this translation rather than of any one reader.
_OPERATORS: Final[Mapping[StrEnum, FilterOperator]] = MappingProxyType(
    {
        OperatorScalar.EQ: operators.eq,
        OperatorScalar.NE: operators.ne,
        OperatorScalar.GT: operators.gt,
        OperatorScalar.GE: operators.ge,
        OperatorScalar.LT: operators.lt,
        OperatorScalar.LE: operators.le,
        OperatorStr.LIKE: operators.like_op,
        OperatorStr.ILIKE: operators.ilike_op,
        OperatorList.IN: operators.in_op,
        OperatorList.NOT_IN: operators.not_in_op,
        OperatorNull.IS_NULL: operators.is_,
        OperatorNull.IS_NOT_NULL: operators.is_not,
        OperatorRange.BETWEEN: _between,
        OperatorRange.NOT_BETWEEN: _not_between,
    },
)

_DIRECTIONS: Final[Mapping[StrEnum, Callable[[Any], UnaryExpression[Any]]]] = MappingProxyType(
    {
        SortDirection.ASC: asc,
        SortDirection.DESC: desc,
    },
)


class SABaseReader[ViewT: DTO, ORMT: BaseORM](ABC):
    # Not a ClassVar: a ClassVar cannot carry the type parameter.
    _model: type[ORMT]

    _filter_map: ClassVar[Mapping[StrEnum, InstrumentedAttribute[Any]]]
    _sort_map: ClassVar[Mapping[StrEnum, InstrumentedAttribute[Any]]]

    # Appended to every ORDER BY so OFFSET paging never repeats or skips rows.
    # A tuple because a bare InstrumentedAttribute class attribute is a
    # descriptor and would be resolved against the reader instance.
    _tie_break: ClassVar[tuple[InstrumentedAttribute[Any], ...]]

    # Columns must be NOT NULL: a row comparison against NULL matches nothing,
    # so such rows would silently drop out of every page.
    _keyset_map: ClassVar[Mapping[StrEnum, InstrumentedAttribute[Any]]]

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    @abstractmethod
    def _to_view(self, orm_object: ORMT) -> ViewT:
        raise NotImplementedError

    def _select(self) -> Select[tuple[ORMT]]:
        return select(self._model)

    async def _find(self, *whereclause: ColumnElement[bool]) -> ViewT | None:
        orm_object: ORMT | None = await self._find_row(*whereclause)
        return None if orm_object is None else self._to_view(orm_object)

    async def _find_row(self, *whereclause: ColumnElement[bool]) -> ORMT | None:
        query: Select[tuple[ORMT]] = self._select().where(*whereclause)
        result: Result[tuple[ORMT]] = await self._execute(query)
        return result.scalars().first()

    async def _search(
        self,
        filter: Filter[Any] | None = None,
        sort: Sort[Any] | None = None,
        pagination: Pagination = DEFAULT_PAGINATION,
    ) -> Page[ViewT]:
        filtered: Select[tuple[ORMT]] = self._apply_filter(self._select(), filter)

        total: int = await self._count(filtered)

        query: Select[tuple[ORMT]] = self._apply_sort(filtered, sort)
        query = query.offset(pagination.offset).limit(pagination.limit)

        result: Result[tuple[ORMT]] = await self._execute(query)
        views: tuple[ViewT, ...] = tuple(
            self._to_view(row) for row in result.scalars().unique().all()
        )

        meta = PageMeta(page=pagination.page, page_size=pagination.page_size, total=total)
        return Page(data=views, meta=meta)

    async def _search_keyset(
        self,
        sort: KeysetSort[Any],
        filter: Filter[Any] | None = None,
        pagination: CursorPagination = DEFAULT_CURSOR_PAGINATION,
    ) -> CursorPage[ViewT]:
        key: tuple[InstrumentedAttribute[Any], ...] = (
            self._keyset_map[sort.field],
            *self._tie_break,
        )

        query: Select[tuple[ORMT]] = self._apply_filter(self._select(), filter)
        if pagination.cursor is not None:
            query = query.where(self._after_cursor(key, sort, pagination.cursor))

        direction: Callable[[Any], UnaryExpression[Any]] = _DIRECTIONS[sort.direction]
        # One extra row tells whether a next page exists without counting.
        query = query.order_by(*(direction(column) for column in key))
        query = query.limit(pagination.limit + 1)

        result: Result[tuple[ORMT]] = await self._execute(query)
        rows: list[ORMT] = list(result.scalars().unique().all())
        page: list[ORMT] = rows[: pagination.limit]

        next_cursor: str | None = None
        if len(rows) > pagination.limit:
            last: tuple[Any, ...] = tuple(getattr(page[-1], column.key) for column in key)
            next_cursor = encode_cursor(sort, last)

        return CursorPage(data=tuple(self._to_view(row) for row in page), next_cursor=next_cursor)

    # A row-value comparison `(a, id) < (:a, :id)` is served directly by a
    # composite index in the same order.
    def _after_cursor(
        self,
        key: tuple[InstrumentedAttribute[Any], ...],
        sort: KeysetSort[Any],
        cursor: str,
    ) -> ColumnElement[bool]:
        raw: tuple[Any, ...] = decode_cursor(cursor, sort, size=len(key))
        bounds: list[Any] = [
            # Typed, or a UUID or timestamp would be compared as text.
            bindparam(None, _normalize(sort.field, value, column.type), type_=column.type)
            for column, value in zip(key, raw, strict=True)
        ]
        row, after = tuple_(*key), tuple_(*bounds)
        return row < after if sort.direction is SortDirection.DESC else row > after

    async def _count(self, query: Select[tuple[ORMT]]) -> int:
        count_query: Select[tuple[int]] = select(func.count()).select_from(query.subquery())
        result: Result[tuple[int]] = await self._execute(count_query)
        return result.scalar_one()

    def _apply_filter(
        self,
        query: Select[tuple[ORMT]],
        filter: Filter[Any] | None,
    ) -> Select[tuple[ORMT]]:
        if filter is None:
            return query

        for param in filter.params:
            operator: FilterOperator = _OPERATORS[param.operator]
            column: InstrumentedAttribute[Any] = self._filter_map[param.field]
            value: Any = _normalize(param.field, param.value, column.type)
            query = query.where(operator(column, value))

        return query

    def _apply_sort(
        self,
        query: Select[tuple[ORMT]],
        sort: Sort[Any] | None,
    ) -> Select[tuple[ORMT]]:
        if sort is None:
            return query.order_by(*self._tie_break)

        for param in sort.params:
            direction: Callable[[Any], UnaryExpression[Any]] = _DIRECTIONS[param.direction]
            query = query.order_by(direction(self._sort_map[param.field]))

        return query.order_by(*self._tie_break)

    @handle_sqlalchemy_errors
    async def _execute[RowT: tuple[Any, ...]](self, query: Select[RowT]) -> Result[RowT]:
        result: Result[RowT] = await self._session.execute(query)
        return result


# Filter values arrive as JSON scalars; only the column type knows what they
# must become.
def _normalize(field: StrEnum, value: Any, column_type: TypeEngine[Any]) -> Any:
    if isinstance(value, tuple):
        return tuple(_normalize(field, item, column_type) for item in value)

    # `Uuid`, not `UUID`: `Mapped[UUID]` maps to the generic type, and the
    # dialect-specific `UUID` is only its subclass.
    if isinstance(column_type, Uuid) and isinstance(value, str):
        return _coerce(field, value, UUID)

    if isinstance(column_type, FlagType):
        return _to_flag(field, value, column_type)

    if isinstance(column_type, DateTime) and isinstance(value, str):
        return _to_datetime(field, value, column_type)

    if isinstance(column_type, Date) and isinstance(value, str):
        return _coerce(field, value, date.fromisoformat, expected="date")

    return value


def _to_flag(field: StrEnum, value: Any, column_type: FlagType[Any]) -> Any:
    if isinstance(value, str):
        member: Any = column_type.flag.__members__.get(value.strip().upper())
        if member is None:
            raise ValidationError(field=field.value, reason=f"unknown value '{value}'")
        return member
    return _coerce(field, value, column_type.flag)


# A naive value is refused: Postgres would silently apply the session timezone.
def _to_datetime(field: StrEnum, value: str, column_type: DateTime) -> datetime:
    moment: datetime = _coerce(field, value, datetime.fromisoformat, expected="datetime")

    if column_type.timezone and moment.tzinfo is None:
        raise ValidationError(
            field=field.value,
            reason="must carry a UTC offset, as the column is timezone-aware",
        )

    return moment


def _coerce(
    field: StrEnum,
    value: Any,
    into: Callable[[Any], Any],
    expected: str | None = None,
) -> Any:
    try:
        return into(value)
    except (ValueError, TypeError) as error:
        raise ValidationError(
            field=field.value,
            reason=f"is not a valid {expected or into.__name__}",
        ) from error
