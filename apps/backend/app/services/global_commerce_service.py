from __future__ import annotations

from dataclasses import replace
from math import ceil
from time import time
from uuid import uuid4

from app.core.config import Settings
from app.ports.global_commerce import GlobalCommerceRepository, GlobalEntitlement, GlobalPlan, UsageKind, UsageReservation


class GlobalCommerceUnavailable(RuntimeError):
    pass


class GlobalEntitlementDenied(RuntimeError):
    pass


class GlobalFairUseRestricted(RuntimeError):
    pass


class GlobalCommerceService:
    def __init__(self, settings: Settings, repository: GlobalCommerceRepository) -> None:
        self.settings = settings
        self.repository = repository

    def _require_global(self) -> None:
        if self.settings.product_edition != "global":
            raise GlobalCommerceUnavailable("global commerce is unavailable in the Chinese edition")

    def catalogue(self) -> list[GlobalPlan]:
        self._require_global()
        return self.repository.active_plans()

    def ensure_free_grant(self, user_id: str, now_ms: int | None = None) -> GlobalEntitlement:
        self._require_global()
        existing = self.repository.initial_free_grant(user_id)
        if existing:
            return existing
        now = now_ms or int(time() * 1000)
        plan = self.repository.plan("global-free")
        if plan is None:
            raise GlobalCommerceUnavailable("global Free plan is not published")
        entitlement = self._entitlement_from_plan(user_id=user_id, plan=plan, source_kind="free_grant", source_id=f"free:{user_id}", starts_at_ms=now, ends_at_ms=None)
        return self.repository.record_initial_free_grant(user_id, entitlement)

    def grant_purchase(self, *, user_id: str, offer_code: str, source_kind: str, source_id: str, starts_at_ms: int, ends_at_ms: int | None = None, plan_version: int | None = None) -> GlobalEntitlement:
        self._require_global()
        plan = self.repository.plan(offer_code, plan_version)
        if plan is None or plan.status != "active" and plan_version is None:
            raise ValueError("offer is not published")
        if plan.billing_mode == "free":
            raise ValueError("Free is granted only through the account grant flow")
        resolved_end = ends_at_ms
        if resolved_end is None and plan.duration_days:
            resolved_end = starts_at_ms + plan.duration_days * 86_400_000
        return self.repository.grant_entitlement(self._entitlement_from_plan(user_id=user_id, plan=plan, source_kind=source_kind, source_id=source_id, starts_at_ms=starts_at_ms, ends_at_ms=resolved_end))

    def active_entitlements(self, user_id: str, now_ms: int | None = None) -> list[GlobalEntitlement]:
        self._require_global()
        now = now_ms or int(time() * 1000)
        self.ensure_free_grant(user_id, now)
        result: list[GlobalEntitlement] = []
        for entitlement in self.repository.entitlements_for_user(user_id):
            if entitlement.status != "active" or entitlement.starts_at_ms > now:
                continue
            if entitlement.ends_at_ms is not None and entitlement.ends_at_ms <= now:
                self.repository.update_entitlement(replace(entitlement, status="expired"))
                continue
            result.append(entitlement)
        return sorted(result, key=lambda e: (e.ends_at_ms is None, e.ends_at_ms or 2**63, -e.starts_at_ms))

    def reserve(self, *, user_id: str, kind: UsageKind, amount: int, operation_id: str, now_ms: int | None = None) -> UsageReservation:
        self._require_global()
        if amount <= 0:
            raise ValueError("usage reservation amount must be positive")
        existing = self.repository.reservation(operation_id)
        if existing:
            if existing.user_id != user_id or existing.usage_kind != kind or existing.amount != amount:
                raise ValueError("idempotency key was reused with different usage")
            return existing
        now = now_ms or int(time() * 1000)
        self.ensure_free_grant(user_id, now)
        try:
            return self.repository.reserve_usage_atomic(user_id=user_id, usage_kind=kind, amount=amount, operation_id=operation_id, created_at_ms=now)
        except LookupError as exc:
            raise GlobalEntitlementDenied(f"insufficient {kind} entitlement") from exc

    def settle(self, *, operation_id: str, actual_amount: int | None = None) -> UsageReservation:
        self._require_global()
        return self.repository.finalize_usage_atomic(operation_id=operation_id, outcome="settled", actual_amount=actual_amount, finalized_at_ms=int(time() * 1000))

    def release(self, *, operation_id: str) -> UsageReservation:
        self._require_global()
        return self.repository.finalize_usage_atomic(operation_id=operation_id, outcome="released", finalized_at_ms=int(time() * 1000))

    def state(self, user_id: str, now_ms: int | None = None) -> dict[str, object]:
        active = self.active_entitlements(user_id, now_ms)
        primary = active[0] if active else None
        copilot = self._remaining(active, "copilot_minute")
        screen = self._remaining(active, "screen_assist")
        knowledge = self._remaining(active, "knowledge_token")
        subscriptions = self.repository.subscriptions_for_user(user_id)
        return {
            "entitlements": [self._entitlement_payload(item) for item in active],
            "entitlement": self._entitlement_payload(primary) if primary else None,
            "copilot": copilot,
            "screenAssist": screen,
            "knowledge": knowledge,
            "usage": {"copilotMinutesRemaining": copilot["remaining"], "screenAssistUsesRemaining": screen["remaining"], "copilotUnlimited": copilot["unlimited"], "screenAssistUnlimited": screen["unlimited"], "knowledgeTokensRemaining": knowledge["remaining"], "knowledgeTokensUnlimited": knowledge["unlimited"]},
            "features": {
                "resumeJd": any(e.resume_jd_enabled or e.full_product_enabled for e in active),
                "knowledgeBase": any(e.knowledge_base_enabled or e.full_product_enabled for e in active),
                "writtenExam": any(e.written_exam_enabled or e.full_product_enabled for e in active),
            },
            "subscription": self._subscription_payload(subscriptions[0]) if subscriptions else None,
            "orders": [self._order_payload(item) for item in self.repository.orders_for_user(user_id)],
        }

    def reserve_copilot_elapsed(self, *, user_id: str, elapsed_seconds: int, operation_id: str) -> UsageReservation:
        return self.reserve(user_id=user_id, kind="copilot_minute", amount=max(1, ceil(elapsed_seconds / 60)), operation_id=operation_id)

    def authorize_interview(self, *, user_id: str, interview_already_active: bool, now_ms: int | None = None) -> None:
        """Fair-use decisions never interrupt an already active interview."""
        self._require_global()
        if interview_already_active:
            return
        decision = self.repository.active_fair_use_decision(user_id, now_ms or int(time() * 1000))
        if decision and decision.status == "restricted" and decision.restrict_new_sessions:
            raise GlobalFairUseRestricted("new interviews are temporarily restricted; contact support for review")

    @staticmethod
    def _remaining(active: list[GlobalEntitlement], kind: UsageKind) -> dict[str, object]:
        if kind == "copilot_minute":
            limits = [e.copilot_minutes_granted for e in active]
        elif kind == "screen_assist":
            limits = [e.screen_assist_uses_granted for e in active]
        else:
            limits = [e.knowledge_tokens_granted for e in active]
        if any(limit is None for limit in limits):
            return {"unlimited": True, "remaining": None}
        def remaining_for(entitlement: GlobalEntitlement) -> int:
            if kind == "copilot_minute":
                return max(0, (entitlement.copilot_minutes_granted or 0) - entitlement.copilot_minutes_used - entitlement.copilot_minutes_locked)
            if kind == "screen_assist":
                return max(0, (entitlement.screen_assist_uses_granted or 0) - entitlement.screen_assist_uses_used - entitlement.screen_assist_uses_locked)
            return max(0, entitlement.knowledge_tokens_granted - entitlement.knowledge_tokens_used - entitlement.knowledge_tokens_locked)
        remaining = sum(remaining_for(e) for e in active)
        return {"unlimited": False, "remaining": remaining}

    @staticmethod
    def _entitlement_from_plan(*, user_id: str, plan: GlobalPlan, source_kind: str, source_id: str, starts_at_ms: int, ends_at_ms: int | None) -> GlobalEntitlement:
        return GlobalEntitlement(str(uuid4()), user_id, plan.offer_code, plan.version, source_kind, source_id, starts_at_ms, ends_at_ms, plan.copilot_minutes, plan.screen_assist_uses, plan.resume_jd_enabled, plan.knowledge_base_enabled, plan.written_exam_enabled, plan.full_product_enabled, knowledge_tokens_granted=plan.knowledge_tokens)

    @staticmethod
    def _entitlement_payload(item: GlobalEntitlement) -> dict[str, object]:
        return {
            "id": item.entitlement_id,
            "offerCode": item.offer_code,
            "planVersion": item.plan_version,
            "status": item.status,
            "startsAtMs": item.starts_at_ms,
            "endsAtMs": item.ends_at_ms,
            "copilotMinutesRemaining": None if item.copilot_minutes_granted is None else max(0, item.copilot_minutes_granted-item.copilot_minutes_used-item.copilot_minutes_locked),
            "screenAssistUsesRemaining": None if item.screen_assist_uses_granted is None else max(0, item.screen_assist_uses_granted-item.screen_assist_uses_used-item.screen_assist_uses_locked),
            "knowledgeTokensRemaining": max(0, item.knowledge_tokens_granted-item.knowledge_tokens_used-item.knowledge_tokens_locked),
            "benefits": {"copilotMinutes": item.copilot_minutes_granted, "screenAssistUses": item.screen_assist_uses_granted, "resumeAndJobDescription": item.resume_jd_enabled, "knowledgeBase": item.knowledge_base_enabled, "knowledgeTokens": item.knowledge_tokens_granted, "writtenExam": item.written_exam_enabled, "fullProduct": item.full_product_enabled},
        }

    @staticmethod
    def _order_payload(item) -> dict[str, object]:
        return {"id": item.order_id, "offerCode": item.offer_code, "planVersion": item.plan_version, "status": item.status, "amountCents": item.expected_amount_cents, "currency": item.expected_currency, "mode": item.mode, "createdAtMs": item.created_at_ms, "updatedAtMs": item.updated_at_ms, "providerOrderId": item.provider_order_id, "providerSubscriptionId": item.provider_subscription_id}

    @staticmethod
    def _subscription_payload(item) -> dict[str, object]:
        return {"id": item.subscription_id, "offerCode": item.offer_code, "status": item.status, "currentPeriodStartMs": item.current_period_start_ms, "currentPeriodEndMs": item.current_period_end_ms, "canceledAtMs": item.canceled_at_ms}
