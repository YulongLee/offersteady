from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.deps import creem_provider, global_checkout_service, global_commerce_service, global_creem_configuration_service, require_authenticated_context, settings_dependency
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.services.global_commerce_service import GlobalCommerceService, GlobalCommerceUnavailable
from app.services.global_checkout_service import GlobalCheckoutNotReady, GlobalCheckoutService, GlobalCheckoutValidationError
from app.services.creem_provider import CreemProvider, CreemRequestError
from app.services.global_creem_configuration_service import GlobalCreemConfigurationService


router = APIRouter(prefix="/global-commerce", tags=["global-commerce"])
descriptor = ModuleDescriptor(feature="global-commerce", owningApp="apps/backend", routePrefix="/api/v1/global-commerce", mode="active", notes="Global-only catalogue and entitlement state.")


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    offer_code: str = Field(min_length=3, max_length=64, alias="offerCode")
    idempotency_key: str = Field(min_length=8, max_length=128, alias="idempotencyKey")


def _plan_payload(plan) -> dict[str, object]:
    return {
        "offerCode": plan.offer_code, "version": plan.version, "displayName": plan.display_name,
        "description": plan.description, "currency": plan.currency, "priceCents": plan.price_cents,
        "billingMode": plan.billing_mode, "durationDays": plan.duration_days,
        "benefits": {"copilotMinutes": plan.copilot_minutes, "screenAssistUses": plan.screen_assist_uses,
                     "resumeAndJobDescription": plan.resume_jd_enabled, "knowledgeBase": plan.knowledge_base_enabled,
                     "writtenExam": plan.written_exam_enabled, "fullProduct": plan.full_product_enabled},
        "published": plan.status == "active", "featured": plan.featured,
        "displayOrder": plan.display_order, "createdAtMs": plan.created_at_ms,
    }


def _require_global(settings: Settings) -> None:
    if settings.product_edition != "global":
        raise HTTPException(status_code=404, detail="Global commerce is not available for this product edition")


@router.get("/catalogue", response_model=ApiEnvelope[dict[str, object]])
async def catalogue(request: Request, service: GlobalCommerceService = Depends(global_commerce_service), settings: Settings = Depends(settings_dependency)) -> ApiEnvelope[dict[str, object]]:
    _require_global(settings)
    return success_response(request=request, data={"plans": [_plan_payload(plan) for plan in service.catalogue()]}, timestamp=utc_now_iso())


@router.get("/state", response_model=ApiEnvelope[dict[str, object]])
async def state(request: Request, auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context), service: GlobalCommerceService = Depends(global_commerce_service), settings: Settings = Depends(settings_dependency)) -> ApiEnvelope[dict[str, object]]:
    _require_global(settings)
    resolved = service.state(auth_context.user_id)
    provider_activated = bool(service.repository.provider_config(settings.global_commerce_provider_mode).get("enabled"))
    resolved.update({
        "enabled": settings.global_commerce_enabled and provider_activated,
        "provider": "creem" if settings.global_commerce_enabled and provider_activated else "none",
        "mode": settings.global_commerce_provider_mode,
        "plans": [_plan_payload(plan) for plan in service.catalogue()],
        "fairUsePolicyUrl": settings.global_fair_use_policy_url or "",
        "refundPolicyUrl": settings.global_refund_policy_url or "",
        "termsUrl": settings.global_terms_url or "",
        "privacyUrl": settings.global_privacy_url or "",
        "supportEmail": settings.support_email,
    })
    return success_response(request=request, data=resolved, timestamp=utc_now_iso())


@router.get("/readiness", response_model=ApiEnvelope[dict[str, object]])
async def readiness(request: Request, settings: Settings = Depends(settings_dependency), service: GlobalCommerceService = Depends(global_commerce_service), configuration: GlobalCreemConfigurationService = Depends(global_creem_configuration_service)) -> ApiEnvelope[dict[str, object]]:
    _require_global(settings)
    mode = settings.global_commerce_provider_mode
    credentials = configuration.effective_credentials(mode)
    public_base = settings.public_web_base_url.rstrip("/")
    checkout_success_url = settings.creem_checkout_success_url or (f"{public_base}/billing/success" if public_base else "")
    legal_urls = (
        settings.global_terms_url or f"{public_base}/terms",
        settings.global_privacy_url or f"{public_base}/privacy",
        settings.global_refund_policy_url or f"{public_base}/refund-policy",
        settings.global_fair_use_policy_url or f"{public_base}/terms",
    )
    blockers: list[str] = []
    if not credentials.api_key: blockers.append("api_key_missing")
    if not credentials.webhook_secret: blockers.append("webhook_secret_missing")
    if not checkout_success_url: blockers.append("checkout_success_url_missing")
    if not public_base or not all(legal_urls): blockers.append("legal_links_missing")
    mappings_ready = all(
        (mapping := service.repository.provider_mapping(mode, plan.offer_code)) is not None
        and mapping.validation_status == "ready" and mapping.plan_version == plan.version
        for plan in service.catalogue() if plan.billing_mode != "free"
    )
    if not mappings_ready: blockers.append("product_mappings_missing")
    provider_activated = bool(service.repository.provider_config(mode).get("enabled"))
    webhook_url = f"{public_base}/api/v1/global-commerce/webhooks/creem" if public_base else ""
    webhook_accepted = any(event.get("status") in {"processed", "ignored"} for event in service.repository.recent_provider_events(mode=mode, limit=100))
    data = {"edition": "global", "mode": mode, "enabled": settings.global_commerce_enabled,
            "ready": settings.global_commerce_enabled and provider_activated and not blockers, "apiKeyConfigured": bool(credentials.api_key),
            "webhookSecretConfigured": bool(credentials.webhook_secret), "webhookUrlConfigured": bool(webhook_url),
            "legalLinksConfigured": "legal_links_missing" not in blockers, "mappingsReady": mappings_ready,
            "webhookAccepted": webhook_accepted, "checkoutSuccessUrl": checkout_success_url,
            "webhookUrl": webhook_url, "blockers": blockers}
    return success_response(request=request, data=data, timestamp=utc_now_iso())


@router.post("/checkout", response_model=ApiEnvelope[dict[str, object]])
async def checkout(payload: CheckoutRequest, request: Request, auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context), service: GlobalCheckoutService = Depends(global_checkout_service), settings: Settings = Depends(settings_dependency)) -> ApiEnvelope[dict[str, object]]:
    _require_global(settings)
    customer_email = auth_context.login_id.removeprefix("email:") if auth_context.login_id.startswith("email:") else None
    try:
        order = service.create_checkout(user_id=auth_context.user_id, customer_email=customer_email, offer_code=payload.offer_code, idempotency_key=payload.idempotency_key)
    except GlobalCheckoutValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except GlobalCheckoutNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return success_response(request=request, data={"id": order.order_id, "status": order.status, "checkoutUrl": order.checkout_url, "offerCode": order.offer_code, "amountCents": order.expected_amount_cents, "currency": order.expected_currency}, timestamp=utc_now_iso())


@router.get("/orders/{order_id}", response_model=ApiEnvelope[dict[str, object]])
async def order_state(order_id: str, request: Request, auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context), service: GlobalCheckoutService = Depends(global_checkout_service), settings: Settings = Depends(settings_dependency)) -> ApiEnvelope[dict[str, object]]:
    _require_global(settings)
    order = service.repository.order(order_id)
    if order is None or order.user_id != auth_context.user_id:
        raise HTTPException(status_code=404, detail="Order not found")
    return success_response(request=request, data={"id": order.order_id, "status": order.status, "offerCode": order.offer_code, "amountCents": order.expected_amount_cents, "currency": order.expected_currency, "updatedAtMs": order.updated_at_ms}, timestamp=utc_now_iso())


@router.post("/customer-portal", response_model=ApiEnvelope[dict[str, str]])
async def customer_portal(request: Request, auth_context: AuthenticatedRequestContext = Depends(require_authenticated_context), checkout_service: GlobalCheckoutService = Depends(global_checkout_service), provider: CreemProvider = Depends(creem_provider), settings: Settings = Depends(settings_dependency)) -> ApiEnvelope[dict[str, str]]:
    _require_global(settings)
    source = next((order for order in checkout_service.repository.orders_for_user(auth_context.user_id) if order.provider_customer_id), None)
    if source is None or source.provider_customer_id is None:
        raise HTTPException(status_code=404, detail="No billing profile is available for this account")
    try:
        portal_url = provider.create_customer_portal(source.provider_customer_id)
    except (CreemRequestError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Billing management is temporarily unavailable") from exc
    if not portal_url.startswith("https://"):
        raise HTTPException(status_code=502, detail="Provider returned an invalid billing portal URL")
    return success_response(request=request, data={"portalUrl": portal_url}, timestamp=utc_now_iso())


@router.post("/webhooks/creem")
async def creem_webhook(request: Request, creem_signature: str | None = Header(default=None, alias="creem-signature"), provider: CreemProvider = Depends(creem_provider), service: GlobalCheckoutService = Depends(global_checkout_service), settings: Settings = Depends(settings_dependency)):
    _require_global(settings)
    raw_body = await request.body()
    try:
        payload = provider.verify_webhook(raw_body, creem_signature)
        return service.process_verified_event(payload, raw_body)
    except CreemRequestError as exc:
        raise HTTPException(status_code=401, detail=exc.safe_code) from exc
    except GlobalCheckoutValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
