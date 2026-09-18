from dishka import Provider

from kop.main.config.api import APIConfig
from kop.main.config.config import Config
from kop.main.config.database import DatabaseConfig
from kop.main.config.logging import LoggingConfig
from kop.main.config.server import ServerConfig
from kop.main.config.service import ServiceConfig
from kop.main.config.tracing import TracingConfig
from kop.main.di.providers.common import CommonProvider
from kop.main.di.providers.config import ConfigProvider
from kop.main.di.providers.database import DatabaseProvider


# Shared by every entry point; each adds the providers only it needs.
def base_providers() -> list[Provider]:
    return [
        ConfigProvider(),
        CommonProvider(),
        DatabaseProvider(),
    ]


def config_context(config: Config) -> dict[type, object]:
    return {
        Config: config,
        ServiceConfig: config.service,
        ServerConfig: config.server,
        APIConfig: config.api,
        LoggingConfig: config.logging,
        TracingConfig: config.tracing,
        DatabaseConfig: config.database,
    }
