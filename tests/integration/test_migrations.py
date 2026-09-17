from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from typer.testing import CliRunner

from kop.infrastructure.database.common.migrator import AlembicMigrator
from kop.main.cli.entrypoint import app


def test_migrator_upgrades_and_reports_the_revision(database_url: URL) -> None:
    migrator = AlembicMigrator(database_url)

    migrator.upgrade()

    # No revisions yet: the database stays at base, and upgrading is a no-op
    # that must not fail.
    assert migrator.current() is None


def test_cli_prints_the_current_revision(database_url: URL, tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f"""
[logging]
level = "WARNING"

[database]
host = "{database_url.host}"
port = {database_url.port or 5432}
database = "{database_url.database}"
username = "{database_url.username}"
password = "{database_url.password}"
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["--config", str(config_file), "db", "current"])

    assert result.exit_code == 0, result.output
    assert result.output.strip().endswith("base")


def test_database_is_reachable_with_the_test_url(database_url: URL) -> None:
    engine = create_engine(database_url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
