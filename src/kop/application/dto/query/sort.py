from enum import StrEnum, auto
from typing import Annotated, Final, Self

from pydantic import Field, model_validator

from kop.application.dto.base import DTO


__all__: list[str] = ["Sort", "SortDirection", "SortParam"]


_MAX_PARAMS: Final[int] = 8


class SortDirection(StrEnum):
    ASC = auto()
    DESC = auto()


class SortParam[FieldT: StrEnum](DTO):
    field: FieldT
    direction: SortDirection = SortDirection.ASC


# Not a total order by itself: readers append a unique tie-break column.
class Sort[FieldT: StrEnum](DTO):
    params: Annotated[tuple[SortParam[FieldT], ...], Field(max_length=_MAX_PARAMS)] = ()

    @model_validator(mode="after")
    def _reject_repeated_fields(self) -> Self:
        fields: list[FieldT] = [param.field for param in self.params]
        if len(set(fields)) != len(fields):
            raise ValueError("A field may be sorted on only once")
        return self
