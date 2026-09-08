from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from time import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.admin import _client_hashes, _confirmed, _request_id, admin_service, permission
from app.core.config import Settings, get_settings
from app.deps import global_checkout_service, global_commerce_service, global_creem_configuration_service
from app.ports.global_commerce import FairUseDecision, GlobalPlan, GlobalProductMapping
from app.services.creem_provider import CreemProvider, CreemRequestError
from app.services.admin_service import AdminPrincipal
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_checkout_service import GlobalCheckoutService, GlobalCheckoutValidationError
from app.services.global_creem_configuration_service import CreemMode, GlobalCreemConfigurationService


admin_global_commerce_router = APIRouter(prefix="/admin/global-commerce", tags=["admin-global-commerce"])


class PlanDraftRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    offer_code: Literal["global-free", "global-interview-pass", "global-pro-weekly", "global-pro-monthly", "global-job-hunt"] = Field(alias="offerCode")
    display_name: str = Field(min_length=2, max_length=80, alias="displayName")
    description: str = Field(min_length=2, max_length=300)
    price_cents: int = Field(ge=0, alias="priceCents")
    duration_days: int | None = Field(default=None, ge=1, le=366, alias="durationDays")
    copilot_minutes: int | None = Field(default=None, ge=1, alias="copilotMinutes")
    screen_assist_uses: int | None = Field(default=None, ge=1, alias="screenAssistUses")
    resume_jd_enabled: bool = Field(alias="resumeJdEnabled")
    knowledge_base_enabled: bool = Field(alias="knowledgeBaseEnabled")
    written_exam_enabled: bool = Field(alias="writtenExamEnabled")
    full_product_enabled: bool = Field(alias="fullProductEnabled")
    featured: bool = False
    display_order: int = Field(ge=0, alias="displayOrder")
    reason: str = Field(min_length=3, max_length=500)


class PublishRequest(BaseModel):
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


class ProductMappingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    provider_product_id: str = Field(min_length=6, max_length=160, alias="providerProductId")
    reason: str = Field(min_length=3, max_length=500)


class ProviderCredentialRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    api_key: str | None = Field(default=None, max_length=500, alias="apiKey")
    webhook_secret: str | None = Field(default=None, max_length=500, alias="webhookSecret")
    reason: str = Field(min_length=3, max_length=500)


class ProviderActivationRequest(BaseModel):
    enabled: bool
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


class ReconcileOrderRequest(BaseModel):
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


class FairUseReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user_id: str = Field(min_length=3, max_length=160, alias="userId")
    action: Literal["restrict", "clear"]
    reason_code: str = Field(min_length=3, max_length=80, alias="reasonCode")
    expires_at_ms: int | None = Field(default=None, alias="expiresAtMs")
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


class MemberGrantRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    offer_code: Literal["global-interview-pass", "global-pro-weekly", "global-pro-monthly", "global-job-hunt"] = Field(alias="offerCode")
    idempotency_key: str = Field(min_length=8, max_length=160, alias="idempotencyKey")
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


class MemberRevokeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    idempotency_key: str = Field(min_length=8, max_length=160, alias="idempotencyKey")
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


def _guard_global(settings: Settings) -> None:
    if settings.product_edition != "global":
        raise HTTPException(status_code=404, detail="Not found")


def _fingerprint(secret: str | None) -> str | None:
    return sha256(secret.encode()).hexdigest()[:12] if secret else None


def _plan(plan: GlobalPlan) -> dict[str, object]:
    return {**plan.purchased_snapshot(), "status": plan.status, "featured": plan.featured, "displayOrder": plan.display_order, "createdAtMs": plan.created_at_ms}


def _public_id(value: str | None) -> str | None:
    return sha256(value.encode()).hexdigest()[:12] if value else None


def _order_row(order) -> dict[str, object]:
    return {"id": order.order_id, "userFingerprint": _public_id(order.user_id), "offerCode": order.offer_code,
            "planVersion": order.plan_version, "status": order.status, "amountCents": order.expected_amount_cents,
            "currency": order.expected_currency, "providerCheckoutId": order.provider_checkout_id, "providerOrderId": order.provider_order_id,
            "providerSubscriptionId": order.provider_subscription_id, "createdAtMs": order.created_at_ms,
            "updatedAtMs": order.updated_at_ms}


def _subscription_row(item) -> dict[str, object]:
    return {"id": item.subscription_id, "userFingerprint": _public_id(item.user_id), "offerCode": item.offer_code,
            "status": item.status, "providerSubscriptionId": item.provider_subscription_id,
            "currentPeriodStartMs": item.current_period_start_ms, "currentPeriodEndMs": item.current_period_end_ms,
            "updatedAtMs": item.updated_at_ms}


def _entitlement_row(item) -> dict[str, object]:
    return {"id": item.entitlement_id, "offerCode": item.offer_code, "planVersion": item.plan_version,
            "sourceKind": item.source_kind, "status": item.status, "startsAtMs": item.starts_at_ms,
            "endsAtMs": item.ends_at_ms, "copilotMinutesGranted": item.copilot_minutes_granted,
            "copilotMinutesUsed": item.copilot_minutes_used, "screenAssistUsesGranted": item.screen_assist_uses_granted,
            "screenAssistUsesUsed": item.screen_assist_uses_used, "resumeJdEnabled": item.resume_jd_enabled,
            "knowledgeBaseEnabled": item.knowledge_base_enabled, "writtenExamEnabled": item.written_exam_enabled,
            "fullProductEnabled": item.full_product_enabled}


def _provider_product(product) -> dict[str, object]:
    return {"id": product.product_id, "name": product.name, "priceCents": product.amount_cents,
            "currency": product.currency, "billingMode": product.billing_mode,
            "billingPeriod": product.billing_period, "status": product.status, "mode": product.mode}


def _provider_for_mode(configuration: GlobalCreemConfigurationService, mode: CreemMode) -> CreemProvider:
    return CreemProvider(configuration.configured_settings(mode), mode=mode)


@admin_global_commerce_router.get("/overview")
def overview(principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], mode: CreemMode = Query(default="test"), service: GlobalCommerceService = Depends(global_commerce_service), configuration: GlobalCreemConfigurationService = Depends(global_creem_configuration_service)):
    settings = get_settings()
    _guard_global(settings)
    credentials = configuration.effective_credentials(mode)
    public_base = settings.public_web_base_url.rstrip("/")
    checkout_success_url = settings.creem_checkout_success_url or (f"{public_base}/billing/success" if public_base else "")
    webhook_url = f"{public_base}/api/v1/global-commerce/webhooks/creem" if public_base else ""
    legal_urls = (
        settings.global_terms_url or f"{public_base}/terms",
        settings.global_privacy_url or f"{public_base}/privacy",
        settings.global_refund_policy_url or f"{public_base}/refund-policy",
        settings.global_fair_use_policy_url or f"{public_base}/terms",
    )
    blockers = [name for name, ok in {
        "Creem API Key 未配置": credentials.api_key, "Webhook Secret 未配置": credentials.webhook_secret,
        "支付成功返回地址未配置": checkout_success_url,
        "Webhook 地址未配置": webhook_url,
        "条款链接未配置": all(legal_urls),
    }.items() if not ok]
    mappings = []
    for plan in service.catalogue():
        if plan.billing_mode == "free": continue
        mapping = service.repository.provider_mapping(mode, plan.offer_code)
        mappings.append({"offerCode": plan.offer_code, "displayName": plan.display_name,
                         "priceCents": plan.price_cents, "currency": plan.currency,
                         "billingMode": plan.billing_mode, "planVersion": plan.version,
                         "providerProductId": mapping.provider_product_id if mapping else None,
                         "validationStatus": mapping.validation_status if mapping else "missing",
                         "validatedAmountCents": mapping.validated_amount_cents if mapping else None,
                         "validatedCurrency": mapping.validated_currency if mapping else None,
                         "validatedBillingMode": mapping.validated_billing_mode if mapping else None})
        if mapping is None or mapping.validation_status != "ready" or mapping.plan_version != plan.version:
            blockers.append(f"{plan.display_name} 的 Creem Product 映射未通过")
    provider_config = service.repository.provider_config(mode)
    orders = [item for item in service.repository.recent_orders(limit=500) if item.mode == mode]
    paid = [item for item in orders if item.status == "paid"]
    gross_cents = sum(item.expected_amount_cents for item in paid)
    estimated_provider_fee_cents = sum(round(item.expected_amount_cents * 0.039) + 40 for item in paid)
    return {"data": {"edition": "global", "mode": mode, "runtimeMode": settings.global_commerce_provider_mode,
                     "masterSwitchEnabled": settings.global_commerce_enabled,
                     "providerActivated": bool(provider_config.get("enabled")),
                     "ready": mode == settings.global_commerce_provider_mode and settings.global_commerce_enabled and bool(provider_config.get("enabled")) and not blockers,
                     "configurationReady": not blockers, "blockers": blockers,
                     "credentials": configuration.masked(mode),
                     "urls": {"checkoutSuccessUrl": checkout_success_url, "webhookUrl": webhook_url,
                              "termsUrl": legal_urls[0], "privacyUrl": legal_urls[1],
                              "refundPolicyUrl": legal_urls[2], "fairUsePolicyUrl": legal_urls[3]},
                     "plans": [_plan(plan) for plan in service.catalogue()], "mappings": mappings,
                     "metrics": {"paidOrders": len(paid), "grossRevenueCents": gross_cents,
                                 "estimatedProviderFeeCents": estimated_provider_fee_cents,
                                 "estimatedNetBeforeServiceCostCents": gross_cents-estimated_provider_fee_cents,
                                 "refunds": sum(item.status == "refunded" for item in orders),
                                 "disputes": sum(item.status == "disputed" for item in orders)}}}


@admin_global_commerce_router.put("/credentials")
def save_credentials(payload: ProviderCredentialRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], mode: CreemMode = Query(default="test"), configuration: GlobalCreemConfigurationService = Depends(global_creem_configuration_service)):
    settings = get_settings()
    _guard_global(settings)
    if not (payload.api_key or "").strip() and not (payload.webhook_secret or "").strip():
        raise HTTPException(status_code=422, detail="请至少填写一项需要更新的密钥")
    try:
        configuration.save(mode=mode, api_key=payload.api_key, webhook_secret=payload.webhook_secret, user_id=principal.user_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.credentials.replace", resource_type="global_provider_config", resource_id=mode, reason=payload.reason, request_id=_request_id(request), result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"mode": mode, "api_key_replaced": bool((payload.api_key or "").strip()), "webhook_secret_replaced": bool((payload.webhook_secret or "").strip())})
    return {"data": {"mode": mode, "credentials": configuration.masked(mode), "providerActivated": False}}


@admin_global_commerce_router.get("/products")
def list_provider_products(request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], mode: CreemMode = Query(default="test"), service: GlobalCommerceService = Depends(global_commerce_service), configuration: GlobalCreemConfigurationService = Depends(global_creem_configuration_service)):
    settings = get_settings()
    _guard_global(settings)
    now = int(time() * 1000)
    try:
        products = _provider_for_mode(configuration, mode).list_products()
        wrong_mode = [product for product in products if product.mode and product.mode != mode]
        if wrong_mode:
            raise CreemRequestError("provider_environment_mismatch")
        service.repository.mark_provider_connection_checked(mode=mode, checked_at_ms=now, validation_status="draft", validation_errors=[])
    except (CreemRequestError, RuntimeError) as exc:
        service.repository.mark_provider_connection_checked(mode=mode, checked_at_ms=now, validation_status="error", validation_errors=["Creem 连接或商品读取失败"])
        raise HTTPException(status_code=409, detail="无法读取当前环境的 Creem 商品，请检查所选环境和 API Key") from exc
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.products.sync", resource_type="global_provider_config", resource_id=mode, reason="同步 Creem 商品", request_id=_request_id(request), result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"mode": mode, "product_count": len(products)})
    return {"data": {"mode": mode, "items": [_provider_product(product) for product in products], "syncedAtMs": now}}


@admin_global_commerce_router.get("/operations")
def operations(principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], mode: CreemMode = Query(default="test"), service: GlobalCommerceService = Depends(global_commerce_service)):
    settings = get_settings()
    _guard_global(settings)
    events = service.repository.recent_provider_events(mode=mode, limit=100)
    safe_events = [{key: value for key, value in item.items() if key not in {"payload_sha256"}} for item in events]
    fair_use = service.repository.recent_fair_use_decisions(limit=100)
    return {"data": {"orders": [_order_row(item) for item in service.repository.recent_orders(limit=100) if item.mode == mode],
                     "subscriptions": [_subscription_row(item) for item in service.repository.recent_subscriptions(limit=100) if item.mode == mode],
                     "events": safe_events,
                     "fairUseDecisions": [{"id": item.decision_id, "userFingerprint": _public_id(item.user_id), "status": item.status,
                                            "reasonCode": item.reason_code, "restrictNewSessions": item.restrict_new_sessions,
                                            "effectiveAtMs": item.effective_at_ms, "expiresAtMs": item.expires_at_ms} for item in fair_use]}}


@admin_global_commerce_router.get("/members")
def list_members(
    principal: Annotated[AdminPrincipal, Depends(permission("users.read"))],
    search: str = Query(default="", max_length=160),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    _guard_global(get_settings())
    items = admin_service().repository.list_global_members(search=search, limit=limit, offset=offset)
    return {"data": {"items": items, "limit": limit, "offset": offset}}


@admin_global_commerce_router.get("/members/{user_id}")
def member_detail(
    user_id: str,
    principal: Annotated[AdminPrincipal, Depends(permission("users.read"))],
    service: GlobalCommerceService = Depends(global_commerce_service),
):
    _guard_global(get_settings())
    identity = admin_service().repository.global_member_identity(user_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="国际版用户不存在")
    state = service.state(user_id)
    all_entitlements = service.repository.entitlements_for_user(user_id)
    return {"data": {"identity": identity, "state": state,
                     "entitlements": [_entitlement_row(item) for item in all_entitlements],
                     "orders": [_order_row(item) for item in service.repository.orders_for_user(user_id)],
                     "subscriptions": [_subscription_row(item) for item in service.repository.subscriptions_for_user(user_id)]}}


@admin_global_commerce_router.post("/members/{user_id}/grants")
def grant_member_plan(
    user_id: str,
    payload: MemberGrantRequest,
    request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))],
    service: GlobalCommerceService = Depends(global_commerce_service),
):
    _guard_global(get_settings())
    _confirmed(payload.confirmed)
    repository = admin_service().repository
    if repository.global_member_identity(user_id) is None:
        raise HTTPException(status_code=404, detail="国际版用户不存在")
    replay = repository.idempotent_result(actor_user_id=principal.user_id, action="global_member.grant", key=payload.idempotency_key)
    if replay is not None:
        return {"data": replay}
    now = int(time() * 1000)
    entitlement = service.grant_purchase(user_id=user_id, offer_code=payload.offer_code,
                                         source_kind="admin", source_id=f"admin:{principal.user_id}:{payload.idempotency_key}",
                                         starts_at_ms=now)
    result = _entitlement_row(entitlement)
    repository.save_idempotent_result(actor_user_id=principal.user_id, action="global_member.grant", key=payload.idempotency_key, result=result)
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.member.grant", resource_type="global_entitlement",
                          resource_id=entitlement.entitlement_id, reason=payload.reason, request_id=_request_id(request),
                          result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash,
                          details={"offer_code": entitlement.offer_code, "plan_version": entitlement.plan_version,
                                   "entitlement_id": entitlement.entitlement_id, "source_kind": "admin"})
    return {"data": result}


@admin_global_commerce_router.post("/members/{user_id}/entitlements/{entitlement_id}/revoke")
def revoke_member_entitlement(
    user_id: str,
    entitlement_id: str,
    payload: MemberRevokeRequest,
    request: Request,
    principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))],
    service: GlobalCommerceService = Depends(global_commerce_service),
):
    _guard_global(get_settings())
    _confirmed(payload.confirmed)
    repository = admin_service().repository
    replay = repository.idempotent_result(actor_user_id=principal.user_id, action="global_member.revoke", key=payload.idempotency_key)
    if replay is not None:
        return {"data": replay}
    entitlement = next((item for item in service.repository.entitlements_for_user(user_id) if item.entitlement_id == entitlement_id), None)
    if entitlement is None:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    if entitlement.source_kind == "free_grant":
        raise HTTPException(status_code=422, detail="Free 初始权益不可人工撤销")
    if entitlement.status == "revoked":
        result = _entitlement_row(entitlement)
    else:
        result = _entitlement_row(service.repository.update_entitlement(replace(entitlement, status="revoked")))
    repository.save_idempotent_result(actor_user_id=principal.user_id, action="global_member.revoke", key=payload.idempotency_key, result=result)
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.member.revoke", resource_type="global_entitlement",
                          resource_id=entitlement_id, reason=payload.reason, request_id=_request_id(request),
                          result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash,
                          details={"offer_code": entitlement.offer_code, "plan_version": entitlement.plan_version,
                                   "entitlement_id": entitlement_id, "source_kind": entitlement.source_kind})
    return {"data": result}


@admin_global_commerce_router.post("/orders/{order_id}/reconcile")
def reconcile_order(order_id: str, payload: ReconcileOrderRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], service: GlobalCheckoutService = Depends(global_checkout_service)):
    _guard_global(get_settings())
    _confirmed(payload.confirmed)
    try:
        order = service.reconcile_order(order_id)
    except (GlobalCheckoutValidationError, CreemRequestError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail="订单对账失败，请核对当前环境与 Creem 订单状态") from exc
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.order.reconcile", resource_type="global_order", resource_id=order.order_id, reason=payload.reason, request_id=_request_id(request), result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"status": order.status, "offer_code": order.offer_code})
    return {"data": _order_row(order)}


@admin_global_commerce_router.post("/fair-use/review")
def review_fair_use(payload: FairUseReviewRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], service: GlobalCommerceService = Depends(global_commerce_service)):
    _guard_global(get_settings())
    _confirmed(payload.confirmed)
    now = int(time() * 1000)
    existing = service.repository.active_fair_use_decision(payload.user_id, now)
    if payload.action == "clear" and existing is None:
        raise HTTPException(status_code=404, detail="该账号没有待解除的 Fair Use 决定")
    if payload.action == "restrict":
        decision = FairUseDecision(f"fair_{sha256(f'{payload.user_id}:{now}'.encode()).hexdigest()[:24]}", payload.user_id, "restricted", payload.reason_code, {"source": "manual_support_review"}, True, now, payload.expires_at_ms)
    else:
        decision = FairUseDecision(existing.decision_id, existing.user_id, "cleared", payload.reason_code, {**existing.evidence, "cleared_by_support": True}, False, existing.effective_at_ms, existing.expires_at_ms)
    stored = service.repository.save_fair_use_decision(decision)
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action=f"global_commerce.fair_use.{payload.action}", resource_type="global_fair_use_decision", resource_id=stored.decision_id, reason=payload.reason, request_id=_request_id(request), result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"user_fingerprint": _public_id(payload.user_id), "reason_code": payload.reason_code})
    return {"data": {"id": stored.decision_id, "status": stored.status, "userFingerprint": _public_id(stored.user_id)}}


@admin_global_commerce_router.post("/plans/drafts")
def create_plan_draft(payload: PlanDraftRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], service: GlobalCommerceService = Depends(global_commerce_service)):
    settings = get_settings()
    _guard_global(settings)
    current = service.repository.plan(payload.offer_code)
    if current is None:
        raise HTTPException(status_code=404, detail="套餐不存在")
    billing_mode = "free" if payload.offer_code == "global-free" else "recurring" if payload.offer_code == "global-pro-monthly" else "one_time"
    if (billing_mode == "free") != (payload.price_cents == 0):
        raise HTTPException(status_code=422, detail="Free 必须为 $0，付费套餐价格必须大于 $0")
    version = max((plan.version for plan in service.repository.active_plans() if plan.offer_code == payload.offer_code), default=current.version) + 1
    draft = GlobalPlan(payload.offer_code, version, payload.display_name, payload.description, payload.price_cents, billing_mode, payload.duration_days, payload.copilot_minutes, payload.screen_assist_uses, payload.resume_jd_enabled, payload.knowledge_base_enabled, payload.written_exam_enabled, payload.full_product_enabled, "draft", payload.featured, payload.display_order, created_at_ms=int(time() * 1000))
    try:
        stored = service.repository.save_draft(draft)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.plan.draft", resource_type="global_plan_version", resource_id=f"{stored.offer_code}:{stored.version}", reason=payload.reason, request_id=_request_id(request), result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"price_cents": stored.price_cents})
    return {"data": _plan(stored)}


@admin_global_commerce_router.post("/plans/{offer_code}/{version}/publish")
def publish_plan(offer_code: str, version: int, payload: PublishRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], service: GlobalCommerceService = Depends(global_commerce_service)):
    _guard_global(get_settings())
    _confirmed(payload.confirmed)
    try:
        published = service.repository.publish(offer_code, version)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.plan.publish", resource_type="global_plan_version", resource_id=f"{offer_code}:{version}", reason=payload.reason, request_id=_request_id(request), result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"price_cents": published.price_cents})
    return {"data": _plan(published)}


@admin_global_commerce_router.put("/mappings/{offer_code}")
def validate_mapping(offer_code: str, payload: ProductMappingRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], mode: CreemMode = Query(default="test"), service: GlobalCommerceService = Depends(global_commerce_service), configuration: GlobalCreemConfigurationService = Depends(global_creem_configuration_service)):
    settings = get_settings()
    _guard_global(settings)
    plan = service.repository.plan(offer_code)
    if plan is None or plan.billing_mode == "free":
        raise HTTPException(status_code=404, detail="付费套餐不存在")
    try:
        product = _provider_for_mode(configuration, mode).retrieve_product(payload.provider_product_id)
    except (CreemRequestError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail="Creem Product 无法验证，请检查当前 Test/Live 环境和 Product ID") from exc
    errors = []
    if product.amount_cents != plan.price_cents: errors.append("金额不一致")
    if product.currency != plan.currency: errors.append("币种不一致")
    if product.billing_mode != plan.billing_mode: errors.append("计费模式不一致")
    if product.status != "active": errors.append("Creem 商品不是启用状态")
    if product.mode and product.mode != mode: errors.append("Creem 商品环境不一致")
    mapping = GlobalProductMapping(mode, plan.offer_code, plan.version, product.product_id, "error" if errors else "ready", product.amount_cents, product.currency, product.billing_mode)
    stored = service.repository.save_provider_mapping(mapping)
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.mapping.validate", resource_type="global_product_mapping", resource_id=f"{stored.mode}:{offer_code}", reason=payload.reason, request_id=_request_id(request), result="failed" if errors else "success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"validation_errors": errors, "provider_product_fingerprint": _fingerprint(stored.provider_product_id)})
    if errors: raise HTTPException(status_code=409, detail="；".join(errors))
    return {"data": {"offerCode": stored.offer_code, "planVersion": stored.plan_version, "providerProductId": stored.provider_product_id, "validationStatus": stored.validation_status}}


@admin_global_commerce_router.post("/activation")
def activate_provider(payload: ProviderActivationRequest, request: Request, principal: Annotated[AdminPrincipal, Depends(permission("payments.manage"))], mode: CreemMode = Query(default="test"), service: GlobalCommerceService = Depends(global_commerce_service), configuration: GlobalCreemConfigurationService = Depends(global_creem_configuration_service)):
    settings = get_settings()
    _guard_global(settings)
    _confirmed(payload.confirmed)
    blockers: list[str] = []
    credentials = configuration.effective_credentials(mode)
    public_base = settings.public_web_base_url.rstrip("/")
    if payload.enabled:
        if mode != settings.global_commerce_provider_mode: blockers.append(f"当前服务运行环境为 {settings.global_commerce_provider_mode}，不能启用 {mode} 结账")
        if not settings.global_commerce_enabled: blockers.append("服务端商业化总开关未开启")
        if not credentials.api_key or not credentials.webhook_secret: blockers.append("Creem 密钥或 Webhook Secret 未配置")
        if not (settings.creem_checkout_success_url or public_base): blockers.append("支付返回地址未配置")
        if not public_base and not all((settings.global_terms_url,settings.global_privacy_url,settings.global_refund_policy_url,settings.global_fair_use_policy_url)): blockers.append("法律与退款链接未配置")
        for plan in service.catalogue():
            if plan.billing_mode == "free": continue
            mapping = service.repository.provider_mapping(mode, plan.offer_code)
            if mapping is None or mapping.validation_status != "ready" or mapping.plan_version != plan.version: blockers.append(f"{plan.offer_code} 映射未通过")
    if blockers:
        service.repository.set_provider_enabled(mode=mode,enabled=False,validation_status="error",validation_errors=blockers,updated_by_user_id=principal.user_id,updated_at_ms=int(time()*1000))
        raise HTTPException(status_code=409, detail="；".join(blockers))
    result = service.repository.set_provider_enabled(mode=mode,enabled=payload.enabled,validation_status="ready" if payload.enabled else "draft",validation_errors=[],updated_by_user_id=principal.user_id,updated_at_ms=int(time()*1000))
    ip_hash, user_agent_hash = _client_hashes(request)
    admin_service().audit(principal=principal, action="global_commerce.activate" if payload.enabled else "global_commerce.deactivate", resource_type="global_provider_config", resource_id=mode, reason=payload.reason, request_id=_request_id(request), result="success", ip_hash=ip_hash, user_agent_hash=user_agent_hash, details={"enabled": payload.enabled})
    return {"data": {"mode": mode, "enabled": bool(result.get("enabled")), "validationStatus": result.get("validation_status")}}
