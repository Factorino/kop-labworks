"""The command tree.

Only the shape of the CLI lives here: which commands exist, what they take and
how their result is printed. The configuration, the container and the logging
are the composition root's business, and it attaches them as the callback of
this application (see `main/cli/entrypoint.py`).
"""

from typing import Annotated

import typer

from kop.presentation.cli import constants
from kop.presentation.cli.commands.db.current import (
    ShowCurrentRevision,
    ShowCurrentRevisionResponse,
)
from kop.presentation.cli.commands.db.downgrade import (
    DowngradeDatabase,
    DowngradeDatabaseRequest,
    DowngradeDatabaseResponse,
)
from kop.presentation.cli.commands.db.revision import (
    CreateRevision,
    CreateRevisionRequest,
    CreateRevisionResponse,
)
from kop.presentation.cli.commands.db.upgrade import (
    UpgradeDatabase,
    UpgradeDatabaseRequest,
    UpgradeDatabaseResponse,
)
from kop.presentation.cli.io.output import ConsoleWriter
from kop.presentation.cli.runner import run


app = typer.Typer(
    name=constants.APP_NAME,
    help=constants.APP_HELP,
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)

db_app = typer.Typer(help=constants.GROUP_DB_HELP, no_args_is_help=True)
app.add_typer(db_app, name=constants.GROUP_DB)


def _render_upgrade(writer: ConsoleWriter, response: UpgradeDatabaseResponse) -> None:
    writer.success(constants.MSG_UPGRADED.format(revision=_revision(response.revision)))


@db_app.command("upgrade", help=constants.CMD_DB_UPGRADE_HELP)
def db_upgrade(
    ctx: typer.Context,
    revision: Annotated[
        str,
        typer.Argument(help=constants.ARG_UPGRADE_REVISION_HELP),
    ] = "head",
) -> None:
    run(ctx, UpgradeDatabase, UpgradeDatabaseRequest(revision=revision), _render_upgrade)


def _render_downgrade(writer: ConsoleWriter, response: DowngradeDatabaseResponse) -> None:
    writer.success(constants.MSG_DOWNGRADED.format(revision=_revision(response.revision)))


@db_app.command("downgrade", help=constants.CMD_DB_DOWNGRADE_HELP)
def db_downgrade(
    ctx: typer.Context,
    revision: Annotated[str, typer.Argument(help=constants.ARG_DOWNGRADE_REVISION_HELP)],
) -> None:
    run(ctx, DowngradeDatabase, DowngradeDatabaseRequest(revision=revision), _render_downgrade)


def _render_revision(writer: ConsoleWriter, response: CreateRevisionResponse) -> None:
    writer.success(constants.MSG_REVISION_CREATED.format(message=response.message))
    writer.hint(constants.HINT_REVISION_CREATED)


@db_app.command("revision", help=constants.CMD_DB_REVISION_HELP)
def db_revision(
    ctx: typer.Context,
    message: Annotated[str, typer.Option("--message", "-m", help=constants.OPT_MESSAGE_HELP)],
    *,
    empty: Annotated[bool, typer.Option("--empty", help=constants.OPT_EMPTY_HELP)] = False,
) -> None:
    request = CreateRevisionRequest(message=message, autogenerate=not empty)
    run(ctx, CreateRevision, request, _render_revision)


# The revision itself goes to stdout, unadorned: it is the answer, and it is
# read as often by a script as by a person.
def _render_current(writer: ConsoleWriter, response: ShowCurrentRevisionResponse) -> None:
    writer.line(_revision(response.revision))


@db_app.command("current", help=constants.CMD_DB_CURRENT_HELP)
def db_current(ctx: typer.Context) -> None:
    run(ctx, ShowCurrentRevision, None, _render_current)


def _revision(revision: str | None) -> str:
    return revision or constants.BASE_REVISION
