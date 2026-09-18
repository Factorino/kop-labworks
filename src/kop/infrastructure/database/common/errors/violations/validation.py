"""Checks that run when a policy is assembled, not when a request fails."""

from __future__ import annotations
import dataclasses
from typing import TYPE_CHECKING
import warnings

from kop.infrastructure.database.common.errors.violations.binding import Bind
from kop.infrastructure.database.common.errors.violations.violation import (
    VIOLATION_ATTRIBUTES,
)


if TYPE_CHECKING:
    from collections.abc import Collection

    from kop.infrastructure.database.common.errors.violations.rules import Rule


class PolicyError(Exception):
    """A rule that cannot work. Raised while wiring the policy up."""


class UnknownConstraintWarning(UserWarning):
    """A rule names a constraint absent from `MetaData`."""


def check_rule(rule: Rule, known_constraints: Collection[str], *, strict: bool) -> None:
    """Reject a rule that would fail later, when a real error is being handled."""
    _check_bindings_against_factory(rule)
    _check_binding_paths(rule)
    _check_constraint_exists(rule, known_constraints, strict=strict)


def _check_bindings_against_factory(rule: Rule) -> None:
    factory = rule.factory
    if not isinstance(factory, type) or not dataclasses.is_dataclass(factory):
        return
    reserved = frozenset(getattr(factory, "_RESERVED_ATTRS", frozenset()))
    accepted = {f.name for f in dataclasses.fields(factory)}
    unknown = set(rule.bindings) - accepted
    if unknown:
        raise PolicyError(
            f"rule -> {factory.__name__} binds {sorted(unknown)}, which are not its "
            f"fields; it accepts {sorted(accepted - reserved)}",
        )
    missing = _required_fields(factory, reserved) - set(rule.bindings)
    if missing:
        raise PolicyError(
            f"rule -> {factory.__name__} leaves required fields {sorted(missing)} unbound",
        )


def _required_fields(factory: type, reserved: frozenset[str]) -> set[str]:
    return {
        f.name
        for f in dataclasses.fields(factory)
        if f.default is dataclasses.MISSING
        and f.default_factory is dataclasses.MISSING
        and f.name not in reserved
    }


def _check_binding_paths(rule: Rule) -> None:
    for name, spec in rule.bindings.items():
        if not isinstance(spec, Bind):
            continue
        root = spec.root
        if root is not None and root not in VIOLATION_ATTRIBUTES:
            raise PolicyError(
                f"rule -> {_factory_name(rule)}: binding {name}={spec.path} reads "
                f"V.{root}, which a violation does not have",
            )


def _check_constraint_exists(
    rule: Rule,
    known_constraints: Collection[str],
    *,
    strict: bool,
) -> None:
    if not rule.constraint:
        return
    if rule.constraint.lower() in known_constraints:
        return
    message = (
        f"rule targets constraint {rule.constraint!r}, which is not in MetaData; "
        f"it may be a typo, a rename, or a constraint created outside MetaData"
    )
    if strict:
        raise PolicyError(message)
    warnings.warn(message, UnknownConstraintWarning, stacklevel=4)


def _factory_name(rule: Rule) -> str:
    return getattr(rule.factory, "__name__", repr(rule.factory))
