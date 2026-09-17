from functools import partial
import logging.config
from typing import Annotated

from dishka import AsyncContainer
import typer

from kop.main.cli.container import create_cli_container
from kop.main.config.config import Config
from kop.main.logging import ServiceContext, build_log_config, setup_logging
from kop.presentation.cli import constants
from kop.presentation.cli.app import app
from kop.presentation.cli.options import CliOutputOptions
from kop.presentation.cli.runner import CliState


# The wired application: importing this module is what attaches the callback
# below, so `kop-cli` and the tests take it from here rather than from
# presentation.
__all__: list[str] = ["app", "main"]


# Attached here rather than in presentation: the command tree describes what
# the CLI can do, the composition root decides what it is wired to.
@app.callback()
def configure(
    ctx: typer.Context,
    config_path: Annotated[
        str | None,
        typer.Option("--config", help=constants.OPT_CONFIG_HELP),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help=constants.OPT_QUIET_HELP)] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help=constants.OPT_NO_COLOR_HELP),
    ] = False,
) -> None:
    """Remember how the process was invoked; a command opens what it needs."""
    options = CliOutputOptions(quiet=quiet, no_color=no_color)
    ctx.obj = CliState(
        options=options, open_container=partial(_open_container, config_path, options)
    )


# Deferred until a command actually runs: `kop-cli db --help` would otherwise
# demand a readable configuration file to print two lines of help.
def _open_container(config_path: str | None, options: CliOutputOptions) -> AsyncContainer:
    config: Config = Config.load(path=config_path)
    context: ServiceContext = ServiceContext.from_config(config)
    setup_logging(context)
    logging.config.dictConfig(build_log_config(config.logging, context))
    return create_cli_container(config, options)


def main() -> None:
    app()
