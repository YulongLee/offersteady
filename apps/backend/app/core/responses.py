from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Request
from pydantic import BaseModel

from app.core.request_context import RequestContext


T = TypeVar("T")


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class ApiMeta(BaseModel):
    apiVersion: str
    timestamp: str


class ApiEnvelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ApiErrorDetail | None = None
    requestId: str
    meta: ApiMeta


def _request_id_from(request: Request) -> str:
    context = getattr(request.state, "request_context", None)
    if isinstance(context, RequestContext):
        return context.request_id
    return "request-id-unavailable"


def success_response(*, request: Request, data: T, api_version: str = "v1", timestamp: str) -> ApiEnvelope[T]:
    return ApiEnvelope[T](
        success=True,
        data=data,
        error=None,
        requestId=_request_id_from(request),
        meta=ApiMeta(apiVersion=api_version, timestamp=timestamp),
    )


def error_response(
    *,
    request: Request,
    code: str,
    message: str,
    details: dict[str, object] | None,
    api_version: str = "v1",
    timestamp: str,
) -> ApiEnvelope[None]:
    return ApiEnvelope[None](
        success=False,
        data=None,
        error=ApiErrorDetail(code=code, message=message, details=details),
        requestId=_request_id_from(request),
        meta=ApiMeta(apiVersion=api_version, timestamp=timestamp),
    )
