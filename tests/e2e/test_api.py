import pytest
from sqlalchemy.engine import URL

from kop.main.config.api import APIConfig
from kop.main.config.service import ServiceConfig
from kop.main.config.tracing import TracingConfig
from tests.e2e.conftest import ClientFactory, database_config


@pytest.mark.asyncio
async def test_root_reports_the_version(client: ClientFactory) -> None:
    async with client(service=ServiceConfig(version="1.2.3")) as http:
        response = await http.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "API is running", "version": "1.2.3"}


@pytest.mark.asyncio
async def test_health_does_not_depend_on_the_database(client: ClientFactory) -> None:
    async with client() as http:
        response = await http.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_is_503_while_the_database_is_unreachable(client: ClientFactory) -> None:
    async with client() as http:
        response = await http.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"ready": False, "dependencies": {"database": False}}


@pytest.mark.asyncio
async def test_ready_when_the_database_answers(client: ClientFactory, database_url: URL) -> None:
    async with client(database=database_config(database_url)) as http:
        response = await http.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"ready": True, "dependencies": {"database": True}}


@pytest.mark.asyncio
async def test_trace_id_is_echoed_or_generated(client: ClientFactory) -> None:
    async with client() as http:
        echoed = await http.get("/missing", headers={"X-Trace-Id": "abc123"})
        generated = await http.get("/missing")

    assert echoed.status_code == 404
    assert echoed.headers["X-Trace-Id"] == "abc123"
    assert len(generated.headers["X-Trace-Id"]) == 32


@pytest.mark.asyncio
async def test_required_trace_id_is_enforced(client: ClientFactory) -> None:
    async with client(tracing=TracingConfig(required=True)) as http:
        missing = await http.get("/missing")
        health = await http.get("/health")

    assert missing.status_code == 400
    assert missing.json()["code"] == "missing_trace_id_error"
    # Probes are exempt: an orchestrator does not send trace headers.
    assert health.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_documentation_can_be_switched_off(client: ClientFactory, path: str) -> None:
    async with client() as enabled:
        shown = await enabled.get(path)
    async with client(api=APIConfig(docs_enabled=False)) as disabled:
        hidden = await disabled.get(path)

    assert shown.status_code == 200
    assert hidden.status_code == 404
