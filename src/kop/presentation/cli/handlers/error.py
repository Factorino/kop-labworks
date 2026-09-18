from kop.domain.errors.base import AppError
from kop.presentation.cli import constants
from kop.presentation.cli.exit_codes import ExitCode, exit_code_for
from kop.presentation.cli.io.output import ConsoleWriter


class CliErrorHandler:
    def __init__(self, writer: ConsoleWriter) -> None:
        self._writer: ConsoleWriter = writer

    def handle(self, error: AppError) -> ExitCode:
        self._writer.failure(str(error))
        return exit_code_for(error)

    def interrupted(self) -> ExitCode:
        self._writer.warning(constants.MSG_INTERRUPTED)
        return ExitCode.INTERRUPTED

    # Nothing of ours: the type is worth showing, a traceback is not.
    def unexpected(self, error: Exception) -> ExitCode:
        self._writer.failure(f"{type(error).__name__}: {error}")
        return ExitCode.UNEXPECTED
