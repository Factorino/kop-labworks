"""Encoding the position a keyset page stopped at.

A cursor is base64url-encoded JSON: the sort it was cut from and the key of the
last row on the page. It is not signed. It can only position a query inside a
result set the reader has already restricted — a forged one lands on rows the
same caller could reach by paging — so a signature would protect nothing, while
every decoded value is still checked as strictly as a filter value would be.
"""

import base64
from typing import Any, Final

import orjson

from kop.application.dto.query.cursor import KeysetSort
from kop.domain.errors.common import ValidationError


__all__: list[str] = ["decode_cursor", "encode_cursor"]


# Bump when the payload shape changes.
_VERSION: Final[int] = 1
_FIELD_NAME: Final[str] = "cursor"


def encode_cursor(sort: KeysetSort[Any], values: tuple[Any, ...]) -> str:
    payload: dict[str, Any] = {
        "v": _VERSION,
        "f": sort.field.value,
        "d": sort.direction.value,
        "k": list(values),
    }
    raw: bytes = orjson.dumps(payload)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def decode_cursor(cursor: str, sort: KeysetSort[Any], size: int) -> tuple[Any, ...]:
    """Return the raw key values, still as JSON scalars.

    Converting them to column types is the reader's job: it is the only place
    that knows the columns, and it already does the same for filter values.
    """
    payload: Any = _load(cursor)

    if not isinstance(payload, dict) or payload.get("v") != _VERSION:
        raise ValidationError(field=_FIELD_NAME, reason="is malformed or out of date")

    if payload.get("f") != sort.field.value or payload.get("d") != sort.direction.value:
        raise ValidationError(
            field=_FIELD_NAME,
            reason="was issued for a different sort order",
        )

    key: Any = payload.get("k")
    if not isinstance(key, list) or len(key) != size:
        raise ValidationError(field=_FIELD_NAME, reason="is malformed")

    return tuple(key)


def _load(cursor: str) -> Any:
    padded: str = cursor + "=" * (-len(cursor) % 4)
    try:
        return orjson.loads(base64.urlsafe_b64decode(padded.encode()))
    except ValueError as error:
        raise ValidationError(field=_FIELD_NAME, reason="is malformed") from error
