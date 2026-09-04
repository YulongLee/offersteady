from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.config import get_settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import require_authenticated_context
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.foundation import ModuleDescriptor
from app.schemas.promotion import PartnerJoinRequest, PartnerPayoutProfileUpsert
from app.services.partner_program import PartnerProgramRepository


router = APIRouter(prefix="/partner-program", tags=["partner-program"])
descriptor = ModuleDescriptor(
    feature="partner-program",
    owningApp="apps/backend",
    routePrefix="/api/v1/partner-program",
    mode="active",
    notes="First-level partner enrollment, aggregate performance, and manual monthly settlement.",
)


@lru_cache(maxsize=1)
def repository() -> PartnerProgramRepository:
    settings = get_settings()
    if not settings.partner_program_enabled:
        raise RuntimeError("partner_program_disabled")
    if not settings.promotion_enabled:
        raise RuntimeError("partner_program_requires_promotion")
    return PartnerProgramRepository(settings)


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _serialize(value: Any) -> Any:
    if isinstance(value, dict):
        return {_camel(str(key)): _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def _activity_settings() -> dict[str, object]:
    settings = get_settings()
    if not settings.partner_program_enabled or not settings.promotion_enabled:
        return {"enabled": False, "config_version": 0, "updated_at_ms": 0}
    return _call(lambda: repository().activity_settings())


def _settings_payload(activity: dict[str, object] | None = None) -> dict[str, object]:
    settings = get_settings()
    runtime = activity or _activity_settings()
    return {
        "enabled": bool(runtime.get("enabled")),
        "configVersion": int(runtime.get("config_version") or 0),
        "updatedAtMs": int(runtime.get("updated_at_ms") or 0),
        "commissionRateBps": settings.partner_commission_rate_bps,
        "eligibleOrderDays": settings.partner_eligible_order_days,
        "refundHoldDays": settings.partner_refund_hold_days,
        "minimumPayoutCents": settings.partner_minimum_payout_cents,
        "agreementVersion": settings.partner_agreement_version,
        "settlementMode": "manual-monthly",
        "payoutProfileEnabled": settings.partner_payout_profile_enabled,
    }


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
        if str(exc) in {"partner_program_disabled", "partner_program_requires_promotion", "partner_payout_profile_disabled"}:
            raise HTTPException(status_code=404, detail="Not found") from exc
        if str(exc) in {"partner_payout_encryption_key_missing", "partner_payout_profile_decryption_failed"}:
            raise HTTPException(status_code=503, detail="partner_payout_profile_unavailable") from exc
        raise


@router.get("/config")
def partner_config(request: Request):
    return success_response(request=request, data=_settings_payload(), timestamp=utc_now_iso())


@router.get("/me")
def partner_status(request: Request, response: Response,
                   auth: AuthenticatedRequestContext = Depends(require_authenticated_context)):
    settings = get_settings()
    activity = _activity_settings()
    config = _settings_payload(activity)
    if not settings.partner_program_enabled or not bool(activity.get("enabled")):
        return success_response(request=request, data={"joined": False, "config": config}, timestamp=utc_now_iso())
    repo = _call(repository)
    profile = _call(lambda: repo.profile(user_id=auth.user_id))
    data = {"joined": False, "config": config} if not profile else {
        "joined": True,
        "config": config,
        **_serialize(_call(lambda: repo.dashboard(user_id=auth.user_id))),
    }
    if profile:
        data["shareUrl"] = f"{settings.resolved_promotion_public_base_url}/r/{profile['slug']}"
    if settings.partner_payout_profile_enabled:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return success_response(request=request, data=data, timestamp=utc_now_iso())


@router.post("/join")
def join_partner(payload: PartnerJoinRequest, request: Request, auth: AuthenticatedRequestContext = Depends(require_authenticated_context)):
    settings = get_settings()
    if not bool(_activity_settings().get("enabled")):
        raise HTTPException(status_code=404, detail="Not found")
    if not payload.agreement_accepted or payload.agreement_version != settings.partner_agreement_version:
        raise HTTPException(status_code=422, detail="current_partner_agreement_must_be_accepted")
    profile = _call(lambda: repository().join(user_id=auth.user_id, agreement_version=payload.agreement_version))
    dashboard = _serialize(_call(lambda: repository().dashboard(user_id=auth.user_id)))
    return success_response(request=request, data={
        "joined": True,
        **dashboard,
        "shareUrl": f"{settings.resolved_promotion_public_base_url}/r/{profile['slug']}",
        "config": _settings_payload(),
    }, timestamp=utc_now_iso())


@router.post("/payout-requests")
def request_payout(request: Request, auth: AuthenticatedRequestContext = Depends(require_authenticated_context)):
    payout = _call(lambda: repository().request_payout(user_id=auth.user_id))
    return success_response(request=request, data=_serialize(payout), timestamp=utc_now_iso())


@router.put("/payout-profile")
def save_payout_profile(payload: PartnerPayoutProfileUpsert, request: Request, response: Response,
                        auth: AuthenticatedRequestContext = Depends(require_authenticated_context)):
    row = _call(lambda: repository().save_payout_profile(
        user_id=auth.user_id,
        payout_method=payload.payout_method,
        account_name=payload.account_name,
        account_identifier=payload.account_identifier,
    ))
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return success_response(request=request, data=_serialize(row), timestamp=utc_now_iso())
