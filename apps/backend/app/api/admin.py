from __future__ import annotations

from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock
from time import monotonic
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.schemas.admin import (
    AdminActionRequest,
    AdminCreateRequest,
    AdminPointsAdjustmentRequest,
    AdminRedemptionBatchRequest,
    AdminSessionRequest,
    AdminTimeAdjustmentRequest,
)
from app.services.admin_repository import AdminRepository
from app.services.admin_analytics import AdminAnalyticsService
from app.services.admin_service import AdminPrincipal, AdminService, hash_client_value
from app.services.alipay_provider import AlipayPaymentProvider
from app.services.billing_service import BillingService
from app.services.document_processing import DocumentProcessingService
from app.services.realtime_speech_service import RealtimeSpeechService
from app.deps import billing_service, document_processing_service, realtime_speech_service


admin_router = APIRouter(prefix="/admin", tags=["commercial-admin"])
bearer = HTTPBearer(auto_error=False)
_rate_lock = Lock()
_rate_windows: dict[str, deque[float]] = defaultdict(deque)


@lru_cache(maxsize=1)
def admin_service() -> AdminService:
    settings = get_settings()
    return AdminService(settings, AdminRepository(settings))


def _request_id(request: Request) -> str:
    return request.state.request_context.request_id


def _client_hashes(request: Request) -> tuple[str | None, str | None]:
    secret = get_settings().admin_session_signing_secret
    return (
        hash_client_value(request.client.host if request.client else None, secret),
        hash_client_value(request.headers.get("user-agent"), secret),
    )


def require_admin_enabled() -> None:
    settings = get_settings()
    if not settings.admin_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        admin_service().assert_ready()
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc


def current_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    _: Annotated[None, Depends(require_admin_enabled)],
) -> AdminPrincipal:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Admin session required")
    try:
        principal = admin_service().authenticate(credentials.credentials)
        _check_rate_limit(principal.admin_session_id)
        return principal
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _check_rate_limit(key: str) -> None:
    now = monotonic()
    limit = max(1, get_settings().admin_rate_limit_per_minute)
    with _rate_lock:
        window = _rate_windows[key]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(status_code=429, detail="Admin rate limit exceeded")
        window.append(now)


def permission(name: str):
    def dependency(request: Request, principal: Annotated[AdminPrincipal, Depends(current_admin)]) -> AdminPrincipal:
        try:
            admin_service().require_permission(principal, name)
        except PermissionError as exc:
            ip_hash, user_agent_hash = _client_hashes(request)
            admin_service().audit(
                principal=principal,
                action=name,
                resource_type="permission",
                resource_id=None,
                reason=None,
                request_id=_request_id(request),
                result="denied",
                ip_hash=ip_hash,
                user_agent_hash=user_agent_hash,
            )
            status = 428 if str(exc) == "admin_step_up_required" else 403
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return principal
    return dependency


def _page(limit: int, offset: int) -> tuple[int, int]:
    maximum = get_settings().admin_max_page_size
    return min(max(limit, 1), maximum), max(offset, 0)


def _confirmed(value: bool) -> None:
    if not value:
        raise HTTPException(status_code=409, detail="Explicit confirmation required")


@admin_router.post("/session")
def create_session(payload: AdminSessionRequest, request: Request, _: Annotated[None, Depends(require_admin_enabled)]):
    ip_hash, user_agent_hash = _client_hashes(request)
    try:
        token, session = admin_service().create_admin_session(
            user_access_token=payload.access_token,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
        )
        principal = AdminPrincipal(
            admin_session_id=session["adminSessionId"],
            user_id=admin_service().authenticate(token).user_id,
            role=session["role"],
            permissions=frozenset(session["permissions"]),
            recent_mfa_at_ms=0,
        )
        admin_service().audit(
            principal=principal,
            action="admin.session.create",
            resource_type="admin_session",
            resource_id=session["adminSessionId"],
            reason=None,
            request_id=_request_id(request),
            result="success",
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
        )
        return {"data": {**session, "token": token}}
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Administrator identity or MFA is invalid") from exc


@admin_router.get("/session")
def get_session(principal: Annotated[AdminPrincipal, Depends(current_admin)]):
    return {"data": {
        "adminSessionId": principal.admin_session_id,
        "role": principal.role,
        "permissions": sorted(principal.permissions),
    }}


@admin_router.delete("/session")
def revoke_session(principal: Annotated[AdminPrincipal, Depends(current_admin)]):
    admin_service().repository.revoke_session(principal.admin_session_id)
    return {"data": {"revoked": True}}


@admin_router.get("/dashboard")
def dashboard(
    request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("observability.read"))],
):
    data = admin_service().repository.dashboard()
    admin_service().audit(
        principal=principal, action="observability.read", resource_type="dashboard",
        resource_id=None, reason=None, request_id=_request_id(request), result="success",
    )
    return {"data": data}


@admin_router.get("/observability")
def observability(
    principal: Annotated[AdminPrincipal, Depends(permission("observability.read"))],
):
    return {"data": admin_service().repository.observability()}


@admin_router.get("/analytics/trends")
def analytics_trends(
    principal: Annotated[AdminPrincipal, Depends(permission("observability.read"))],
    range_key: str = Query(default="30d", alias="range", pattern="^(7d|30d|90d)$"),
    metrics: str | None = Query(default=None, max_length=400),
):
    selected = [item.strip() for item in metrics.split(",") if item.strip()] if metrics else None
    try:
        data = AdminAnalyticsService(admin_service().repository).trends(
            range_key=range_key,
            metric_keys=selected,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": data}


@admin_router.get("/analytics/health")
def analytics_health(
    principal: Annotated[AdminPrincipal, Depends(permission("observability.read"))],
):
    return {"data": AdminAnalyticsService(admin_service().repository).health()}


@admin_router.get("/capacity")
def capacity(
    request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("observability.read"))],
):
    monitor = getattr(request.app.state, "capacity_monitor", None)
    if monitor is None:
        raise HTTPException(status_code=503, detail="capacity_monitor_unavailable")
    return {"data": monitor.report()}


@admin_router.get("/users")
def users(
    principal: Annotated[AdminPrincipal, Depends(permission("users.read"))],
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
):
    limit, offset = _page(limit, offset)
    return {"data": {"items": admin_service().repository.list_users(search=search, limit=limit, offset=offset), "limit": limit, "offset": offset}}


@admin_router.get("/orders")
def orders(
    principal: Annotated[AdminPrincipal, Depends(permission("billing.read"))],
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
):
    limit, offset = _page(limit, offset)
    return {"data": {"items": admin_service().repository.list_orders(limit=limit, offset=offset), "limit": limit, "offset": offset}}


@admin_router.get("/redemption-batches")
def redemption_batches(
    principal: Annotated[AdminPrincipal, Depends(permission("billing.read"))],
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
):
    limit, offset = _page(limit, offset)
    return {
        "data": {
            "items": admin_service().repository.list_redemption_batches(limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }
    }


@admin_router.get("/materials")
def materials(
    principal: Annotated[AdminPrincipal, Depends(permission("materials.read"))],
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
):
    limit, offset = _page(limit, offset)
    return {"data": {"items": admin_service().repository.list_materials(limit=limit, offset=offset), "limit": limit, "offset": offset}}


@admin_router.get("/interviews")
def interviews(
    principal: Annotated[AdminPrincipal, Depends(permission("sessions.read"))],
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
):
    limit, offset = _page(limit, offset)
    return {"data": {"items": admin_service().repository.list_sessions(limit=limit, offset=offset), "limit": limit, "offset": offset}}


@admin_router.get("/audit")
def audit(
    principal: Annotated[AdminPrincipal, Depends(permission("audit.read"))],
    action: str | None = None,
    request_id: str | None = Query(default=None, alias="requestId"),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
):
    limit, offset = _page(limit, offset)
    return {"data": {"items": admin_service().repository.list_audit(action=action, request_id=request_id, limit=limit, offset=offset), "limit": limit, "offset": offset}}


@admin_router.get("/admins")
def administrators(
    principal: Annotated[AdminPrincipal, Depends(permission("admins.manage"))],
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
):
    limit, offset = _page(limit, offset)
    return {
        "data": {
            "items": admin_service().repository.list_administrators(limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }
    }


def _run_action(
    *,
    request: Request,
    principal: AdminPrincipal,
    payload: AdminActionRequest,
    action: str,
    resource_type: str,
    resource_id: str,
    callback,
):
    _confirmed(payload.confirmed)
    try:
        result, replay = admin_service().execute_idempotent(
            principal=principal, action=action, key=payload.idempotency_key, callback=callback,
        )
        admin_service().audit(
            principal=principal, action=action, resource_type=resource_type,
            resource_id=resource_id, reason=payload.reason, request_id=_request_id(request),
            result="success", details={**result, "idempotent_replay": replay},
        )
        return {"data": {**result, "idempotentReplay": replay}}
    except Exception as exc:
        admin_service().audit(
            principal=principal, action=action, resource_type=resource_type,
            resource_id=resource_id, reason=payload.reason, request_id=_request_id(request),
            result="failed", details={"error_code": exc.__class__.__name__},
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post("/admins")
def create_administrator(
    payload: AdminCreateRequest,
    request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("admins.manage"))],
):
    _confirmed(payload.confirmed)
    try:
        result = admin_service().provision_administrator(
            login_id=payload.login_id,
            role=payload.role,
            actor_user_id=principal.user_id,
        )
        admin_service().audit(
            principal=principal,
            action="admins.create",
            resource_type="admin_authorization",
            resource_id=str(result["user_id"]),
            reason=payload.reason,
            request_id=_request_id(request),
            result="success",
            details={"status": result["status"], "role": result["role"]},
        )
        return {"data": result}
    except Exception as exc:
        admin_service().audit(
            principal=principal,
            action="admins.create",
            resource_type="admin_authorization",
            resource_id=None,
            reason=payload.reason,
            request_id=_request_id(request),
            result="failed",
            details={"error_code": exc.__class__.__name__},
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post("/admins/{user_id}/disable")
def disable_administrator(
    user_id: str,
    payload: AdminActionRequest,
    request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("admins.manage"))],
):
    return _run_action(
        request=request,
        principal=principal,
        payload=payload,
        action="admins.disable",
        resource_type="admin_authorization",
        resource_id=user_id,
        callback=lambda: admin_service().disable_administrator(
            target_user_id=user_id,
            actor_user_id=principal.user_id,
        ),
    )


@admin_router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: str, payload: AdminActionRequest, request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("users.suspend"))],
):
    return _run_action(
        request=request, principal=principal, payload=payload, action="users.suspend",
        resource_type="user", resource_id=user_id,
        callback=lambda: dict(admin_service().repository.set_user_restriction(
            user_id=user_id, active=True, reason=payload.reason, actor_user_id=principal.user_id,
        )),
    )


@admin_router.post("/users/{user_id}/restore")
def restore_user(
    user_id: str, payload: AdminActionRequest, request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("users.suspend"))],
):
    return _run_action(
        request=request, principal=principal, payload=payload, action="users.restore",
        resource_type="user", resource_id=user_id,
        callback=lambda: dict(admin_service().repository.set_user_restriction(
            user_id=user_id, active=False, reason=payload.reason, actor_user_id=principal.user_id,
        )),
    )


@admin_router.post("/users/{user_id}/points")
def adjust_points(
    user_id: str, payload: AdminPointsAdjustmentRequest, request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("billing.adjust"))],
):
    if payload.points == 0:
        raise HTTPException(status_code=422, detail="Points adjustment cannot be zero")
    return _run_action(
        request=request, principal=principal, payload=payload, action="billing.adjust.points",
        resource_type="user", resource_id=user_id,
        callback=lambda: admin_service().repository.adjust_points(
            user_id=user_id, points=payload.points, reason=payload.reason,
            reference_id=f"admin:{principal.user_id}:{payload.idempotency_key}",
        ),
    )


@admin_router.post("/redemption-batches")
def create_redemption_batch(
    payload: AdminRedemptionBatchRequest,
    request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("redemptions.generate"))],
):
    _confirmed(payload.confirmed)
    try:
        result, replay = admin_service().create_redemption_batch(
            principal=principal,
            idempotency_key=payload.idempotency_key,
            campaign=payload.campaign,
            reason=payload.reason,
            points=payload.points,
            quantity=payload.quantity,
            expires_in_days=payload.expires_in_days,
        )
        admin_service().audit(
            principal=principal,
            action="redemptions.generate",
            resource_type="redemption_batch",
            resource_id=str(result["batch_id"]),
            reason=payload.reason,
            request_id=_request_id(request),
            result="success",
            details={
                "batch_id": result["batch_id"],
                "campaign": result["campaign"],
                "points_per_code": result["points_per_code"],
                "code_count": result["code_count"],
                "expires_at_ms": result["expires_at_ms"],
                "idempotent_replay": replay,
            },
        )
        return {"data": {**result, "idempotentReplay": replay}}
    except Exception as exc:
        admin_service().audit(
            principal=principal,
            action="redemptions.generate",
            resource_type="redemption_batch",
            resource_id=None,
            reason=payload.reason,
            request_id=_request_id(request),
            result="failed",
            details={"error_code": exc.__class__.__name__},
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post("/users/{user_id}/time")
def adjust_time(
    user_id: str, payload: AdminTimeAdjustmentRequest, request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("billing.adjust"))],
):
    return _run_action(
        request=request, principal=principal, payload=payload, action="billing.adjust.time",
        resource_type="user", resource_id=user_id,
        callback=lambda: admin_service().repository.adjust_time(
            user_id=user_id, days=payload.days, reason=payload.reason,
            reference_id=f"admin:{principal.user_id}:{payload.idempotency_key}",
            actor_user_id=principal.user_id,
        ),
    )


@admin_router.post("/orders/{order_id}/reconcile")
def reconcile_order(
    order_id: str, payload: AdminActionRequest, request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("payments.reconcile"))],
    billing: Annotated[BillingService, Depends(billing_service)],
):
    def reconcile():
        order = admin_service().repository.order_for_reconciliation(order_id)
        if not order:
            raise LookupError("order_not_found")
        if order["status"] == "paid":
            return {
                "order_id": order_id,
                "provider": order["provider"],
                "order_status": "paid",
                "status": "already_reconciled",
            }
        if order["provider"] != "alipay":
            return {
                "order_id": order_id,
                "provider": order["provider"],
                "order_status": order["status"],
                "status": "provider_query_not_supported",
            }
        authority = AlipayPaymentProvider(get_settings()).query_order(order_id=order_id)
        if not authority.verified:
            raise PermissionError("payment_provider_response_not_verified")
        if not authority.paid:
            return {
                "order_id": order_id,
                "provider": order["provider"],
                "order_status": order["status"],
                "provider_status": authority.provider_status,
                "status": "provider_reports_unpaid",
            }
        reconciled = billing.confirm_checkout_paid(
            order_id=order_id,
            amount_cents=authority.amount_cents,
            provider_trade_no=authority.provider_trade_no,
        )
        return {
            "order_id": order_id,
            "provider": order["provider"],
            "order_status": reconciled.status,
            "provider_status": authority.provider_status,
            "status": "reconciled" if reconciled.status == "paid" else "amount_mismatch",
        }
    return _run_action(
        request=request, principal=principal, payload=payload, action="payments.reconcile",
        resource_type="order", resource_id=order_id, callback=reconcile,
    )


@admin_router.post("/materials/tasks/{task_id}/retry")
def retry_material(
    task_id: str, payload: AdminActionRequest, request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("materials.retry"))],
    processing: Annotated[DocumentProcessingService, Depends(document_processing_service)],
):
    def retry():
        owner = admin_service().repository.material_task_owner(task_id)
        if not owner:
            raise LookupError("material_task_not_found")
        task = processing.retry_task(task_id=task_id, user_id=str(owner["owner_user_id"]))
        return {"task_id": task.task_id, "status": task.current_stage, "document_id": task.document_id}
    return _run_action(
        request=request, principal=principal, payload=payload, action="materials.retry",
        resource_type="material_task", resource_id=task_id, callback=retry,
    )


@admin_router.post("/interviews/{session_id}/terminate")
def terminate_interview(
    session_id: str, payload: AdminActionRequest, request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("sessions.terminate"))],
    realtime: Annotated[RealtimeSpeechService, Depends(realtime_speech_service)],
):
    def terminate():
        session = admin_service().repository.session_for_termination(session_id)
        if not session:
            raise LookupError("session_not_found")
        return realtime.terminate_session_for_admin(
            user_id=str(session["owner_user_id"]),
            session_id=session_id,
        )
    return _run_action(
        request=request, principal=principal, payload=payload, action="sessions.terminate",
        resource_type="interview_session", resource_id=session_id,
        callback=terminate,
    )
