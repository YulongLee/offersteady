from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from threading import RLock
from time import time

from app.ports.global_commerce import FairUseDecision, GlobalCommerceRepository, GlobalEntitlement, GlobalOrder, GlobalPlan, GlobalProductMapping, GlobalSubscription, UsageKind, UsageReservation


def seeded_global_plans(now_ms: int | None = None) -> list[GlobalPlan]:
    created = now_ms or int(time() * 1000)
    return [
        GlobalPlan("global-free", 1, "Free", "Try OfferSteady without a card.", 0, "free", None, 15, 3, False, False, False, False, display_order=0, created_at_ms=created, knowledge_tokens=0),
        GlobalPlan("global-interview-pass", 2, "Interview Day Pass", "Focused access for your interview day.", 999, "one_time", 1, 180, None, True, False, True, False, display_order=1, created_at_ms=created, knowledge_tokens=0),
        GlobalPlan("global-pro-weekly", 2, "Pro Weekly", "Unlimited full-product access for interview week.", 4999, "one_time", 7, None, None, True, True, True, True, featured=True, display_order=2, created_at_ms=created, knowledge_tokens=50_000),
        GlobalPlan("global-pro-monthly", 2, "Pro Monthly", "Unlimited full-product access with monthly renewal.", 9999, "recurring", 30, None, None, True, True, True, True, display_order=3, created_at_ms=created, knowledge_tokens=200_000),
        GlobalPlan("global-job-hunt", 2, "Job Hunt", "Unlimited full-product access for a focused job search.", 19999, "one_time", 90, None, None, True, True, True, True, display_order=4, created_at_ms=created, knowledge_tokens=1_000_000),
    ]


class InMemoryGlobalCommerceRepository(GlobalCommerceRepository):
    def __init__(self) -> None:
        self._lock = RLock()
        self._plans = {(plan.offer_code, plan.version): plan for plan in seeded_global_plans()}
        self._entitlements: dict[str, GlobalEntitlement] = {}
        self._free_grants: dict[str, str] = {}
        self._reservations: dict[str, UsageReservation] = {}
        self._mappings: dict[tuple[str, str], GlobalProductMapping] = {}
        self._orders: dict[str, GlobalOrder] = {}
        self._subscriptions: dict[str, GlobalSubscription] = {}
        self._events: dict[tuple[str, str], dict[str, object]] = {}
        self._provider_configs = {mode: {"mode": mode, "enabled": False, "validation_status": "draft", "validation_errors": [], "credential_ciphertext": None, "api_key_fingerprint": None, "webhook_secret_fingerprint": None, "connection_checked_at_ms": None} for mode in ("test", "live")}
        self._fair_use: dict[str, FairUseDecision] = {}

    @contextmanager
    def transaction(self):
        """Mirror the all-or-nothing webhook contract used by Postgres."""
        with self._lock:
            snapshot = deepcopy((self._plans, self._entitlements, self._free_grants, self._reservations, self._mappings, self._orders, self._subscriptions, self._events, self._provider_configs, self._fair_use))
            try:
                yield
            except Exception:
                (self._plans, self._entitlements, self._free_grants, self._reservations, self._mappings, self._orders, self._subscriptions, self._events, self._provider_configs, self._fair_use) = snapshot
                raise

    def active_plans(self) -> list[GlobalPlan]:
        with self._lock:
            return sorted((p for p in self._plans.values() if p.status == "active"), key=lambda p: (p.display_order, p.offer_code))

    def plan(self, offer_code: str, version: int | None = None) -> GlobalPlan | None:
        with self._lock:
            candidates = [p for (code, _), p in self._plans.items() if code == offer_code and (version is None and p.status == "active" or p.version == version)]
            return max(candidates, key=lambda p: p.version, default=None)

    def save_draft(self, plan: GlobalPlan) -> GlobalPlan:
        if plan.status != "draft":
            raise ValueError("new plan versions must begin as draft")
        with self._lock:
            key = (plan.offer_code, plan.version)
            if key in self._plans:
                raise ValueError("plan version already exists")
            self._plans[key] = plan
            return plan

    def publish(self, offer_code: str, version: int) -> GlobalPlan:
        with self._lock:
            key = (offer_code, version)
            draft = self._plans.get(key)
            if draft is None or draft.status != "draft":
                raise ValueError("publish target must be an existing draft")
            for existing_key, existing in tuple(self._plans.items()):
                if existing.offer_code == offer_code and existing.status == "active":
                    self._plans[existing_key] = replace(existing, status="retired")
            published = replace(draft, status="active")
            self._plans[key] = published
            return published

    def entitlements_for_user(self, user_id: str) -> list[GlobalEntitlement]:
        with self._lock:
            return [e for e in self._entitlements.values() if e.user_id == user_id]

    def grant_entitlement(self, entitlement: GlobalEntitlement) -> GlobalEntitlement:
        with self._lock:
            if entitlement.entitlement_id in self._entitlements:
                return self._entitlements[entitlement.entitlement_id]
            source = (entitlement.source_kind, entitlement.source_id)
            existing = next((e for e in self._entitlements.values() if (e.source_kind, e.source_id) == source), None)
            if existing:
                return existing
            self._entitlements[entitlement.entitlement_id] = entitlement
            return entitlement

    def initial_free_grant(self, user_id: str) -> GlobalEntitlement | None:
        with self._lock:
            entitlement_id = self._free_grants.get(user_id)
            return self._entitlements.get(entitlement_id) if entitlement_id else None

    def record_initial_free_grant(self, user_id: str, entitlement: GlobalEntitlement) -> GlobalEntitlement:
        with self._lock:
            existing = self.initial_free_grant(user_id)
            if existing:
                return existing
            stored = self.grant_entitlement(entitlement)
            self._free_grants[user_id] = stored.entitlement_id
            return stored

    def reservation(self, operation_id: str) -> UsageReservation | None:
        with self._lock:
            return self._reservations.get(operation_id)

    def reserve_usage(self, reservation: UsageReservation) -> UsageReservation:
        with self._lock:
            existing = self._reservations.get(reservation.operation_id)
            if existing:
                return existing
            self._reservations[reservation.operation_id] = reservation
            return reservation

    def reserve_usage_atomic(self, *, user_id: str, usage_kind: UsageKind, amount: int, operation_id: str, created_at_ms: int) -> UsageReservation:
        with self._lock:
            existing = self._reservations.get(operation_id)
            if existing:
                if existing.user_id != user_id or existing.usage_kind != usage_kind or existing.amount != amount:
                    raise ValueError("idempotency key was reused with different usage")
                return existing
            candidates = sorted(
                (
                    entitlement
                    for entitlement in self._entitlements.values()
                    if entitlement.user_id == user_id
                    and entitlement.status == "active"
                    and entitlement.starts_at_ms <= created_at_ms
                    and (entitlement.ends_at_ms is None or entitlement.ends_at_ms > created_at_ms)
                ),
                key=lambda entitlement: (entitlement.ends_at_ms is None, entitlement.ends_at_ms or 2**63, -entitlement.starts_at_ms),
            )
            for entitlement in candidates:
                if usage_kind == "copilot_minute":
                    limit, used, locked = entitlement.copilot_minutes_granted, entitlement.copilot_minutes_used, entitlement.copilot_minutes_locked
                elif usage_kind == "screen_assist":
                    limit, used, locked = entitlement.screen_assist_uses_granted, entitlement.screen_assist_uses_used, entitlement.screen_assist_uses_locked
                else:
                    limit, used, locked = entitlement.knowledge_tokens_granted, entitlement.knowledge_tokens_used, entitlement.knowledge_tokens_locked
                if limit is not None and limit - used - locked < amount:
                    continue
                self._entitlements[entitlement.entitlement_id] = entitlement.with_usage(kind=usage_kind, locked_delta=amount)
                reservation = UsageReservation(operation_id, user_id, entitlement.entitlement_id, usage_kind, amount, "reserved", created_at_ms)
                self._reservations[operation_id] = reservation
                return reservation
            raise LookupError(f"insufficient {usage_kind} entitlement")

    def update_reservation(self, reservation: UsageReservation) -> UsageReservation:
        with self._lock:
            if reservation.operation_id not in self._reservations:
                raise KeyError(reservation.operation_id)
            self._reservations[reservation.operation_id] = reservation
            return reservation

    def finalize_usage_atomic(self, *, operation_id: str, outcome: str, actual_amount: int | None = None, finalized_at_ms: int) -> UsageReservation:
        with self._lock:
            reservation = self._reservations.get(operation_id)
            if reservation is None:
                raise KeyError(operation_id)
            if reservation.status != "reserved":
                return reservation
            entitlement = self._entitlements[reservation.entitlement_id]
            used = reservation.amount if actual_amount is None else max(0, actual_amount)
            self._entitlements[entitlement.entitlement_id] = entitlement.with_usage(kind=reservation.usage_kind, locked_delta=-reservation.amount, used_delta=used if outcome == "settled" else 0)
            finalized = replace(reservation, status=outcome)
            self._reservations[operation_id] = finalized
            return finalized

    def update_entitlement(self, entitlement: GlobalEntitlement) -> GlobalEntitlement:
        with self._lock:
            if entitlement.entitlement_id not in self._entitlements:
                raise KeyError(entitlement.entitlement_id)
            self._entitlements[entitlement.entitlement_id] = entitlement
            return entitlement

    def provider_mapping(self, mode: str, offer_code: str) -> GlobalProductMapping | None:
        with self._lock:
            return self._mappings.get((mode, offer_code))

    def save_provider_mapping(self, mapping: GlobalProductMapping) -> GlobalProductMapping:
        with self._lock:
            self._mappings[(mapping.mode, mapping.offer_code)] = mapping
            self._provider_configs[mapping.mode].update({"enabled": False, "validation_status": "draft"})
            return mapping

    def order_for_idempotency(self, user_id: str, idempotency_key: str) -> GlobalOrder | None:
        with self._lock:
            return next((order for order in self._orders.values() if order.user_id == user_id and order.idempotency_key == idempotency_key), None)

    def order(self, order_id: str) -> GlobalOrder | None:
        with self._lock:
            return self._orders.get(order_id)

    def order_by_provider_order(self, *, mode: str, provider_order_id: str) -> GlobalOrder | None:
        with self._lock:
            return next((item for item in self._orders.values() if item.mode == mode and item.provider_order_id == provider_order_id), None)

    def order_by_provider_subscription(self, *, mode: str, provider_subscription_id: str) -> GlobalOrder | None:
        with self._lock:
            return next((item for item in self._orders.values() if item.mode == mode and item.provider_subscription_id == provider_subscription_id), None)

    def save_order(self, order: GlobalOrder) -> GlobalOrder:
        with self._lock:
            existing = self.order_for_idempotency(order.user_id, order.idempotency_key)
            if existing:
                return existing
            self._orders[order.order_id] = order
            return order

    def update_order(self, order: GlobalOrder) -> GlobalOrder:
        with self._lock:
            if order.order_id not in self._orders:
                raise KeyError(order.order_id)
            self._orders[order.order_id] = order
            return order

    def orders_for_user(self, user_id: str) -> list[GlobalOrder]:
        with self._lock:
            return sorted((item for item in self._orders.values() if item.user_id == user_id), key=lambda item: item.created_at_ms, reverse=True)

    def recent_orders(self, *, limit: int = 100) -> list[GlobalOrder]:
        with self._lock:
            return sorted(self._orders.values(), key=lambda item: item.created_at_ms, reverse=True)[:limit]

    def subscription_by_provider_id(self, *, mode: str, provider_subscription_id: str) -> GlobalSubscription | None:
        with self._lock:
            return next((item for item in self._subscriptions.values() if item.mode == mode and item.provider_subscription_id == provider_subscription_id), None)

    def subscriptions_for_user(self, user_id: str) -> list[GlobalSubscription]:
        with self._lock:
            return sorted((item for item in self._subscriptions.values() if item.user_id == user_id), key=lambda item: item.updated_at_ms, reverse=True)

    def recent_subscriptions(self, *, limit: int = 100) -> list[GlobalSubscription]:
        with self._lock:
            return sorted(self._subscriptions.values(), key=lambda item: item.updated_at_ms, reverse=True)[:limit]

    def upsert_subscription(self, subscription: GlobalSubscription) -> GlobalSubscription:
        with self._lock:
            existing = self.subscription_by_provider_id(mode=subscription.mode, provider_subscription_id=subscription.provider_subscription_id)
            if existing and existing.provider_updated_at_ms > subscription.provider_updated_at_ms:
                return existing
            stored = replace(subscription, subscription_id=existing.subscription_id, created_at_ms=existing.created_at_ms) if existing else subscription
            self._subscriptions[stored.subscription_id] = stored
            return stored

    def revoke_entitlements_for_source(self, *, source_kind: str, source_id_prefix: str) -> int:
        with self._lock:
            matched = [item for item in self._entitlements.values() if item.source_kind == source_kind and item.source_id.startswith(source_id_prefix) and item.status != "revoked"]
            for item in matched:
                self._entitlements[item.entitlement_id] = replace(item, status="revoked")
            return len(matched)

    def record_provider_event_once(self, *, mode: str, event_id: str, event_type: str, payload_sha256: str, provider_created_at_ms: int, received_at_ms: int, order_id: str | None) -> bool:
        with self._lock:
            key = (mode, event_id)
            existing = self._events.get(key)
            if existing:
                # Creem retries failed deliveries. Reclaim only the exact same
                # payload; a reused provider event ID with different bytes is not
                # trusted and remains a duplicate.
                if existing.get("status") == "failed" and existing.get("payload_sha256") == payload_sha256:
                    existing.update({"status": "processing", "received_at_ms": received_at_ms, "error_code": None})
                    return True
                return False
            self._events[key] = {"event_type": event_type, "payload_sha256": payload_sha256, "status": "processing", "order_id": order_id, "received_at_ms": received_at_ms, "provider_created_at_ms": provider_created_at_ms}
            return True

    def mark_provider_event(self, *, mode: str, event_id: str, status: str, processed_at_ms: int, error_code: str | None = None) -> None:
        with self._lock:
            self._events[(mode, event_id)].update({"status": status, "processed_at_ms": processed_at_ms, "error_code": error_code})

    def recent_provider_events(self, *, mode: str, limit: int = 100) -> list[dict[str, object]]:
        with self._lock:
            rows = [dict(value, provider_event_id=event_id, mode=event_mode) for (event_mode, event_id), value in self._events.items() if event_mode == mode]
            return sorted(rows, key=lambda item: int(item.get("received_at_ms", 0)), reverse=True)[:limit]

    def provider_config(self, mode: str) -> dict[str, object]:
        with self._lock:
            return dict(self._provider_configs[mode])

    def save_provider_credentials(self, *, mode: str, credential_ciphertext: str, api_key_fingerprint: str, webhook_secret_fingerprint: str, updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]:
        with self._lock:
            self._provider_configs[mode].update({"credential_ciphertext": credential_ciphertext, "api_key_fingerprint": api_key_fingerprint, "webhook_secret_fingerprint": webhook_secret_fingerprint, "enabled": False, "validation_status": "draft", "validation_errors": [], "connection_checked_at_ms": None, "updated_by_user_id": updated_by_user_id, "updated_at_ms": updated_at_ms})
            return dict(self._provider_configs[mode])

    def mark_provider_connection_checked(self, *, mode: str, checked_at_ms: int, validation_status: str, validation_errors: list[str]) -> dict[str, object]:
        with self._lock:
            self._provider_configs[mode].update({"connection_checked_at_ms": checked_at_ms, "validation_status": validation_status, "validation_errors": list(validation_errors)})
            return dict(self._provider_configs[mode])

    def set_provider_enabled(self, *, mode: str, enabled: bool, validation_status: str, validation_errors: list[str], updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]:
        with self._lock:
            self._provider_configs[mode].update({"enabled": enabled, "validation_status": validation_status, "validation_errors": list(validation_errors), "updated_by_user_id": updated_by_user_id, "updated_at_ms": updated_at_ms})
            return dict(self._provider_configs[mode])

    def active_fair_use_decision(self, user_id: str, now_ms: int) -> FairUseDecision | None:
        with self._lock:
            decisions = [item for item in self._fair_use.values() if item.user_id == user_id and item.status in {"review", "restricted"} and item.effective_at_ms <= now_ms and (item.expires_at_ms is None or item.expires_at_ms > now_ms)]
            return max(decisions, key=lambda item: item.effective_at_ms, default=None)

    def save_fair_use_decision(self, decision: FairUseDecision) -> FairUseDecision:
        with self._lock:
            self._fair_use[decision.decision_id] = decision
            return decision

    def recent_fair_use_decisions(self, *, limit: int = 100) -> list[FairUseDecision]:
        with self._lock:
            return sorted(self._fair_use.values(), key=lambda item: item.effective_at_ms, reverse=True)[:limit]
