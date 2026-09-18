from typing import ClassVar, override

import pytest

from kop.application.interfaces.system.dependency_probe import IDependencyProbe
from kop.application.queries.system.check_readiness import CheckReadiness


class FakeProbe(IDependencyProbe):
    name: ClassVar[str] = "fake"

    def __init__(self, name: str, available: bool) -> None:
        self.name = name  # type: ignore[misc]
        self._available = available

    @override
    async def is_available(self) -> bool:
        return self._available


@pytest.mark.asyncio
async def test_ready_when_every_dependency_is_available() -> None:
    result = await CheckReadiness(
        [FakeProbe("database", available=True), FakeProbe("broker", available=True)]
    ).execute()

    assert result.ready
    assert result.dependencies == {"database": True, "broker": True}


@pytest.mark.asyncio
async def test_not_ready_when_any_dependency_is_unavailable() -> None:
    result = await CheckReadiness(
        [FakeProbe("database", available=True), FakeProbe("broker", available=False)]
    ).execute()

    assert not result.ready
    assert result.dependencies == {"database": True, "broker": False}
