"""Map database constraint violations onto your own exceptions.

Reads the error every SQLAlchemy driver raises, normalises it into a
`Violation`, and applies declarative rules that say which exception to raise
instead. The rules name your exceptions; this package never imports them.
"""

from kop.infrastructure.database.common.errors.violations.binding import Bind, Spec, V
from kop.infrastructure.database.common.errors.violations.integration import (
    backend_of,
    entities_from,
    install,
)
from kop.infrastructure.database.common.errors.violations.kinds import RETRYABLE, Kind
from kop.infrastructure.database.common.errors.violations.parser import (
    Backend,
    ViolationParser,
)
from kop.infrastructure.database.common.errors.violations.policy import ErrorPolicy
from kop.infrastructure.database.common.errors.violations.registry import (
    ConstraintInfo,
    ConstraintRegistry,
    ForeignKeyInfo,
)
from kop.infrastructure.database.common.errors.violations.rules import Rule, rule
from kop.infrastructure.database.common.errors.violations.validation import (
    PolicyError,
    UnknownConstraintWarning,
)
from kop.infrastructure.database.common.errors.violations.violation import (
    Confidence,
    Violation,
)


__all__ = [
    "RETRYABLE",
    "Backend",
    "Bind",
    "Confidence",
    "ConstraintInfo",
    "ConstraintRegistry",
    "ErrorPolicy",
    "ForeignKeyInfo",
    "Kind",
    "PolicyError",
    "Rule",
    "Spec",
    "UnknownConstraintWarning",
    "V",
    "Violation",
    "ViolationParser",
    "backend_of",
    "entities_from",
    "install",
    "rule",
]
