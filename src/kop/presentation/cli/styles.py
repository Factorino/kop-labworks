"""The vocabulary of styles the CLI prints with.

Named roles rather than colours, so that a message says what it is and the
theme decides how it looks.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from rich.theme import Theme


_STYLES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "success": "bold green",
        "warning": "bold yellow",
        "failure": "bold red",
        "info": "cyan",
        "hint": "dim italic",
        "heading": "bold",
        "label": "dim",
        "value": "default",
        "revision": "magenta",
    },
)

THEME: Final[Theme] = Theme(dict(_STYLES))
