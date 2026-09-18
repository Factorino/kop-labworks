"""The reverse index over `MetaData`.

It does more than decorate a violation. Where the server cannot answer, the
schema can: no backend distinguishes a primary key from a unique constraint by
code alone, MySQL discards the pk_* name outright, and Oracle upper-cases
everything it reports.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.sql.schema import ColumnCollectionConstraint

from kop.infrastructure.database.common.errors.violations.kinds import Kind


if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from sqlalchemy import Constraint, MetaData, Table


@dataclass(frozen=True, slots=True)
class ConstraintInfo:
    """What `MetaData` knows about one constraint or unique index."""

    name: str | None
    kind: Kind
    table: str
    columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ForeignKeyInfo:
    """The far side of a foreign key: the thing that was not found."""

    table: str
    columns: tuple[str, ...]


_CONSTRAINT_KINDS: tuple[tuple[type[Constraint], Kind], ...] = (
    (PrimaryKeyConstraint, Kind.PRIMARY_KEY),
    (UniqueConstraint, Kind.UNIQUE),
    (ForeignKeyConstraint, Kind.FOREIGN_KEY),
    (CheckConstraint, Kind.CHECK),
)


def _columns_of(constraint: Constraint) -> tuple[str, ...]:
    # A CheckConstraint is one of these too, and reports the columns its
    # expression mentions - useful, when SQLAlchemy can work them out.
    if isinstance(constraint, ColumnCollectionConstraint):
        return tuple(column.name for column in constraint.columns)
    return ()


def _kind_of(constraint: Constraint) -> Kind | None:
    for constraint_type, kind in _CONSTRAINT_KINDS:
        if isinstance(constraint, constraint_type):
            return kind
    return None


class ConstraintRegistry:
    """Looks a reported name, or a table and columns, back up in the schema."""

    def __init__(self, metadata: MetaData, entities: Mapping[str, str] | None = None) -> None:
        self._by_name: dict[str, ConstraintInfo] = {}
        self._by_columns: dict[tuple[str, tuple[str, ...]], ConstraintInfo] = {}
        self._primary_keys: dict[str, ConstraintInfo] = {}
        self._foreign_keys: dict[str, ForeignKeyInfo] = {}
        self._tables: dict[str, Table] = {}
        self._entities: dict[str, str] = {
            table.lower(): entity for table, entity in (entities or {}).items()
        }
        for table in metadata.tables.values():
            self._index(table)

    def _index(self, table: Table) -> None:
        self._tables[table.name.lower()] = table
        for constraint in table.constraints:
            self._index_constraint(table, constraint)
        for index in table.indexes:
            # unique=True together with index=True yields an index, not a
            # UniqueConstraint, and the server reports the index name.
            if index.unique and index.name:
                columns = tuple(column.name for column in index.columns)
                info = ConstraintInfo(str(index.name), Kind.UNIQUE, table.name, columns)
                self._by_name[str(index.name).lower()] = info
                self._by_columns.setdefault((table.name.lower(), columns), info)

    def _index_constraint(self, table: Table, constraint: Constraint) -> None:
        kind = _kind_of(constraint)
        if kind is None:
            return
        columns = _columns_of(constraint)
        name = str(constraint.name) if constraint.name is not None else None
        info = ConstraintInfo(name, kind, table.name, columns)
        if name is not None:
            self._by_name[name.lower()] = info
        if kind is Kind.PRIMARY_KEY:
            self._primary_keys[table.name.lower()] = info
        if kind in (Kind.PRIMARY_KEY, Kind.UNIQUE) and columns:
            self._by_columns[table.name.lower(), columns] = info
        if isinstance(constraint, ForeignKeyConstraint) and name is not None:
            target = constraint.elements[0].column.table.name
            referred = tuple(element.column.name for element in constraint.elements)
            self._foreign_keys[name.lower()] = ForeignKeyInfo(target, referred)

    def by_name(self, name: str | None) -> ConstraintInfo | None:
        """Look a constraint up by the name the server reported."""
        return self._by_name.get(name.lower()) if name else None

    def by_columns(self, table: str | None, columns: Iterable[str]) -> ConstraintInfo | None:
        """Look a unique or primary key up by the columns it covers."""
        if not table:
            return None
        return self._by_columns.get((table.lower(), tuple(columns)))

    def primary_key(self, table: str | None) -> ConstraintInfo | None:
        """The primary key of a table, for backends that refuse to name it."""
        return self._primary_keys.get(table.lower()) if table else None

    def foreign_key(self, name: str | None) -> ForeignKeyInfo | None:
        """The referenced table and columns of a foreign key."""
        return self._foreign_keys.get(name.lower()) if name else None

    def entity(self, table: str | None) -> str | None:
        """The human-readable name of whatever the table holds."""
        return self._entities.get(table.lower()) if table else None

    def canonical_table(self, table: str | None) -> str | None:
        """The table name as declared, correcting the case Oracle reports."""
        if not table:
            return None
        known = self._tables.get(table.lower())
        return known.name if known is not None else table

    def canonical_columns(self, table: str | None, columns: Iterable[str]) -> tuple[str, ...]:
        """Column names as declared, correcting the case Oracle reports."""
        known = self._tables.get(table.lower()) if table else None
        if known is None:
            return tuple(columns)
        declared = {column.name.lower(): column.name for column in known.columns}
        return tuple(declared.get(column.lower(), column) for column in columns)

    @property
    def names(self) -> frozenset[str]:
        """Every constraint and unique index name, lower-cased."""
        return frozenset(self._by_name)
