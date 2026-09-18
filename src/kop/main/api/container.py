from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from kop.main.config.config import Config
from kop.main.di.base import base_providers, config_context
from kop.main.di.providers.system import SystemProvider
from kop.main.di.providers.tracing import TracingProvider


def create_container(config: Config) -> AsyncContainer:
    return make_async_container(
        FastapiProvider(),
        *base_providers(),
        TracingProvider(),
        SystemProvider(),
        context=config_context(config),
    )
