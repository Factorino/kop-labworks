from typing import override
from uuid import uuid4

from kop.application.errors.tracing import MissingTraceIdError
from kop.presentation.api.interfaces.trace_provider import ITraceProvider, TraceId


class HTTPTraceProvider(ITraceProvider):
    def __init__(self, raw_trace_id: str | None, header: str, required: bool) -> None:
        self._raw_trace_id: str | None = raw_trace_id
        self._header: str = header
        self._required: bool = required

    @override
    def get_trace_id(self) -> TraceId:
        if self._raw_trace_id is None and self._required:
            raise MissingTraceIdError(header=self._header)

        return TraceId(self._raw_trace_id or uuid4().hex)
