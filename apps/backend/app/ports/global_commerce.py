from __future__ import annotations

from dataclasses import dataclass, replace
from contextlib import AbstractContextManager
from typing import Literal, Protocol


OfferCode = Literal[
    "global-free",
    "global-interview-pass",
    "global-pro-weekly",
    "global-pro-monthly",
    "global-job-hunt",
]
BillingMode = Literal["free", "one_time", "recurring"]
UsageKind = Literal["copilot_minute", "screen_assist"]


@dataclass(frozen=True)
class GlobalPlan:
    offer_code: OfferCode
    version: int
    display_name: str
    description: str
    price_cents: int
    billing_mode: BillingMode
    duration_days: int | None
    copilot_minutes: int | None
    screen_assist_uses: int | None
    resume_jd_enabled: bool
    knowledge_base_enabled: bool
    written_exam_enabled: bool
    full_product_enabled: bool
    status: Literal["draft", "active", "retired"] = "active"
    featured: bool = False
    display_order: int = 0
    currency: Literal["USD"] = "USD"
    created_at_ms: int = 0

    def purchased_snapshot(self) -> dict[str, object]:
        return {
            "offerCode": self.offer_code,
            "planVersion": self.version,
            "displayName": self.display_name,
            "currency": self.currency,
            "priceCents": self.price_cents,
            "billingMode": self.billing_mode,
            "durationDays": self.duration_days,
            "copilotMinutes": self.copilot_minutes,
            "screenAssistUses": self.screen_assist_uses,
            "resumeJdEnabled": self.resume_jd_enabled,
            "knowledgeBaseEnabled": self.knowledge_base_enabled,
            "writtenExamEnabled": self.written_exam_enabled,
            "fullProductEnabled": self.full_product_enabled,
        }


@dataclass(frozen=True)
class GlobalEntitlement:
    entitlement_id: str
    user_id: str
    offer_code: OfferCode
    plan_version: int
    source_kind: Literal["free_grant", "order", "subscription_period", "admin"]
    source_id: str
    starts_at_ms: int
    ends_at_ms: int | None
    copilot_minutes_granted: int | None
    screen_assist_uses_granted: int | None
    resume_jd_enabled: bool
    knowledge_base_enabled: bool
    written_exam_enabled: bool
    full_product_enabled: bool
    status: Literal["active", "exhausted", "expired", "revoked"] = "active"
    copilot_minutes_used: int = 0
    copilot_minutes_locked: int = 0
    screen_assist_uses_used: int = 0
    screen_assist_uses_locked: int = 0

    def with_usage(self, *, kind: UsageKind, used_delta: int = 0, locked_delta: int = 0) -> "GlobalEntitlement":
        if kind == "copilot_minute":
            return replace(
                self,
                copilot_minutes_used=max(0, self.copilot_minutes_used + used_delta),
                copilot_minutes_locked=max(0, self.copilot_minutes_locked + locked_delta),
            )
        return replace(
            self,
            screen_assist_uses_used=max(0, self.screen_assist_uses_used + used_delta),
            screen_assist_uses_locked=max(0, self.screen_assist_uses_locked + locked_delta),
        )


@dataclass(frozen=True)
class UsageReservation:
    operation_id: str
    user_id: str
    entitlement_id: str
    usage_kind: UsageKind
    amount: int
    status: Literal["reserved", "settled", "released"]
    created_at_ms: int


@dataclass(frozen=True)
class GlobalProductMapping:
    mode: Literal["test", "live"]
    offer_code: OfferCode
    plan_version: int
    provider_product_id: str
    validation_status: Literal["draft", "ready", "error"]
    validated_amount_cents: int | None = None
    validated_currency: str | None = None
    validated_billing_mode: str | None = None


@dataclass(frozen=True)
class GlobalOrder:
    order_id: str
    user_id: str
    offer_code: OfferCode
    plan_version: int
    mode: Literal["test", "live"]
    expected_amount_cents: int
    expected_currency: Literal["USD"]
    status: Literal["pending", "checkout_created", "confirming", "paid", "failed", "expired", "refunded", "disputed"]
    idempotency_key: str
    created_at_ms: int
    updated_at_ms: int
    checkout_url: str | None = None
    provider_checkout_id: str | None = None
    provider_order_id: str | None = None
    provider_subscription_id: str | None = None
    provider_customer_id: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True)
class GlobalSubscription:
    subscription_id: str
    user_id: str
    offer_code: OfferCode
    plan_version: int
    mode: Literal["test", "live"]
    provider_subscription_id: str
    provider_customer_id: str
    status: Literal["trialing", "active", "past_due", "unpaid", "canceling", "canceled", "paused", "expired"]
    current_period_start_ms: int
    current_period_end_ms: int
    provider_updated_at_ms: int
    created_at_ms: int
    updated_at_ms: int
    canceled_at_ms: int | None = None


@dataclass(frozen=True)
class FairUseDecision:
    decision_id: str
    user_id: str
    status: Literal["review", "restricted", "cleared", "expired"]
    reason_code: str
    evidence: dict[str, object]
    restrict_new_sessions: bool
    effective_at_ms: int
    expires_at_ms: int | None


class GlobalCommerceRepository(Protocol):
    def transaction(self) -> AbstractContextManager[None]: ...
    def active_plans(self) -> list[GlobalPlan]: ...
    def plan(self, offer_code: str, version: int | None = None) -> GlobalPlan | None: ...
    def save_draft(self, plan: GlobalPlan) -> GlobalPlan: ...
    def publish(self, offer_code: str, version: int) -> GlobalPlan: ...
    def entitlements_for_user(self, user_id: str) -> list[GlobalEntitlement]: ...
    def grant_entitlement(self, entitlement: GlobalEntitlement) -> GlobalEntitlement: ...
    def initial_free_grant(self, user_id: str) -> GlobalEntitlement | None: ...
    def record_initial_free_grant(self, user_id: str, entitlement: GlobalEntitlement) -> GlobalEntitlement: ...
    def reservation(self, operation_id: str) -> UsageReservation | None: ...
    def reserve_usage_atomic(self, *, user_id: str, usage_kind: UsageKind, amount: int, operation_id: str, created_at_ms: int) -> UsageReservation: ...
    def finalize_usage_atomic(self, *, operation_id: str, outcome: Literal["settled", "released"], actual_amount: int | None = None, finalized_at_ms: int) -> UsageReservation: ...
    def reserve_usage(self, reservation: UsageReservation) -> UsageReservation: ...
    def update_reservation(self, reservation: UsageReservation) -> UsageReservation: ...
    def update_entitlement(self, entitlement: GlobalEntitlement) -> GlobalEntitlement: ...
    def provider_mapping(self, mode: str, offer_code: str) -> GlobalProductMapping | None: ...
    def save_provider_mapping(self, mapping: GlobalProductMapping) -> GlobalProductMapping: ...
    def order_for_idempotency(self, user_id: str, idempotency_key: str) -> GlobalOrder | None: ...
    def order(self, order_id: str) -> GlobalOrder | None: ...
    def order_by_provider_order(self, *, mode: str, provider_order_id: str) -> GlobalOrder | None: ...
    def order_by_provider_subscription(self, *, mode: str, provider_subscription_id: str) -> GlobalOrder | None: ...
    def save_order(self, order: GlobalOrder) -> GlobalOrder: ...
    def update_order(self, order: GlobalOrder) -> GlobalOrder: ...
    def orders_for_user(self, user_id: str) -> list[GlobalOrder]: ...
    def recent_orders(self, *, limit: int = 100) -> list[GlobalOrder]: ...
    def subscription_by_provider_id(self, *, mode: str, provider_subscription_id: str) -> GlobalSubscription | None: ...
    def subscriptions_for_user(self, user_id: str) -> list[GlobalSubscription]: ...
    def recent_subscriptions(self, *, limit: int = 100) -> list[GlobalSubscription]: ...
    def upsert_subscription(self, subscription: GlobalSubscription) -> GlobalSubscription: ...
    def revoke_entitlements_for_source(self, *, source_kind: str, source_id_prefix: str) -> int: ...
    def record_provider_event_once(self, *, mode: str, event_id: str, event_type: str, payload_sha256: str, provider_created_at_ms: int, received_at_ms: int, order_id: str | None) -> bool: ...
    def mark_provider_event(self, *, mode: str, event_id: str, status: str, processed_at_ms: int, error_code: str | None = None) -> None: ...
    def recent_provider_events(self, *, mode: str, limit: int = 100) -> list[dict[str, object]]: ...
    def provider_config(self, mode: str) -> dict[str, object]: ...
    def save_provider_credentials(self, *, mode: str, credential_ciphertext: str, api_key_fingerprint: str, webhook_secret_fingerprint: str, updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]: ...
    def mark_provider_connection_checked(self, *, mode: str, checked_at_ms: int, validation_status: str, validation_errors: list[str]) -> dict[str, object]: ...
    def set_provider_enabled(self, *, mode: str, enabled: bool, validation_status: str, validation_errors: list[str], updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]: ...
    def active_fair_use_decision(self, user_id: str, now_ms: int) -> FairUseDecision | None: ...
    def save_fair_use_decision(self, decision: FairUseDecision) -> FairUseDecision: ...
    def recent_fair_use_decisions(self, *, limit: int = 100) -> list[FairUseDecision]: ...
