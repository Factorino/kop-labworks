from typing import Final

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL, Connection, Engine


# By package, so it resolves both in a checkout and in the installed wheel.
_SCRIPT_LOCATION: Final[str] = "kop.infrastructure.database:migrations"

# Must match URL_ATTRIBUTE in migrations/env.py.
_URL_ATTRIBUTE: Final[str] = "url"

# Doubled percent signs: configparser interpolates the value.
_FILE_TEMPLATE: Final[str] = (
    "%%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s"
)

_POST_WRITE_HOOKS: Final[dict[str, str]] = {
    "hooks": "ruff_fix, ruff_format",
    "ruff_fix.type": "module",
    "ruff_fix.module": "ruff",
    "ruff_fix.options": "check --fix REVISION_SCRIPT_FILENAME",
    "ruff_format.type": "module",
    "ruff_format.module": "ruff",
    "ruff_format.options": "format REVISION_SCRIPT_FILENAME",
}


# Synchronous: alembic's env.py runs its own event loop.
class AlembicMigrator:
    def __init__(self, url: URL) -> None:
        self._url: URL = url

    def upgrade(self, revision: str = "head") -> None:
        command.upgrade(self._config(), revision)

    def downgrade(self, revision: str) -> None:
        command.downgrade(self._config(), revision)

    def revision(self, message: str, *, autogenerate: bool) -> None:
        config: AlembicConfig = self._config()
        for key, value in _POST_WRITE_HOOKS.items():
            config.set_section_option("post_write_hooks", key, value)
        command.revision(config, message=message, autogenerate=autogenerate)

    def current(self) -> str | None:
        engine: Engine = create_engine(self._url, poolclass=pool.NullPool)
        try:
            with engine.connect() as connection:
                return self._current_of(connection)
        finally:
            engine.dispose()

    def _config(self) -> AlembicConfig:
        config: AlembicConfig = AlembicConfig()
        config.set_main_option("script_location", _SCRIPT_LOCATION)
        config.set_main_option("file_template", _FILE_TEMPLATE)
        config.attributes[_URL_ATTRIBUTE] = self._url
        return config

    @staticmethod
    def _current_of(connection: Connection) -> str | None:
        return MigrationContext.configure(connection).get_current_revision()
