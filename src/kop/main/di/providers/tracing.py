from dishka import BaseScope, Provider, Scope, provide
from fastapi import Request

from kop.main.config.tracing import TracingConfig
from kop.presentation.api.interfaces.trace_provider import ITraceProvider, TraceId
from kop.presentation.api.tracing.http_provider import HTTPTraceProvider


class TracingProvider(Provider):
    scope: BaseScope | None = Scope.REQUEST

    @provide
    def trace_provider(self, request: Request, config: TracingConfig) -> ITraceProvider:
        return HTTPTraceProvider(
            raw_trace_id=request.headers.get(config.header),
            header=config.header,
            required=config.required,
        )

    @provide
    def trace_id(self, trace_provider: ITraceProvider) -> TraceId:
        return trace_provider.get_trace_id()
