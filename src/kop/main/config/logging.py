from enum import StrEnum

from pydantic import NonNegativeInt, field_validator

from kop.main.config.base import BaseConfig


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogRotation(StrEnum):
    NEVER = "never"
    HOURLY = "hourly"
    DAILY = "daily"
    MIDNIGHT = "midnight"
    WEEKLY = "weekly"

    @property
    def when(self) -> str:
        return {
            LogRotation.HOURLY: "H",
            LogRotation.DAILY: "D",
            LogRotation.MIDNIGHT: "midnight",
            LogRotation.WEEKLY: "W0",
        }[self]


class LoggingConfig(BaseConfig):
    level: LogLevel = LogLevel.INFO

    json_format: bool = True

    file_path: str | None = None
    rotation: LogRotation = LogRotation.MIDNIGHT
    backups: NonNegativeInt = 7

    @property
    def file_enabled(self) -> bool:
        return self.file_path is not None

    @field_validator("level", mode="before")
    @classmethod
    def _normalise_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator("rotation", mode="before")
    @classmethod
    def _normalise_rotation(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value
