from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.core.errors import PlaceholderNotImplementedError
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor


def build_status_router(feature: str, route_prefix: str, notes: str) -> tuple[APIRouter, ModuleDescriptor]:
    router = APIRouter(prefix=route_prefix, tags=[feature])

    @router.get("/status", response_model=ApiEnvelope[dict[str, str]])
    async def status(request: Request) -> ApiEnvelope[dict[str, str]]:
        return success_response(
            request=request,
            data={
                "status": "placeholder",
                "feature": feature,
                "message": f"{feature} module is scaffolded for MVP phase one.",
            },
            timestamp=utc_now_iso(),
        )

    descriptor = ModuleDescriptor(
        feature=feature,
        owning_app="apps/backend",
        route_prefix=f"/api/v1{route_prefix}",
        mode="placeholder",
        notes=notes,
    )
    return router, descriptor


def raise_placeholder(feature: str, action: str) -> None:
    raise PlaceholderNotImplementedError(feature=feature, action=action)
