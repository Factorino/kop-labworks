from abc import ABC
from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Any, Self, dataclass_transform, override


@dataclass_transform(kw_only_default=True, eq_default=False, field_specifiers=(field,))
def entity[ClsT](cls: type[ClsT]) -> type[ClsT]:
    return dataclass(cls, kw_only=True, eq=False)


@entity
class Entity[IdT: Hashable](ABC):
    id: IdT

    def __new__(cls, *_args: Any, **_kwargs: Any) -> Self:
        if cls is Entity:
            raise TypeError("Base Entity cannot be instantiated directly")
        return object.__new__(cls)

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        if name == "id" and "id" in self.__dict__:
            raise AttributeError("Changing entity ID is not permitted")
        return object.__setattr__(self, name, value)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity) or type(other) is not type(self):
            return False
        return other.id == self.id

    @override
    def __hash__(self) -> int:
        return hash((type(self), self.id))
