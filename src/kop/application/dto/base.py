from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict


class DTO(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    _abstract_: ClassVar[bool] = True

    def __new__(cls, *_args: Any, **_kwargs: Any) -> Self:
        origin: type[BaseModel] | None = cls.__pydantic_generic_metadata__["origin"]
        declaring: type[BaseModel] = origin or cls
        if declaring.__dict__.get("_abstract_", False):
            raise TypeError(f"{declaring.__name__} cannot be instantiated directly")
        return super().__new__(cls)
