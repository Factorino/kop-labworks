import secrets
import time
from typing import ClassVar, cast, override
from uuid import UUID

from kop.application.interfaces.common.id_generator import IIdGenerator


class UUIDv7Generator[IdT: UUID](IIdGenerator[IdT]):
    _VERSION: ClassVar[int] = 7
    _VARIANT: ClassVar[int] = 0b10

    _TIMESTAMP_BITS: ClassVar[int] = 48
    _RAND_A_BITS: ClassVar[int] = 12
    _RAND_B_BITS: ClassVar[int] = 62

    _MS_IN_NS: ClassVar[int] = 1_000_000

    @override
    def generate(self) -> IdT:
        return cast("IdT", self._uuid7())

    # RFC 9562 layout: 48 bits of ms, 4 version, 12 random, 2 variant, 62 random.
    def _uuid7(self) -> UUID:
        timestamp_ms: int = time.time_ns() // self._MS_IN_NS

        value: int = (timestamp_ms & (1 << self._TIMESTAMP_BITS) - 1) << 80
        value |= self._VERSION << 76
        value |= secrets.randbits(self._RAND_A_BITS) << 64
        value |= self._VARIANT << self._RAND_B_BITS
        value |= secrets.randbits(self._RAND_B_BITS)

        return UUID(int=value)
