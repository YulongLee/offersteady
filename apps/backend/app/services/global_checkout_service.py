from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime
from time import time
from uuid import uuid4

from app.core.config import Settings
from app.ports.global_commerce import GlobalCommerceRepository, GlobalOrder, GlobalSubscription
from app.ports.international_commerce_provider import InternationalCommerceProvider
from app.services.global_commerce_service import GlobalCommerceService, GlobalCommerceUnavailable


class GlobalCheckoutNotReady(RuntimeError):
    pass


class GlobalCheckoutValidationError(RuntimeError):
    pass


class GlobalCheckoutService:
    def __init__(self, *, settings: Settings, repository: GlobalCommerceRepository, provider: InternationalCommerceProvider, entitlements: GlobalCommerceService) -> None:
        self.settings = settings
        self.repository = repository
        self.provider = provider
        self.entitlements = entitlements

    def create_checkout(self, *, user_id: str, customer_email: str | None, offer_code: str, idempotency_key: str, now_ms: int | None = None) -> GlobalOrder:
        self._require_ready()
        if len(idempotency_key) < 8:
            raise GlobalCheckoutValidationError("idempotency key is too short")
        existing = self.repository.order_for_idempotency(user_id, idempotency_key)
        if existing:
            if existing.offer_code != offer_code:
                raise GlobalCheckoutValidationError("idempotency key was reused for another offer")
            return existing
        plan = self.repository.plan(offer_code)
        if plan is None or plan.billing_mode == "free" or plan.price_cents <= 0:
            raise GlobalCheckoutValidationError("offer cannot be purchased")
        mapping = self.repository.provider_mapping(self.settings.global_commerce_provider_mode, offer_code)
        if mapping is None or mapping.validation_status != "ready" or mapping.plan_version != plan.version:
            raise GlobalCheckoutNotReady("offer mapping is not validated")
        if (mapping.validated_amount_cents, mapping.validated_currency, mapping.validated_billing_mode) != (plan.price_cents, plan.currency, plan.billing_mode):
            raise GlobalCheckoutNotReady("provider product no longer matches the published offer")
        now = now_ms or int(time() * 1000)
        pending = GlobalOrder(f"gorder_{uuid4().hex}", user_id, plan.offer_code, plan.version, self.settings.global_commerce_provider_mode, plan.price_cents, "USD", "pending", idempotency_key, now, now)
        stored = self.repository.save_order(pending)
        if stored.order_id != pending.order_id:
            return stored
        try:
            checkout = self.provider.create_checkout(product_id=mapping.provider_product_id, request_id=pending.order_id, success_url=self.checkout_success_url(), customer_email=customer_email)
        except Exception as exc:
            self.repository.update_order(replace(pending, status="failed", failure_code="provider_checkout_failed", updated_at_ms=int(time() * 1000)))
            raise GlobalCheckoutNotReady("secure checkout is temporarily unavailable") from exc
        return self.repository.update_order(replace(pending, status="checkout_created", checkout_url=checkout.checkout_url, provider_checkout_id=checkout.checkout_id, provider_order_id=checkout.provider_order_id, provider_subscription_id=checkout.provider_subscription_id, provider_customer_id=checkout.provider_customer_id, updated_at_ms=int(time() * 1000)))

    def process_verified_event(self, payload: dict[str, object], raw_body: bytes, now_ms: int | None = None) -> dict[str, object]:
        self._require_global()
        now = now_ms or int(time() * 1000)
        event_id = self._text(payload.get("id"))
        event_type = self._text(payload.get("eventType") or payload.get("event_type") or payload.get("type"))
        created = payload.get("created_at") or payload.get("createdAt") or now
        created_ms = self._epoch_ms(created, fallback=now)
        obj = payload.get("object") if isinstance(payload.get("object"), dict) else payload.get("data")
        if not isinstance(obj, dict):
            raise GlobalCheckoutValidationError("provider event object is missing")
        order_id = self._internal_order_id(obj)
        provider_subscription_id = self._provider_subscription_id(obj, event_type=event_type)
        order = self.repository.order(order_id) if order_id else None
        if order is None and provider_subscription_id:
            order = self.repository.order_by_provider_subscription(mode=self.settings.global_commerce_provider_mode, provider_subscription_id=provider_subscription_id)
        if order is None and (provider_order_id := self._provider_order_id(obj)):
            order = self.repository.order_by_provider_order(mode=self.settings.global_commerce_provider_mode, provider_order_id=provider_order_id)
        payload_hash = hashlib.sha256(raw_body).hexdigest()
        try:
            with self.repository.transaction():
                if not self.repository.record_provider_event_once(mode=self.settings.global_commerce_provider_mode, event_id=event_id, event_type=event_type, payload_sha256=payload_hash, provider_created_at_ms=created_ms, received_at_ms=now, order_id=order_id):
                    return {"accepted": True, "duplicate": True}
                result = self._apply_verified_event(order=order, obj=obj, event_type=event_type, provider_subscription_id=provider_subscription_id, created_ms=created_ms, now_ms=now, event_id=event_id)
                if not result.get("ignored"):
                    self.repository.mark_provider_event(mode=self.settings.global_commerce_provider_mode, event_id=event_id, status="processed", processed_at_ms=now)
                return result
        except Exception as exc:
            # The business transaction has rolled back. Persist only a diagnostic
            # failure record so the provider may retry the exact same payload.
            try:
                if self.repository.record_provider_event_once(mode=self.settings.global_commerce_provider_mode, event_id=event_id, event_type=event_type, payload_sha256=payload_hash, provider_created_at_ms=created_ms, received_at_ms=now, order_id=order_id):
                    self.repository.mark_provider_event(mode=self.settings.global_commerce_provider_mode, event_id=event_id, status="failed", processed_at_ms=now, error_code=type(exc).__name__)
            except Exception:
                pass
            raise

    def _apply_verified_event(self, *, order: GlobalOrder | None, obj: dict[str, object], event_type: str, provider_subscription_id: str | None, created_ms: int, now_ms: int, event_id: str) -> dict[str, object]:
        if order is None:
            raise GlobalCheckoutValidationError("internal order reference is unknown")
        self._validate_business_facts(order, obj, require_financials=event_type in {"checkout.completed", "subscription.paid"})
        if event_type in {"checkout.completed", "subscription.paid"}:
            plan = self.repository.plan(order.offer_code, order.plan_version)
            if plan is None:
                raise GlobalCheckoutValidationError("purchased plan version is missing")
            customer_id = self._provider_customer_id(obj) or order.provider_customer_id
            if event_type == "checkout.completed" and plan.billing_mode == "recurring":
                self.repository.update_order(replace(order, status="confirming", provider_order_id=self._provider_order_id(obj) or order.provider_order_id, provider_subscription_id=provider_subscription_id or order.provider_subscription_id, provider_customer_id=customer_id, updated_at_ms=now_ms))
            elif order.status not in {"refunded", "disputed"}:
                existing_subscription = self.repository.subscription_by_provider_id(mode=order.mode, provider_subscription_id=provider_subscription_id) if provider_subscription_id else None
                if existing_subscription and existing_subscription.provider_updated_at_ms > created_ms:
                    self.repository.mark_provider_event(mode=self.settings.global_commerce_provider_mode, event_id=event_id, status="ignored", processed_at_ms=now_ms, error_code="stale_subscription_event")
                    return {"accepted": True, "duplicate": False, "ignored": True}
                source_kind = "subscription_period" if event_type == "subscription.paid" else "order"
                period_end = self._period_ms(obj, "end", fallback=0) or None
                source_id = f"subscription:{provider_subscription_id}:{event_id}" if source_kind == "subscription_period" else f"order:{order.order_id}:{event_id}"
                self.entitlements.grant_purchase(user_id=order.user_id, offer_code=order.offer_code, plan_version=order.plan_version, source_kind=source_kind, source_id=source_id, starts_at_ms=created_ms, ends_at_ms=period_end)
                order = self.repository.update_order(replace(order, status="paid", provider_order_id=self._provider_order_id(obj) or order.provider_order_id, provider_subscription_id=provider_subscription_id or order.provider_subscription_id, provider_customer_id=customer_id, updated_at_ms=now_ms))
                if event_type == "subscription.paid":
                    self._sync_subscription(order=order, obj=obj, event_type=event_type, provider_updated_at_ms=created_ms, now_ms=now_ms)
        elif event_type in {"subscription.trialing", "subscription.active", "subscription.update", "subscription.past_due", "subscription.unpaid", "subscription.canceling", "subscription.scheduled_cancel", "subscription.canceled", "subscription.cancelled", "subscription.paused", "subscription.expired"}:
            synced = self._sync_subscription(order=order, obj=obj, event_type=event_type, provider_updated_at_ms=created_ms, now_ms=now_ms)
            if synced.provider_updated_at_ms == created_ms and synced.status in {"paused", "expired"} and provider_subscription_id:
                self.repository.revoke_entitlements_for_source(source_kind="subscription_period", source_id_prefix=f"subscription:{provider_subscription_id}:")
        elif "refund" in event_type:
            self.repository.update_order(replace(order, status="refunded", updated_at_ms=now_ms))
            self.repository.revoke_entitlements_for_source(source_kind="order", source_id_prefix=f"order:{order.order_id}:")
            if provider_subscription_id:
                self.repository.revoke_entitlements_for_source(source_kind="subscription_period", source_id_prefix=f"subscription:{provider_subscription_id}:")
        elif "dispute" in event_type:
            self.repository.update_order(replace(order, status="disputed", updated_at_ms=now_ms))
            self.repository.revoke_entitlements_for_source(source_kind="order", source_id_prefix=f"order:{order.order_id}:")
            if provider_subscription_id:
                self.repository.revoke_entitlements_for_source(source_kind="subscription_period", source_id_prefix=f"subscription:{provider_subscription_id}:")
        return {"accepted": True, "duplicate": False}

    def reconcile_order(self, order_id: str, *, now_ms: int | None = None) -> GlobalOrder:
        """Reconcile one known order from provider truth without trusting browser state."""
        self._require_global()
        order = self.repository.order(order_id)
        if order is None:
            raise GlobalCheckoutValidationError("internal order reference is unknown")
        if order.mode != self.settings.global_commerce_provider_mode:
            raise GlobalCheckoutValidationError("provider environment mismatch")
        if order.status in {"paid", "refunded", "disputed"}:
            return order
        if not order.provider_checkout_id:
            raise GlobalCheckoutValidationError("provider checkout reference is missing")
        now = now_ms or int(time() * 1000)
        checkout = self.provider.retrieve_checkout(order.provider_checkout_id)
        if self._internal_order_id(checkout) != order.order_id:
            raise GlobalCheckoutValidationError("provider checkout reference mismatch")
        checkout_status = (self._optional_text(checkout.get("status")) or "").lower()
        if checkout_status == "expired":
            return self.repository.update_order(replace(order, status="expired", updated_at_ms=now))
        if checkout_status != "completed":
            return order
        self._process_reconciliation_event(
            event_id=f"reconcile:checkout:{order.provider_checkout_id}:completed",
            event_type="checkout.completed",
            obj=checkout,
            now_ms=now,
        )
        reconciled = self.repository.order(order.order_id) or order
        plan = self.repository.plan(reconciled.offer_code, reconciled.plan_version)
        if plan and plan.billing_mode == "recurring" and reconciled.provider_subscription_id:
            subscription = self.provider.retrieve_subscription(reconciled.provider_subscription_id)
            if (self._optional_text(subscription.get("status")) or "").lower() == "active":
                if not isinstance(subscription.get("product"), dict):
                    mapping = self.repository.provider_mapping(reconciled.mode, reconciled.offer_code)
                    if mapping:
                        product = self.provider.retrieve_product(mapping.provider_product_id)
                        subscription = {**subscription, "product": {"id": product.product_id, "price": product.amount_cents, "currency": product.currency}}
                transaction_id = self._optional_text(subscription.get("last_transaction_id") or subscription.get("lastTransactionId")) or "active"
                self._process_reconciliation_event(
                    event_id=f"reconcile:subscription:{reconciled.provider_subscription_id}:{transaction_id}",
                    event_type="subscription.paid",
                    obj=subscription,
                    now_ms=now,
                )
        return self.repository.order(order.order_id) or reconciled

    def _process_reconciliation_event(self, *, event_id: str, event_type: str, obj: dict[str, object], now_ms: int) -> None:
        payload: dict[str, object] = {"id": event_id, "eventType": event_type, "created_at": obj.get("updated_at") or obj.get("created_at") or now_ms, "object": obj}
        raw_body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        self.process_verified_event(payload, raw_body, now_ms=now_ms)

    def _validate_business_facts(self, order: GlobalOrder, obj: dict[str, object], *, require_financials: bool) -> None:
        mapping = self.repository.provider_mapping(order.mode, order.offer_code)
        product_id = self._provider_product_id(obj)
        amount, currency = self._provider_financials(obj)
        if mapping is None or product_id != mapping.provider_product_id:
            raise GlobalCheckoutValidationError("provider product mismatch")
        event_mode = self._provider_mode(obj)
        if event_mode and event_mode != order.mode:
            raise GlobalCheckoutValidationError("provider environment mismatch")
        customer_id = self._provider_customer_id(obj)
        if order.provider_customer_id and customer_id and order.provider_customer_id != customer_id:
            raise GlobalCheckoutValidationError("provider customer mismatch")
        if require_financials and (amount is None or currency is None):
            raise GlobalCheckoutValidationError("provider amount or currency is missing")
        if amount is not None and amount != order.expected_amount_cents:
            raise GlobalCheckoutValidationError("provider amount or currency mismatch")
        if currency is not None and currency.upper() != order.expected_currency:
            raise GlobalCheckoutValidationError("provider amount or currency mismatch")
        provider_order = self._mapping(obj.get("order"))
        provider_status = self._optional_text(provider_order.get("status") if provider_order else None) or self._optional_text(obj.get("status"))
        if require_financials and provider_status and provider_status.lower() not in {"paid", "completed", "active", "success", "succeeded"}:
            raise GlobalCheckoutValidationError("provider payment status is not fulfilled")

    def _sync_subscription(self, *, order: GlobalOrder, obj: dict[str, object], event_type: str, provider_updated_at_ms: int, now_ms: int) -> GlobalSubscription:
        provider_subscription_id = self._provider_subscription_id(obj, event_type=event_type) or order.provider_subscription_id
        customer_id = self._provider_customer_id(obj) or order.provider_customer_id
        if not provider_subscription_id or not customer_id:
            raise GlobalCheckoutValidationError("subscription or customer reference is missing")
        existing = self.repository.subscription_by_provider_id(mode=order.mode, provider_subscription_id=provider_subscription_id)
        start = self._period_ms(obj, "start", fallback=existing.current_period_start_ms if existing else provider_updated_at_ms)
        end = self._period_ms(obj, "end", fallback=existing.current_period_end_ms if existing else 0)
        if end <= start:
            raise GlobalCheckoutValidationError("subscription period is invalid")
        raw_status = event_type.removeprefix("subscription.")
        if raw_status == "update":
            raw_status = (self._optional_text(obj.get("status")) or (existing.status if existing else "active")).lower()
        status = "canceled" if raw_status == "cancelled" else raw_status
        if status == "scheduled_cancel":
            status = "canceling"
        if status == "paid":
            status = "active"
        if status not in {"trialing", "active", "past_due", "unpaid", "canceling", "canceled", "paused", "expired"}:
            raise GlobalCheckoutValidationError("subscription state is unsupported")
        return self.repository.upsert_subscription(GlobalSubscription(
            subscription_id=existing.subscription_id if existing else f"gsub_{uuid4().hex}",
            user_id=order.user_id,
            offer_code=order.offer_code,
            plan_version=order.plan_version,
            mode=order.mode,
            provider_subscription_id=provider_subscription_id,
            provider_customer_id=customer_id,
            status=status,
            current_period_start_ms=start,
            current_period_end_ms=end,
            provider_updated_at_ms=provider_updated_at_ms,
            created_at_ms=existing.created_at_ms if existing else now_ms,
            updated_at_ms=now_ms,
            canceled_at_ms=provider_updated_at_ms if status in {"canceled", "expired"} else (existing.canceled_at_ms if existing else None),
        ))

    @classmethod
    def _provider_subscription_id(cls, obj: dict[str, object], *, event_type: str | None = None) -> str | None:
        subscription = obj.get("subscription")
        nested_id = cls._optional_text(subscription.get("id")) if isinstance(subscription, dict) else None
        nested_id = nested_id or (subscription if isinstance(subscription, str) and subscription else None)
        explicit_id = cls._optional_text(obj.get("subscription_id") or obj.get("subscriptionId"))
        if nested_id or explicit_id:
            return nested_id or explicit_id
        return cls._optional_text(obj.get("id")) if event_type and event_type.startswith("subscription.") else None

    @classmethod
    def _provider_customer_id(cls, obj: dict[str, object]) -> str | None:
        customer = obj.get("customer")
        if isinstance(customer, dict):
            return cls._optional_text(customer.get("id"))
        if isinstance(customer, str) and customer:
            return customer
        return cls._optional_text(obj.get("customer_id") or obj.get("customerId"))

    @classmethod
    def _provider_order_id(cls, obj: dict[str, object]) -> str | None:
        order = obj.get("order")
        if isinstance(order, dict):
            return cls._optional_text(order.get("id"))
        if isinstance(order, str) and order:
            return order
        return cls._optional_text(obj.get("order_id") or obj.get("orderId"))

    @classmethod
    def _internal_order_id(cls, obj: dict[str, object]) -> str | None:
        metadata = cls._mapping(obj.get("metadata"))
        direct = cls._optional_text(obj.get("request_id") or obj.get("requestId") or metadata.get("order_id"))
        if direct:
            return direct
        checkout = cls._mapping(obj.get("checkout"))
        checkout_metadata = cls._mapping(checkout.get("metadata")) if checkout else {}
        return cls._optional_text(checkout.get("request_id") or checkout.get("requestId") or checkout_metadata.get("order_id")) if checkout else None

    @classmethod
    def _provider_product_id(cls, obj: dict[str, object]) -> str | None:
        product = obj.get("product")
        if isinstance(product, dict):
            product_id = cls._optional_text(product.get("id"))
            if product_id:
                return product_id
        elif isinstance(product, str) and product:
            return product
        order = cls._mapping(obj.get("order"))
        nested_product = order.get("product") if order else None
        if isinstance(nested_product, dict):
            product_id = cls._optional_text(nested_product.get("id"))
            if product_id:
                return product_id
        elif isinstance(nested_product, str) and nested_product:
            return nested_product
        return cls._optional_text(obj.get("product_id") or obj.get("productId"))

    @classmethod
    def _provider_financials(cls, obj: dict[str, object]) -> tuple[int | None, str | None]:
        order = cls._mapping(obj.get("order"))
        product = cls._mapping(obj.get("product"))
        raw_amount = obj.get("amount") or obj.get("amount_paid") or obj.get("amountPaid")
        raw_currency = obj.get("currency")
        if order:
            raw_amount = raw_amount or order.get("amount") or order.get("amount_paid") or order.get("amountPaid")
            raw_currency = raw_currency or order.get("currency")
        if product:
            raw_price = product.get("price")
            if isinstance(raw_price, dict):
                raw_amount = raw_amount or raw_price.get("amount")
                raw_currency = raw_currency or raw_price.get("currency")
            else:
                raw_amount = raw_amount or raw_price
            raw_currency = raw_currency or product.get("currency")
        return cls._optional_int(raw_amount), cls._optional_text(raw_currency)

    @classmethod
    def _provider_mode(cls, obj: dict[str, object]) -> str | None:
        order = cls._mapping(obj.get("order"))
        product = cls._mapping(obj.get("product"))
        raw = cls._optional_text(obj.get("mode") or obj.get("environment"))
        raw = raw or (cls._optional_text(order.get("mode") or order.get("environment")) if order else None)
        raw = raw or (cls._optional_text(product.get("mode") or product.get("environment")) if product else None)
        if not raw:
            return None
        return {"prod": "live", "production": "live", "sandbox": "test", "local": "test"}.get(raw.lower(), raw.lower())

    @staticmethod
    def _mapping(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    @classmethod
    def _period_ms(cls, obj: dict[str, object], boundary: str, *, fallback: int) -> int:
        snake = f"current_period_{boundary}"
        camel = f"currentPeriod{boundary.title()}"
        return cls._epoch_ms(obj.get(snake) or obj.get(f"{snake}_date") or obj.get(camel), fallback=fallback)

    def _require_ready(self) -> None:
        self._require_global()
        if not self.settings.global_commerce_enabled:
            raise GlobalCheckoutNotReady("checkout is disabled")
        if not bool(self.repository.provider_config(self.settings.global_commerce_provider_mode).get("enabled")):
            raise GlobalCheckoutNotReady("provider checkout is not activated")
        if not self.checkout_success_url():
            raise GlobalCheckoutNotReady("checkout return URL is missing")

    def checkout_success_url(self) -> str:
        explicit = (self.settings.creem_checkout_success_url or "").strip()
        if explicit:
            return explicit
        base = self.settings.public_web_base_url.rstrip("/")
        return f"{base}/billing/success" if base else ""

    def _require_global(self) -> None:
        if self.settings.product_edition != "global":
            raise GlobalCommerceUnavailable("global commerce is unavailable in the Chinese edition")

    @staticmethod
    def _text(value: object) -> str:
        if not isinstance(value, str) or not value:
            raise GlobalCheckoutValidationError("provider event identifier is missing")
        return value

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return int(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _epoch_ms(value: object, *, fallback: int) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return int(parsed.timestamp() * 1000)
            except ValueError:
                return fallback
        return fallback
