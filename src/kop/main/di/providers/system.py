from collections.abc import Sequence

from dishka import BaseScope, Provider, Scope, provide
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from kop.application.interfaces.system.dependency_probe import IDependencyProbe
from kop.application.queries.system.check_readiness import CheckReadiness
from kop.infrastructure.database.common.probe import SADatabaseProbe


_PROBE_TIMEOUT_SECONDS: float = 2.0


# A dependency joins the readiness check together with the code that uses it.
class SystemProvider(Provider):
    scope: BaseScope | None = Scope.APP

    @provide
    def probes(self, engine: AsyncEngine) -> Sequence[IDependencyProbe]:
        return (SADatabaseProbe(engine, timeout_seconds=_PROBE_TIMEOUT_SECONDS),)

    @provide
    def check_readiness(self, probes: Sequence[IDependencyProbe]) -> CheckReadiness:
        return CheckReadiness(probes)
