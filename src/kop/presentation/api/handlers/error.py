from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from kop.application.errors.common import (
    AlreadyExistsError,
    ConflictError,
    InternalError,
    NotFoundError,
    UnexpectedError,
)
from kop.application.errors.tracing import MissingTraceIdError
from kop.domain.errors.base import AppError, DomainError
from kop.domain.errors.common import ValidationError


_logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(__name__)


# Looked up along the MRO, so subclasses need no entry. Infrastructure errors
# fall through to 500.
_ERROR_STATUS_CODE: Final[Mapping[type[AppError], int]] = MappingProxyType(
    {
        ValidationError: status.HTTP_400_BAD_REQUEST,
        DomainError: status.HTTP_400_BAD_REQUEST,
        MissingTraceIdError: status.HTTP_400_BAD_REQUEST,
        NotFoundError: status.HTTP_404_NOT_FOUND,
        AlreadyExistsError: status.HTTP_409_CONFLICT,
        ConflictError: status.HTTP_409_CONFLICT,
        InternalError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        UnexpectedError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AppError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    },
)


class ErrorResponse(BaseModel):
    status_code: int
    code: str
    message: str
    detail: dict[str, Any] = {}


async def error_handler(_request: Request, exception: Exception) -> JSONResponse:
    error: AppError = exception if isinstance(exception, AppError) else UnexpectedError()
    error_status_code: int = _get_error_status_code(error)

    error_response: dict[str, Any] = ErrorResponse(
        status_code=error_status_code,
        code=error.code,
        message=str(error),
        detail=error.context,
    ).model_dump(mode="json")

    await _log_error(exception, error_status_code, error_response)

    return JSONResponse(status_code=error_status_code, content=error_response)


def _get_error_status_code(exception: AppError) -> int:
    for cls in type(exception).mro():
        if cls in _ERROR_STATUS_CODE:
            return _ERROR_STATUS_CODE[cls]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


# The raised exception, not the substitute: only it carries the traceback.
async def _log_error(
    exception: Exception,
    error_status_code: int,
    error_response: dict[str, Any],
) -> None:
    if error_status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        await _logger.aerror("request.failed", exc_info=exception, **error_response)
        return

    await _logger.awarning("request.failed", **error_response)
