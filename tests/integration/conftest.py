"""Fixtures for integration tests.

Infrastructure adapters checked against the real dependencies they wrap —
PostgreSQL, Redis, RabbitMQ, recorded responses of external APIs — together
with their setup and cleanup.

The database is the one named by KOP_TEST_DATABASE_URL (see `database_url` in
tests/conftest.py); without it the tests that need it are skipped. `just
test-container` and CI provide one; locally, point the variable at any
PostgreSQL database you do not mind being written to.
"""

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from kop.infrastructure.database.common.errors.policy import build_policy
from kop.infrastructure.database.common.errors.violations import install
from kop.infrastructure.database.models.base import BaseORM
from tests.integration.models import TABLES


@pytest.fixture(scope="session")
def schema(database_url: URL) -> Iterator[None]:
    """Create the test tables once per run and drop them afterwards."""
    engine: Engine = create_engine(database_url, poolclass=NullPool)
    try:
        BaseORM.metadata.drop_all(engine, tables=TABLES)
        BaseORM.metadata.create_all(engine, tables=TABLES)
        yield
        BaseORM.metadata.drop_all(engine, tables=TABLES)
    finally:
        engine.dispose()


@pytest_asyncio.fixture
async def engine(database_url: URL, schema: None) -> AsyncIterator[AsyncEngine]:
    """An engine per test, wired to the error policy, over empty tables.

    NullPool and a fresh engine per test: an async connection belongs to the
    event loop it was opened on, and each test runs on a loop of its own.
    The policy is built here rather than imported, so that it sees the test
    tables, which are registered after the application's policy is.
    """
    engine: AsyncEngine = create_async_engine(database_url, poolclass=NullPool)
    install(engine, build_policy())
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE test_items, test_parents"))
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        yield session
