"""Where the correlation id of a request comes from.

Declared in presentation because that is who asks for it: the middleware binds
it to the log context and echoes it back in the response header. An adapter for
another transport — a broker message, say — implements the same protocol.
"""

from abc import abstractmethod
from typing import NewType, Protocol


TraceId = NewType("TraceId", str)


class ITraceProvider(Protocol):
    @abstractmethod
    def get_trace_id(self) -> TraceId: ...
