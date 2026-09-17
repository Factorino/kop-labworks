from dishka import AsyncContainer, make_async_container

from kop.main.config.config import Config
from kop.main.di.base import base_providers, config_context
from kop.main.di.providers.cli import CliProvider
from kop.presentation.cli.options import CliOutputOptions


def create_cli_container(config: Config, options: CliOutputOptions) -> AsyncContainer:
    return make_async_container(
        *base_providers(),
        CliProvider(),
        context={**config_context(config), CliOutputOptions: options},
    )
