from typing import Any

from pydantic import Field, NonNegativeInt, PositiveInt, SecretStr, model_validator
from sqlalchemy.engine import URL

from kop.main.config.base import BaseConfig
from kop.main.config.secrets import resolve_secret


_DRIVERNAME: str = "postgresql+psycopg"


class PoolConfig(BaseConfig):
    size: PositiveInt = 5
    max_overflow: NonNegativeInt = 10
    timeout: PositiveInt = 30

    # Must stay below the server's idle timeout. -1 disables recycling.
    recycle: int = Field(default=1800, ge=-1)

    pre_ping: bool = True

    @property
    def engine_options(self) -> dict[str, Any]:
        return {
            "pool_pre_ping": self.pre_ping,
            "pool_size": self.size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.timeout,
            "pool_recycle": self.recycle,
        }


class DatabaseConfig(BaseConfig):
    host: str
    port: int = Field(default=5432, ge=1, le=65535)
    database: str
    username: str
    password: SecretStr | None = None
    password_file: str | None = None

    echo: bool = False

    pool: PoolConfig = Field(default_factory=PoolConfig)

    @property
    def url(self) -> URL:
        return URL.create(
            _DRIVERNAME,
            username=self.username,
            password=self.password.get_secret_value() if self.password else None,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    @property
    def dsn(self) -> str:
        return self.url.render_as_string(hide_password=False)

    @property
    def engine_options(self) -> dict[str, Any]:
        return {"echo": self.echo} | self.pool.engine_options

    @model_validator(mode="before")
    @classmethod
    def _read_password_file(cls, data: Any) -> Any:
        return resolve_secret(data, key="password")
