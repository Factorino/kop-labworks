from enum import StrEnum, auto


class StatusCode(StrEnum):
    APPLICATION_ERROR = auto()
    INTERNAL_ERROR = auto()
    UNEXPECTED_ERROR = auto()

    NOT_FOUND_ERROR = auto()
    ALREADY_EXISTS_ERROR = auto()
    CONFLICT_ERROR = auto()

    MISSING_TRACE_ID_ERROR = auto()
