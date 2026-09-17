from pathlib import Path

from pydantic import ValidationError
import pytest

from kop.main.config.api import APIConfig, CORSConfig
from kop.main.config.config import Config
from kop.main.config.database import DatabaseConfig
from kop.main.config.logging import LogLevel, LogRotation
from kop.main.config.server import ServerConfig
from kop.main.config.service import Environment, ServiceConfig


MINIMAL_TOML = """
[database]
host = "db"
database = "kop"
username = "kop"
password = "secret"
"""


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_reads_the_named_file(tmp_path: Path) -> None:
    config_file = _write(tmp_path / "config.toml", MINIMAL_TOML + "\n[server]\nport = 9000\n")

    config = Config.load(path=str(config_file))

    assert config.database.host == "db"
    assert config.server.port == 9000
    assert config.service.environment is Environment.LOCAL


def test_load_takes_the_path_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write(tmp_path / "named.toml", MINIMAL_TOML)
    monkeypatch.setenv("CONFIG_FILE", str(config_file))

    assert Config.load().database.database == "kop"


def test_missing_named_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Configuration file not found"):
        Config.load(path=str(tmp_path / "absent.toml"))


def test_environment_variable_overrides_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = _write(tmp_path / "config.toml", MINIMAL_TOML)
    monkeypatch.setenv("APP__DATABASE__HOST", "override")
    monkeypatch.setenv("APP__LOGGING__LEVEL", "warning")

    config = Config.load(path=str(config_file))

    assert config.database.host == "override"
    assert config.database.username == "kop"
    assert config.logging.level is LogLevel.WARNING


def test_unknown_key_is_rejected(tmp_path: Path) -> None:
    config_file = _write(tmp_path / "config.toml", MINIMAL_TOML + "\n[server]\nprot = 1\n")

    with pytest.raises(ValidationError, match="prot"):
        Config.load(path=str(config_file))


def test_database_is_required() -> None:
    with pytest.raises(ValidationError, match="database"):
        Config.load()


def test_production_refuses_debug() -> None:
    with pytest.raises(ValidationError, match=r"service\.debug must be off"):
        ServiceConfig(environment=Environment.PRODUCTION, debug=True)


def test_environment_is_case_insensitive() -> None:
    assert ServiceConfig(environment="STAGING").environment.is_deployed  # type: ignore[arg-type]
    assert not Environment.LOCAL.is_deployed


def test_production_refuses_reload(tmp_path: Path) -> None:
    config_file = _write(
        tmp_path / "config.toml",
        MINIMAL_TOML + '\n[service]\nenvironment = "production"\n[server]\nreload = true\n',
    )

    with pytest.raises(ValidationError, match=r"server\.reload must be off in production"):
        Config.load(path=str(config_file))


def test_reload_cannot_run_several_workers() -> None:
    with pytest.raises(ValidationError, match="more than one worker"):
        ServerConfig(reload=True, workers=2)


def test_rotating_log_file_cannot_be_shared_by_workers(tmp_path: Path) -> None:
    config_file = _write(
        tmp_path / "config.toml",
        MINIMAL_TOML + '\n[server]\nworkers = 2\n[logging]\nfile_path = "app.log"\n',
    )

    with pytest.raises(ValidationError, match=r"logging\.rotation must be 'never'"):
        Config.load(path=str(config_file))


def test_cors_credentials_need_explicit_origins() -> None:
    with pytest.raises(ValidationError, match="cannot be combined"):
        CORSConfig(allow_credentials=True)


def test_disabled_docs_hide_every_documentation_url() -> None:
    api = APIConfig(docs_enabled=False)

    assert (api.docs_url, api.redoc_url, api.openapi_url) == (None, None, None)


def test_database_password_is_read_from_file_and_masked(tmp_path: Path) -> None:
    secret = _write(tmp_path / "pg_pwd.txt", "p@ss:word/1\n")

    database = DatabaseConfig(host="db", database="kop", username="kop", password_file=str(secret))

    assert database.password is not None
    assert database.password.get_secret_value() == "p@ss:word/1"
    assert "p@ss" not in repr(database.url)
    assert database.dsn == "postgresql+psycopg://kop:p%40ss%3Aword%2F1@db:5432/kop"
    assert database.engine_options["pool_size"] == 5


def test_missing_password_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="password_file"):
        DatabaseConfig(
            host="db",
            database="kop",
            username="kop",
            password_file=str(tmp_path / "absent.txt"),
        )


def test_log_rotation_speaks_the_handler_vocabulary() -> None:
    assert LogRotation.MIDNIGHT.when == "midnight"
    assert LogRotation.WEEKLY.when == "W0"
