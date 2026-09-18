from typing import Any

import uvicorn

from kop.main.config.config import Config
from kop.main.logging import ServiceContext, build_log_config


# An import string rather than the app object: with reload or several workers
# uvicorn imports the application again in every child process.
_APP_FACTORY: str = "kop.main.api.app:app_factory"


def main() -> None:
    config: Config = Config.load()
    log_config: dict[str, Any] = build_log_config(
        config.logging,
        ServiceContext.from_config(config),
    )
    uvicorn.run(
        _APP_FACTORY,
        factory=True,
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        workers=config.server.workers,
        log_config=log_config,
        access_log=False,
    )
