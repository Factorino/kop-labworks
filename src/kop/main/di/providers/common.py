from dishka import BaseScope, Provider, Scope, provide

from kop.application.interfaces.common.clock import IClock
from kop.infrastructure.common.clock import SystemClock


class CommonProvider(Provider):
    scope: BaseScope | None = Scope.APP

    @provide
    def clock(self) -> IClock:
        return SystemClock()
