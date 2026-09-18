from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Self

import structlog
import structlog.tracebacks
from structlog.typing import EventDict, Processor, WrappedLogger

from kop.main.config.config import Config
from kop.main.config.logging import LoggingConfig, LogRotation


_CONSOLE_HANDLER: Final[str] = "console"
_FILE_HANDLER: Final[str] = "file"


# show_locals=False: frame locals would include requests and passwords.
_JSON_TRACEBACKS: Final[Processor] = structlog.processors.ExceptionRenderer(
    structlog.tracebacks.ExceptionDictTransformer(show_locals=False),
)


@dataclass(frozen=True, slots=True)
class ServiceContext:
    service: str
    environment: str
    version: str

    @classmethod
    def from_config(cls, config: Config) -> Self:
        return cls(
            service=config.service.name,
            environment=config.service.environment,
            version=config.service.version,
        )


@dataclass(frozen=True, slots=True)
class _AddServiceContext:
    context: ServiceContext

    def __call__(
        self,
        _logger: WrappedLogger,
        _method_name: str,
        event_dict: EventDict,
    ) -> MutableMapping[str, Any]:
        event_dict.setdefault("service", self.context.service)
        event_dict.setdefault("environment", self.context.environment)
        event_dict.setdefault("version", self.context.version)
        return event_dict


# Separate: structlog must be configured in every process uvicorn spawns, while
# the stdlib config is applied by uvicorn itself.
def setup_logging(context: ServiceContext) -> None:
    structlog.configure(
        processors=[
            *_processors(context),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def build_log_config(config: LoggingConfig, context: ServiceContext) -> dict[str, Any]:
    handlers: dict[str, Any] = {
        _CONSOLE_HANDLER: {
            "class": "logging.StreamHandler",
            "formatter": _CONSOLE_HANDLER,
            "stream": "ext://sys.stdout",
        },
    }
    formatters: dict[str, Any] = {
        _CONSOLE_HANDLER: (
            _json_formatter(context) if config.json_format else _console_formatter(context)
        ),
    }

    if config.file_path is not None:
        handlers[_FILE_HANDLER] = _file_handler(config, config.file_path)
        formatters[_FILE_HANDLER] = _json_formatter(context)

    names: list[str] = list(handlers)
    logger_config: dict[str, Any] = {
        "level": config.level,
        "handlers": names,
        "propagate": False,
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": {"level": config.level, "handlers": names},
        "loggers": {
            "uvicorn": logger_config,
            "uvicorn.error": logger_config,
            "uvicorn.access": logger_config,
        },
    }


def _processors(context: ServiceContext) -> list[Processor]:
    return [
        _service_context(context),
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]


# `processors` needs remove_processors_meta by hand, or structlog's bookkeeping
# keys land in the JSON.
def _json_formatter(context: ServiceContext) -> dict[str, Any]:
    return {
        "()": structlog.stdlib.ProcessorFormatter,
        "processors": [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            _JSON_TRACEBACKS,
            structlog.processors.JSONRenderer(sort_keys=True, ensure_ascii=False),
        ],
        "foreign_pre_chain": _processors(context),
    }


def _console_formatter(context: ServiceContext) -> dict[str, Any]:
    return {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(colors=True),
        "foreign_pre_chain": _processors(context),
    }


def _service_context(context: ServiceContext) -> Processor:
    return _AddServiceContext(context)


def _file_handler(config: LoggingConfig, file_path: str) -> dict[str, Any]:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    common: dict[str, Any] = {
        "formatter": _FILE_HANDLER,
        "filename": str(path),
        "encoding": "utf-8",
    }

    if config.rotation is LogRotation.NEVER:
        return {"class": "logging.handlers.WatchedFileHandler", **common}

    return {
        "class": "logging.handlers.TimedRotatingFileHandler",
        "when": config.rotation.when,
        "backupCount": config.backups,
        "utc": True,  # The timestamps in the records are UTC; the file names match.
        **common,
    }
