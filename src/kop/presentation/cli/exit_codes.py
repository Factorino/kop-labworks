"""What the shell learns from a command that did not work.

The same idea as the status codes in `presentation/api/handlers/error.py`, and
with the same blind spot: an infrastructure error cannot be named here, because
presentation may not import that layer. It arrives as an `AppError` and becomes
FAILURE, just as it becomes 500 over HTTP.
"""

from collections.abc import Mapping
from enum import IntEnum
from types import MappingProxyType
from typing import Final

from kop.application.errors.common import (
    AlreadyExistsError,
    ConflictError,
    NotFoundError,
)
from kop.domain.errors.base import AppError
from kop.domain.errors.common import ValidationError


class ExitCode(IntEnum):
    OK = 0
    USAGE = 1
    CONFIG = 2
    NOT_FOUND = 3
    CONFLICT = 4
    FAILURE = 5
    UNEXPECTED = 70
    # 128 + SIGINT, which is what a shell reports for a command killed by it.
    INTERRUPTED = 130


# Looked up along the MRO, so a subclass needs no entry of its own.
_EXIT_CODES: Final[Mapping[type[AppError], ExitCode]] = MappingProxyType(
    {
        ValidationError: ExitCode.USAGE,
        NotFoundError: ExitCode.NOT_FOUND,
        AlreadyExistsError: ExitCode.CONFLICT,
        ConflictError: ExitCode.CONFLICT,
        AppError: ExitCode.FAILURE,
    },
)


def exit_code_for(error: AppError) -> ExitCode:
    for cls in type(error).mro():
        if cls in _EXIT_CODES:
            return _EXIT_CODES[cls]
    return ExitCode.FAILURE
