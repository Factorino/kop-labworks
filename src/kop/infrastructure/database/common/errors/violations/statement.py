"""The last-resort tier: what the statement itself reveals.

MariaDB reports neither the constraint nor the table when a primary key clashes,
so without this the violation cannot be placed at all.
"""

from __future__ import annotations
import re
from typing import Final


_TABLE: Final[re.Pattern[str]] = re.compile(
    r"(?:INSERT\s+(?:INTO|IGNORE\s+INTO)|UPDATE|DELETE\s+FROM)\s+[`\"\[]?(?P<table>[\w$]+)",
    re.IGNORECASE,
)


_DELETE: Final[re.Pattern[str]] = re.compile(r"^\s*DELETE\s+FROM\b", re.IGNORECASE)


def is_delete(statement: str | None) -> bool:
    """Whether the statement removes rows.

    A DELETE can only break a foreign key one way: rows elsewhere still point
    at what it removed. It never creates a reference, so the direction is
    certain even when the backend does not say - which SQLite never does.
    """
    return bool(statement) and _DELETE.match(statement or "") is not None


def table_in(statement: str | None) -> str | None:
    """Return the table a statement writes to, if it can be read off cheaply."""
    if not statement:
        return None
    matched = _TABLE.search(statement)
    return matched["table"] if matched else None
