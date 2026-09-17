from collections.abc import AsyncIterator

from dishka import BaseScope, Provider, Scope, provide
import orjson
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from kop.application.interfaces.common.transaction_manager import (
    AbstractTransactionManager,
)
from kop.infrastructure.database.common.errors.policy import POLICY
from kop.infrastructure.database.common.errors.violations import install
from kop.infrastructure.database.common.transaction_manager import SATransactionManager
from kop.main.config.database import DatabaseConfig


class DatabaseProvider(Provider):
    scope: BaseScope | None = Scope.APP

    @provide
    async def engine(self, config: DatabaseConfig) -> AsyncIterator[AsyncEngine]:
        engine: AsyncEngine = create_async_engine(
            config.url,
            json_serializer=_dump_json,
            json_deserializer=orjson.loads,
            **config.engine_options,
        )
        install(engine, POLICY)
        yield engine
        await engine.dispose()

    @provide
    def session_maker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def transaction_manager(self, session: AsyncSession) -> AbstractTransactionManager:
        return SATransactionManager(session)


# SQLAlchemy hands the serialized JSON to the driver as text.
def _dump_json(value: object) -> str:
    return orjson.dumps(value).decode()
