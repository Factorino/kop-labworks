import asyncio
from typing import override

from pydantic import BaseModel

from kop.presentation.cli.commands.base import CliCommand
from kop.presentation.cli.interfaces.migrator import IMigrator


class ShowCurrentRevisionResponse(BaseModel):
    revision: str | None


class ShowCurrentRevision(CliCommand[None, ShowCurrentRevisionResponse]):
    def __init__(self, migrator: IMigrator) -> None:
        self._migrator: IMigrator = migrator

    # In a thread, for the reason given in upgrade.py.
    @override
    async def execute(self, request: None = None) -> ShowCurrentRevisionResponse:
        revision: str | None = await asyncio.to_thread(self._migrator.current)
        return ShowCurrentRevisionResponse(revision=revision)
