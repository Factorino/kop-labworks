from typing import Literal

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from kop.application.queries.system.check_readiness import (
    CheckReadiness,
    CheckReadinessResponse,
)


router = APIRouter(tags=["Health"], route_class=DishkaRoute)


class HealthResponse(BaseModel):
    status: Literal["ok"]


# Liveness only: checking dependencies here would turn outages into restarts.
@router.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


# 503 rather than 200 with `ready: false`: orchestrators and load balancers
# read the status code, not the body.
@router.get(
    "/ready",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": CheckReadinessResponse}},
)
async def ready(
    interactor: FromDishka[CheckReadiness],
    response: Response,
) -> CheckReadinessResponse:
    result: CheckReadinessResponse = await interactor.execute()
    if not result.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
