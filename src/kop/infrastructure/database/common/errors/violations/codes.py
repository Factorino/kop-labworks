"""Backend code tables.

Data, not logic: SQLSTATE codes as PostgreSQL reports them. A table per
backend, never a shared one — the same number means different things on
different servers.
"""

from __future__ import annotations
from typing import Final

from kop.infrastructure.database.common.errors.violations.kinds import Kind


POSTGRES: Final[dict[str, Kind]] = {
    "23505": Kind.UNIQUE,
    "23503": Kind.FOREIGN_KEY,
    "23502": Kind.NOT_NULL,
    "23514": Kind.CHECK,
    "23P01": Kind.EXCLUSION,
    "23001": Kind.FOREIGN_KEY_CHILD,
    "22001": Kind.VALUE_TOO_LONG,
    "22P02": Kind.INVALID_VALUE,
    "22003": Kind.INVALID_VALUE,
    "40P01": Kind.DEADLOCK,
    "40001": Kind.SERIALIZATION,
    "55P03": Kind.LOCK_TIMEOUT,
}
