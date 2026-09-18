"""The contracts the extraction layer is built from.

Two independent axes, as the research established: how a driver exposes its
error (the transport) and what the resulting code means (the backend).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    from kop.infrastructure.database.common.errors.violations.extraction.raw import RawError


@runtime_checkable
class Transport(Protocol):
    """Normalises the shape of a driver exception before a backend reads it."""

    def unwrap(self, error: BaseException) -> BaseException:
        """Return the exception a backend extractor should read."""
        ...


@runtime_checkable
class ErrorExtractor(Protocol):
    """Reads one backend's errors. One implementation per backend."""

    def extract(self, error: BaseException) -> RawError:
        """Establish everything this backend reports about the error."""
        ...
