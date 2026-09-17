import base64
from enum import StrEnum

import pytest

from kop.application.dto.query.cursor import KeysetSort
from kop.application.dto.query.sort import SortDirection
from kop.domain.errors.common import ValidationError
from kop.infrastructure.database.readers.cursor import decode_cursor, encode_cursor


class Field(StrEnum):
    CREATED_AT = "created_at"
    SCORE = "score"


SORT = KeysetSort[Field](field=Field.CREATED_AT, direction=SortDirection.DESC)


def _raw(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()


def test_cursor_round_trips_the_key() -> None:
    key = ("2026-09-01T10:00:00+00:00", "0199a0b0-0000-7000-8000-000000000001")

    cursor = encode_cursor(SORT, key)

    assert "=" not in cursor
    assert decode_cursor(cursor, SORT, size=2) == key


@pytest.mark.parametrize(
    "other",
    [
        KeysetSort[Field](field=Field.SCORE, direction=SortDirection.DESC),
        KeysetSort[Field](field=Field.CREATED_AT, direction=SortDirection.ASC),
    ],
)
def test_cursor_is_bound_to_its_sort(other: KeysetSort[Field]) -> None:
    cursor = encode_cursor(SORT, ("a", "b"))

    with pytest.raises(ValidationError, match="different sort order"):
        decode_cursor(cursor, other, size=2)


@pytest.mark.parametrize(
    "cursor",
    [
        "!!not-base64!!",
        _raw(b"not json"),
        _raw(b"[1, 2]"),
        _raw(b'{"v": 99, "f": "created_at", "d": "desc", "k": ["a", "b"]}'),
    ],
)
def test_malformed_or_outdated_cursor_is_rejected(cursor: str) -> None:
    with pytest.raises(ValidationError, match="cursor"):
        decode_cursor(cursor, SORT, size=2)


def test_cursor_with_wrong_key_size_is_rejected() -> None:
    cursor = encode_cursor(SORT, ("a",))

    with pytest.raises(ValidationError, match="malformed"):
        decode_cursor(cursor, SORT, size=2)
