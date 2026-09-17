import asyncio
from typing import override

from pydantic import BaseModel

from kop.presentation.cli.commands.base import CliCommand
from kop.presentation.cli.interfaces.migrator import IMigrator


class UpgradeDatabaseRequest(BaseModel):
    revision: str = "head"


class UpgradeDatabaseResponse(BaseModel):
    revision: str | None


class UpgradeDatabase(CliCommand[UpgradeDatabaseRequest, UpgradeDatabaseResponse]):
    def __init__(self, migrator: IMigrator) -> None:
        self._migrator: IMigrator = migrator

    # In a thread: the migrator is synchronous, and alembic runs an event loop
    # of its own, which it cannot do inside ours.
    @override
    async def execute(self, request: UpgradeDatabaseRequest) -> UpgradeDatabaseResponse:
        await asyncio.to_thread(self._migrator.upgrade, request.revision)
        revision: str | None = await asyncio.to_thread(self._migrator.current)
        return UpgradeDatabaseResponse(revision=revision)
