import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import URL, Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Registers every table on the metadata for autogenerate.
import kop.infrastructure.database.models  # noqa: F401
from kop.infrastructure.database.models.base import BaseORM


# Passed as an object: configparser would mangle '%' in an encoded password.
URL_ATTRIBUTE: str = "url"


def _url() -> URL:
    url: object = context.config.attributes.get(URL_ATTRIBUTE)
    if not isinstance(url, URL):
        raise TypeError("Migrations run through `kop-cli db ...`, which supplies the database URL")
    return url


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=BaseORM.metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    engine: AsyncEngine = create_async_engine(_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise NotImplementedError("Offline (--sql) migrations are not supported")

asyncio.run(_run_async_migrations())
