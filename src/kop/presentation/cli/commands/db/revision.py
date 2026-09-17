import asyncio
from typing import override

from pydantic import BaseModel

from kop.presentation.cli.commands.base import CliCommand
from kop.presentation.cli.interfaces.migrator import IMigrator


class CreateRevisionRequest(BaseModel):
    message: str
    autogenerate: bool = True


class CreateRevisionResponse(BaseModel):
    message: str


class CreateRevision(CliCommand[CreateRevisionRequest, CreateRevisionResponse]):
    def __init__(self, migrator: IMigrator) -> None:
        self._migrator: IMigrator = migrator

    # In a thread, for the reason given in upgrade.py.
    @override
    async def execute(self, request: CreateRevisionRequest) -> CreateRevisionResponse:
        await asyncio.to_thread(
            self._migrator.revision,
            request.message,
            autogenerate=request.autogenerate,
        )
        return CreateRevisionResponse(message=request.message)
