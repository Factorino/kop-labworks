"""The normalised description of a database error."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Mapping

    from kop.infrastructure.database.common.errors.violations.kinds import Kind


class Confidence(StrEnum):
    """Which tier of the extraction pipeline produced the facts.

    The tiers are ordered: a driver that exposes error fields is believed over
    a regular expression, which is believed over anything reconstructed from
    the statement that was sent.
    """

    STRUCTURED = auto()
    """Read from fields the driver exposes; no text was parsed."""
    PARSED = auto()
    """Recovered by matching the server's message."""
    INFERRED = auto()
    """Reconstructed from the statement or the schema, not reported by the server."""


@dataclass(frozen=True, slots=True)
class Violation:
    """Everything known about one database error, in a backend-neutral shape."""

    kind: Kind
    backend: str
    driver: str
    code: str | None
    """The backend's own code: SQLSTATE, errno, ORA number or SQLite error name."""
    message: str
    confidence: Confidence

    constraint: str | None = None
    """The name exactly as the server reported it."""
    resolved: str | None = None
    """The name as `MetaData` knows it, once the registry has had its say."""
    table: str | None = None
    columns: tuple[str, ...] = ()
    values: Mapping[str, str] = field(default_factory=dict)
    """Offending values by column, where the backend reports them."""

    referred_table: str | None = None
    """For a foreign key, the table pointed at. Taken from `MetaData`."""
    referred_columns: tuple[str, ...] = ()

    entity: str | None = None
    referred_entity: str | None = None

    statement: str | None = None
    params: Any = None
    orig: BaseException | None = None

    @property
    def column(self) -> str | None:
        """The first column involved, if any."""
        return self.columns[0] if self.columns else None

    @property
    def referred_column(self) -> str | None:
        """The first referenced column, if any."""
        return self.referred_columns[0] if self.referred_columns else None

    @property
    def value(self) -> str | None:
        """The first offending value, if the backend reported one."""
        return next(iter(self.values.values()), None)


VIOLATION_ATTRIBUTES: frozenset[str] = frozenset(Violation.__slots__) | {
    "column",
    "referred_column",
    "value",
}
"""Names a binding may read. Used to reject typos before the application runs."""
