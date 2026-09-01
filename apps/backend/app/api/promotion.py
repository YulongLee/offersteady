from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock
from time import time
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.core.config import Settings, get_settings
from app.deps import require_authenticated_context
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.promotion import PromotionClaim, PromotionQualification
from app.services.promotion_repository import (
    PromotionEventQueue,
    PromotionRepository,
    classify_client,
    device_class,
    hmac_identifier,
    now_ms,
)


public_promotion_router = APIRouter(tags=["promotion-redirect"])
promotion_router = APIRouter(prefix="/promotion", tags=["promotion-attribution"])

VISITOR_COOKIE = "offersteady_pv"
CLICK_COOKIE = "offersteady_pc"
OPTOUT_COOKIE = "offersteady_analytics_optout"
INTERNAL_COOKIE = "offersteady_internal_traffic"
QUALIFY_MARKER_COOKIE = "offersteady_pq"
_rate_lock = Lock()
_rate_windows: dict[str, deque[float]] = defaultdict(deque)


def _admit(key: str, limit: int) -> bool:
    moment = time()
    with _rate_lock:
        window = _rate_windows[key]
        while window and window[0] <= moment - 60:
            window.popleft()
        if len(window) >= max(1, limit):
            return False
        window.append(moment)
        return True


@lru_cache(maxsize=1)
def promotion_repository() -> PromotionRepository:
    settings = get_settings()
    if not settings.promotion_enabled or not settings.database_url:
        raise RuntimeError("promotion_collection_disabled")
    return PromotionRepository(settings)


@lru_cache(maxsize=1)
def promotion_queue() -> PromotionEventQueue:
    return PromotionEventQueue(get_settings())


def _sign_click(slug: str, click_id: str, issued_at_ms: int, settings: Settings) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"s": slug, "c": click_id, "t": issued_at_ms}, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.promotion_visitor_hmac_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def _read_click(value: str | None, settings: Settings) -> dict[str, object] | None:
    if not value or "." not in value or len(value) > 512:
        return None
    body, signature = value.rsplit(".", 1)
    expected = hmac.new(settings.promotion_visitor_hmac_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if not isinstance(payload, dict) or not isinstance(payload.get("s"), str) or not isinstance(payload.get("c"), str):
            return None
        if now_ms() - int(payload.get("t", 0)) > settings.promotion_attribution_window_days * 86_400_000:
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _referrer_host(request: Request) -> str | None:
    try:
        value = urlparse(request.headers.get("referer", "")).hostname
        return value[:120].lower() if value else None
    except ValueError:
        return None


def _safe_fallback(settings: Settings) -> str:
    return f"{settings.public_web_base_url.rstrip('/')}{settings.promotion_safe_fallback_path}"


@public_promotion_router.get("/r/{slug}")
def redirect_promotion_link(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    preview: bool = Query(default=False, alias="preview"),
) -> Response:
    settings = get_settings()
    if not settings.promotion_enabled or not settings.database_url or not slug.isalnum() or not (8 <= len(slug) <= 32):
        return RedirectResponse(_safe_fallback(settings), status_code=302)
    try:
        link = promotion_repository().resolve_active_link(slug, at_ms=now_ms())
    except Exception:
        link = None
    if not link:
        return RedirectResponse(_safe_fallback(settings), status_code=302)

    client_key = hmac_identifier(request.client.host if request.client else "unknown", settings)
    rate_admitted = _admit(f"redirect:{client_key}", settings.promotion_redirect_rate_limit_per_minute)

    opted_out = request.cookies.get(OPTOUT_COOKIE) == "1"
    internal_test = request.cookies.get(INTERNAL_COOKIE) == "1"
    exclusion = "rate_limited" if not rate_admitted else classify_client(request.headers.get("user-agent"), admin_preview=preview, internal_test=internal_test)
    visitor_raw = request.cookies.get(VISITOR_COOKIE) if not opted_out else None
    if visitor_raw is not None and (len(visitor_raw) > 128 or not visitor_raw.replace("-", "").replace("_", "").isalnum()):
        visitor_raw = None
    if not opted_out and visitor_raw is None:
        visitor_raw = secrets.token_urlsafe(24)
    click_raw = secrets.token_urlsafe(18)
    occurred = now_ms()
    event = {
        "event_kind": "touchpoint",
        "event_id": f"promotion-event-{uuid4().hex}",
        "event_type": "redirect_hit",
        "link_id": link["link_id"],
        "visitor_hmac": hmac_identifier(visitor_raw, settings) if visitor_raw else None,
        "click_hmac": hmac_identifier(click_raw, settings),
        "occurred_at_ms": occurred,
        "destination_key": str(link["destination_path"]).split("?", 1)[0][:120],
        "referrer_host": _referrer_host(request),
        "device_class": device_class(request.headers.get("user-agent")),
        "qualification_state": "anonymous_aggregate" if opted_out else "excluded" if exclusion else "raw",
        "exclusion_reason": "analytics_optout" if opted_out else exclusion,
    }
    if rate_admitted:
        background_tasks.add_task(promotion_queue().publish, event)
    destination = f"{settings.public_web_base_url.rstrip('/')}{link['destination_path']}"
    response = RedirectResponse(destination, status_code=302)
    secure = settings.environment in {"staging", "production"}
    if visitor_raw:
        response.set_cookie(VISITOR_COOKIE, visitor_raw, max_age=settings.promotion_visitor_cookie_days * 86_400, secure=secure, httponly=True, samesite="lax", path="/")
    response.set_cookie(CLICK_COOKIE, _sign_click(slug, click_raw, occurred, settings), max_age=settings.promotion_attribution_window_days * 86_400, secure=secure, httponly=True, samesite="lax", path="/")
    response.set_cookie(QUALIFY_MARKER_COOKIE, "1", max_age=3_600, secure=secure, httponly=False, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@promotion_router.post("/qualify")
def qualify_promotion_visit(
    payload: PromotionQualification,
    request: Request,
    background_tasks: BackgroundTasks,
    click_cookie: str | None = Cookie(default=None, alias=CLICK_COOKIE),
    visitor_cookie: str | None = Cookie(default=None, alias=VISITOR_COOKIE),
) -> dict[str, object]:
    settings = get_settings()
    if not settings.promotion_enabled:
        return {"data": {"accepted": False, "reason": "collection_disabled"}}
    click = _read_click(click_cookie, settings)
    if not click or not visitor_cookie or request.cookies.get(OPTOUT_COOKIE) == "1":
        return {"data": {"accepted": False, "reason": "no_eligible_touchpoint"}}
    visitor_hmac = hmac_identifier(visitor_cookie, settings)
    if not _admit(f"qualify:{visitor_hmac}", settings.promotion_qualification_rate_limit_per_minute):
        return {"data": {"accepted": False, "reason": "rate_limited"}}
    try:
        link = promotion_repository().resolve_active_link(str(click["s"]), at_ms=now_ms())
    except Exception:
        link = None
    if not link:
        return {"data": {"accepted": False, "reason": "link_unavailable"}}
    exclusion = classify_client(
        request.headers.get("user-agent"),
        admin_preview=False,
        internal_test=request.cookies.get(INTERNAL_COOKIE) == "1",
    )
    qualified = payload.page_visible and payload.visible_ms >= settings.promotion_qualification_min_visible_ms and exclusion is None
    event = {
        "event_kind": "touchpoint",
        "event_id": f"promotion-qualification-{hashlib.sha256(f'{visitor_hmac}:{payload.event_id}'.encode()).hexdigest()}",
        "event_type": "qualified_visit",
        "link_id": link["link_id"],
        "visitor_hmac": visitor_hmac,
        "click_hmac": hmac_identifier(str(click["c"]), settings),
        "occurred_at_ms": now_ms(),
        "destination_key": str(link["destination_path"]).split("?", 1)[0][:120],
        "referrer_host": _referrer_host(request),
        "device_class": device_class(request.headers.get("user-agent")),
        "qualification_state": "qualified" if qualified else "excluded",
        "exclusion_reason": exclusion or (None if qualified else "qualification_threshold_not_met"),
    }
    background_tasks.add_task(promotion_queue().publish, event)
    return {"data": {"accepted": True, "qualified": qualified}}


@promotion_router.post("/claim")
def claim_promotion_identity(
    payload: PromotionClaim,
    background_tasks: BackgroundTasks,
    auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context),
    visitor_cookie: str | None = Cookie(default=None, alias=VISITOR_COOKIE),
) -> dict[str, object]:
    settings = get_settings()
    if not settings.promotion_enabled or not visitor_cookie:
        return {"data": {"accepted": False, "reason": "no_eligible_touchpoint"}}
    if not _admit(f"claim:{hmac_identifier(auth_context.user_id, settings)}", settings.promotion_claim_rate_limit_per_minute):
        return {"data": {"accepted": False, "reason": "rate_limited"}}

    background_tasks.add_task(promotion_queue().publish, {
        "event_kind": "claim",
        "event_id": f"promotion-claim-event-{uuid4().hex}",
        "claim_key": f"promotion-claim-{hashlib.sha256(f'{auth_context.user_id}:{payload.claim_key}'.encode()).hexdigest()}",
        "visitor_hmac": hmac_identifier(visitor_cookie, settings),
        "user_id": auth_context.user_id,
        "occurred_at_ms": now_ms(),
    })
    return {"data": {"accepted": True, "pending": True}}


@promotion_router.post("/opt-out")
def opt_out(response: Response) -> dict[str, object]:
    settings = get_settings()
    secure = settings.environment in {"staging", "production"}
    response.set_cookie(OPTOUT_COOKIE, "1", max_age=365 * 86_400, secure=secure, httponly=True, samesite="lax", path="/")
    response.delete_cookie(VISITOR_COOKIE, path="/")
    response.delete_cookie(CLICK_COOKIE, path="/")
    return {"data": {"optedOut": True}}


def record_desktop_download_completion(*, visitor_cookie: str | None, user_id: str | None, artifact: str) -> None:
    """Best-effort response background hook; failures never affect the download."""
    settings = get_settings()
    if not settings.promotion_enabled:
        return
    try:
        safe_artifact = artifact[:180]
        identity = user_id or (hmac_identifier(visitor_cookie, settings) if visitor_cookie else "anonymous")
        promotion_queue().publish({
            "event_kind": "conversion",
            "event_id": f"download-{uuid4().hex}",
            "conversion_type": "download",
            "source_record_id": hashlib.sha256(f"{identity}:{safe_artifact}".encode()).hexdigest(),
            "visitor_hmac": hmac_identifier(visitor_cookie, settings) if visitor_cookie else None,
            "user_id": user_id,
            "occurred_at_ms": now_ms(),
        })
    except Exception:
        return
