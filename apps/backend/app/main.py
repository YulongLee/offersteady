from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, utc_now_iso
from app.core.responses import ApiEnvelope, success_response
from app.core.errors import install_exception_handlers
from app.middleware.request_context import RequestContextMiddleware
from app.schemas.foundation import HealthResponse


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version=settings.app_version)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header, "X-OfferSteady-App-Version", "X-OfferSteady-Environment"],
    )
    logger = configure_logging(settings)
    application.add_middleware(RequestContextMiddleware, settings=settings, logger=logger)
    install_exception_handlers(application, settings=settings, logger=logger)

    @application.get("/healthz", response_model=ApiEnvelope[HealthResponse])
    async def healthz(request: Request) -> ApiEnvelope[HealthResponse]:
        return success_response(
            request=request,
            data=HealthResponse(
                status="ok",
                service=settings.app_name,
                version=settings.app_version,
                environment=settings.environment,
            ),
            timestamp=utc_now_iso(),
        )

    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
