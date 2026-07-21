from __future__ import annotations

from hashlib import sha256
from json import dumps
from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.core.logging import utc_now_iso
from app.core.responses import success_response
from app.core.config import Settings
from app.deps import billing_service, optional_authenticated_context, resolve_owned_user_id, settings_dependency
from app.ports.authentication import AuthenticatedRequestContext
from app.schemas.foundation import ApiEnvelope, ModuleDescriptor
from app.services.billing_service import BillingService
from app.services.mzfpay_provider import MzfpayPaymentProvider


router = APIRouter(prefix="/billing", tags=["billing"])
descriptor = ModuleDescriptor(
    feature="billing",
    owningApp="apps/backend",
    routePrefix="/api/v1/billing",
    mode="active",
    notes="Wallet balance, pricing catalog, points ledger, and redemption code APIs.",
)


class RedeemPointsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str | None = Field(default=None, alias="userId")
    code: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, alias="idempotencyKey")


class CheckoutOrderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str | None = Field(default=None, alias="userId")
    product_id: str = Field(min_length=1, alias="productId")
    channel: str = Field(pattern="^(wechat|alipay)$")
    idempotency_key: str = Field(min_length=1, alias="idempotencyKey")


@router.get("/status", response_model=ApiEnvelope[dict[str, str]])
async def status(request: Request) -> ApiEnvelope[dict[str, str]]:
    return success_response(
        request=request,
        data={"status": "active", "feature": "billing", "message": "Billing Service is available for wallet, catalog, ledger, and redemption code flows."},
        timestamp=utc_now_iso(),
    )


@router.get("/state", response_model=ApiEnvelope[dict[str, object]])
async def get_billing_state(
    request: Request,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: BillingService = Depends(billing_service),
) -> ApiEnvelope[dict[str, object]]:
    data = service.state_payload(service.state_for_user(user_id=resolve_owned_user_id(explicit_user_id=None, auth_context=auth_context)))
    return success_response(request=request, data=data, timestamp=utc_now_iso())


@router.post("/redemptions", response_model=ApiEnvelope[dict[str, object]])
async def redeem_points(
    request_context: Request,
    request: RedeemPointsRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: BillingService = Depends(billing_service),
) -> ApiEnvelope[dict[str, object]]:
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    result = service.redeem_points(user_id=user_id, code=request.code, idempotency_key=request.idempotency_key)
    return success_response(request=request_context, data=result, timestamp=utc_now_iso())


@router.post("/checkout-orders", response_model=ApiEnvelope[dict[str, object]])
async def create_checkout_order(
    request_context: Request,
    request: CheckoutOrderRequest,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: BillingService = Depends(billing_service),
    settings: Settings = Depends(settings_dependency),
) -> ApiEnvelope[dict[str, object]]:
    provider = MzfpayPaymentProvider(settings)
    if not provider.enabled:
        raise HTTPException(status_code=503, detail="码支付尚未配置商户参数")
    user_id = resolve_owned_user_id(explicit_user_id=request.user_id, auth_context=auth_context)
    expires_at_ms = int(request_context.scope.get("time", 0) * 1000) if request_context.scope.get("time") else 0
    if not expires_at_ms:
        from time import time
        expires_at_ms = int((time() + settings.mzfpay_payment_ttl_seconds) * 1000)
    order = service.create_checkout_order(
        user_id=user_id,
        product_id=request.product_id,
        channel=request.channel,
        idempotency_key=request.idempotency_key,
        payment_url="#",
        expires_at_ms=expires_at_ms,
    )
    payment_url = provider.payment_url(
        order_id=order.id,
        product_name=order.product.display_name,
        amount_cents=order.amount_cents,
        channel=order.channel,
        client_ip=request_context.client.host if request_context.client else None,
    )
    order = service.replace_checkout_action(order_id=order.id, payment_url=payment_url, expires_at_ms=expires_at_ms)
    return success_response(request=request_context, data=service._official_order_payload(order), timestamp=utc_now_iso())


@router.get("/checkout-orders/{order_id}", response_model=ApiEnvelope[dict[str, object]])
async def get_checkout_order(
    order_id: str,
    request: Request,
    auth_context: AuthenticatedRequestContext | None = Depends(optional_authenticated_context),
    service: BillingService = Depends(billing_service),
) -> ApiEnvelope[dict[str, object]]:
    user_id = resolve_owned_user_id(explicit_user_id=None, auth_context=auth_context)
    try:
        order = service.checkout_order_for_user(user_id=user_id, order_id=order_id)
    except (KeyError, PermissionError) as exc:
        raise HTTPException(status_code=404, detail="订单不存在") from exc
    return success_response(request=request, data=service._official_order_payload(order), timestamp=utc_now_iso())


@router.api_route("/payment-providers/mzfpay/notify", methods=["GET", "POST"], response_class=PlainTextResponse, include_in_schema=False)
async def handle_mzfpay_notify(
    request: Request,
    service: BillingService = Depends(billing_service),
    settings: Settings = Depends(settings_dependency),
) -> PlainTextResponse:
    if request.method == "POST":
        form = await request.form()
        params = {key: str(value) for key, value in form.items()}
    else:
        params = {key: value for key, value in request.query_params.items()}
    provider = MzfpayPaymentProvider(settings)
    notification = provider.parse_notification(params)
    event_fingerprint = sha256(dumps(params, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
    outcome = service.process_payment_notification(
        event_fingerprint=event_fingerprint,
        order_id=notification.order_id,
        provider_trade_no=notification.provider_trade_no,
        amount_cents=notification.amount_cents,
        verified=notification.verified,
        paid=notification.paid,
    )
    return PlainTextResponse("success" if outcome == "paid" else "fail")


@router.get("/payment-providers/mzfpay/return")
async def handle_mzfpay_return(settings: Settings = Depends(settings_dependency)) -> RedirectResponse:
    return RedirectResponse(settings.mzfpay_return_url or f"{settings.public_web_base_url.rstrip('/')}/app/billing")
