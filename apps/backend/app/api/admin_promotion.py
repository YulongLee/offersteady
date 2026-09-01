from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.admin import _client_hashes, _page, _request_id, admin_service, permission
from app.core.config import get_settings
from app.schemas.promotion import (
    PromotionCampaignCreate,
    PromotionCampaignUpdate,
    PromotionChannelCreate,
    PromotionChannelUpdate,
    PromotionCloneRequest,
    PromotionCostCreate,
    PromotionCostReverse,
    PromotionLinkCreate,
    PromotionLinkUpdate,
)
from app.services.admin_service import AdminPrincipal
from app.services.promotion_analytics_job import PromotionAnalyticsJob
from app.services.promotion_repository import ATTRIBUTION_MODELS, PromotionEventQueue, PromotionRepository, now_ms


admin_promotion_router = APIRouter(prefix="/admin/promotion", tags=["admin-promotion"])


@lru_cache(maxsize=1)
def repository() -> PromotionRepository:
    settings = get_settings()
    if not settings.promotion_enabled:
        raise RuntimeError("promotion_center_disabled")
    return PromotionRepository(settings)


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _serialize(value: Any) -> Any:
    if isinstance(value, dict):
        return {_camel(str(key)): _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _call(callback):
    try:
        return callback()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        if str(exc) == "promotion_center_disabled":
            raise HTTPException(status_code=404, detail="Not found") from exc
        raise


def _audit(request: Request, principal: AdminPrincipal, *, action: str, resource_type: str, resource_id: str | None, reason: str | None, details: dict[str, Any] | None = None) -> None:
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(
        principal=principal,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
        request_id=_request_id(request),
        result="success",
        details=details,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    )


def _range(range_key: str, start_ms: int | None, end_ms: int | None) -> tuple[int, int]:
    settings = get_settings()
    timezone_info = ZoneInfo(settings.promotion_reporting_timezone)
    now = datetime.now(timezone_info)
    if range_key == "custom":
        if start_ms is None or end_ms is None or start_ms >= end_ms or end_ms - start_ms > 366 * 86_400_000:
            raise HTTPException(status_code=422, detail="invalid_custom_range")
        return start_ms, end_ms
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_key == "today":
        start, end = today, now
    elif range_key == "yesterday":
        start, end = today - timedelta(days=1), today
    else:
        days = int(range_key[:-1])
        start, end = today - timedelta(days=days - 1), now
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _metadata(*, model: str, start_ms: int, end_ms: int) -> dict[str, Any]:
    settings = get_settings()
    observing = end_ms + settings.promotion_attribution_window_days * 86_400_000 > now_ms()
    return {
        "generatedAtMs": now_ms(),
        "timezone": settings.promotion_reporting_timezone,
        "attributionModel": model,
        "modelVersion": settings.promotion_model_version,
        "coverageStartMs": start_ms,
        "freshness": "current",
        "unattributedCount": 0,
        "cohortState": "observing" if observing else "mature",
        "range": {"startMs": start_ms, "endMs": end_ms},
    }


def _quality_metadata(*, model: str, start_ms: int, end_ms: int, excluded_bots: int = 0) -> dict[str, Any]:
    metadata = _metadata(model=model, start_ms=start_ms, end_ms=end_ms)
    buckets = _call(lambda: repository().attribution_buckets(start_ms=start_ms, end_ms=end_ms, model=model))
    unattributed = next((item for item in buckets if item.get("bucket") == "unattributed"), None)
    metadata["unattributedCount"] = int(unattributed.get("registrations") or 0) if unattributed else 0
    metadata["excludedBots"] = excluded_bots
    return metadata


def _compact_funnel(metrics: dict[str, Any] | None) -> list[dict[str, Any]]:
    values = metrics or {}
    stages = [
        ("visit", "有效访问", int(values.get("unique_visitors") or 0)),
        ("registration", "注册", int(values.get("registrations") or 0)),
        ("download", "下载", int(values.get("downloads") or 0)),
        ("use", "首次使用", int(values.get("activated_users") or 0)),
        ("order", "下单", int(values.get("orders") or 0)),
        ("payment", "支付", int(values.get("paying_users") or 0)),
    ]
    base = stages[0][2]
    previous = base
    result = []
    for key, label, count in stages:
        result.append({
            "key": key,
            "label": label,
            "count": count,
            "stageRate": round(count / previous, 6) if previous else None,
            "cumulativeRate": round(count / base, 6) if base else None,
            "dropOff": max(0, previous - count),
        })
        previous = count
    return result


@admin_promotion_router.get("/channels")
def list_channels(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], include_inactive: bool = True):
    return {"data": {"items": _serialize(_call(lambda: repository().list_channels(include_inactive=include_inactive)))}}


@admin_promotion_router.post("/channels")
def create_channel(payload: PromotionChannelCreate, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.manage"))]):
    row = _call(lambda: repository().create_channel(code=payload.code, name=payload.name, sort_order=payload.sort_order, actor_user_id=principal.user_id))
    _audit(request, principal, action="promotion.channel.create", resource_type="promotion_channel", resource_id=row["channel_id"], reason="create promotion channel", details={"channel_id": row["channel_id"]})
    return {"data": _serialize(row)}


@admin_promotion_router.patch("/channels/{channel_id}")
def update_channel(channel_id: str, payload: PromotionChannelUpdate, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.manage"))]):
    row = _call(lambda: repository().update_channel(channel_id, name=payload.name, sort_order=payload.sort_order, status=payload.status))
    _audit(request, principal, action="promotion.channel.update", resource_type="promotion_channel", resource_id=channel_id, reason=payload.reason, details={"channel_id": channel_id, "status": row["status"]})
    return {"data": _serialize(row)}


@admin_promotion_router.get("/campaigns")
def list_campaigns(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], limit: int = 50, offset: int = 0):
    limit, offset = _page(limit, offset)
    return {"data": {"items": _serialize(_call(lambda: repository().list_campaigns(limit=limit, offset=offset))), "limit": limit, "offset": offset}}


@admin_promotion_router.post("/campaigns")
def create_campaign(payload: PromotionCampaignCreate, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.manage"))]):
    row = _call(lambda: repository().create_campaign(payload.model_dump(), actor_user_id=principal.user_id))
    _audit(request, principal, action="promotion.campaign.create", resource_type="promotion_campaign", resource_id=row["campaign_id"], reason="create promotion campaign", details={"campaign_id": row["campaign_id"], "status": row["status"]})
    return {"data": _serialize(row)}


@admin_promotion_router.get("/campaigns/{campaign_id}")
def campaign_detail(campaign_id: str, principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))]):
    row = _call(lambda: repository().campaign(campaign_id))
    if not row:
        raise HTTPException(status_code=404, detail="promotion_campaign_not_found")
    return {"data": _serialize(row)}


@admin_promotion_router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, payload: PromotionCampaignUpdate, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.manage"))]):
    row = _call(lambda: repository().update_campaign(campaign_id, payload.model_dump(exclude={"reason"})))
    _audit(request, principal, action="promotion.campaign.update", resource_type="promotion_campaign", resource_id=campaign_id, reason=payload.reason, details={"campaign_id": campaign_id, "status": row["status"]})
    return {"data": _serialize(row)}


@admin_promotion_router.get("/links")
def list_links(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], limit: int = 50, offset: int = 0, status: str | None = Query(default=None, pattern="^(active|inactive)$")):
    limit, offset = _page(limit, offset)
    items = _call(lambda: repository().list_links(limit=limit, offset=offset, status=status))
    base_url = get_settings().promotion_public_base_url.rstrip("/")
    return {"data": {"items": [{**_serialize(item), "publicUrl": f"{base_url}/r/{item['slug']}"} for item in items], "limit": limit, "offset": offset}}


@admin_promotion_router.post("/links")
def create_link(payload: PromotionLinkCreate, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.manage"))]):
    row = _call(lambda: repository().create_link(payload.model_dump(), actor_user_id=principal.user_id))
    _audit(request, principal, action="promotion.link.create", resource_type="promotion_link", resource_id=row["link_id"], reason="create promotion link", details={"link_id": row["link_id"], "channel_id": row["channel_id"], "campaign_id": row["campaign_id"]})
    return {"data": {**_serialize(row), "publicUrl": f"{get_settings().promotion_public_base_url.rstrip('/')}/r/{row['slug']}"}}


@admin_promotion_router.put("/links/{link_id}")
def update_link(link_id: str, payload: PromotionLinkUpdate, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.manage"))]):
    row = _call(lambda: repository().update_link(link_id, payload.model_dump(exclude={"reason"})))
    _audit(request, principal, action="promotion.link.update", resource_type="promotion_link", resource_id=link_id, reason=payload.reason, details={"link_id": link_id, "status": row["status"]})
    return {"data": _serialize(row)}


@admin_promotion_router.post("/links/{link_id}/clone")
def clone_link(link_id: str, payload: PromotionCloneRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.manage"))]):
    changes = payload.model_dump(exclude={"reason"}, exclude_unset=True)
    row = _call(lambda: repository().clone_link(link_id, changes, actor_user_id=principal.user_id))
    _audit(request, principal, action="promotion.link.clone", resource_type="promotion_link", resource_id=row["link_id"], reason=payload.reason, details={"link_id": row["link_id"]})
    return {"data": _serialize(row)}


@admin_promotion_router.post("/costs")
def add_cost(payload: PromotionCostCreate, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.cost.manage"))]):
    row = _call(lambda: repository().add_cost(payload.model_dump(), actor_user_id=principal.user_id))
    _audit(request, principal, action="promotion.cost.create", resource_type="promotion_cost", resource_id=row["cost_entry_id"], reason=payload.reason, details={"scope_type": payload.scope_type, "amount_cents": payload.amount_cents})
    return {"data": _serialize(row)}


@admin_promotion_router.get("/costs")
def list_costs(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], limit: int = 50, offset: int = 0):
    limit, offset = _page(limit, offset)
    return {"data": {"items": _serialize(_call(lambda: repository().list_costs(limit=limit, offset=offset))), "limit": limit, "offset": offset}}


@admin_promotion_router.post("/costs/{cost_entry_id}/reverse")
def reverse_cost(cost_entry_id: str, payload: PromotionCostReverse, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("promotion.cost.manage"))]):
    row = _call(lambda: repository().reverse_cost(cost_entry_id, reason=payload.reason, actor_user_id=principal.user_id))
    _audit(request, principal, action="promotion.cost.reverse", resource_type="promotion_cost", resource_id=row["cost_entry_id"], reason=payload.reason, details={"amount_cents": row["amount_cents"]})
    return {"data": _serialize(row)}


def _report_parameters(range_key: str, model: str, start_ms: int | None, end_ms: int | None) -> tuple[int, int]:
    if model not in ATTRIBUTION_MODELS:
        raise HTTPException(status_code=422, detail="unsupported_attribution_model")
    return _range(range_key, start_ms, end_ms)


@admin_promotion_router.get("/overview")
def overview(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], range_key: str = Query(default="30d", alias="range", pattern="^(today|yesterday|7d|30d|90d|custom)$"), model: str = "last_non_direct_touch", start_ms: int | None = None, end_ms: int | None = None):
    start, end = _report_parameters(range_key, model, start_ms, end_ms)
    metrics = _call(lambda: repository().overview(start_ms=start, end_ms=end, model=model))
    return {"data": {"metrics": metrics, "metadata": _quality_metadata(model=model, start_ms=start, end_ms=end, excluded_bots=int(metrics.get("excludedBots") or 0))}}


@admin_promotion_router.get("/reports/{dimension}")
def dimension_report(dimension: str, principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], range_key: str = Query(default="30d", alias="range", pattern="^(today|yesterday|7d|30d|90d|custom)$"), model: str = "last_non_direct_touch", start_ms: int | None = None, end_ms: int | None = None, limit: int = 100, offset: int = 0):
    start, end = _report_parameters(range_key, model, start_ms, end_ms)
    items = _call(lambda: repository().dimension_report(start_ms=start, end_ms=end, model=model, dimension=dimension))
    limit, offset = _page(limit, offset)
    return {"data": {"items": _serialize(items[offset:offset + limit]), "total": len(items), "limit": limit, "offset": offset, "metadata": _quality_metadata(model=model, start_ms=start, end_ms=end)}}


@admin_promotion_router.get("/trends")
def promotion_trends(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], range_key: str = Query(default="30d", alias="range", pattern="^(7d|30d|90d|custom)$"), model: str = "last_non_direct_touch", start_ms: int | None = None, end_ms: int | None = None):
    start, end = _report_parameters(range_key, model, start_ms, end_ms)
    items = _call(lambda: repository().snapshot_trend(start_ms=start, end_ms=end, model=model))
    return {"data": {"items": _serialize(items), "metadata": _quality_metadata(model=model, start_ms=start, end_ms=end)}}


@admin_promotion_router.get("/campaigns/{campaign_id}/report")
def campaign_report(campaign_id: str, principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], range_key: str = Query(default="30d", alias="range", pattern="^(today|yesterday|7d|30d|90d|custom)$"), model: str = "last_non_direct_touch", start_ms: int | None = None, end_ms: int | None = None):
    start, end = _report_parameters(range_key, model, start_ms, end_ms)
    campaign = _call(lambda: repository().campaign(campaign_id))
    if not campaign:
        raise HTTPException(status_code=404, detail="promotion_campaign_not_found")
    report = _call(lambda: repository().dimension_report(start_ms=start, end_ms=end, model=model, dimension="campaign"))
    metrics = next((item for item in report if str(item["dimension_id"]) == campaign_id), None)
    trend = _call(lambda: repository().snapshot_trend(start_ms=start, end_ms=end, model=model, dimension_type="campaign", dimension_id=campaign_id))
    return {"data": {"campaign": _serialize(campaign), "metrics": _serialize(metrics), "trend": _serialize(trend), "funnel": _compact_funnel(metrics), "metadata": _quality_metadata(model=model, start_ms=start, end_ms=end)}}


@admin_promotion_router.get("/funnel")
def funnel(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))], range_key: str = Query(default="30d", alias="range", pattern="^(today|yesterday|7d|30d|90d|custom)$"), model: str = "last_non_direct_touch", start_ms: int | None = None, end_ms: int | None = None):
    start, end = _report_parameters(range_key, model, start_ms, end_ms)
    data = _call(lambda: repository().funnel(start_ms=start, end_ms=end, model=model))
    return {"data": {**data, "metadata": _quality_metadata(model=model, start_ms=start, end_ms=end)}}


@admin_promotion_router.get("/health")
def health(principal: Annotated[AdminPrincipal, Depends(permission("promotion.read"))]):
    return {"data": _serialize({
        **_call(lambda: repository().health()),
        "queue": PromotionEventQueue(get_settings()).health(),
    })}
