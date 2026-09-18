from typing import ClassVar

from kop.domain.errors.base import AppError, error
from kop.infrastructure.errors.status_code import StatusCode


@error
class InfrastructureError(AppError):
    code: ClassVar[str] = StatusCode.INFRASTRUCTURE_ERROR
    msg: str = "An infrastructure error occurred"
