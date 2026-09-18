"""Turning a driver exception into a `Violation`.

Composes the pieces without knowing any of them concretely: a transport chosen
by driver, an extractor chosen by backend, then the schema registry.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kop.infrastructure.database.common.errors.violations import statement as statement_reader
from kop.infrastructure.database.common.errors.violations.extraction.dispatch import (
    ExtractorRegistry,
    default_extractors,
)
from kop.infrastructure.database.common.errors.violations.extraction.transport import (
    transport_for,
)
from kop.infrastructure.database.common.errors.violations.kinds import Kind
from kop.infrastructure.database.common.errors.violations.violation import (
    Confidence,
    Violation,
)


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from kop.infrastructure.database.common.errors.violations.extraction.protocols import (
        Transport,
    )
    from kop.infrastructure.database.common.errors.violations.extraction.raw import RawError
    from kop.infrastructure.database.common.errors.violations.registry import (
        ConstraintInfo,
        ConstraintRegistry,
    )


@dataclass(frozen=True, slots=True)
class Backend:
    """Which dialect and driver an error came from."""

    name: str
    driver: str


_UNIQUE_LIKE: frozenset[Kind] = frozenset({Kind.UNIQUE, Kind.PRIMARY_KEY})


class ViolationParser:
    """Stages two through five of the pipeline."""

    def __init__(
        self,
        registry: ConstraintRegistry,
        extractors: ExtractorRegistry | None = None,
        transports: Callable[[str | None], Transport] = transport_for,
    ) -> None:
        self._registry = registry
        self._extractors = extractors if extractors is not None else default_extractors()
        self._transports = transports

    def parse(self, error: BaseException, backend: Backend) -> Violation | None:
        """Return the violation behind a SQLAlchemy error, or None if unreadable."""
        original = getattr(error, "orig", None)
        if original is None:
            return None
        extractor = self._extractors.get(backend.name)
        if extractor is None:
            return None
        raw = extractor.extract(self._transports(backend.driver).unwrap(original))
        return self._compose(raw, error, backend, original)

    def _compose(
        self,
        raw: RawError,
        error: BaseException,
        backend: Backend,
        original: BaseException,
    ) -> Violation:
        kind, resolved, table, columns = self._locate(raw, error)
        table = self._registry.canonical_table(table)
        columns = self._registry.canonical_columns(table, columns)
        foreign_key = self._registry.foreign_key(resolved or raw.constraint)
        referred_table = foreign_key.table if foreign_key else None
        return Violation(
            kind=kind,
            backend=backend.name,
            driver=backend.driver,
            code=raw.code,
            message=raw.message,
            confidence=_confidence(raw),
            constraint=raw.constraint,
            resolved=resolved,
            table=table,
            columns=columns,
            values=_align_values(raw.values, columns),
            referred_table=referred_table,
            referred_columns=foreign_key.columns if foreign_key else (),
            entity=self._registry.entity(table),
            referred_entity=self._registry.entity(referred_table),
            statement=getattr(error, "statement", None),
            params=getattr(error, "params", None),
            orig=original,
        )

    def _locate(
        self,
        raw: RawError,
        error: BaseException,
    ) -> tuple[Kind, str | None, str | None, tuple[str, ...]]:
        """Place the violation in the schema, correcting the backend where it errs."""
        named = self._registry.by_name(raw.constraint)
        if named is not None:
            return self._from_name(raw, named)

        statement = getattr(error, "statement", None)
        table = raw.table or statement_reader.table_in(statement)
        if raw.kind not in _UNIQUE_LIKE:
            return self._undirected(raw, statement), None, table, raw.columns

        by_columns = self._registry.by_columns(table, raw.columns)
        if by_columns is not None:
            return by_columns.kind, by_columns.name, table, raw.columns
        if raw.kind is Kind.PRIMARY_KEY:
            # MySQL and MariaDB report "PRIMARY" instead of the declared name.
            primary = self._registry.primary_key(table)
            if primary is not None:
                return raw.kind, primary.name, table, primary.columns
        return raw.kind, None, table, raw.columns

    @staticmethod
    def _undirected(raw: RawError, statement: str | None) -> Kind:
        """Settle a foreign key direction the backend refused to report."""
        reported_nothing = not raw.constraint and not raw.table
        if (
            raw.kind is Kind.FOREIGN_KEY
            and reported_nothing
            and statement_reader.is_delete(statement)
        ):
            return Kind.FOREIGN_KEY_CHILD
        return raw.kind

    @staticmethod
    def _from_name(
        raw: RawError,
        named: ConstraintInfo,
    ) -> tuple[Kind, str | None, str | None, tuple[str, ...]]:
        # Only the schema can tell a primary key from a unique constraint.
        kind = named.kind if raw.kind in _UNIQUE_LIKE else raw.kind
        return kind, named.name, named.table, named.columns or raw.columns


def _align_values(values: Mapping[str, str], columns: tuple[str, ...]) -> dict[str, str]:
    """Key the offending values by column name wherever that is knowable.

    Only PostgreSQL names the columns in its detail line; MySQL and MSSQL report
    a bare value. When the schema settles which column it belonged to, the
    caller gets the same shape from every backend.
    """
    if len(values) == 1 and len(columns) == 1:
        only = next(iter(values.values()))
        return {columns[0]: only}
    return dict(values)


def _confidence(raw: RawError) -> Confidence:
    if raw.structured:
        return Confidence.STRUCTURED
    if raw.constraint or raw.columns or raw.table:
        return Confidence.PARSED
    return Confidence.INFERRED
