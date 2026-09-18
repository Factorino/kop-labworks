"""PostgreSQL: the one backend that exposes structured error fields.

Five drivers expose them in four different shapes, so reading the fields is a
strategy of its own, chosen per exception rather than per driver.
"""

from __future__ import annotations
from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Any, Final, Protocol, runtime_checkable

from kop.infrastructure.database.common.errors.violations import codes
from kop.infrastructure.database.common.errors.violations.extraction.raw import RawError
from kop.infrastructure.database.common.errors.violations.kinds import Kind


if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class PostgresFields:
    """The subset of the PostgreSQL error protocol this library uses."""

    sqlstate: str | None
    message: str
    constraint: str | None = None
    table: str | None = None
    column: str | None = None
    detail: str | None = None
    structured: bool = True


@runtime_checkable
class FieldReader(Protocol):
    """One way of getting at the PostgreSQL error fields."""

    def read(self, error: BaseException) -> PostgresFields | None:
        """Return the fields, or None if this reader does not apply."""
        ...


class DiagReader:
    """psycopg2, psycopg2cffi and psycopg 3, which all carry a `diag` object."""

    def read(self, error: BaseException) -> PostgresFields | None:
        """Read the fields off the driver's `diag` object."""
        diag: Any = getattr(error, "diag", None)
        if diag is None:
            return None
        return PostgresFields(
            sqlstate=getattr(diag, "sqlstate", None),
            message=diag.message_primary or str(error),
            constraint=diag.constraint_name,
            table=diag.table_name,
            column=diag.column_name,
            detail=diag.message_detail,
        )


class CauseReader:
    """asyncpg, whose adapter keeps only SQLSTATE but chains the original."""

    def read(self, error: BaseException) -> PostgresFields | None:
        """Read the fields off the chained asyncpg exception."""
        cause = error.__cause__
        if cause is None or not hasattr(cause, "constraint_name"):
            return None
        return PostgresFields(
            sqlstate=getattr(cause, "sqlstate", None),
            message=getattr(cause, "message", str(cause)),
            constraint=cause.constraint_name,
            table=getattr(cause, "table_name", None),
            column=getattr(cause, "column_name", None),
            detail=getattr(cause, "detail", None),
        )


class MappingReader:
    """pg8000, which hands over the protocol fields as a dict."""

    def read(self, error: BaseException) -> PostgresFields | None:
        """Read the fields out of pg8000's argument dict."""
        args: tuple[Any, ...] = getattr(error, "args", ())
        if not args or not isinstance(args[0], dict):
            return None
        fields: dict[str, Any] = args[0]
        return PostgresFields(
            sqlstate=fields.get("C"),
            message=fields.get("M", ""),
            constraint=fields.get("n"),
            table=fields.get("t"),
            column=fields.get("c"),
            detail=fields.get("D"),
        )


class MessageReader:
    """Last resort: whatever the exception says, plus a SQLSTATE if present."""

    def read(self, error: BaseException) -> PostgresFields:
        """Fall back to the message text and whatever code is exposed."""
        return PostgresFields(
            sqlstate=getattr(error, "sqlstate", None) or getattr(error, "pgcode", None),
            message=str(error),
            structured=False,
        )


_DETAIL_KEY: Final[re.Pattern[str]] = re.compile(
    r"Key \((?P<columns>.+?)\)=\((?P<values>.+?)\)",
)
_RELATION: Final[re.Pattern[str]] = re.compile(r'relation "(.+?)"|table "(.+?)"')
_NULL_COLUMN: Final[re.Pattern[str]] = re.compile(r'null value in column "(.+?)"')

# 23503 covers both directions; only the opening words distinguish them.
_CHILD_PREFIXES: Final[tuple[str, ...]] = ("update or delete", "remove or update")


class PostgresExtractor:
    """Reads a PostgreSQL error through whichever field reader applies."""

    def __init__(self, readers: Sequence[FieldReader] | None = None) -> None:
        self._readers: tuple[FieldReader, ...] = tuple(
            readers
            if readers is not None
            else (DiagReader(), CauseReader(), MappingReader(), MessageReader())
        )

    def extract(self, error: BaseException) -> RawError:
        """Read a PostgreSQL error through the first reader that applies."""
        fields = self._read(error)
        kind = self._kind(fields)
        columns, values = self._key(fields)
        return RawError(
            kind=kind,
            code=fields.sqlstate,
            message=fields.message,
            constraint=fields.constraint,
            table=fields.table or self._table_from_message(fields.message),
            columns=columns,
            values=values,
            structured=fields.structured,
        )

    def _read(self, error: BaseException) -> PostgresFields:
        for reader in self._readers:
            fields = reader.read(error)
            if fields is not None:
                return fields
        return MessageReader().read(error)

    @staticmethod
    def _kind(fields: PostgresFields) -> Kind:
        kind = codes.POSTGRES.get(fields.sqlstate or "", Kind.UNKNOWN)
        if kind is Kind.FOREIGN_KEY and fields.message.startswith(_CHILD_PREFIXES):
            return Kind.FOREIGN_KEY_CHILD
        return kind

    def _key(self, fields: PostgresFields) -> tuple[tuple[str, ...], dict[str, str]]:
        if fields.detail:
            matched = _DETAIL_KEY.search(fields.detail)
            if matched is not None:
                columns = tuple(c.strip() for c in matched["columns"].split(","))
                values = [v.strip() for v in matched["values"].split(",")]
                return columns, dict(zip(columns, values, strict=False))
        if fields.column:
            return (fields.column,), {}
        return self._null_column(fields.message), {}

    @staticmethod
    def _null_column(message: str) -> tuple[str, ...]:
        matched = _NULL_COLUMN.search(message)
        return (matched[1],) if matched else ()

    @staticmethod
    def _table_from_message(message: str) -> str | None:
        matched = _RELATION.search(message)
        if matched is None:
            return None
        return matched[1] or matched[2]
