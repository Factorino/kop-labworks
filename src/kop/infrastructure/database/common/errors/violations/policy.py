"""The public entry point: a policy that turns database errors into your own."""

from __future__ import annotations
from typing import TYPE_CHECKING

from kop.infrastructure.database.common.errors.violations.binding import resolve
from kop.infrastructure.database.common.errors.violations.kinds import Kind
from kop.infrastructure.database.common.errors.violations.parser import ViolationParser
from kop.infrastructure.database.common.errors.violations.registry import ConstraintRegistry
from kop.infrastructure.database.common.errors.violations.rules import Rule, rule
from kop.infrastructure.database.common.errors.violations.validation import check_rule


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from sqlalchemy import MetaData

    from kop.infrastructure.database.common.errors.violations.binding import Spec
    from kop.infrastructure.database.common.errors.violations.extraction.dispatch import (
        ExtractorRegistry,
    )
    from kop.infrastructure.database.common.errors.violations.parser import Backend
    from kop.infrastructure.database.common.errors.violations.violation import Violation


type _Factory = Callable[[Violation], BaseException]


class ErrorPolicy:
    """Holds the rules and applies them.

    Knows nothing about any particular exception hierarchy: a rule supplies the
    callable, this class only decides which rule applies and what to pass it.
    """

    def __init__(
        self,
        metadata: MetaData,
        *,
        rules: Sequence[Rule] = (),
        entities: Mapping[str, str] | None = None,
        default: Callable[..., BaseException] | None = None,
        default_bindings: Mapping[str, Spec] | None = None,
        extractors: ExtractorRegistry | None = None,
        strict: bool = True,
    ) -> None:
        self._registry = ConstraintRegistry(metadata, entities)
        self._parser = ViolationParser(self._registry, extractors)
        self._strict = strict
        self._default = default
        self._default_bindings: dict[str, Spec] = dict(default_bindings or {})
        self._rules: list[Rule] = []
        for declared in rules:
            self.add(declared)

    def add(self, declared: Rule) -> ErrorPolicy:
        """Register a rule, after checking it can actually run."""
        check_rule(declared, self._registry.names, strict=self._strict)
        self._rules.append(declared)
        # sorted() is stable, so rules of equal specificity keep declaration order.
        self._rules.sort(key=lambda item: -item.specificity)
        return self

    def rule(
        self,
        *,
        constraint: str | None = None,
        kind: Kind | Sequence[Kind] | None = None,
        table: str | None = None,
        columns: Sequence[str] | None = None,
        where: Callable[[Violation], bool] | None = None,
    ) -> Callable[[_Factory], _Factory]:
        """Register a rule whose body needs real logic.

        Used as a decorator over a function taking the violation and returning
        the exception to raise.
        """

        def decorate(factory: _Factory) -> _Factory:
            self.add(
                rule(
                    to=factory,
                    constraint=constraint,
                    kind=kind,
                    table=table,
                    columns=columns,
                    where=where,
                ),
            )
            return factory

        return decorate

    def inspect(self, error: BaseException, backend: Backend) -> Violation | None:
        """Read the error without applying any rule."""
        return self._parser.parse(error, backend)

    def translate(self, error: BaseException, backend: Backend) -> BaseException | None:
        """Return the exception to raise instead, or None to leave the error alone."""
        violation = self._parser.parse(error, backend)
        if violation is None:
            return None
        for declared in self._rules:
            if declared.matches(violation):
                return declared.build(violation)
        return self._fallback(violation)

    def _fallback(self, violation: Violation) -> BaseException | None:
        # A connection failure reaches the same hook. Nothing unrecognised may
        # be swallowed by the default.
        if self._default is None or violation.kind is Kind.UNKNOWN:
            return None
        return self._default(
            **{name: resolve(spec, violation) for name, spec in self._default_bindings.items()},
        )

    @property
    def rules(self) -> tuple[Rule, ...]:
        """The registered rules, most specific first."""
        return tuple(self._rules)
