"""Which of our errors each constraint violation becomes.

The only module that knows both halves: the constraint names come from the
naming convention on `BaseORM.metadata`, the exceptions from the domain and
application layers. `violations/` knows neither and never imports them.

Rules are weighed by how narrow they are, not by the order they are written in,
so a rule naming a constraint always beats one that only names a kind. Where
two rules are equally narrow, the earlier one wins — which is why each pair
below puts the rule needing more from the backend first, with a plainer one
under it for the backends that report less.

Every mistake in a rule — a field an exception does not take, a constraint no
longer in the schema — is raised while the policy is being built, at startup,
rather than when a request fails.

Related files:
  - violations/       the backend-neutral machinery the rules are declared to
  - handler.py        what happens to errors the policy leaves alone
  - main/di/providers/database.py  installs the policy on the engine
"""

from typing import Final

from kop.application.errors.common import (
    AlreadyExistsError,
    ConflictError,
    NotFoundError,
)
from kop.domain.errors.common import ValidationError
from kop.infrastructure.database.common.errors.violations import (
    RETRYABLE,
    ErrorPolicy,
    Kind,
    V,
    entities_from,
    rule,
)
import kop.infrastructure.database.models  # pyright: ignore[reportUnusedImport] # noqa: F401  (fills the metadata)
from kop.infrastructure.database.models.base import BaseORM
from kop.infrastructure.errors.base import InfrastructureError


def build_policy(*, strict: bool = True) -> ErrorPolicy:
    """Assemble the policy. Any mistake in a rule surfaces here."""
    return ErrorPolicy(
        metadata=BaseORM.metadata,
        entities=entities_from(BaseORM),
        strict=strict,
        rules=[
            # Rules for specific constraints, with messages worded for them, go
            # first: they outweigh the generic rules below regardless of order.
            #
            # A factory rather than bindings here: the conflicting columns are
            # known only per violation, and the error takes them as keywords.
            rule(
                kind=(Kind.UNIQUE, Kind.PRIMARY_KEY),
                to=lambda violation: AlreadyExistsError(
                    entity=violation.entity or "Record",
                    **(violation.values or dict.fromkeys(violation.columns)),
                ),
            ),
            rule(
                kind=Kind.FOREIGN_KEY,
                where=lambda violation: violation.referred_entity is not None,
                to=NotFoundError,
                entity=V.referred_entity,
                field=V.referred_column.or_("id"),
                value=V.value.or_("unknown"),
            ),
            rule(
                kind=Kind.FOREIGN_KEY,
                to=ConflictError,
                entity=V.entity.or_("Record"),
                reason="refers to a record that does not exist",
            ),
            # The row that cannot be removed belongs to the referred table.
            rule(
                kind=Kind.FOREIGN_KEY_CHILD,
                to=ConflictError,
                entity=lambda violation: violation.referred_entity or violation.entity or "Record",
                reason="is still referenced by other records",
            ),
            rule(
                kind=Kind.NOT_NULL,
                to=ValidationError,
                field=V.column.or_("unknown"),
                reason="must not be null",
            ),
            rule(
                kind=Kind.CHECK,
                to=ValidationError,
                field=V.column.or_("unknown"),
                reason=V.resolved.map(lambda name: f"violates {name}").or_(
                    "violates a database constraint",
                ),
            ),
            rule(
                kind=Kind.VALUE_TOO_LONG,
                to=ValidationError,
                field=V.column.or_("unknown"),
                reason="is too long",
            ),
            rule(
                kind=Kind.INVALID_VALUE,
                to=ValidationError,
                field=V.column.or_("unknown"),
                reason="has the wrong type",
            ),
            rule(kind=tuple(RETRYABLE), to=InfrastructureError),
        ],
        # Unrecognised errors (lost connection, syntax) are left to handler.py.
        default=ConflictError,
        default_bindings={
            "entity": V.entity.or_("Record"),
            "reason": "could not be stored",
        },
    )


POLICY: Final[ErrorPolicy] = build_policy()
"""The policy the engine is wired to. Built at import, so it fails at startup."""
