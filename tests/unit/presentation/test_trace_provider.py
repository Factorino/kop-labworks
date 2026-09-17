import pytest

from kop.application.errors.tracing import MissingTraceIdError
from kop.presentation.api.tracing.http_provider import HTTPTraceProvider


def test_trace_id_is_taken_from_the_header() -> None:
    provider = HTTPTraceProvider(raw_trace_id="abc", header="X-Trace-Id", required=True)

    assert provider.get_trace_id() == "abc"


def test_trace_id_is_generated_when_optional_and_absent() -> None:
    provider = HTTPTraceProvider(raw_trace_id=None, header="X-Trace-Id", required=False)

    assert len(provider.get_trace_id()) == 32


def test_missing_required_trace_id_is_an_error() -> None:
    provider = HTTPTraceProvider(raw_trace_id=None, header="X-Trace-Id", required=True)

    with pytest.raises(MissingTraceIdError, match="X-Trace-Id"):
        provider.get_trace_id()
