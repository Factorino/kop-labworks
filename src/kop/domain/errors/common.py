from typing import ClassVar

from kop.domain.errors.base import DomainError, error
from kop.domain.errors.status_code import StatusCode


@error
class ValidationError(DomainError, ValueError, TypeError):
    code: ClassVar[str] = StatusCode.VALIDATION_ERROR
    msg: str = "Field '{field}' validation error: {reason}"

    field: str
    reason: str = "invalid value"
