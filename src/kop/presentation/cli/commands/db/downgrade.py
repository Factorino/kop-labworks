import asyncio
from typing import override

from pydantic import BaseModel

from kop.presentation.cli.commands.base import CliCommand
from kop.presentation.cli.interfaces.migrator import IMigrator


class DowngradeDatabaseRequest(BaseModel):
    revision: str


class DowngradeDatabaseResponse(BaseModel):
    revision: str | None


class DowngradeDatabase(CliCommand[DowngradeDatabaseRequest, DowngradeDatabaseResponse]):
    def __init__(self, migrator: IMigrator) -> None:
        self._migrator: IMigrator = migrator

    # In a thread, for the reason given in upgrade.py.
    @override
    async def execute(self, request: DowngradeDatabaseRequest) -> DowngradeDatabaseResponse:
        await asyncio.to_thread(self._migrator.downgrade, request.revision)
        revision: str | None = await asyncio.to_thread(self._migrator.current)
        return DowngradeDatabaseResponse(revision=revision)
