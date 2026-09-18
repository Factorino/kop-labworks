import json

import pytest
from starlette.requests import Request

from kop.application.errors.common import (
    AlreadyExistsError,
    ConflictError,
    NotFoundError,
)
from kop.application.errors.tracing import MissingTraceIdError
from kop.domain.errors.base import AppError, DomainError
from kop.domain.errors.common import ValidationError
from kop.infrastructure.errors.base import InfrastructureError
from kop.presentation.api.handlers.error import error_handler


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "status_code"),
    [
        (ValidationError(field="title"), 400),
        (DomainError(), 400),
        (MissingTraceIdError(header="X-Trace-Id"), 400),
        (NotFoundError(entity="Post", value=1), 404),
        (AlreadyExistsError(entity="Post"), 409),
        (ConflictError(entity="Post"), 409),
        (InfrastructureError(), 500),
        (AppError(), 500),
    ],
)
async def test_errors_map_to_status_codes(exception: AppError, status_code: int) -> None:
    response = await error_handler(_request(), exception)

    assert response.status_code == status_code


@pytest.mark.asyncio
async def test_response_body_describes_the_error() -> None:
    response = await error_handler(_request(), NotFoundError(entity="Post", value=7))

    assert json.loads(bytes(response.body)) == {
        "status_code": 404,
        "code": "not_found_error",
        "message": "Post with id=7 not found",
        "detail": {"entity": "Post", "field": "id", "value": 7},
    }


@pytest.mark.asyncio
async def test_foreign_exception_is_hidden_behind_unexpected_error() -> None:
    response = await error_handler(_request(), RuntimeError("secret internals"))

    body = json.loads(bytes(response.body))
    assert response.status_code == 500
    assert body["code"] == "unexpected_error"
    assert "secret" not in bytes(response.body).decode()
