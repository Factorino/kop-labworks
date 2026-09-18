"""The only place the CLI writes to a terminal.

Results go to stdout and everything about them to stderr, so that
`kop-cli db current` stays usable in a pipeline while still explaining itself
on screen.
"""

from typing import ClassVar

from rich.console import RenderableType

from kop.presentation.cli.console import ErrConsole, OutConsole
from kop.presentation.cli.options import CliOutputOptions
from kop.presentation.cli.styles import THEME


class ConsoleWriter:
    _SUCCESS: ClassVar[str] = "\u2714"
    _FAILURE: ClassVar[str] = "\u2718"
    _WARNING: ClassVar[str] = "!"
    _INFO: ClassVar[str] = "\u00b7"

    def __init__(
        self,
        out_console: OutConsole,
        err_console: ErrConsole,
        options: CliOutputOptions,
    ) -> None:
        self._out: OutConsole = out_console
        self._err: ErrConsole = err_console
        self._quiet: bool = options.quiet

    def payload(self, renderable: RenderableType) -> None:
        self._out.print(renderable)

    def line(self, text: str) -> None:
        self._out.print(text, markup=False, highlight=False, soft_wrap=True)

    def success(self, message: str) -> None:
        self._notify(self._SUCCESS, message, "success")

    def warning(self, message: str) -> None:
        self._notify(self._WARNING, message, "warning")

    def info(self, message: str) -> None:
        self._notify(self._INFO, message, "info")

    def failure(self, message: str) -> None:
        # Errors ignore --quiet: otherwise the exit code has no explanation.
        self._err.print(f"[failure]{self._FAILURE}[/failure] {message}", highlight=False)

    def hint(self, message: str) -> None:
        if self._quiet:
            return
        self._err.print(f"  [hint]{message}[/hint]", highlight=False)

    def _notify(self, marker: str, message: str, style: str) -> None:
        if self._quiet:
            return
        self._err.print(f"[{style}]{marker}[/{style}] {message}", highlight=False)


# The one way a writer is built, used by the container and by the runner when
# there is no container yet. Rich highlighting of numbers and paths is switched
# off: in a report it decorates the wrong words.
def console_writer(options: CliOutputOptions) -> ConsoleWriter:
    return ConsoleWriter(
        OutConsole(theme=THEME, highlight=False, no_color=options.no_color),
        ErrConsole(theme=THEME, stderr=True, highlight=False, no_color=options.no_color),
        options,
    )
