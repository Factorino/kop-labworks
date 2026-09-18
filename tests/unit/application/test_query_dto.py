from datetime import date
from enum import StrEnum

from pydantic import ValidationError
import pytest

from kop.application.dto.base import DTO
from kop.application.dto.query.cursor import CursorPage, CursorPagination
from kop.application.dto.query.filter import (
    Filter,
    FilterList,
    FilterNull,
    FilterRange,
    FilterScalar,
    FilterStr,
    OperatorRange,
)
from kop.application.dto.query.pagination import Page, PageMeta, Pagination
from kop.application.dto.query.sort import Sort, SortDirection, SortParam


class Field(StrEnum):
    TITLE = "title"
    SCORE = "score"


def test_base_dto_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError, match="cannot be instantiated directly"):
        DTO()


def test_dto_is_frozen_and_rejects_unknown_fields() -> None:
    pagination = Pagination()

    with pytest.raises(ValidationError):
        pagination.page = 2
    with pytest.raises(ValidationError):
        Pagination(unknown=1)  # type: ignore[call-arg]


@pytest.mark.parametrize(("page", "page_size", "offset"), [(1, 25, 0), (3, 10, 20)])
def test_pagination_offset_and_limit(page: int, page_size: int, offset: int) -> None:
    pagination = Pagination(page=page, page_size=page_size)

    assert pagination.offset == offset
    assert pagination.limit == page_size


@pytest.mark.parametrize("page_size", [0, 101])
def test_page_size_is_bounded(page_size: int) -> None:
    with pytest.raises(ValidationError):
        Pagination(page_size=page_size)


def test_page_meta_derives_navigation() -> None:
    meta = PageMeta(page=2, page_size=10, total=25)

    assert meta.total_pages == 3
    assert meta.has_next
    assert meta.has_prev
    assert not PageMeta(page=1, page_size=10, total=0).has_next


def test_page_rejects_more_rows_than_its_size() -> None:
    with pytest.raises(ValidationError, match="more than the page size"):
        Page(data=(1, 2, 3), meta=PageMeta(page=1, page_size=2, total=3))


def test_sort_rejects_repeated_fields() -> None:
    param = SortParam(field=Field.TITLE)

    with pytest.raises(ValidationError, match="only once"):
        Sort(params=(param, SortParam(field=Field.TITLE, direction=SortDirection.DESC)))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"field": "score", "operator": "ge", "value": 3}, FilterScalar),
        ({"field": "title", "operator": "ilike", "value": "%a%"}, FilterStr),
        ({"field": "score", "operator": "in", "value": [1, 2]}, FilterList),
        ({"field": "title", "operator": "is_null"}, FilterNull),
        ({"field": "score", "operator": "between", "value": [1, 5]}, FilterRange),
    ],
)
def test_filter_operator_selects_the_parameter_type(
    raw: dict[str, object], expected: type
) -> None:
    parsed = Filter[Field].model_validate({"params": [raw]})

    assert isinstance(parsed.params[0], expected)


def test_filter_list_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        Filter[Field].model_validate(
            {"params": [{"field": "score", "operator": "in", "value": []}]}
        )


def test_filter_range_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError, match="must not exceed"):
        FilterRange[Field](field=Field.SCORE, operator=OperatorRange.BETWEEN, value=(5, 1))


def test_filter_range_rejects_mixed_types() -> None:
    with pytest.raises(ValidationError, match="same type"):
        FilterRange[Field](
            field=Field.SCORE, operator=OperatorRange.BETWEEN, value=(date(2026, 1, 1), 1)
        )


def test_cursor_page_has_next_follows_cursor() -> None:
    assert CursorPage[int](data=(1,), next_cursor="abc").has_next
    assert not CursorPage[int](data=(1,)).has_next
    assert CursorPagination().cursor is None
