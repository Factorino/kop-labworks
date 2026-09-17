from fastapi import APIRouter

from kop.presentation.api.routes.health import router as health_router
from kop.presentation.api.routes.root import router as root_router


__all__: list[str] = ["router"]


router = APIRouter()
router.include_router(root_router)
router.include_router(health_router)
