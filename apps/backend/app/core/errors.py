from __future__ import annotations

import logging
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.core.logging import log_event, utc_now_iso
from app.core.responses import error_response


_CONTROL_ERROR_LOG_WINDOW_SECONDS = 5.0
_control_error_log_state: dict[tuple[str, str, int], tuple[float, int]] = {}


def _control_error_log_sample(exc: "DomainRequestError") -> tuple[bool, int]:
    if exc.feature != "realtime-speech" or exc.action not in {
        "desktop-active-binding",
        "desktop-capture-binding",
    }:
        return True, 0
    key = (exc.feature, exc.action, exc.status_code)
    current = monotonic()
    previous_at, suppressed = _control_error_log_state.get(key, (0.0, 0))
    if current - previous_at < _CONTROL_ERROR_LOG_WINDOW_SECONDS:
        _control_error_log_state[key] = (previous_at, suppressed + 1)
        return False, suppressed + 1
    _control_error_log_state[key] = (current, 0)
    return True, suppressed


class PlaceholderNotImplementedError(Exception):
    def __init__(self, feature: str, action: str, message: str | None = None):
        self.feature = feature
        self.action = action
        self.message = message or f"{feature}::{action} is reserved for a later implementation phase."
        super().__init__(self.message)


class DomainRequestError(Exception):
    def __init__(self, feature: str, action: str, message: str, status_code: int = 400, error_code: str | None = None):
        self.feature = feature
        self.action = action
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def install_exception_handlers(app: FastAPI, *, settings: Settings, logger: logging.Logger) -> None:
    @app.exception_handler(PlaceholderNotImplementedError)
    async def handle_placeholder(request: Request, exc: PlaceholderNotImplementedError) -> JSONResponse:
        log_event(
            logger,
            logging.WARNING,
            settings=settings,
            event="request.placeholder",
            request_id=getattr(getattr(request.state, "request_context", None), "request_id", None),
            feature=exc.feature,
            action=exc.action,
            error_code="placeholder_not_implemented",
        )
        return JSONResponse(
            status_code=501,
            content=error_response(
                request=request,
                code="placeholder_not_implemented",
                message=exc.message,
                details={"feature": exc.feature, "action": exc.action, "errorCode": exc.error_code},
                timestamp=utc_now_iso(),
            ).model_dump(by_alias=True),
        )

    @app.exception_handler(DomainRequestError)
    async def handle_domain_error(request: Request, exc: DomainRequestError) -> JSONResponse:
        should_log, suppressed_count = _control_error_log_sample(exc)
        if should_log:
            log_event(
                logger,
                logging.WARNING,
                settings=settings,
                event="request.domain_error",
                request_id=getattr(getattr(request.state, "request_context", None), "request_id", None),
                feature=exc.feature,
                action=exc.action,
                error_code="domain_request_error",
                suppressed_count=suppressed_count,
            )
        retry_after_ms = 2_000 if exc.feature == "realtime-speech" and exc.action in {
            "desktop-active-binding",
            "desktop-capture-binding",
        } else None
        return JSONResponse(
            status_code=exc.status_code,
            headers={"Retry-After": "2"} if retry_after_ms is not None else None,
            content=error_response(
                request=request,
                code="domain_request_error",
                message=exc.message,
                details={
                    "feature": exc.feature,
                    "action": exc.action,
                    "errorCode": exc.error_code,
                    **({"retryAfterMs": retry_after_ms} if retry_after_ms is not None else {}),
                },
                timestamp=utc_now_iso(),
            ).model_dump(by_alias=True),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                request=request,
                code="request_validation_error",
                message="请求参数校验失败。",
                details={"issues": exc.errors()},
                timestamp=utc_now_iso(),
            ).model_dump(by_alias=True),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger,
            logging.ERROR,
            settings=settings,
            event="request.unexpected_error",
            request_id=getattr(getattr(request.state, "request_context", None), "request_id", None),
            error_code=exc.__class__.__name__,
        )
        return JSONResponse(
            status_code=500,
            content=error_response(
                request=request,
                code="internal_server_error",
                message="服务暂时不可用，请稍后重试。",
                details=None,
                timestamp=utc_now_iso(),
            ).model_dump(by_alias=True),
        )
