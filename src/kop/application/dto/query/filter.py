from datetime import date, datetime
from enum import StrEnum, auto
from typing import Annotated, Any, ClassVar, Final, Self

from pydantic import Discriminator, Field, Tag, model_validator

from kop.application.dto.base import DTO


__all__: list[str] = [
    "AnyFilter",
    "Filter",
    "FilterList",
    "FilterNull",
    "FilterRange",
    "FilterScalar",
    "FilterStr",
    "OperatorList",
    "OperatorNull",
    "OperatorRange",
    "OperatorScalar",
    "OperatorStr",
    "ScalarValue",
]


_MAX_PARAMS: Final[int] = 32


# Richer types (UUID, flags) travel as strings and are coerced by the reader,
# the only place that knows the column type.
ScalarValue = int | float | str | bool | date | datetime


class OperatorScalar(StrEnum):
    EQ = auto()
    NE = auto()
    GT = auto()
    GE = auto()
    LT = auto()
    LE = auto()


class OperatorStr(StrEnum):
    LIKE = auto()
    ILIKE = auto()


class OperatorList(StrEnum):
    IN = auto()
    NOT_IN = auto()


class OperatorNull(StrEnum):
    IS_NULL = auto()
    IS_NOT_NULL = auto()


class OperatorRange(StrEnum):
    BETWEEN = auto()
    NOT_BETWEEN = auto()


class _FilterParam[FieldT: StrEnum](DTO):
    _abstract_: ClassVar[bool] = True

    field: FieldT


class FilterScalar[FieldT: StrEnum](_FilterParam[FieldT]):
    operator: OperatorScalar
    value: ScalarValue


class FilterStr[FieldT: StrEnum](_FilterParam[FieldT]):
    operator: OperatorStr
    # A raw LIKE pattern: '%' and '_' are wildcards.
    value: str


class FilterList[FieldT: StrEnum](_FilterParam[FieldT]):
    operator: OperatorList
    # `IN ()` is a syntax error on some databases.
    value: Annotated[tuple[ScalarValue, ...], Field(min_length=1)]


class FilterNull[FieldT: StrEnum](_FilterParam[FieldT]):
    operator: OperatorNull
    value: None = None


# Exists for NOT BETWEEN and for rejecting an inverted range; a closed range
# alone is expressible as `ge` plus `le`.
class FilterRange[FieldT: StrEnum](_FilterParam[FieldT]):
    operator: OperatorRange
    value: tuple[ScalarValue, ScalarValue]

    @model_validator(mode="after")
    def _reject_inverted_range(self) -> Self:
        # Ends of different types (str vs date) raise TypeError on comparison.
        lower: Any
        upper: Any
        lower, upper = self.value

        try:
            inverted: bool = lower > upper
        except TypeError as error:
            raise ValueError("Both ends of a range must be of the same type") from error

        if inverted:
            raise ValueError("The lower end of a range must not exceed the upper end")
        return self


_SCALAR: Final[str] = "scalar"
_STR: Final[str] = "str"
_LIST: Final[str] = "list"
_NULL: Final[str] = "null"
_RANGE: Final[str] = "range"

# The operator enums are disjoint, so the operator picks the branch; without
# the tag pydantic reports a failure for every member of the union.
_TAG_BY_OPERATOR: Final[dict[str, str]] = (
    {operator.value: _SCALAR for operator in OperatorScalar}
    | {operator.value: _STR for operator in OperatorStr}
    | {operator.value: _LIST for operator in OperatorList}
    | {operator.value: _NULL for operator in OperatorNull}
    | {operator.value: _RANGE for operator in OperatorRange}
)


def _operator_tag(value: Any) -> str | None:
    operator: Any = (
        value.get("operator") if isinstance(value, dict) else getattr(value, "operator", None)
    )
    return None if operator is None else _TAG_BY_OPERATOR.get(str(operator))


type AnyFilter[FieldT: StrEnum] = Annotated[
    Annotated[FilterScalar[FieldT], Tag(_SCALAR)]
    | Annotated[FilterStr[FieldT], Tag(_STR)]
    | Annotated[FilterList[FieldT], Tag(_LIST)]
    | Annotated[FilterNull[FieldT], Tag(_NULL)]
    | Annotated[FilterRange[FieldT], Tag(_RANGE)],
    Discriminator(_operator_tag),
]


class Filter[FieldT: StrEnum](DTO):
    params: Annotated[tuple[AnyFilter[FieldT], ...], Field(max_length=_MAX_PARAMS)] = ()
