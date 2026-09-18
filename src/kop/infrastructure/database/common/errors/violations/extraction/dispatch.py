"""Selecting the extractor for a backend."""

from __future__ import annotations
from typing import TYPE_CHECKING

from kop.infrastructure.database.common.errors.violations.extraction.postgresql import (
    PostgresExtractor,
)


if TYPE_CHECKING:
    from collections.abc import Mapping

    from kop.infrastructure.database.common.errors.violations.extraction.protocols import (
        ErrorExtractor,
    )


class ExtractorRegistry:
    """Maps a backend name to the extractor that understands it.

    Adding a backend means registering an extractor, not editing a dispatch:
    the parser depends on this registry, never on a concrete extractor.
    """

    def __init__(self, extractors: Mapping[str, ErrorExtractor] | None = None) -> None:
        self._extractors: dict[str, ErrorExtractor] = dict(extractors or {})

    def register(self, backend: str, extractor: ErrorExtractor) -> None:
        """Teach the registry about a backend, replacing any previous entry."""
        self._extractors[backend] = extractor

    def get(self, backend: str) -> ErrorExtractor | None:
        """Return the extractor for `backend`, or None if it is unknown."""
        return self._extractors.get(backend)

    @property
    def backends(self) -> frozenset[str]:
        """Every backend this registry can read."""
        return frozenset(self._extractors)


def default_extractors() -> ExtractorRegistry:
    """PostgreSQL, the only backend this application runs on.

    The application relies on SKIP LOCKED, LISTEN/NOTIFY and ON CONFLICT, so no
    other backend is reachable; another one would be registered here.
    """
    return ExtractorRegistry({"postgresql": PostgresExtractor()})
