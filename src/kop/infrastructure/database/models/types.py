from enum import Flag
from typing import Any, override

from sqlalchemy import Dialect, Integer
from sqlalchemy.types import TypeDecorator, TypeEngine


# SQLAlchemy's Enum stores member names and has none for a composite flag, so
# a flag is stored as its integer value.
class FlagType[FlagT: Flag](TypeDecorator[FlagT]):
    impl: TypeEngine[Any] | type[TypeEngine[Any]] = Integer
    cache_ok: bool | None = True

    def __init__(self, flag: type[FlagT]) -> None:
        super().__init__()
        self.flag: type[FlagT] = flag

    @override
    def process_bind_param(self, value: FlagT | None, dialect: Dialect) -> int | None:
        return None if value is None else value.value

    @override
    def process_result_value(self, value: int | None, dialect: Dialect) -> FlagT | None:
        return None if value is None else self.flag(value)
