from dishka import BaseScope, Provider, Scope, from_context, provide

from kop.infrastructure.database.common.migrator import AlembicMigrator
from kop.main.config.database import DatabaseConfig
from kop.presentation.cli.commands.db.current import ShowCurrentRevision
from kop.presentation.cli.commands.db.downgrade import DowngradeDatabase
from kop.presentation.cli.commands.db.revision import CreateRevision
from kop.presentation.cli.commands.db.upgrade import UpgradeDatabase
from kop.presentation.cli.handlers.error import CliErrorHandler
from kop.presentation.cli.interfaces.migrator import IMigrator
from kop.presentation.cli.io.output import ConsoleWriter, console_writer
from kop.presentation.cli.options import CliOutputOptions


class CliProvider(Provider):
    scope: BaseScope | None = Scope.APP

    options = from_context(CliOutputOptions)

    @provide
    def writer(self, options: CliOutputOptions) -> ConsoleWriter:
        return console_writer(options)

    @provide
    def error_handler(self, writer: ConsoleWriter) -> CliErrorHandler:
        return CliErrorHandler(writer)

    # The port is declared in presentation and satisfied structurally here:
    # this is the only place where both sides are known.
    @provide
    def migrator(self, config: DatabaseConfig) -> IMigrator:
        return AlembicMigrator(config.url)

    @provide(scope=Scope.REQUEST)
    def upgrade_database(self, migrator: IMigrator) -> UpgradeDatabase:
        return UpgradeDatabase(migrator)

    @provide(scope=Scope.REQUEST)
    def downgrade_database(self, migrator: IMigrator) -> DowngradeDatabase:
        return DowngradeDatabase(migrator)

    @provide(scope=Scope.REQUEST)
    def create_revision(self, migrator: IMigrator) -> CreateRevision:
        return CreateRevision(migrator)

    @provide(scope=Scope.REQUEST)
    def show_current_revision(self, migrator: IMigrator) -> ShowCurrentRevision:
        return ShowCurrentRevision(migrator)
