from abc import ABC
from dataclasses import dataclass, field, fields
from typing import Any, Self, dataclass_transform


@dataclass_transform(kw_only_default=True, frozen_default=True, field_specifiers=(field,))
def value_object[ClsT](cls: type[ClsT]) -> type[ClsT]:
    dtcls: type[ClsT] = dataclass(cls, frozen=True, kw_only=True)
    _validate_fields(dtcls)
    return dtcls


def _validate_fields(cls: type[Any]) -> None:
    if not any("__dataclass_fields__" in vars(base) for base in cls.__bases__):
        return
    if not fields(cls):
        raise TypeError(f"{cls.__name__} must have at least one field")


@value_object
class ValueObject(ABC):
    def __new__(cls, *_args: Any, **_kwargs: Any) -> Self:
        if cls is ValueObject:
            raise TypeError("Base Value Object cannot be instantiated directly")
        if "__dataclass_fields__" not in vars(cls):
            raise TypeError(f"{cls.__name__} is missing the @value_object decorator")
        return object.__new__(cls)

    def _set(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
