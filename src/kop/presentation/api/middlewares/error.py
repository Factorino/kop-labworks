from collections.abc import Awaitable, Callable
from typing import override

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from kop.presentation.api.handlers.error import error_handler


# Catching here instead of registering an Exception handler: Starlette would
# log such errors a second time, outside the request's log context.
class ErrorMiddleware(BaseHTTPMiddleware):
    @override
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exception:  # noqa: BLE001 — the point of the class.
            return await error_handler(request, exception)
