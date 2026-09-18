from dishka import BaseScope, Provider, Scope, from_context
from dishka.dependency_source import CompositeDependencySource

from kop.main.config.api import APIConfig
from kop.main.config.config import Config
from kop.main.config.database import DatabaseConfig
from kop.main.config.logging import LoggingConfig
from kop.main.config.server import ServerConfig
from kop.main.config.service import ServiceConfig
from kop.main.config.tracing import TracingConfig


class ConfigProvider(Provider):
    scope: BaseScope | None = Scope.APP

    configs: CompositeDependencySource = (
        from_context(Config)
        + from_context(ServiceConfig)
        + from_context(ServerConfig)
        + from_context(APIConfig)
        + from_context(LoggingConfig)
        + from_context(TracingConfig)
        + from_context(DatabaseConfig)
    )
