from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from uuid import uuid4

from app.core.config import Settings


WELCOME_GRANT_POINTS = 200
DEFAULT_REDEMPTION_CODE_POINTS = {
    "OFFERSTEADY-DEMO": 120,
    "SYNTHETIC-DEMO": 120,
}


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True)
class BillingProductRecord:
    id: str
    catalog_version: int
    kind: str
    display_name: str
    price_cents: int
    points: int | None = None
    duration_days: int | None = None
    knowledge_index_allowance: int | None = None
    published: bool = True


@dataclass(frozen=True)
class PointsLedgerRecord:
    id: str
    user_id: str
    kind: str
    points: int
    created_at_ms: int
    reference_id: str
    description: str


@dataclass(frozen=True)
class BillingStateRecord:
    catalog: list[BillingProductRecord]
    rates: dict[str, object]
    balance: int
    ledger: list[PointsLedgerRecord]
    active_pass: dict[str, object] | None
    queued_passes: list[dict[str, object]]
    orders: list[dict[str, object]]
    official_orders: list[dict[str, object]]
    support: dict[str, object]


@dataclass(frozen=True)
class PointsRedemptionRecord:
    redemption_id: str
    points: int
    new_balance: int
    public_hint: str
    redeemed_at_ms: int
    ledger_entry: PointsLedgerRecord


@dataclass(frozen=True)
class KnowledgeIndexQuoteRecord:
    quote_id: str
    user_id: str
    document_version_id: str
    token_estimate: int
    catalog_version: int
    tokenizer_version: str
    points_required: int
    projected_balance: int
    created_at_ms: int


@dataclass(frozen=True)
class KnowledgeIndexReservationRecord:
    reservation_id: str
    quote_id: str
    user_id: str
    document_version_id: str
    points_reserved: int
    status: str
    created_at_ms: int
    settled_at_ms: int | None = None
    released_at_ms: int | None = None


@dataclass(frozen=True)
class TimePassEntitlementRecord:
    id: str
    user_id: str
    product_id: str
    starts_at_ms: int
    ends_at_ms: int
    order_id: str
    knowledge_allowance_granted: int
    knowledge_allowance_used: int = 0
    knowledge_allowance_locked: int = 0


@dataclass(frozen=True)
class OfficialCheckoutOrderRecord:
    id: str
    user_id: str
    product: BillingProductRecord
    amount_cents: int
    currency: str
    channel: str
    status: str
    action: dict[str, object]
    created_at_ms: int
    updated_at_ms: int
    provider_trade_no: str | None = None
    paid_at_ms: int | None = None


class BillingService:
    def __init__(self, settings: Settings | None = None) -> None:
        configured_codes = settings.redemption_code_points if settings is not None else {}
        self.redemption_code_points: dict[str, int] = {
            **DEFAULT_REDEMPTION_CODE_POINTS,
            **{code.strip().upper(): int(points) for code, points in configured_codes.items() if code.strip() and int(points) > 0},
        }
        self.ledger_by_user: dict[str, list[PointsLedgerRecord]] = {}
        self.redemptions_by_user_and_key: dict[tuple[str, str], dict[str, object]] = {}
        self.redemptions_by_user_and_code: dict[tuple[str, str], PointsRedemptionRecord] = {}
        self.redemptions_by_code: dict[str, PointsRedemptionRecord] = {}
        self.index_quotes_by_user_and_key: dict[tuple[str, str], KnowledgeIndexQuoteRecord] = {}
        self.index_quotes_by_id: dict[str, KnowledgeIndexQuoteRecord] = {}
        self.index_reservations_by_quote: dict[str, KnowledgeIndexReservationRecord] = {}
        self.checkout_orders_by_id: dict[str, OfficialCheckoutOrderRecord] = {}
        self.checkout_orders_by_user_and_key: dict[tuple[str, str], str] = {}
        self.pass_entitlements_by_user: dict[str, list[TimePassEntitlementRecord]] = {}

    def state_for_user(self, *, user_id: str) -> BillingStateRecord:
        self._ensure_welcome_grant(user_id=user_id)
        ledger = sorted(self.ledger_by_user.get(user_id, []), key=lambda item: item.created_at_ms, reverse=True)
        return BillingStateRecord(
            catalog=self.catalog(),
            rates=self.rates(),
            balance=sum(item.points for item in ledger),
            ledger=ledger,
            active_pass=self._active_pass_payload(user_id=user_id),
            queued_passes=self._queued_pass_payloads(user_id=user_id),
            orders=[],
            official_orders=[
                self._official_order_payload(item)
                for item in sorted(self.checkout_orders_by_id.values(), key=lambda order: order.created_at_ms, reverse=True)
                if item.user_id == user_id
            ],
            support={
                "wechatId": "offersteady_support",
                "qrAssetPath": "/support/wechat-placeholder.png",
                "serviceHours": "工作日 10:00-18:00",
                "refundSummary": "退款按订单状态和未使用权益审核",
            },
        )

    def public_state(self) -> BillingStateRecord:
        return BillingStateRecord(
            catalog=self.catalog(),
            rates=self.rates(),
            balance=0,
            ledger=[],
            active_pass=None,
            queued_passes=[],
            orders=[],
            official_orders=[],
            support={
                "wechatId": "offersteady_support",
                "qrAssetPath": "/support/wechat-placeholder.png",
                "serviceHours": "工作日 10:00-18:00",
                "refundSummary": "退款按订单状态和未使用权益审核",
            },
        )

    def redeem_points(self, *, user_id: str, code: str, idempotency_key: str) -> dict[str, object]:
        normalized_code = code.strip().upper()
        request_key = (user_id, idempotency_key)
        replay = self.redemptions_by_user_and_key.get(request_key)
        if replay is not None:
            return replay
        if normalized_code == "SYNTHETIC-LIMIT":
            result: dict[str, object] = {"outcome": "rate-limited", "retryAfterMs": 30_000}
            self.redemptions_by_user_and_key[request_key] = result
            return result
        if normalized_code in {"SYNTHETIC-OUTAGE", "API-OUTAGE"}:
            result = {"outcome": "temporarily-unavailable"}
            self.redemptions_by_user_and_key[request_key] = result
            return result
        points = self.redemption_code_points.get(normalized_code)
        if points is None:
            result = {"outcome": "code-unavailable"}
            self.redemptions_by_user_and_key[request_key] = result
            return result
        code_key = (user_id, normalized_code)
        existing = self.redemptions_by_user_and_code.get(code_key)
        if existing is not None:
            result = {"outcome": "already-redeemed-by-you", "data": self._redemption_payload(existing)}
            self.redemptions_by_user_and_key[request_key] = result
            return result
        if normalized_code not in DEFAULT_REDEMPTION_CODE_POINTS and normalized_code in self.redemptions_by_code:
            result = {"outcome": "code-unavailable"}
            self.redemptions_by_user_and_key[request_key] = result
            return result
        self._ensure_welcome_grant(user_id=user_id)
        redeemed_at_ms = _now_ms()
        ledger_entry = PointsLedgerRecord(
            id=f"ledger-{uuid4().hex}",
            user_id=user_id,
            kind="redemption_credit",
            points=points,
            created_at_ms=redeemed_at_ms,
            reference_id=f"redemption:{normalized_code}",
            description="兑换码积分入账",
        )
        self.ledger_by_user.setdefault(user_id, []).append(ledger_entry)
        new_balance = sum(item.points for item in self.ledger_by_user[user_id])
        redemption = PointsRedemptionRecord(
            redemption_id=f"redemption-{uuid4().hex}",
            points=points,
            new_balance=new_balance,
            public_hint=f"****-{normalized_code[-4:]}",
            redeemed_at_ms=redeemed_at_ms,
            ledger_entry=ledger_entry,
        )
        self.redemptions_by_user_and_code[code_key] = redemption
        if normalized_code not in DEFAULT_REDEMPTION_CODE_POINTS:
            self.redemptions_by_code[normalized_code] = redemption
        result = {"outcome": "redeemed", "data": self._redemption_payload(redemption)}
        self.redemptions_by_user_and_key[request_key] = result
        return result

    def create_checkout_order(
        self,
        *,
        user_id: str,
        product_id: str,
        channel: str,
        idempotency_key: str,
        payment_url: str,
        expires_at_ms: int,
    ) -> OfficialCheckoutOrderRecord:
        self._ensure_welcome_grant(user_id=user_id)
        existing_id = self.checkout_orders_by_user_and_key.get((user_id, idempotency_key))
        if existing_id:
            return self.checkout_orders_by_id[existing_id]
        product = next((item for item in self.catalog() if item.id == product_id and item.published), None)
        if product is None:
            raise ValueError("商品不可购买或已下架")
        if channel not in {"wechat", "alipay"}:
            raise ValueError("支付渠道不可用")
        now = _now_ms()
        order = OfficialCheckoutOrderRecord(
            id=f"official-order-{uuid4().hex}",
            user_id=user_id,
            product=product,
            amount_cents=product.price_cents,
            currency="CNY",
            channel=channel,
            status="payment_pending",
            action={"kind": "redirect", "url": payment_url, "expiresAtMs": expires_at_ms},
            created_at_ms=now,
            updated_at_ms=now,
        )
        self.checkout_orders_by_id[order.id] = order
        self.checkout_orders_by_user_and_key[(user_id, idempotency_key)] = order.id
        return order

    def replace_checkout_action(self, *, order_id: str, payment_url: str, expires_at_ms: int) -> OfficialCheckoutOrderRecord:
        order = self.checkout_orders_by_id[order_id]
        updated = OfficialCheckoutOrderRecord(**{**order.__dict__, "action": {"kind": "redirect", "url": payment_url, "expiresAtMs": expires_at_ms}})
        self.checkout_orders_by_id[order_id] = updated
        return updated

    def checkout_order_for_user(self, *, user_id: str, order_id: str) -> OfficialCheckoutOrderRecord:
        order = self.checkout_orders_by_id[order_id]
        if order.user_id != user_id:
            raise PermissionError("Cannot access another user's checkout order.")
        return order

    def confirm_checkout_paid(self, *, order_id: str, amount_cents: int, provider_trade_no: str) -> OfficialCheckoutOrderRecord:
        order = self.checkout_orders_by_id[order_id]
        if order.status == "paid":
            return order
        if amount_cents != order.amount_cents:
            failed = OfficialCheckoutOrderRecord(**{**order.__dict__, "status": "failed", "updated_at_ms": _now_ms(), "provider_trade_no": provider_trade_no})
            self.checkout_orders_by_id[order_id] = failed
            return failed
        paid_at_ms = _now_ms()
        if order.product.kind == "points_pack":
            reference_id = f"checkout:{order.id}"
            if not any(item.reference_id == reference_id and item.kind == "purchase_credit" for item in self.ledger_by_user.get(order.user_id, [])):
                self.ledger_by_user.setdefault(order.user_id, []).append(
                    PointsLedgerRecord(
                        id=f"ledger-{uuid4().hex}",
                        user_id=order.user_id,
                        kind="purchase_credit",
                        points=order.product.points or 0,
                        created_at_ms=paid_at_ms,
                        reference_id=reference_id,
                        description=f"购买{order.product.display_name}到账",
                    )
                )
        elif order.product.kind == "time_pass":
            self._grant_time_pass(order=order, paid_at_ms=paid_at_ms)
        paid = OfficialCheckoutOrderRecord(**{**order.__dict__, "status": "paid", "updated_at_ms": paid_at_ms, "provider_trade_no": provider_trade_no, "paid_at_ms": paid_at_ms})
        self.checkout_orders_by_id[order_id] = paid
        return paid

    def catalog(self) -> list[BillingProductRecord]:
        return [
            BillingProductRecord(id="pass-3", catalog_version=4, kind="time_pass", display_name="3 天会员", price_cents=6990, duration_days=3, knowledge_index_allowance=0),
            BillingProductRecord(id="pass-7", catalog_version=4, kind="time_pass", display_name="7 天会员", price_cents=12990, duration_days=7, knowledge_index_allowance=0),
            BillingProductRecord(id="pass-15", catalog_version=4, kind="time_pass", display_name="15 天会员", price_cents=21990, duration_days=15, knowledge_index_allowance=2),
            BillingProductRecord(id="pass-30", catalog_version=4, kind="time_pass", display_name="30 天会员", price_cents=32990, duration_days=30, knowledge_index_allowance=2),
            BillingProductRecord(id="points-300", catalog_version=4, kind="points_pack", display_name="300 点", price_cents=3990, points=300),
            BillingProductRecord(id="points-800", catalog_version=4, kind="points_pack", display_name="800 点", price_cents=8990, points=800),
            BillingProductRecord(id="points-2000", catalog_version=4, kind="points_pack", display_name="2000 点", price_cents=19990, points=2000),
        ]

    def rates(self) -> dict[str, object]:
        return {
            "catalogVersion": 4,
            "answerPoints": 5,
            "screenshotAnswerPoints": 15,
            "knowledgeIndexMinimumPoints": 20,
            "knowledgeIndexPointsPer1000Tokens": 4,
            "tokenizerVersion": "mvp-v1",
        }

    def quote_knowledge_index(self, *, user_id: str, document_version_id: str, token_estimate: int, idempotency_key: str) -> KnowledgeIndexQuoteRecord:
        self._ensure_welcome_grant(user_id=user_id)
        request_key = (user_id, idempotency_key)
        existing = self.index_quotes_by_user_and_key.get(request_key)
        if existing is not None:
            return existing
        rates = self.rates()
        points_per_5000 = int(rates["knowledgeIndexPointsPer1000Tokens"]) * 5
        minimum = int(rates["knowledgeIndexMinimumPoints"])
        points_required = max(minimum, ((max(1, token_estimate) + 4999) // 5000) * points_per_5000)
        balance = sum(item.points for item in self.ledger_by_user.get(user_id, []))
        quote = KnowledgeIndexQuoteRecord(
            quote_id=f"index-quote-{uuid4().hex}",
            user_id=user_id,
            document_version_id=document_version_id,
            token_estimate=max(1, token_estimate),
            catalog_version=int(rates["catalogVersion"]),
            tokenizer_version=str(rates["tokenizerVersion"]),
            points_required=points_required,
            projected_balance=balance - points_required,
            created_at_ms=_now_ms(),
        )
        self.index_quotes_by_user_and_key[request_key] = quote
        self.index_quotes_by_id[quote.quote_id] = quote
        return quote

    def reserve_knowledge_index(self, *, user_id: str, quote_id: str) -> KnowledgeIndexReservationRecord:
        quote = self.index_quotes_by_id[quote_id]
        if quote.user_id != user_id:
            raise PermissionError("Cannot reserve another user's knowledge index quote.")
        existing = self.index_reservations_by_quote.get(quote_id)
        if existing is not None:
            return existing
        balance = sum(item.points for item in self.ledger_by_user.get(user_id, []))
        if balance < quote.points_required:
            return KnowledgeIndexReservationRecord(
                reservation_id=f"index-reservation-{uuid4().hex}",
                quote_id=quote.quote_id,
                user_id=user_id,
                document_version_id=quote.document_version_id,
                points_reserved=quote.points_required,
                status="insufficient_balance",
                created_at_ms=_now_ms(),
            )
        reservation = KnowledgeIndexReservationRecord(
            reservation_id=f"index-reservation-{uuid4().hex}",
            quote_id=quote.quote_id,
            user_id=user_id,
            document_version_id=quote.document_version_id,
            points_reserved=quote.points_required,
            status="reserved",
            created_at_ms=_now_ms(),
        )
        self.index_reservations_by_quote[quote_id] = reservation
        return reservation

    def settle_knowledge_index(self, *, quote_id: str, reference_id: str) -> KnowledgeIndexReservationRecord | None:
        reservation = self.index_reservations_by_quote.get(quote_id)
        if reservation is None or reservation.status != "reserved":
            return reservation
        if any(item.reference_id == reference_id and item.kind == "knowledge_index_settlement" for item in self.ledger_by_user.get(reservation.user_id, [])):
            return reservation
        settled_at_ms = _now_ms()
        self.ledger_by_user.setdefault(reservation.user_id, []).append(
            PointsLedgerRecord(
                id=f"ledger-{uuid4().hex}",
                user_id=reservation.user_id,
                kind="knowledge_index_settlement",
                points=-reservation.points_reserved,
                created_at_ms=settled_at_ms,
                reference_id=reference_id,
                description="知识资料索引结算",
            )
        )
        settled = KnowledgeIndexReservationRecord(**{**reservation.__dict__, "status": "settled", "settled_at_ms": settled_at_ms})
        self.index_reservations_by_quote[quote_id] = settled
        return settled

    def release_knowledge_index(self, *, quote_id: str) -> KnowledgeIndexReservationRecord | None:
        reservation = self.index_reservations_by_quote.get(quote_id)
        if reservation is None or reservation.status != "reserved":
            return reservation
        released = KnowledgeIndexReservationRecord(**{**reservation.__dict__, "status": "released", "released_at_ms": _now_ms()})
        self.index_reservations_by_quote[quote_id] = released
        return released

    def _ensure_welcome_grant(self, *, user_id: str) -> None:
        ledger = self.ledger_by_user.setdefault(user_id, [])
        if any(item.kind == "welcome_grant" for item in ledger):
            return
        ledger.append(
            PointsLedgerRecord(
                id=f"ledger-welcome-{uuid4().hex}",
                user_id=user_id,
                kind="welcome_grant",
                points=WELCOME_GRANT_POINTS,
                created_at_ms=_now_ms(),
                reference_id=f"welcome:{user_id}",
                description="新用户赠送积分",
            )
        )

    def _redemption_payload(self, redemption: PointsRedemptionRecord) -> dict[str, object]:
        return {
            "redemptionId": redemption.redemption_id,
            "points": redemption.points,
            "newBalance": redemption.new_balance,
            "publicHint": redemption.public_hint,
            "redeemedAtMs": redemption.redeemed_at_ms,
            "ledgerEntry": self._ledger_payload(redemption.ledger_entry),
        }

    def _ledger_payload(self, item: PointsLedgerRecord) -> dict[str, object]:
        return {
            "id": item.id,
            "userId": item.user_id,
            "kind": item.kind,
            "points": item.points,
            "createdAtMs": item.created_at_ms,
            "referenceId": item.reference_id,
            "description": item.description,
        }

    def _grant_time_pass(self, *, order: OfficialCheckoutOrderRecord, paid_at_ms: int) -> None:
        if any(item.order_id == order.id for item in self.pass_entitlements_by_user.get(order.user_id, [])):
            return
        existing = self.pass_entitlements_by_user.setdefault(order.user_id, [])
        latest_end = max([paid_at_ms, *[item.ends_at_ms for item in existing if item.ends_at_ms > paid_at_ms]])
        starts_at_ms = latest_end
        duration_ms = (order.product.duration_days or 0) * 86_400_000
        existing.append(
            TimePassEntitlementRecord(
                id=f"entitlement-{uuid4().hex}",
                user_id=order.user_id,
                product_id=order.product.id,
                starts_at_ms=starts_at_ms,
                ends_at_ms=starts_at_ms + duration_ms,
                order_id=order.id,
                knowledge_allowance_granted=order.product.knowledge_index_allowance or 0,
            )
        )

    def _pass_payload(self, item: TimePassEntitlementRecord) -> dict[str, object]:
        return {
            "id": item.id,
            "userId": item.user_id,
            "productId": item.product_id,
            "startsAtMs": item.starts_at_ms,
            "endsAtMs": item.ends_at_ms,
            "orderId": item.order_id,
            "knowledgeAllowanceGranted": item.knowledge_allowance_granted,
            "knowledgeAllowanceUsed": item.knowledge_allowance_used,
            "knowledgeAllowanceLocked": item.knowledge_allowance_locked,
        }

    def _active_pass_payload(self, *, user_id: str) -> dict[str, object] | None:
        now = _now_ms()
        active = next((item for item in sorted(self.pass_entitlements_by_user.get(user_id, []), key=lambda pass_item: pass_item.starts_at_ms) if item.starts_at_ms <= now < item.ends_at_ms), None)
        return self._pass_payload(active) if active else None

    def _queued_pass_payloads(self, *, user_id: str) -> list[dict[str, object]]:
        now = _now_ms()
        return [self._pass_payload(item) for item in sorted(self.pass_entitlements_by_user.get(user_id, []), key=lambda pass_item: pass_item.starts_at_ms) if item.starts_at_ms > now]

    def _product_payload(self, item: BillingProductRecord) -> dict[str, object]:
        return {
            "id": item.id,
            "catalogVersion": item.catalog_version,
            "kind": item.kind,
            "displayName": item.display_name,
            "priceCents": item.price_cents,
            **({"points": item.points} if item.points is not None else {}),
            **({"durationDays": item.duration_days} if item.duration_days is not None else {}),
            **({"knowledgeIndexAllowance": item.knowledge_index_allowance} if item.knowledge_index_allowance is not None else {}),
            "published": item.published,
        }

    def _official_order_payload(self, item: OfficialCheckoutOrderRecord) -> dict[str, object]:
        return {
            "id": item.id,
            "userId": item.user_id,
            "product": self._product_payload(item.product),
            "amountCents": item.amount_cents,
            "currency": item.currency,
            "channel": item.channel,
            "status": item.status,
            "action": item.action,
            "createdAtMs": item.created_at_ms,
            "updatedAtMs": item.updated_at_ms,
        }

    def state_payload(self, state: BillingStateRecord) -> dict[str, object]:
        return {
            "catalog": [
                self._product_payload(item)
                for item in state.catalog
            ],
            "rates": state.rates,
            "balance": state.balance,
            "ledger": [self._ledger_payload(item) for item in state.ledger],
            "activePass": state.active_pass,
            "queuedPasses": state.queued_passes,
            "orders": state.orders,
            "officialOrders": state.official_orders,
            "support": state.support,
        }
