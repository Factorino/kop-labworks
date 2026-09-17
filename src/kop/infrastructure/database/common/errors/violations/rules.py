"""Declaring which exception a violation becomes."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kop.infrastructure.database.common.errors.violations.binding import resolve
from kop.infrastructure.database.common.errors.violations.kinds import Kind


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from kop.infrastructure.database.common.errors.violations.binding import Spec
    from kop.infrastructure.database.common.errors.violations.violation import Violation


# Weights, not an ordering: a rule naming a constraint must beat one that only
# names a kind, however the two were declared.
_CONSTRAINT_WEIGHT = 400
_COLUMNS_WEIGHT = 200
_TABLE_WEIGHT = 100
_KIND_WEIGHT = 50
_PREDICATE_WEIGHT = 10


@dataclass(frozen=True, slots=True)
class Rule:
    """One mapping from a matched violation to an exception."""

    factory: Callable[..., BaseException]
    bindings: Mapping[str, Spec] = field(default_factory=dict)
    constraint: str | None = None
    kinds: frozenset[Kind] = frozenset()
    table: str | None = None
    columns: tuple[str, ...] | None = None
    predicate: Callable[[Violation], bool] | None = None

    @property
    def specificity(self) -> int:
        """How narrow this rule is. Higher wins."""
        return (
            (_CONSTRAINT_WEIGHT if self.constraint else 0)
            + (_COLUMNS_WEIGHT if self.columns is not None else 0)
            + (_TABLE_WEIGHT if self.table else 0)
            + (_KIND_WEIGHT if self.kinds else 0)
            + (_PREDICATE_WEIGHT if self.predicate else 0)
        )

    def matches(self, violation: Violation) -> bool:
        """Whether this rule claims the violation."""
        # An unrecognised error goes only to a rule that asked for it by name,
        # so that a connection failure is never dressed up as a domain error.
        if violation.kind is Kind.UNKNOWN and Kind.UNKNOWN not in self.kinds:
            return False
        if self.kinds and violation.kind not in self.kinds:
            return False
        if self.constraint and self.constraint.lower() != _name_of(violation):
            return False
        if self.table and self.table.lower() != (violation.table or "").lower():
            return False
        if self.columns is not None and _columns_of(violation) != self.columns:
            return False
        return self.predicate is None or self.predicate(violation)

    def build(self, violation: Violation) -> BaseException:
        """Construct the exception this rule declares."""
        if not self.bindings and not isinstance(self.factory, type):
            return self.factory(violation)
        return self.factory(
            **{name: resolve(spec, violation) for name, spec in self.bindings.items()},
        )


def _name_of(violation: Violation) -> str:
    return (violation.resolved or violation.constraint or "").lower()


def _columns_of(violation: Violation) -> tuple[str, ...]:
    return tuple(column.lower() for column in violation.columns)


def rule(
    *,
    to: Callable[..., BaseException],
    constraint: str | None = None,
    kind: Kind | Sequence[Kind] | None = None,
    table: str | None = None,
    columns: Sequence[str] | None = None,
    where: Callable[[Violation], bool] | None = None,
    bindings: Mapping[str, Spec] | None = None,
    **keyword_bindings: Spec,
) -> Rule:
    """Declare a rule.

    `to` is either an exception class called with the bindings as keywords, or
    any callable taking the violation and returning an exception. Bindings
    accept a `V` expression, a callable or a plain value.

    `where` gates the rule on facts the backend actually supplies, so one set
    of rules can serve backends that report different amounts of detail.

    The parameter names above are taken, so an exception with a field called
    `constraint`, `table`, `columns`, `kind`, `where`, `to` or `bindings` is
    bound through the explicit `bindings` mapping instead of a keyword.

    Raises:
        ValueError: if a name is given both ways.
    """
    combined = dict(keyword_bindings)
    if bindings:
        clashing = set(bindings) & set(combined)
        if clashing:
            raise ValueError(f"{sorted(clashing)} given both as keywords and in bindings")
        combined.update(bindings)
    kinds = frozenset(
        () if kind is None else ((kind,) if isinstance(kind, Kind) else tuple(kind)),
    )
    return Rule(
        factory=to,
        bindings=combined,
        constraint=constraint,
        kinds=kinds,
        table=table,
        columns=None if columns is None else tuple(c.lower() for c in columns),
        predicate=where,
    )
