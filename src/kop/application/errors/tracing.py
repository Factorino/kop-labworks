from typing import ClassVar

from kop.application.errors.base import ApplicationError
from kop.application.errors.status_code import StatusCode
from kop.domain.errors.base import error


@error
class MissingTraceIdError(ApplicationError):
    code: ClassVar[str] = StatusCode.MISSING_TRACE_ID_ERROR
    msg: str = "Required trace id header '{header}' is missing"

    header: str
