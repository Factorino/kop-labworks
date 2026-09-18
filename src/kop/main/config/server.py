from typing import Self

from pydantic import Field, model_validator

from kop.main.config.base import BaseConfig


class ServerConfig(BaseConfig):
    host: str = "0.0.0.0"  # noqa: S104
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1)

    reload: bool = False

    @model_validator(mode="after")
    def _guard_reload_across_workers(self) -> Self:
        if self.reload and self.workers > 1:
            raise ValueError(
                "Setting server.reload cannot be combined with more than one worker: "
                "uvicorn's reloader owns the child process itself"
            )
        return self
