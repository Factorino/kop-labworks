"""Reading a driver exception into a backend-neutral `RawError`."""

from kop.infrastructure.database.common.errors.violations.extraction.detail import Detail
from kop.infrastructure.database.common.errors.violations.extraction.dispatch import (
    ExtractorRegistry,
    default_extractors,
)
from kop.infrastructure.database.common.errors.violations.extraction.protocols import (
    ErrorExtractor,
    Transport,
)
from kop.infrastructure.database.common.errors.violations.extraction.raw import RawError
from kop.infrastructure.database.common.errors.violations.extraction.transport import (
    DirectTransport,
    transport_for,
)


__all__ = [
    "Detail",
    "DirectTransport",
    "ErrorExtractor",
    "ExtractorRegistry",
    "RawError",
    "Transport",
    "default_extractors",
    "transport_for",
]
