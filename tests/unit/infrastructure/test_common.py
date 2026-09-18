from datetime import UTC, datetime, timedelta
from uuid import UUID

from kop.infrastructure.common.clock import SystemClock
from kop.infrastructure.common.id_generator import UUIDv7Generator


def test_system_clock_is_timezone_aware_utc() -> None:
    now = SystemClock().now()

    assert now.tzinfo is UTC
    assert abs(datetime.now(tz=UTC) - now) < timedelta(seconds=5)


def test_uuid7_carries_version_variant_and_time_order() -> None:
    generator = UUIDv7Generator[UUID]()

    ids = [generator.generate() for _ in range(50)]

    assert all(value.version == 7 for value in ids)
    assert all(value.variant == "specified in RFC 4122" for value in ids)
    assert len(set(ids)) == len(ids)
    # The leading 48 bits are milliseconds, so ids never go back in time.
    timestamps = [value.int >> 80 for value in ids]
    assert timestamps == sorted(timestamps)
