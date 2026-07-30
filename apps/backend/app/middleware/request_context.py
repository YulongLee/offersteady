from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings
from app.core.logging import log_event, utc_now_iso
from app.core.request_context import RequestContext


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings, logger: logging.Logger) -> None:
        super().__init__(app)
        self.settings = settings
        self.logger = logger

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self.settings.request_id_header) or f"req_{uuid4().hex}"
        request.state.request_context = RequestContext(request_id=request_id)
        started = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            monitor = getattr(request.app.state, "capacity_monitor", None)
            if monitor is not None:
                monitor.record_request(
                    path=request.url.path,
                    elapsed_ms=elapsed_ms,
                    status_code=status_code,
                )
            log_event(
                self.logger,
                logging.INFO,
                settings=self.settings,
                event="request.completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed_ms,
            )
        response.headers[self.settings.request_id_header] = request_id
        response.headers["X-OfferSteady-App-Version"] = self.settings.app_version
        response.headers["X-OfferSteady-Environment"] = self.settings.environment
        response.headers["X-OfferSteady-Response-Timestamp"] = utc_now_iso()
        return response
