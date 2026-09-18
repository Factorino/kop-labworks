from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from kop.domain.errors.base import AppError
from kop.main.api.container import create_container
from kop.main.config.api import APIConfig
from kop.main.config.config import Config
from kop.main.logging import ServiceContext, setup_logging
from kop.presentation.api.handlers.error import error_handler
from kop.presentation.api.middlewares.error import ErrorMiddleware
from kop.presentation.api.middlewares.tracing import TracingMiddleware
from kop.presentation.api.routes import router as api_router


if TYPE_CHECKING:
    from dishka import AsyncContainer


def app_factory() -> FastAPI:
    return create_app(Config.load())


def create_app(config: Config) -> FastAPI:
    setup_logging(ServiceContext.from_config(config))

    app = FastAPI(
        title=config.service.title,
        version=config.service.version,
        debug=config.service.debug,
        docs_url=config.api.docs_url,
        redoc_url=config.api.redoc_url,
        openapi_url=config.api.openapi_url,
        lifespan=_lifespan(),
    )

    container: AsyncContainer = create_container(config)

    _include_errors(app)
    _include_tracing(app, config)
    setup_dishka(container, app)
    _include_cors(app, config)
    _include_routers(app)
    _include_handlers(app)

    return app


# The container outlives every request and is closed once, on shutdown: that is
# what disposes the engine and returns its connections.
def _lifespan() -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        container: AsyncContainer = app.state.dishka_container
        try:
            yield
        finally:
            await container.close()

    return lifespan


# Innermost, so errors are logged inside the tracing context.
def _include_errors(app: FastAPI) -> None:
    app.add_middleware(ErrorMiddleware)


def _include_tracing(app: FastAPI, config: Config) -> None:
    app.add_middleware(
        TracingMiddleware,
        header=config.tracing.header,
        untraced_paths=_untraced_paths(config.api),
    )


def _untraced_paths(config: APIConfig) -> frozenset[str]:
    paths: set[str] = {"/", "/health", "/ready"}
    paths.update(path for path in (config.docs_url, config.redoc_url, config.openapi_url) if path)
    return frozenset(paths)


def _include_cors(app: FastAPI, config: Config) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors.allow_origins,
        allow_credentials=config.api.cors.allow_credentials,
        allow_methods=config.api.cors.allow_methods,
        allow_headers=config.api.cors.allow_headers,
        max_age=config.api.cors.max_age,
    )


def _include_routers(app: FastAPI) -> None:
    app.include_router(api_router)


def _include_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, error_handler)
