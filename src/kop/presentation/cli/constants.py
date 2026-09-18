"""Every text the CLI prints, in one place.

Kept out of the command modules so that the wording can be read as a whole and
changed without touching behaviour.
"""

from typing import Final


APP_NAME: Final[str] = "kop-cli"
APP_HELP: Final[str] = "Operator commands of the blog aggregator."

GROUP_DB: Final[str] = "db"
GROUP_DB_HELP: Final[str] = "Database schema migrations."

OPT_CONFIG_HELP: Final[str] = "Configuration file; CONFIG_FILE when omitted."
OPT_QUIET_HELP: Final[str] = "Report nothing but the result itself."
OPT_NO_COLOR_HELP: Final[str] = "Print without colours, for a log or a pipe."

CMD_DB_UPGRADE_HELP: Final[str] = "Apply migrations up to a revision."
CMD_DB_DOWNGRADE_HELP: Final[str] = "Revert migrations down to a revision."
CMD_DB_REVISION_HELP: Final[str] = "Create a revision by comparing the models with the database."
CMD_DB_CURRENT_HELP: Final[str] = "Print the revision the database is at."

ARG_UPGRADE_REVISION_HELP: Final[str] = "Target revision."
ARG_DOWNGRADE_REVISION_HELP: Final[str] = "Target revision, e.g. -1 or base."
OPT_MESSAGE_HELP: Final[str] = "Short description."
OPT_EMPTY_HELP: Final[str] = "Write an empty revision instead of autogenerating."

# What alembic calls an empty database, and what `db current` prints for one.
BASE_REVISION: Final[str] = "base"

MSG_UPGRADED: Final[str] = "Database upgraded to {revision}"
MSG_DOWNGRADED: Final[str] = "Database downgraded to {revision}"
MSG_REVISION_CREATED: Final[str] = "Revision written for {message}"
MSG_INTERRUPTED: Final[str] = "Interrupted"

HINT_REVISION_CREATED: Final[str] = "Read the generated file before committing it."
