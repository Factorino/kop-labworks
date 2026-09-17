from typing import Any, ClassVar

from kop.application.errors.base import ApplicationError
from kop.application.errors.status_code import StatusCode
from kop.domain.errors.base import AppError, error


@error
class NotFoundError(ApplicationError):
    code: ClassVar[str] = StatusCode.NOT_FOUND_ERROR
    msg: str = "{entity} with {field}={value} not found"

    entity: str
    field: str = "id"
    value: Any


@error
class AlreadyExistsError(ApplicationError):
    code: ClassVar[str] = StatusCode.ALREADY_EXISTS_ERROR
    msg: str = "{entity} already exists"

    entity: str

    # Written by hand so that the conflicting fields arrive as plain keywords:
    # a conflict may involve any number of them, and a dataclass keeps an
    # __init__ declared in the body. Subclasses declare their fields instead
    # and get the generated one, along with a message naming them.
    def __init__(self, *, entity: str, **criteria: Any) -> None:
        # `msg` may be overridden at the raise site; the rest is machinery.
        if clashing := set(criteria) & (self._RESERVED_ATTRS - {"msg"}):
            raise TypeError(f"Criteria {sorted(clashing)} are reserved attributes of the error")
        self.entity = entity
        self.__dict__.update(criteria)
        self.__post_init__()


@error
class ConflictError(ApplicationError):
    code: ClassVar[str] = StatusCode.CONFLICT_ERROR
    msg: str = "{entity} {reason}"

    entity: str
    reason: str = "conflicts with existing data"


@error
class InternalError(ApplicationError):
    code: ClassVar[str] = StatusCode.INTERNAL_ERROR
    msg: str = "An internal error occurred"


@error
class UnexpectedError(AppError):
    code: ClassVar[str] = StatusCode.UNEXPECTED_ERROR
    msg: str = "An unexpected error occurred"
