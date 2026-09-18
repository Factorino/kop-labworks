from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from typing import Self

from pydantic import Field, field_validator, model_validator

from kop.main.config.base import BaseConfig


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production(self) -> bool:
        return self is Environment.PRODUCTION

    @property
    def is_deployed(self) -> bool:
        """Anything running on a server rather than on a developer's machine."""
        return self in {Environment.STAGING, Environment.PRODUCTION}


def _distribution() -> str:
    return (__package__ or "").partition(".")[0]


def _package_version() -> str:
    try:
        return version(_distribution())
    except PackageNotFoundError:
        return "0.0.0"


class ServiceConfig(BaseConfig):
    name: str = Field(default_factory=_distribution, min_length=1)
    title: str = Field(default="KOP Blog API", min_length=1)
    version: str = Field(default_factory=_package_version, min_length=1)
    environment: Environment = Environment.LOCAL

    debug: bool = False

    @field_validator("environment", mode="before")
    @classmethod
    def _normalise_environment(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _guard_production_debug(self) -> Self:
        if self.environment.is_production and self.debug:
            raise ValueError(
                "Setting service.debug must be off in production: it leaks internals — "
                "tracebacks, paths and configuration — into error responses"
            )
        return self
