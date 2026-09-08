from __future__ import annotations

from dataclasses import replace
from threading import RLock
from time import time

from app.services.billing_service import BillingStateRecord, KnowledgeIndexQuoteRecord, KnowledgeIndexReservationRecord, UsageReservationRecord
from app.services.global_commerce_service import GlobalCommerceService, GlobalEntitlementDenied


class GlobalUsageBillingAdapter:
    """Compatibility seam for existing AI/audio services; it never touches domestic billing tables."""

    def __init__(self, commerce: GlobalCommerceService) -> None:
        self.commerce = commerce
        self._lock = RLock()
        self._records: dict[str, UsageReservationRecord] = {}
        self._quotes: dict[str, KnowledgeIndexQuoteRecord] = {}
        self._index_reservations: dict[str, KnowledgeIndexReservationRecord] = {}

    def reserve_usage(self, *, user_id: str, usage_id: str, usage_kind: str, wallet_only: bool = False) -> UsageReservationRecord:
        with self._lock:
            existing = self._records.get(usage_id)
            if existing:
                return existing
        created = int(time() * 1000)
        mapped = "copilot_minute" if usage_kind == "realtime_minute" else "screen_assist" if usage_kind == "screenshot_answer" else None
        try:
            if mapped:
                reservation = self.commerce.reserve(user_id=user_id, kind=mapped, amount=1, operation_id=usage_id, now_ms=created)
                record = UsageReservationRecord(reservation.operation_id, usage_id, user_id, usage_kind, 0, "global_entitlement", reservation.status, created)
            else:
                state = self.commerce.state(user_id, created)
                allowed = bool(state["features"]["writtenExam"]) if usage_kind == "written_exam_entry" else bool(state["copilot"]["unlimited"] or (state["copilot"]["remaining"] or 0) > 0)
                record = UsageReservationRecord(usage_id, usage_id, user_id, usage_kind, 0, "global_entitlement", "reserved" if allowed else "insufficient_balance", created)
        except GlobalEntitlementDenied:
            record = UsageReservationRecord(usage_id, usage_id, user_id, usage_kind, 0, "global_entitlement", "insufficient_balance", created)
        with self._lock:
            self._records[usage_id] = record
        return record

    def settle_usage(self, *, usage_id: str) -> UsageReservationRecord | None:
        with self._lock:
            record = self._records.get(usage_id)
        if record is None or record.status != "reserved": return record
        if record.usage_kind in {"realtime_minute", "screenshot_answer"}:
            self.commerce.settle(operation_id=usage_id)
        settled = replace(record, status="settled", settled_at_ms=int(time() * 1000))
        with self._lock: self._records[usage_id] = settled
        return settled

    def release_usage(self, *, usage_id: str) -> UsageReservationRecord | None:
        with self._lock:
            record = self._records.get(usage_id)
        if record is None or record.status != "reserved": return record
        if record.usage_kind in {"realtime_minute", "screenshot_answer"}:
            self.commerce.release(operation_id=usage_id)
        released = replace(record, status="released", released_at_ms=int(time() * 1000))
        with self._lock: self._records[usage_id] = released
        return released

    def rates(self) -> dict[str, object]:
        return {"catalogVersion": 1, "tokenizerVersion": "global-entitlement-v1", "knowledgeIndexMinimumPoints": 0, "knowledgeIndexPointsPer1000Tokens": 0}

    def quote_knowledge_index(self, *, user_id: str, document_version_id: str, token_estimate: int, idempotency_key: str) -> KnowledgeIndexQuoteRecord:
        if not bool(self.commerce.state(user_id)["features"]["knowledgeBase"]):
            quote = KnowledgeIndexQuoteRecord(f"global-quote:{idempotency_key}", user_id, document_version_id, max(1, token_estimate), 1, "global-entitlement-v1", 1, 0, int(time() * 1000))
        else:
            quote = KnowledgeIndexQuoteRecord(f"global-quote:{idempotency_key}", user_id, document_version_id, max(1, token_estimate), 1, "global-entitlement-v1", 0, 0, int(time() * 1000))
        with self._lock: self._quotes[quote.quote_id] = quote
        return quote

    def knowledge_index_quote(self, *, user_id: str, quote_id: str, document_version_id: str | None = None) -> KnowledgeIndexQuoteRecord:
        quote = self._quotes[quote_id]
        if quote.user_id != user_id or document_version_id is not None and quote.document_version_id != document_version_id: raise PermissionError("knowledge quote ownership mismatch")
        return quote

    def reserve_knowledge_index_for_quote(self, *, user_id: str, quote_id: str, document_version_id: str) -> KnowledgeIndexReservationRecord:
        quote = self.knowledge_index_quote(user_id=user_id, quote_id=quote_id, document_version_id=document_version_id)
        allowed = bool(self.commerce.state(user_id)["features"]["knowledgeBase"])
        reservation = KnowledgeIndexReservationRecord(f"global-index:{quote_id}", quote_id, user_id, document_version_id, 0, "reserved" if allowed else "insufficient_balance", int(time() * 1000), "global_entitlement")
        with self._lock: self._index_reservations[quote_id] = reservation
        return reservation

    def settle_knowledge_index_for_document(self, *, user_id: str, document_version_id: str) -> KnowledgeIndexReservationRecord | None:
        with self._lock:
            found = next((item for item in self._index_reservations.values() if item.user_id == user_id and item.document_version_id == document_version_id), None)
            if found is None: return None
            settled = replace(found, status="settled", settled_at_ms=int(time() * 1000))
            self._index_reservations[found.quote_id] = settled
            return settled

    def release_knowledge_index_for_document(self, *, user_id: str, document_version_id: str) -> KnowledgeIndexReservationRecord | None:
        with self._lock:
            found = next((item for item in self._index_reservations.values() if item.user_id == user_id and item.document_version_id == document_version_id), None)
            if found is None: return None
            released = replace(found, status="released", released_at_ms=int(time() * 1000))
            self._index_reservations[found.quote_id] = released
            return released

    def release_knowledge_index(self, *, quote_id: str) -> KnowledgeIndexReservationRecord | None:
        with self._lock:
            found = self._index_reservations.get(quote_id)
            if found is None: return None
            released = replace(found, status="released", released_at_ms=int(time() * 1000))
            self._index_reservations[quote_id] = released
            return released

    def state_for_user(self, *, user_id: str) -> BillingStateRecord:
        state = self.commerce.state(user_id)
        active_pass = {"knowledgeAllowanceGranted": 1, "knowledgeAllowanceUsed": 0, "knowledgeAllowanceLocked": 0} if state["features"]["knowledgeBase"] else None
        return BillingStateRecord([], self.rates(), 0, [], active_pass, [], [], [], {"email": "contact@oneshowailab.com"})
