"""The vocabulary the library normalises every backend down to."""

from __future__ import annotations
from enum import StrEnum, auto


class Kind(StrEnum):
    """What the database refused to do.

    One member per situation a caller would plausibly react to differently.
    Backends that cannot tell two of these apart are corrected by the
    constraint registry where the schema makes the answer unambiguous.
    """

    UNIQUE = auto()
    PRIMARY_KEY = auto()
    FOREIGN_KEY = auto()
    """A row referenced a parent that does not exist."""
    FOREIGN_KEY_CHILD = auto()
    """A row is still referenced by children and cannot be removed."""
    NOT_NULL = auto()
    CHECK = auto()
    EXCLUSION = auto()
    VALUE_TOO_LONG = auto()
    INVALID_VALUE = auto()
    DEADLOCK = auto()
    SERIALIZATION = auto()
    LOCK_TIMEOUT = auto()
    UNKNOWN = auto()
    """Nothing was recognised. Never mapped unless a rule asks for it by name."""


RETRYABLE: frozenset[Kind] = frozenset({Kind.DEADLOCK, Kind.SERIALIZATION, Kind.LOCK_TIMEOUT})
"""Kinds where the same statement may succeed if simply run again."""
