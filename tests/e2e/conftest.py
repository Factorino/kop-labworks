"""Fixtures for end-to-end tests.

Assembling the application through ``main`` and driving it via its external
interface.

Internals are off limits here: an end-to-end test may only use what a real
user of the application can see.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING, Any

from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
import pytest
from sqlalchemy.engine import URL

from kop.main.api.app import create_app
from kop.main.config.config import Config
from kop.main.config.database import DatabaseConfig


if TYPE_CHECKING:
    from fastapi import FastAPI


# A port nothing listens on: the connection is refused at once, so a readiness
# check against it fails fast instead of waiting for a timeout.
UNREACHABLE_DATABASE = DatabaseConfig(
    host="127.0.0.1",
    port=9,
    database="kop",
    username="kop",
    password=SecretStr("unused"),
)


def database_config(url: URL) -> DatabaseConfig:
    return DatabaseConfig(
        host=url.host or "localhost",
        port=url.port or 5432,
        database=url.database or "",
        username=url.username or "",
        password=SecretStr(url.password) if url.password else None,
    )


type ClientFactory = Callable[..., AbstractAsyncContextManager[AsyncClient]]


@pytest.fixture
def client() -> ClientFactory:
    """Start the application with a configuration of the test's choosing.

    The client talks to the ASGI application in process, with no server and
    no port. The container is closed on exit, which is what the lifespan does
    in a real run and what returns the engine's connections.
    """

    @asynccontextmanager
    async def start(
        database: DatabaseConfig = UNREACHABLE_DATABASE,
        **groups: Any,
    ) -> AsyncIterator[AsyncClient]:
        app: FastAPI = create_app(Config(database=database, **groups))
        transport = ASGITransport(app=app)
        try:
            async with AsyncClient(transport=transport, base_url="http://test") as http:
                yield http
        finally:
            await app.state.dishka_container.close()

    return start
