from typing import Self

from pydantic import Field, model_validator

from kop.main.config.base import BaseConfig


class CORSConfig(BaseConfig):
    allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = False
    max_age: int = Field(default=600, ge=0)

    @model_validator(mode="after")
    def _reject_wildcard_with_credentials(self) -> Self:
        # Browsers reject credentials combined with a wildcard origin.
        if self.allow_credentials and "*" in self.allow_origins:
            raise ValueError(
                "Setting api.cors.allow_credentials cannot be combined with the '*' origin; "
                "list the origins explicitly"
            )
        return self


class APIConfig(BaseConfig):
    docs_enabled: bool = True

    cors: CORSConfig = Field(default_factory=CORSConfig)

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.docs_enabled else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.docs_enabled else None

    @property
    def openapi_url(self) -> str | None:
        return "/openapi.json" if self.docs_enabled else None
