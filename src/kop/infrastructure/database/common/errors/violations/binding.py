"""Lazy reads out of a `Violation`, usable anywhere a literal is accepted."""

from __future__ import annotations
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal, Self, override


if TYPE_CHECKING:
    from collections.abc import Callable

    from kop.infrastructure.database.common.errors.violations.violation import Violation


@dataclass(frozen=True, slots=True)
class Step:
    """One hop of a binding path: an attribute or an item lookup."""

    how: Literal["attr", "item"]
    key: Any

    @override
    def __str__(self) -> str:
        return f".{self.key}" if self.how == "attr" else f"[{self.key!r}]"


@dataclass(frozen=True, slots=True)
class Bind:
    """A deferred read from a `Violation`.

    Built by attribute and item access on the `V` singleton, so a rule can say
    `entity=V.entity` where the exception constructor expects a plain value.
    Every operation returns a new instance; nothing is mutated.
    """

    steps: tuple[Step, ...] = ()
    fallback: Any = None
    transform: Callable[[Any], Any] | None = None

    def __getattr__(self, name: str) -> Self:
        # Guard against dunder lookups made by copy, pickle and inspect, which
        # would otherwise be answered with a Bind and confuse them badly.
        if name.startswith("_"):
            raise AttributeError(name)
        return replace(self, steps=(*self.steps, Step("attr", name)))

    def __getitem__(self, key: Any) -> Self:
        return replace(self, steps=(*self.steps, Step("item", key)))

    def or_(self, fallback: Any) -> Self:
        """Return `fallback` when the path yields `None` or cannot be walked."""
        return replace(self, fallback=fallback)

    def map(self, transform: Callable[[Any], Any]) -> Self:
        """Apply `transform` to the value, unless the fallback was used."""
        return replace(self, transform=transform)

    def read(self, violation: Violation) -> Any:
        """Walk the path against `violation`."""
        current: Any = violation
        for step in self.steps:
            try:
                current = getattr(current, step.key) if step.how == "attr" else current[step.key]
            except (AttributeError, KeyError, IndexError, TypeError):
                return self.fallback
            if current is None:
                return self.fallback
        if self.transform is not None:
            return self.transform(current)
        return current

    @property
    def path(self) -> str:
        """The binding rendered back as source, for error messages."""
        return "V" + "".join(str(step) for step in self.steps)

    @property
    def root(self) -> str | None:
        """The first attribute the path reads, if it starts with one."""
        if self.steps and self.steps[0].how == "attr":
            return str(self.steps[0].key)
        return None


V: Bind = Bind()
"""Entry point for bindings: `V.entity`, `V.values["email"]`, `V.column.or_("id")`."""


type Spec = Bind | Callable[[Violation], Any] | Any
"""What a rule accepts for a constructor argument: a binding, a callable or a literal."""


def resolve(spec: Spec, violation: Violation) -> Any:
    """Turn one argument specification into the value to pass."""
    if isinstance(spec, Bind):
        return spec.read(violation)
    if callable(spec) and not isinstance(spec, type):
        return spec(violation)
    return spec
