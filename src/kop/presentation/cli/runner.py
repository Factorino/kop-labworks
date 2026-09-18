"""Running one command: open the container, execute, print, exit.

Every command goes through here, so error handling and exit codes are decided
in one place. What the CLI does not do is crash: an error of ours becomes a
line on stderr and a code the shell can read.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from dishka import AsyncContainer
import typer

from kop.domain.errors.base import AppError
from kop.presentation.cli.commands.base import CliCommand
from kop.presentation.cli.exit_codes import ExitCode
from kop.presentation.cli.handlers.error import CliErrorHandler
from kop.presentation.cli.io.output import ConsoleWriter, console_writer
from kop.presentation.cli.options import CliOutputOptions


type Renderer[ResponseData] = Callable[[ConsoleWriter, ResponseData], None]

# Deferred on purpose: `--help` must cost neither a configuration file nor a
# container, and the composition root is the only one that can build either.
type ContainerFactory = Callable[[], AsyncContainer]


@dataclass(frozen=True, slots=True)
class CliState:
    """What the root callback leaves behind for the commands to use."""

    options: CliOutputOptions
    open_container: ContainerFactory


def cli_state(ctx: typer.Context) -> CliState:
    return cast("CliState", ctx.obj)


def run[RequestData, ResponseData](
    ctx: typer.Context,
    command: type[CliCommand[RequestData, ResponseData]],
    request: RequestData,
    render: Renderer[ResponseData] | None = None,
) -> None:
    raise typer.Exit(asyncio.run(_execute(cli_state(ctx), command, request, render)))


async def _execute[RequestData, ResponseData](
    state: CliState,
    command: type[CliCommand[RequestData, ResponseData]],
    request: RequestData,
    render: Renderer[ResponseData] | None,
) -> int:
    try:
        container: AsyncContainer = state.open_container()
    except Exception as error:  # noqa: BLE001
        console_writer(state.options).failure(str(error))
        return ExitCode.CONFIG

    writer: ConsoleWriter = await container.get(ConsoleWriter)
    handler: CliErrorHandler = await container.get(CliErrorHandler)

    try:
        async with container() as request_container:
            resolved: CliCommand[RequestData, ResponseData] = await request_container.get(command)
            response: ResponseData = await resolved.execute(request)
    except AppError as error:
        return handler.handle(error)
    except KeyboardInterrupt:
        return handler.interrupted()
    except Exception as error:  # noqa: BLE001
        return handler.unexpected(error)
    finally:
        # Closing the container is what disposes the engine, if one was opened.
        await container.close()

    if render is not None:
        render(writer, response)

    return ExitCode.OK
