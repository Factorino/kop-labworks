"""The per-kind detail a backend can read out of its message."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class Detail:
    """Whatever a message yielded beyond the code itself."""

    constraint: str | None = None
    table: str | None = None
    columns: tuple[str, ...] = ()
    values: Mapping[str, str] = field(default_factory=dict)
    primary_key: bool = False
    """Set when the server said the key was the primary one without naming it."""
