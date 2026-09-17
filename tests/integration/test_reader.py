from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, ClassVar, override
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from kop.application.dto.base import DTO
from kop.application.dto.query.cursor import CursorPage, CursorPagination, KeysetSort
from kop.application.dto.query.filter import Filter, FilterScalar, OperatorScalar
from kop.application.dto.query.pagination import Page, Pagination
from kop.application.dto.query.sort import Sort, SortDirection, SortParam
from kop.domain.errors.common import ValidationError
from kop.infrastructure.common.id_generator import UUIDv7Generator
from kop.infrastructure.database.readers.base import SABaseReader
from tests.integration.models import ItemORM, ParentORM


START = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


class ItemField(StrEnum):
    ID = "id"
    TITLE = "title"
    SCORE = "score"
    CREATED_AT = "created_at"


class ItemView(DTO):
    id: UUID
    title: str
    score: int


class ItemReader(SABaseReader[ItemView, ItemORM]):
    _model = ItemORM
    _filter_map: ClassVar[Mapping[StrEnum, InstrumentedAttribute[Any]]] = {
        ItemField.ID: ItemORM.id,
        ItemField.TITLE: ItemORM.title,
        ItemField.SCORE: ItemORM.score,
        ItemField.CREATED_AT: ItemORM.created_at,
    }
    _sort_map: ClassVar[Mapping[StrEnum, InstrumentedAttribute[Any]]] = {
        ItemField.TITLE: ItemORM.title,
        ItemField.SCORE: ItemORM.score,
    }
    _tie_break: ClassVar[tuple[InstrumentedAttribute[Any], ...]] = (ItemORM.id,)
    _keyset_map: ClassVar[Mapping[StrEnum, InstrumentedAttribute[Any]]] = {
        ItemField.CREATED_AT: ItemORM.created_at,
    }

    @override
    def _to_view(self, orm_object: ItemORM) -> ItemView:
        return ItemView(id=orm_object.id, title=orm_object.title, score=orm_object.score)

    async def search(self, **kwargs: Any) -> Page[ItemView]:
        return await self._search(**kwargs)

    async def search_keyset(self, **kwargs: Any) -> CursorPage[ItemView]:
        return await self._search_keyset(**kwargs)


@pytest_asyncio.fixture
async def items(session: AsyncSession) -> list[ItemORM]:
    """Seven items; two pairs share a creation time to exercise the tie-break."""
    ids = UUIDv7Generator[UUID]()
    parent = ParentORM(id=uuid4(), name="parent")
    offsets = [0, 1, 1, 2, 3, 3, 4]
    rows = [
        ItemORM(
            id=ids.generate(),
            parent_id=parent.id,
            title=f"item-{index}",
            score=index,
            created_at=START + timedelta(minutes=offset),
        )
        for index, offset in enumerate(offsets)
    ]
    # No relationship() on the test models, so the unit of work cannot order
    # the inserts itself: the parent goes first.
    session.add(parent)
    await session.flush()
    session.add_all(rows)
    await session.commit()
    return rows


@pytest.mark.asyncio
async def test_offset_search_pages_and_counts(session: AsyncSession, items: list[ItemORM]) -> None:
    page = await ItemReader(session).search(pagination=Pagination(page=2, page_size=3))

    # Without a sort only the tie-break orders the rows. UUIDv7 ids created
    # within one millisecond are not ordered among themselves, so the expected
    # page is derived from the ids rather than from the insertion order.
    by_id = sorted(items, key=lambda item: item.id)
    assert page.meta.total == 7
    assert page.meta.has_next
    assert [view.id for view in page.data] == [item.id for item in by_id[3:6]]


@pytest.mark.asyncio
async def test_filter_and_sort_are_applied(session: AsyncSession, items: list[ItemORM]) -> None:
    page = await ItemReader(session).search(
        filter=Filter[ItemField](
            params=(FilterScalar(field=ItemField.SCORE, operator=OperatorScalar.GE, value=4),),
        ),
        sort=Sort[ItemField](
            params=(SortParam(field=ItemField.SCORE, direction=SortDirection.DESC),),
        ),
    )

    assert [view.score for view in page.data] == [6, 5, 4]
    assert page.meta.total == 3


@pytest.mark.asyncio
async def test_string_filter_values_are_coerced_to_column_types(
    session: AsyncSession, items: list[ItemORM]
) -> None:
    reader = ItemReader(session)

    by_id = await reader.search(
        filter=Filter[ItemField](
            params=(
                FilterScalar(
                    field=ItemField.ID, operator=OperatorScalar.EQ, value=str(items[2].id)
                ),
            ),
        ),
    )
    since = await reader.search(
        filter=Filter[ItemField](
            params=(
                FilterScalar(
                    field=ItemField.CREATED_AT,
                    operator=OperatorScalar.GE,
                    value=(START + timedelta(minutes=3)).isoformat(),
                ),
            ),
        ),
    )

    assert [view.title for view in by_id.data] == ["item-2"]
    assert since.meta.total == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("value", "reason"),
    [("not-a-uuid", "not a valid UUID"), ("2026-09-01T12:00:00", "UTC offset")],
)
async def test_invalid_filter_value_is_a_validation_error(
    session: AsyncSession, value: str, reason: str
) -> None:
    field = ItemField.ID if reason.endswith("UUID") else ItemField.CREATED_AT

    with pytest.raises(ValidationError, match=reason):
        await ItemReader(session).search(
            filter=Filter[ItemField](
                params=(FilterScalar(field=field, operator=OperatorScalar.EQ, value=value),),
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", [SortDirection.DESC, SortDirection.ASC])
async def test_keyset_walks_every_row_exactly_once(
    session: AsyncSession, items: list[ItemORM], direction: SortDirection
) -> None:
    reader = ItemReader(session)
    sort = KeysetSort[ItemField](field=ItemField.CREATED_AT, direction=direction)

    seen: list[UUID] = []
    cursor: str | None = None
    pages = 0
    while True:
        page = await reader.search_keyset(
            sort=sort,
            pagination=CursorPagination(cursor=cursor, limit=3),
        )
        seen.extend(view.id for view in page.data)
        pages += 1
        if not page.has_next:
            break
        cursor = page.next_cursor

    expected = sorted(items, key=lambda item: (item.created_at, item.id))
    if direction is SortDirection.DESC:
        expected.reverse()
    assert seen == [item.id for item in expected]
    assert pages == 3


@pytest.mark.asyncio
async def test_keyset_cursor_cannot_be_reused_for_another_order(
    session: AsyncSession, items: list[ItemORM]
) -> None:
    reader = ItemReader(session)
    first = await reader.search_keyset(
        sort=KeysetSort[ItemField](field=ItemField.CREATED_AT),
        pagination=CursorPagination(limit=2),
    )

    with pytest.raises(ValidationError, match="different sort order"):
        await reader.search_keyset(
            sort=KeysetSort[ItemField](field=ItemField.CREATED_AT, direction=SortDirection.ASC),
            pagination=CursorPagination(cursor=first.next_cursor, limit=2),
        )
