import asyncio
from collections.abc import Sequence
from typing import override

from kop.application.dto.base import DTO
from kop.application.interfaces.common.interactor import Interactor
from kop.application.interfaces.system.dependency_probe import IDependencyProbe


class CheckReadinessResponse(DTO):
    ready: bool
    dependencies: dict[str, bool]


class CheckReadiness(Interactor[None, CheckReadinessResponse]):
    def __init__(self, probes: Sequence[IDependencyProbe]) -> None:
        self._probes: Sequence[IDependencyProbe] = probes

    @override
    async def execute(self, request: None = None) -> CheckReadinessResponse:
        results: list[bool] = await asyncio.gather(
            *(probe.is_available() for probe in self._probes),
        )
        dependencies: dict[str, bool] = {
            probe.name: result for probe, result in zip(self._probes, results, strict=True)
        }
        return CheckReadinessResponse(ready=all(results), dependencies=dependencies)
