from typer.testing import CliRunner

from kop.application.errors.common import AlreadyExistsError, NotFoundError
from kop.domain.errors.base import AppError, DomainError
from kop.domain.errors.common import ValidationError
from kop.main.cli.entrypoint import app
from kop.presentation.cli.exit_codes import ExitCode, exit_code_for
from kop.presentation.cli.handlers.error import CliErrorHandler
from kop.presentation.cli.io.output import console_writer
from kop.presentation.cli.options import CliOutputOptions


def test_exit_codes_follow_the_error_hierarchy() -> None:
    assert exit_code_for(ValidationError(field="title")) is ExitCode.USAGE
    assert exit_code_for(NotFoundError(entity="Post", value=1)) is ExitCode.NOT_FOUND
    assert exit_code_for(AlreadyExistsError(entity="Post")) is ExitCode.CONFLICT
    # A kind with no entry of its own falls back along the MRO.
    assert exit_code_for(DomainError()) is ExitCode.FAILURE
    assert exit_code_for(AppError()) is ExitCode.FAILURE


def test_error_handler_reports_and_returns_a_code(capsys) -> None:
    handler = CliErrorHandler(console_writer(CliOutputOptions(no_color=True)))

    code = handler.handle(NotFoundError(entity="Post", value=7))

    assert code is ExitCode.NOT_FOUND
    assert "Post with id=7 not found" in capsys.readouterr().err


def test_unexpected_error_names_its_type_without_a_traceback(capsys) -> None:
    handler = CliErrorHandler(console_writer(CliOutputOptions(no_color=True)))

    code = handler.unexpected(RuntimeError("boom"))

    captured = capsys.readouterr().err
    assert code is ExitCode.UNEXPECTED
    assert "RuntimeError: boom" in captured
    assert "Traceback" not in captured


def test_help_needs_no_configuration() -> None:
    result = CliRunner().invoke(app, ["db", "--help"])

    assert result.exit_code == 0, result.output
    assert "upgrade" in result.output


def test_unreadable_configuration_is_reported_not_raised() -> None:
    result = CliRunner().invoke(app, ["--config", "absent.toml", "db", "current"])

    assert result.exit_code == ExitCode.CONFIG
    assert "Configuration file not found" in result.output
