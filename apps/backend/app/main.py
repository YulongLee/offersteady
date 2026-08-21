from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.api.admin import admin_router, admin_service
from app.core.config import get_settings
from app.core.logging import configure_logging, utc_now_iso
from app.core.responses import ApiEnvelope, success_response
from app.core.errors import install_exception_handlers
from app.middleware.request_context import RequestContextMiddleware
from app.schemas.foundation import HealthResponse
from app.services.admin_capacity import AdminCapacityMonitor
from app.services.realtime_event_wait import RealtimeEventWaitExecutor


def create_app() -> FastAPI:
    settings = get_settings()
    logger = configure_logging(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        task: asyncio.Task[None] | None = None
        realtime_event_wait_executor = RealtimeEventWaitExecutor(
            max_workers=settings.realtime_event_wait_workers,
        )
        application.state.realtime_event_wait_executor = realtime_event_wait_executor
        if settings.admin_enabled and settings.database_url:
            try:
                monitor = AdminCapacityMonitor(settings, admin_service().repository)
                application.state.capacity_monitor = monitor

                async def sample_capacity() -> None:
                    while True:
                        try:
                            await asyncio.to_thread(monitor.sample)
                        except Exception:
                            logger.warning("admin_capacity_sample_failed")
                        await asyncio.sleep(max(10, settings.admin_capacity_sample_interval_seconds))

                task = asyncio.create_task(sample_capacity())
            except Exception:
                logger.warning("admin_capacity_monitor_unavailable")
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            realtime_event_wait_executor.shutdown()

    application = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            *settings.cors_allowed_origins,
            *(settings.admin_allowed_origins if settings.admin_enabled else []),
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[settings.request_id_header, "X-OfferSteady-App-Version", "X-OfferSteady-Environment"],
    )
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
    application.include_router(admin_router, prefix=settings.api_prefix)
    return application


app = create_app()
