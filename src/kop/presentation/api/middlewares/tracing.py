from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import TYPE_CHECKING, ClassVar, override

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import structlog

from kop.application.errors.tracing import MissingTraceIdError
from kop.presentation.api.handlers.error import error_handler
from kop.presentation.api.interfaces.trace_provider import TraceId


if TYPE_CHECKING:
    from dishka import AsyncContainer

_logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(__name__)


# dishka's middleware must be outermost for request.state to hold the
# container, so this one is added before setup_dishka.
class TracingMiddleware(BaseHTTPMiddleware):
    _TRACED_METHODS: ClassVar[frozenset[str]] = frozenset(
        {"GET", "POST", "PUT", "PATCH", "DELETE"},
    )
    _MS_IN_SECOND: ClassVar[int] = 1000

    def __init__(
        self,
        app: ASGIApp,
        header: str,
        untraced_paths: frozenset[str],
    ) -> None:
        super().__init__(app)
        self._header: str = header
        self._untraced_paths: frozenset[str] = untraced_paths

    @override
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method not in self._TRACED_METHODS or request.url.path in self._untraced_paths:
            return await call_next(request)

        container: AsyncContainer = request.state.dishka_container
        try:
            trace_id: TraceId = await container.get(TraceId)
        except MissingTraceIdError as error:
            return await error_handler(request, error)

        with structlog.contextvars.bound_contextvars(trace_id=trace_id):
            return await self._call_traced(request, call_next, trace_id)

    async def _call_traced(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
        trace_id: TraceId,
    ) -> Response:
        await _logger.ainfo("request.started", method=request.method, path=request.url.path)
        started_at: float = perf_counter()

        response: Response = await call_next(request)

        await _logger.ainfo(
            "request.finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((perf_counter() - started_at) * self._MS_IN_SECOND, 2),
        )
        response.headers[self._header] = trace_id
        return response
