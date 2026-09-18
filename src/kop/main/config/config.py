from contextvars import ContextVar, Token
import os
from pathlib import Path
from typing import Final, Self, override

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from kop.main.config.api import APIConfig
from kop.main.config.database import DatabaseConfig
from kop.main.config.logging import LoggingConfig, LogRotation
from kop.main.config.server import ServerConfig
from kop.main.config.service import ServiceConfig
from kop.main.config.tracing import TracingConfig


CONFIG_FILE_VARIABLE: Final[str] = "CONFIG_FILE"
DEFAULT_CONFIG_FILE: Final[str] = "./.config/local.toml"

ENV_PREFIX: Final[str] = "APP__"
ENV_NESTED_DELIMITER: Final[str] = "__"

# Passed out of band: settings_customise_sources takes no arguments of ours.
_PATH: Final[ContextVar[str | None]] = ContextVar("config_path")


def _resolve_path(path: str | None) -> str | None:
    requested: str | None = path or os.environ.get(CONFIG_FILE_VARIABLE)
    if requested is None:
        return DEFAULT_CONFIG_FILE if Path(DEFAULT_CONFIG_FILE).is_file() else None

    if not Path(requested).is_file():
        raise ValueError(
            f"Configuration file not found at {requested}. It is named by "
            f"{CONFIG_FILE_VARIABLE}; `just init` creates the ones under .config/"
        )

    return requested


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True,
        extra="forbid",
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        # Otherwise an env variable replaces a whole default group.
        nested_model_default_partial_update=True,
    )

    service: ServiceConfig = Field(default_factory=ServiceConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)

    database: DatabaseConfig

    @classmethod
    def load(cls, *, path: str | None = None) -> "Config":
        token: Token[str | None] = _PATH.set(_resolve_path(path))
        try:
            # No arguments on purpose: the required groups are filled by the
            # sources below, which mypy cannot see into.
            return cls()  # type: ignore[call-arg]
        finally:
            _PATH.reset(token)

    @model_validator(mode="after")
    def _guard_production_reload(self) -> Self:
        if self.service.environment.is_production and self.server.reload:
            raise ValueError(
                "Setting server.reload must be off in production: it watches the source tree "
                "and cannot coexist with more than one worker"
            )
        return self

    @model_validator(mode="after")
    def _guard_rotation_across_workers(self) -> Self:
        rotates: bool = (
            self.logging.file_enabled and self.logging.rotation is not LogRotation.NEVER
        )
        if rotates and self.server.workers > 1:
            raise ValueError(
                "Setting logging.rotation must be 'never' when server.workers is above one: "
                "workers would rotate the same file against each other. Leave rotation "
                "to logrotate, or collect the logs from stdout instead"
            )
        return self

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        try:
            path: str | None = _PATH.get()
        except LookupError:
            path = _resolve_path(None)

        sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
        if path is not None:
            sources.append(TomlConfigSettingsSource(settings_cls, toml_file=path))
        return tuple(sources)
