from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel


router = APIRouter(tags=["Root"])


class RootResponse(BaseModel):
    message: Literal["API is running"]
    version: str


@router.get("/")
async def root(request: Request) -> RootResponse:
    return RootResponse(message="API is running", version=request.app.version)
