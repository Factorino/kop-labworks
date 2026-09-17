from enum import StrEnum
from typing import Annotated, Final

from pydantic import Field, computed_field

from kop.application.dto.base import DTO
from kop.application.dto.query.pagination import PageSize
from kop.application.dto.query.sort import SortDirection


__all__: list[str] = [
    "DEFAULT_CURSOR_PAGINATION",
    "Cursor",
    "CursorPage",
    "CursorPagination",
    "KeysetSort",
]


Cursor = Annotated[str, Field(min_length=1, max_length=512)]


# A single key: continuing after a row is only defined for the ordering the
# cursor was cut from.
class KeysetSort[FieldT: StrEnum](DTO):
    field: FieldT
    direction: SortDirection = SortDirection.DESC


class CursorPagination(DTO):
    cursor: Cursor | None = None
    limit: PageSize = 25


DEFAULT_CURSOR_PAGINATION: Final[CursorPagination] = CursorPagination()


class CursorPage[DataT](DTO):
    data: tuple[DataT, ...]
    next_cursor: Cursor | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_next(self) -> bool:
        return self.next_cursor is not None
