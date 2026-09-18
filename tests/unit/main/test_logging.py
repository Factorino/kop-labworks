import logging.config
import pickle

import structlog

from kop.main.config.logging import LoggingConfig, LogRotation
from kop.main.logging import ServiceContext, build_log_config, setup_logging


CONTEXT = ServiceContext(service="kop", environment="testing", version="1.2.3")


def test_console_only_by_default() -> None:
    config = build_log_config(LoggingConfig(), CONTEXT)

    assert list(config["handlers"]) == ["console"]
    assert config["root"]["level"] == "INFO"


def test_file_sink_rotates_as_configured(tmp_path) -> None:
    file_path = tmp_path / "logs" / "app.log"

    config = build_log_config(
        LoggingConfig(file_path=str(file_path), rotation=LogRotation.DAILY, backups=3),
        CONTEXT,
    )

    handler = config["handlers"]["file"]
    assert handler["class"] == "logging.handlers.TimedRotatingFileHandler"
    assert (handler["when"], handler["backupCount"]) == ("D", 3)
    assert file_path.parent.is_dir()


def test_file_sink_without_rotation_is_watched(tmp_path) -> None:
    config = build_log_config(
        LoggingConfig(file_path=str(tmp_path / "app.log"), rotation=LogRotation.NEVER),
        CONTEXT,
    )

    assert config["handlers"]["file"]["class"] == "logging.handlers.WatchedFileHandler"


def test_log_config_survives_pickling() -> None:
    # uvicorn pickles it into every child process under reload or workers.
    for json_format in (True, False):
        config = build_log_config(LoggingConfig(json_format=json_format), CONTEXT)

        # The data was pickled a line above, by this very test.
        assert pickle.loads(pickle.dumps(config))["handlers"]  # noqa: S301


def test_records_carry_the_service_context(capsys) -> None:
    setup_logging(CONTEXT)
    logging.config.dictConfig(build_log_config(LoggingConfig(json_format=True), CONTEXT))

    structlog.stdlib.get_logger("test").info("something.happened", answer=42)

    output = capsys.readouterr().out
    assert '"event": "something.happened"' in output
    assert '"service": "kop"' in output
    assert '"environment": "testing"' in output
    assert '"answer": 42' in output
