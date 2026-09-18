"""The result of reading a driver exception, before the schema is consulted."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping

    from kop.infrastructure.database.common.errors.violations.kinds import Kind


@dataclass(frozen=True, slots=True)
class RawError:
    """What one backend extractor could establish on its own."""

    kind: Kind
    code: str | None
    message: str
    constraint: str | None = None
    table: str | None = None
    columns: tuple[str, ...] = ()
    values: Mapping[str, str] = field(default_factory=dict)
    structured: bool = False
    """True when every field above came from driver attributes, not a regex."""
