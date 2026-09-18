from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kop.application.errors.common import AlreadyExistsError, ConflictError, NotFoundError
from kop.domain.errors.common import ValidationError
from kop.infrastructure.database.common.probe import SADatabaseProbe
from kop.infrastructure.database.common.transaction_manager import SATransactionManager
from tests.integration.models import ItemORM, ParentORM


NOW = datetime(2026, 9, 1, tzinfo=UTC)


def _item(parent_id: UUID, title: str = "title", score: int = 1) -> ItemORM:
    return ItemORM(id=uuid4(), parent_id=parent_id, title=title, score=score, created_at=NOW)


@pytest_asyncio.fixture
async def parent(session: AsyncSession) -> ParentORM:
    parent = ParentORM(id=uuid4(), name="parent")
    session.add(parent)
    await session.commit()
    return parent


@pytest.mark.asyncio
async def test_unique_violation_becomes_already_exists(
    session: AsyncSession, parent: ParentORM
) -> None:
    manager = SATransactionManager(session)
    session.add(_item(parent.id, title="same"))
    await manager.commit()

    session.add(_item(parent.id, title="same"))
    with pytest.raises(AlreadyExistsError) as raised:
        await manager.commit()

    assert raised.value.entity == "Item"
    # The conflicting column arrives as a plain keyword, with the value the
    # server reported alongside it.
    assert raised.value.context == {"entity": "Item", "title": "same"}


@pytest.mark.asyncio
async def test_missing_parent_becomes_not_found(session: AsyncSession, parent: ParentORM) -> None:
    missing = uuid4()
    session.add(_item(missing))

    with pytest.raises(NotFoundError) as raised:
        await SATransactionManager(session).commit()

    assert (raised.value.entity, raised.value.field) == ("Parent", "id")
    assert str(missing) in str(raised.value.value)


@pytest.mark.asyncio
async def test_removing_a_referenced_row_becomes_conflict(
    session: AsyncSession, parent: ParentORM
) -> None:
    session.add(_item(parent.id))
    await session.commit()

    with pytest.raises(ConflictError, match="still referenced"):
        await session.execute(delete(ParentORM).where(ParentORM.id == parent.id))


@pytest.mark.asyncio
async def test_check_violation_becomes_validation_error(
    session: AsyncSession, parent: ParentORM
) -> None:
    session.add(_item(parent.id, score=-1))

    with pytest.raises(ValidationError, match="ck_test_items_score_non_negative"):
        await SATransactionManager(session).commit()


@pytest.mark.asyncio
async def test_value_too_long_becomes_validation_error(
    session: AsyncSession, parent: ParentORM
) -> None:
    session.add(_item(parent.id, title="x" * 17))

    with pytest.raises(ValidationError, match="too long"):
        await SATransactionManager(session).flush()


@pytest.mark.asyncio
async def test_session_is_usable_after_a_translated_error(
    session: AsyncSession, parent: ParentORM
) -> None:
    # Read before the failure: a rollback expires every loaded attribute.
    parent_id = parent.id
    manager = SATransactionManager(session)
    session.add(_item(uuid4()))
    with pytest.raises(NotFoundError):
        await manager.commit()

    async with manager.transaction():
        session.add(_item(parent_id, title="after"))

    assert (await session.execute(text("SELECT count(*) FROM test_items"))).scalar_one() == 1


@pytest.mark.asyncio
async def test_probe_reports_a_reachable_database(engine: AsyncEngine) -> None:
    assert await SADatabaseProbe(engine, timeout_seconds=5).is_available()
