from __future__ import annotations

from dataclasses import dataclass, field
import secrets
from time import time
from typing import Callable
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.authentication import AuthenticationRepository
from app.ports.billing_persistence import BillingPersistencePort
from app.ports.points_redemption import PersistedPointsLedgerEntry, PersistedPointsRedemption, PointsRedemptionRepository


WELCOME_GRANT_POINTS = 200
REFERRAL_ACTIVATION_WINDOW_MS = 72 * 60 * 60 * 1000
KNOWLEDGE_INDEX_QUOTE_TTL_MS = 15 * 60 * 1000
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
    billing_source: str = "points"
    entitlement_id: str | None = None
    allowance_reserved: int = 0
    settled_at_ms: int | None = None
    released_at_ms: int | None = None


@dataclass(frozen=True)
class UsageReservationRecord:
    reservation_id: str
    usage_id: str
    user_id: str
    usage_kind: str
    points_reserved: int
    billing_source: str
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
    provider: str
    status: str
    action: dict[str, object]
    created_at_ms: int
    updated_at_ms: int
    provider_trade_no: str | None = None
    paid_at_ms: int | None = None


class BillingService:
    def __init__(
        self,
        settings: Settings | None = None,
        redemption_repository: PointsRedemptionRepository | None = None,
        billing_repository: BillingPersistencePort | None = None,
        authentication_repository: AuthenticationRepository | None = None,
        now_ms_provider: Callable[[], int] | None = None,
    ) -> None:
        self.settings = settings
        configured_codes = settings.redemption_code_points if settings is not None else {}
        self.redemption_code_points: dict[str, int] = {
            **(DEFAULT_REDEMPTION_CODE_POINTS if settings is None or settings.environment != "production" else {}),
            **{code.strip().upper(): int(points) for code, points in configured_codes.items() if code.strip() and int(points) > 0},
        }
        self.redemption_repository = redemption_repository
        self.billing_repository = billing_repository
        self.authentication_repository = authentication_repository
        self.now_ms_provider = now_ms_provider or _now_ms
        self.support = {
            "wechatId": settings.support_wechat_id if settings is not None else "mianshiwen-cn",
            "email": settings.support_email if settings is not None else "contact@oneshowailab.com",
            "qrAssetPath": "",
            "serviceHours": "工作日 10:00-18:00",
            "refundSummary": "退款按订单状态和未使用权益审核",
        }
        if self.redemption_repository is not None:
            self.redemption_repository.sync_configured_codes({
                code: points
                for code, points in self.redemption_code_points.items()
                if code not in DEFAULT_REDEMPTION_CODE_POINTS
            })
        self.ledger_by_user: dict[str, list[PointsLedgerRecord]] = {}
        self.redemptions_by_user_and_key: dict[tuple[str, str], dict[str, object]] = {}
        self.redemptions_by_user_and_code: dict[tuple[str, str], PointsRedemptionRecord] = {}
        self.redemptions_by_code: dict[str, PointsRedemptionRecord] = {}
        self.index_quotes_by_user_and_key: dict[tuple[str, str], KnowledgeIndexQuoteRecord] = {}
        self.index_quotes_by_id: dict[str, KnowledgeIndexQuoteRecord] = {}
        self.index_reservations_by_quote: dict[str, KnowledgeIndexReservationRecord] = {}
        self.usage_reservations_by_id: dict[str, UsageReservationRecord] = {}
        self.checkout_orders_by_id: dict[str, OfficialCheckoutOrderRecord] = {}
        self.checkout_orders_by_user_and_key: dict[tuple[str, str], str] = {}
        self.pass_entitlements_by_user: dict[str, list[TimePassEntitlementRecord]] = {}
        self.referral_codes_by_user: dict[str, str] = {}
        self.referral_users_by_code: dict[str, str] = {}
        self.referral_activations_by_invitee: dict[str, dict[str, object]] = {}
        self.referral_activations_by_inviter: dict[str, list[dict[str, object]]] = {}
        self.referral_settings: dict[str, object] = {
            "enabled": False,
            "rewardPoints": 500,
            "inviterRewardPoints": 500,
            "inviteeRewardPoints": 500,
            "activationWindowDays": 3,
            "configVersion": 1,
            "updatedByUserId": None,
            "updatedAtMs": 0,
        }
        self.referral_registration_ms_by_user: dict[str, int] = {}

    def state_for_user(self, *, user_id: str) -> BillingStateRecord:
        self._release_stale_usage_reservations(user_id=user_id)
        self._ensure_welcome_grant(user_id=user_id)
        ledger = self._ledger_for_user(user_id=user_id)
        return BillingStateRecord(
            catalog=self.catalog(),
            rates=self.rates(),
            balance=sum(item.points for item in ledger),
            ledger=ledger,
            active_pass=self._active_pass_payload(user_id=user_id),
            queued_passes=self._queued_pass_payloads(user_id=user_id),
            orders=[],
            official_orders=[self._official_order_payload(item) for item in self._orders_for_user(user_id=user_id)],
            support=dict(self.support),
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
            support=dict(self.support),
        )

    def referral_status(self, *, user_id: str) -> dict[str, object]:
        self._require_persistent_referrals()
        now_ms = self.now_ms_provider()
        code = self._referral_code_for_user(user_id=user_id)
        if self.billing_repository is not None:
            status = self.billing_repository.referral_status(user_id=user_id)
        else:
            activations = self.referral_activations_by_inviter.get(user_id, [])
            status = {
                **self.referral_settings,
                "inviteCount": len(activations),
                "totalRewardPoints": sum(int(item["inviterRewardPoints"]) for item in activations),
                "hasActivatedReferral": user_id in self.referral_activations_by_invitee,
                "activatedReward": self._activated_reward(user_id=user_id),
            }
        created_at_ms = self._user_created_at_ms(user_id=user_id, observed_at_ms=now_ms)
        deadline_ms = None if created_at_ms is None else created_at_ms + REFERRAL_ACTIVATION_WINDOW_MS
        status.update(self._referral_eligibility(status=status, now_ms=now_ms, deadline_ms=deadline_ms))
        public_base_url = (self.settings.public_web_base_url if self.settings is not None else "http://127.0.0.1:5173").rstrip("/")
        return {
            **status,
            "referralCode": code,
            "shareUrl": f"{public_base_url}/invite/{code}",
        }

    def resolve_referral(self, *, referral_code: str) -> dict[str, object]:
        self._require_persistent_referrals()
        code = referral_code.strip()
        if len(code) < 12 or len(code) > 48:
            return {"valid": False, "enabled": False}
        if self.billing_repository is not None:
            resolved = self.billing_repository.resolve_referral_code(referral_code=code)
            if resolved is None:
                return {"valid": False, "enabled": False}
            return {
                "valid": True,
                "enabled": bool(resolved["enabled"]),
                "rewardPoints": int(resolved["reward_points"]),
                "inviterRewardPoints": int(resolved["reward_points"]),
                "inviteeRewardPoints": int(resolved["invitee_reward_points"]),
                "activationWindowDays": 3,
            }
        inviter_user_id = self.referral_users_by_code.get(code)
        return {
            "valid": inviter_user_id is not None,
            "enabled": inviter_user_id is not None and bool(self.referral_settings["enabled"]),
            "rewardPoints": int(self.referral_settings["rewardPoints"]),
            "inviterRewardPoints": int(self.referral_settings["inviterRewardPoints"]),
            "inviteeRewardPoints": int(self.referral_settings["inviteeRewardPoints"]),
            "activationWindowDays": 3,
        }

    def activate_referral(self, *, invitee_user_id: str, referral_code: str) -> dict[str, object]:
        self._require_persistent_referrals()
        code = referral_code.strip()
        activated_at_ms = self.now_ms_provider()
        registered_at_ms = self._user_created_at_ms(user_id=invitee_user_id, observed_at_ms=activated_at_ms)
        deadline_ms = None if registered_at_ms is None else registered_at_ms + REFERRAL_ACTIVATION_WINDOW_MS
        if self.billing_repository is not None:
            return self.billing_repository.activate_referral(
                invitee_user_id=invitee_user_id,
                referral_code=code,
                activated_at_ms=activated_at_ms,
                invitee_registered_at_ms=registered_at_ms,
                activation_deadline_ms=deadline_ms,
            )
        inviter_user_id = self.referral_users_by_code.get(code)
        if inviter_user_id is None:
            return {"outcome": "invalid-code"}
        if inviter_user_id == invitee_user_id:
            return {"outcome": "self-referral"}
        existing = self.referral_activations_by_invitee.get(invitee_user_id)
        if existing is not None:
            same_code = existing["referralCode"] == code
            return {
                "outcome": "activated" if same_code else "already-activated",
                "replayed": same_code,
                "rewardPoints": int(existing["rewardPoints"]),
                "inviterRewardPoints": int(existing["inviterRewardPoints"]),
                "inviteeRewardPoints": int(existing["inviteeRewardPoints"]),
                "activatedAtMs": int(existing["activatedAtMs"]),
            }
        if registered_at_ms is None or deadline_ms is None:
            return {"outcome": "registration-time-unavailable"}
        if activated_at_ms > deadline_ms:
            return {"outcome": "activation-window-expired", "activationDeadlineMs": deadline_ms}
        if not bool(self.referral_settings["enabled"]):
            return {"outcome": "disabled"}
        reward_points = int(self.referral_settings["inviterRewardPoints"])
        invitee_reward_points = int(self.referral_settings["inviteeRewardPoints"])
        activation_id = f"referral-activation-{uuid4().hex}"
        activation = {
            "activationId": activation_id,
            "inviterUserId": inviter_user_id,
            "inviteeUserId": invitee_user_id,
            "referralCode": code,
            "rewardPoints": reward_points,
            "inviterRewardPoints": reward_points,
            "inviteeRewardPoints": invitee_reward_points,
            "configVersion": int(self.referral_settings["configVersion"]),
            "activationDeadlineMs": deadline_ms,
            "activatedAtMs": activated_at_ms,
        }
        self._ensure_welcome_grant(user_id=inviter_user_id)
        self._ensure_welcome_grant(user_id=invitee_user_id)
        inviter_reference_id = f"referral:{activation_id}:inviter"
        invitee_reference_id = f"referral:{activation_id}:invitee"
        if not any(item.reference_id == inviter_reference_id for item in self.ledger_by_user.get(inviter_user_id, [])):
            self.ledger_by_user.setdefault(inviter_user_id, []).append(PointsLedgerRecord(
                id=f"ledger-{uuid4().hex}", user_id=inviter_user_id, kind="referral_credit",
                points=reward_points, created_at_ms=activated_at_ms, reference_id=inviter_reference_id,
                description="邀请好友奖励",
            ))
        if not any(item.reference_id == invitee_reference_id for item in self.ledger_by_user.get(invitee_user_id, [])):
            self.ledger_by_user.setdefault(invitee_user_id, []).append(PointsLedgerRecord(
                id=f"ledger-{uuid4().hex}", user_id=invitee_user_id, kind="referral_invitee_credit",
                points=invitee_reward_points, created_at_ms=activated_at_ms, reference_id=invitee_reference_id,
                description="新用户邀请激活奖励",
            ))
        self.referral_activations_by_invitee[invitee_user_id] = activation
        self.referral_activations_by_inviter.setdefault(inviter_user_id, []).append(activation)
        return {
            "outcome": "activated",
            "replayed": False,
            "rewardPoints": reward_points,
            "inviterRewardPoints": reward_points,
            "inviteeRewardPoints": invitee_reward_points,
            "activatedAtMs": activated_at_ms,
            "inviterBalance": self._balance_for_user(user_id=inviter_user_id),
            "inviteeBalance": self._balance_for_user(user_id=invitee_user_id),
        }

    def growth_referral_settings(self) -> dict[str, object]:
        self._require_persistent_referrals()
        if self.billing_repository is not None:
            return self.billing_repository.growth_referral_settings()
        return dict(self.referral_settings)

    def update_growth_referral_settings(self, *, enabled: bool, reward_points: int, updated_by_user_id: str, invitee_reward_points: int | None = None) -> dict[str, object]:
        self._require_persistent_referrals()
        invitee_points = reward_points if invitee_reward_points is None else invitee_reward_points
        if isinstance(reward_points, bool) or reward_points < 1 or reward_points > 100_000:
            raise ValueError("referral_reward_points_invalid")
        if isinstance(invitee_points, bool) or invitee_points < 1 or invitee_points > 100_000:
            raise ValueError("referral_invitee_reward_points_invalid")
        updated_at_ms = self.now_ms_provider()
        if self.billing_repository is not None:
            return self.billing_repository.update_growth_referral_settings(
                enabled=enabled,
                reward_points=reward_points,
                invitee_reward_points=invitee_points,
                updated_by_user_id=updated_by_user_id,
                updated_at_ms=updated_at_ms,
            )
        self.referral_settings = {
            "enabled": enabled,
            "rewardPoints": reward_points,
            "inviterRewardPoints": reward_points,
            "inviteeRewardPoints": invitee_points,
            "activationWindowDays": 3,
            "configVersion": int(self.referral_settings["configVersion"]) + 1,
            "updatedByUserId": updated_by_user_id,
            "updatedAtMs": updated_at_ms,
        }
        return dict(self.referral_settings)

    def _user_created_at_ms(self, *, user_id: str, observed_at_ms: int) -> int | None:
        if self.authentication_repository is not None:
            user = self.authentication_repository.get_user(user_id)
            return None if user is None else int(user.created_at_ms)
        return self.referral_registration_ms_by_user.setdefault(user_id, observed_at_ms)

    @staticmethod
    def _referral_eligibility(*, status: dict[str, object], now_ms: int, deadline_ms: int | None) -> dict[str, object]:
        has_activated = bool(status.get("hasActivatedReferral"))
        if has_activated:
            reason = "already-activated"
        elif deadline_ms is None:
            reason = "registration-time-unavailable"
        elif now_ms > deadline_ms:
            reason = "activation-window-expired"
        elif not bool(status.get("enabled")):
            reason = "activity-disabled"
        else:
            reason = None
        return {
            "eligibleToActivate": reason is None,
            "activationDeadlineMs": deadline_ms,
            "activationEligibilityReason": reason,
            "activationWindowDays": 3,
        }

    def _activated_reward(self, *, user_id: str) -> dict[str, object] | None:
        activation = self.referral_activations_by_invitee.get(user_id)
        if activation is None:
            return None
        return {
            "inviterRewardPoints": int(activation["inviterRewardPoints"]),
            "inviteeRewardPoints": int(activation["inviteeRewardPoints"]),
            "activatedAtMs": int(activation["activatedAtMs"]),
        }

    def _require_persistent_referrals(self) -> None:
        if self.settings is not None and self.settings.environment == "production" and self.billing_repository is None:
            raise RuntimeError("Production billing and referral state requires PostgreSQL persistence")

    def _referral_code_for_user(self, *, user_id: str) -> str:
        existing = self.referral_codes_by_user.get(user_id)
        if existing is not None:
            return existing
        candidate = secrets.token_urlsafe(16)
        if self.billing_repository is not None:
            return self.billing_repository.get_or_create_referral_code(
                user_id=user_id,
                candidate_code=candidate,
                created_at_ms=_now_ms(),
            )
        self.referral_codes_by_user[user_id] = candidate
        self.referral_users_by_code[candidate] = user_id
        return candidate

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
        if normalized_code not in DEFAULT_REDEMPTION_CODE_POINTS and self.redemption_repository is not None:
            persisted = self.redemption_repository.redeem(
                user_id=user_id,
                code=normalized_code,
                idempotency_key=idempotency_key,
            )
            if persisted.redemption is None:
                return {"outcome": persisted.outcome}
            redemption = self._persistent_redemption_record(persisted.redemption)
            payload = self._redemption_payload(redemption)
            payload["newBalance"] = self._balance_for_user(user_id=user_id)
            return {"outcome": persisted.outcome, "data": payload}
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
        new_balance = self._balance_for_user(user_id=user_id)
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
        provider: str = "mzfpay",
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
        if provider not in {"mzfpay", "alipay", "wechat"}:
            raise ValueError("支付提供方不可用")
        now = _now_ms()
        order = OfficialCheckoutOrderRecord(
            # WeChat Native requires out_trade_no to be 6-32 characters and
            # limits it to ASCII letters, digits and a small punctuation set.
            # The local order id is also the provider order id so callbacks can
            # continue to resolve the order without a second identifier map.
            id=f"os{uuid4().hex[:30]}",
            user_id=user_id,
            product=product,
            amount_cents=product.price_cents,
            currency="CNY",
            channel=channel,
            provider=provider,
            status="payment_pending",
            action={"kind": "redirect", "url": payment_url, "expiresAtMs": expires_at_ms},
            created_at_ms=now,
            updated_at_ms=now,
        )
        if self.billing_repository is not None:
            return self._persisted_order(self.billing_repository.create_checkout_order(
                order={**order.__dict__, "product": order.product.__dict__},
                idempotency_key=idempotency_key,
            ))
        self.checkout_orders_by_id[order.id] = order
        self.checkout_orders_by_user_and_key[(user_id, idempotency_key)] = order.id
        return order

    def replace_checkout_action(self, *, order_id: str, payment_url: str, expires_at_ms: int, action_kind: str = "redirect") -> OfficialCheckoutOrderRecord:
        action = ({"kind": "dynamic_qr", "value": payment_url, "expiresAtMs": expires_at_ms}
                  if action_kind == "dynamic_qr" else {"kind": "redirect", "url": payment_url, "expiresAtMs": expires_at_ms})
        if self.billing_repository is not None:
            return self._persisted_order(self.billing_repository.replace_checkout_action(
                order_id=order_id,
                action=action,
                updated_at_ms=_now_ms(),
            ))
        order = self.checkout_orders_by_id[order_id]
        updated = OfficialCheckoutOrderRecord(**{**order.__dict__, "action": action})
        self.checkout_orders_by_id[order_id] = updated
        return updated

    def mark_checkout_failed(self, *, order_id: str, failure_reason: str) -> OfficialCheckoutOrderRecord:
        safe_reason = "".join(character for character in failure_reason if character.isalnum() or character in {"_", "-"})[:96]
        safe_reason = safe_reason or "payment_provider_request_failed"
        if self.billing_repository is not None:
            return self._persisted_order(self.billing_repository.mark_checkout_failed(
                order_id=order_id,
                failure_reason=safe_reason,
                updated_at_ms=_now_ms(),
            ))
        order = self.checkout_orders_by_id[order_id]
        if order.status != "payment_pending":
            return order
        failed = OfficialCheckoutOrderRecord(**{
            **order.__dict__,
            "status": "failed",
            "action": {"kind": "unavailable"},
            "updated_at_ms": _now_ms(),
        })
        self.checkout_orders_by_id[order_id] = failed
        return failed

    def checkout_order_for_user(self, *, user_id: str, order_id: str) -> OfficialCheckoutOrderRecord:
        if self.billing_repository is not None:
            self.billing_repository.expire_checkout_orders(now_ms=_now_ms(), order_id=order_id)
        order = self._persisted_order(self.billing_repository.checkout_order(order_id=order_id)) if self.billing_repository is not None else self.checkout_orders_by_id[order_id]
        if order.user_id != user_id:
            raise PermissionError("Cannot access another user's checkout order.")
        return order

    def confirm_checkout_paid(self, *, order_id: str, amount_cents: int, provider_trade_no: str) -> OfficialCheckoutOrderRecord:
        if self.billing_repository is not None:
            return self._persisted_order(self.billing_repository.confirm_checkout_paid(
                order_id=order_id,
                amount_cents=amount_cents,
                provider_trade_no=provider_trade_no,
                paid_at_ms=_now_ms(),
            ))
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

    def process_payment_notification(
        self,
        *,
        event_fingerprint: str,
        order_id: str,
        provider_trade_no: str,
        amount_cents: int,
        verified: bool,
        paid: bool,
        provider: str = "mzfpay",
        signature_verified: bool | None = None,
        app_identity_verified: bool | None = None,
        seller_identity_verified: bool | None = None,
    ) -> str:
        now_ms = _now_ms()
        if self.billing_repository is not None:
            self.billing_repository.record_payment_callback(event={
                "event_fingerprint": event_fingerprint,
                "provider": provider,
                "order_id": order_id,
                "provider_trade_no": provider_trade_no,
                "amount_cents": amount_cents,
                "signature_verified": verified if signature_verified is None else signature_verified,
                "app_identity_verified": app_identity_verified,
                "seller_identity_verified": seller_identity_verified,
                "paid": paid,
                "received_at_ms": now_ms,
            })
        order_known: bool | None = None
        amount_matches: bool | None = None
        if signature_verified is False:
            outcome = "invalid_signature"
        elif app_identity_verified is False:
            outcome = "app_identity_mismatch"
        elif seller_identity_verified is False:
            outcome = "seller_identity_mismatch"
        elif not verified:
            outcome = "invalid_signature"
        elif not paid:
            outcome = "ignored_not_paid"
        else:
            try:
                order = (
                    self._persisted_order(self.billing_repository.checkout_order(order_id=order_id))
                    if self.billing_repository is not None
                    else self.checkout_orders_by_id[order_id]
                )
                order_known = True
                amount_matches = order.amount_cents == amount_cents
                if order.provider != provider:
                    outcome = "provider_mismatch"
                else:
                    order = self.confirm_checkout_paid(
                        order_id=order_id,
                        amount_cents=amount_cents,
                        provider_trade_no=provider_trade_no,
                    )
                    outcome = "paid" if order.status == "paid" else "amount_mismatch"
            except KeyError:
                order_known = False
                outcome = "unknown_order"
            except Exception:
                outcome = "processing_failure"
        if self.billing_repository is not None:
            if outcome in {"unknown_order", "amount_mismatch", "provider_mismatch", "processing_failure", "invalid_signature", "app_identity_mismatch", "seller_identity_mismatch"}:
                self.billing_repository.create_reconciliation_issue(
                    issue_type=outcome,
                    event_fingerprint=event_fingerprint,
                    order_id=order_id,
                    detected_at_ms=now_ms,
                )
            self.billing_repository.complete_payment_callback(
                event_fingerprint=event_fingerprint,
                outcome=outcome,
                completed_at_ms=now_ms,
                order_known=order_known,
                amount_matches=amount_matches,
            )
        return outcome

    def reconciliation_summary(self) -> dict[str, object]:
        if self.billing_repository is None:
            return {"generatedAtMs": _now_ms(), "orders": {}, "callbackEvents": 0, "callbackFailures": 0, "openIssues": 0, "issues": []}
        return self.billing_repository.reconciliation_summary(now_ms=_now_ms())

    def catalog(self) -> list[BillingProductRecord]:
        if self.billing_repository is not None:
            return [BillingProductRecord(**item) for item in self.billing_repository.list_catalog_products()]
        return self._fallback_catalog()

    @staticmethod
    def _fallback_catalog() -> list[BillingProductRecord]:
        return [
            BillingProductRecord(id="pass-1", catalog_version=5, kind="time_pass", display_name="1 天会员", price_cents=2990, duration_days=1, knowledge_index_allowance=0),
            BillingProductRecord(id="pass-3", catalog_version=5, kind="time_pass", display_name="3 天会员", price_cents=6990, duration_days=3, knowledge_index_allowance=0),
            BillingProductRecord(id="pass-7", catalog_version=5, kind="time_pass", display_name="7 天会员", price_cents=12990, duration_days=7, knowledge_index_allowance=0),
            BillingProductRecord(id="pass-15", catalog_version=5, kind="time_pass", display_name="15 天会员", price_cents=21990, duration_days=15, knowledge_index_allowance=2),
            BillingProductRecord(id="pass-30", catalog_version=5, kind="time_pass", display_name="30 天会员", price_cents=32990, duration_days=30, knowledge_index_allowance=2),
            BillingProductRecord(id="points-1000", catalog_version=5, kind="points_pack", display_name="1000 积分", price_cents=9990, points=1000),
            BillingProductRecord(id="points-3000", catalog_version=5, kind="points_pack", display_name="3000 积分", price_cents=26990, points=3000),
            BillingProductRecord(id="points-10000", catalog_version=5, kind="points_pack", display_name="10000 积分", price_cents=79990, points=10000),
            BillingProductRecord(id="points-30000", catalog_version=5, kind="points_pack", display_name="30000 积分", price_cents=199990, points=30000),
            BillingProductRecord(id="points-66666", catalog_version=5, kind="points_pack", display_name="66666 积分", price_cents=399990, points=66666),
        ]

    def rates(self) -> dict[str, object]:
        catalog = self.catalog()
        return {
            "catalogVersion": max((item.catalog_version for item in catalog), default=5),
            "answerPoints": 5,
            "screenshotAnswerPoints": 15,
            "writtenExamPoints": 30,
            "realtimeMinutePoints": max(
                1,
                int(self.settings.realtime_asr_points_per_minute) if self.settings is not None else 5,
            ),
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
        balance = self._balance_for_user(user_id=user_id)
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
        if self.billing_repository is not None:
            return KnowledgeIndexQuoteRecord(**self.billing_repository.create_index_quote(
                quote=quote.__dict__, idempotency_key=idempotency_key,
            ))
        self.index_quotes_by_user_and_key[request_key] = quote
        self.index_quotes_by_id[quote.quote_id] = quote
        return quote

    def knowledge_index_quote(self, *, user_id: str, quote_id: str, document_version_id: str | None = None) -> KnowledgeIndexQuoteRecord:
        try:
            quote = (
                KnowledgeIndexQuoteRecord(**self.billing_repository.index_quote(quote_id=quote_id))
                if self.billing_repository is not None
                else self.index_quotes_by_id[quote_id]
            )
        except KeyError as exc:
            raise DomainRequestError("knowledge", "index-quote", "索引报价不存在或已失效，请重新获取报价。", 404) from exc
        if quote.user_id != user_id:
            raise DomainRequestError("knowledge", "index-quote", "索引报价不属于当前用户，请重新获取报价。", 403)
        if document_version_id is not None and quote.document_version_id != document_version_id:
            raise DomainRequestError("knowledge", "index-quote", "索引报价与当前文件不匹配，请重新获取报价。", 409)
        if self.now_ms_provider() - quote.created_at_ms >= KNOWLEDGE_INDEX_QUOTE_TTL_MS:
            raise DomainRequestError("knowledge", "index-quote", "索引报价已过期，请重新获取报价。", 409)
        return quote

    def reserve_knowledge_index_for_quote(
        self,
        *,
        user_id: str,
        quote_id: str,
        document_version_id: str,
    ) -> KnowledgeIndexReservationRecord:
        self.knowledge_index_quote(
            user_id=user_id,
            quote_id=quote_id,
            document_version_id=document_version_id,
        )
        return self.reserve_knowledge_index(user_id=user_id, quote_id=quote_id)

    def reserve_knowledge_index(self, *, user_id: str, quote_id: str) -> KnowledgeIndexReservationRecord:
        if self.billing_repository is not None:
            quote = KnowledgeIndexQuoteRecord(**self.billing_repository.index_quote(quote_id=quote_id))
            if quote.user_id != user_id:
                raise PermissionError("Cannot reserve another user's knowledge index quote.")
            return KnowledgeIndexReservationRecord(**self.billing_repository.reserve_index_quote(quote_id=quote_id, created_at_ms=_now_ms()))
        quote = self.index_quotes_by_id[quote_id]
        if quote.user_id != user_id:
            raise PermissionError("Cannot reserve another user's knowledge index quote.")
        existing = self.index_reservations_by_quote.get(quote_id)
        if existing is not None:
            return existing
        active_pass = next((item for item in self._passes_for_user(user_id=user_id) if item.starts_at_ms <= _now_ms() < item.ends_at_ms and item.knowledge_allowance_granted - item.knowledge_allowance_used - item.knowledge_allowance_locked > 0), None)
        if active_pass is not None:
            updated_pass = TimePassEntitlementRecord(**{**active_pass.__dict__, "knowledge_allowance_locked": active_pass.knowledge_allowance_locked + 1})
            self.pass_entitlements_by_user[user_id] = [updated_pass if item.id == active_pass.id else item for item in self.pass_entitlements_by_user.get(user_id, [])]
            reservation = KnowledgeIndexReservationRecord(
                reservation_id=f"index-reservation-{uuid4().hex}", quote_id=quote.quote_id,
                user_id=user_id, document_version_id=quote.document_version_id,
                points_reserved=0, billing_source="pass_allowance", entitlement_id=active_pass.id,
                allowance_reserved=1, status="reserved", created_at_ms=_now_ms(),
            )
            self.index_reservations_by_quote[quote_id] = reservation
            return reservation
        balance = self._balance_for_user(user_id=user_id)
        if balance < quote.points_required:
            return KnowledgeIndexReservationRecord(
                reservation_id=f"index-reservation-{uuid4().hex}",
                quote_id=quote.quote_id,
                user_id=user_id,
                document_version_id=quote.document_version_id,
                points_reserved=quote.points_required,
                billing_source="points",
                status="insufficient_balance",
                created_at_ms=_now_ms(),
            )
        reservation = KnowledgeIndexReservationRecord(
            reservation_id=f"index-reservation-{uuid4().hex}",
            quote_id=quote.quote_id,
            user_id=user_id,
            document_version_id=quote.document_version_id,
            points_reserved=quote.points_required,
            billing_source="points",
            status="reserved",
            created_at_ms=_now_ms(),
        )
        self.index_reservations_by_quote[quote_id] = reservation
        return reservation

    def settle_knowledge_index(self, *, quote_id: str, reference_id: str) -> KnowledgeIndexReservationRecord | None:
        if self.billing_repository is not None:
            item = self.billing_repository.settle_index_quote(quote_id=quote_id, reference_id=reference_id, settled_at_ms=_now_ms())
            return KnowledgeIndexReservationRecord(**item) if item is not None else None
        reservation = self.index_reservations_by_quote.get(quote_id)
        if reservation is None or reservation.status != "reserved":
            return reservation
        if reservation.billing_source == "pass_allowance" and reservation.entitlement_id:
            passes = self.pass_entitlements_by_user.get(reservation.user_id, [])
            self.pass_entitlements_by_user[reservation.user_id] = [
                TimePassEntitlementRecord(**{
                    **item.__dict__,
                    "knowledge_allowance_locked": max(0, item.knowledge_allowance_locked - reservation.allowance_reserved),
                    "knowledge_allowance_used": item.knowledge_allowance_used + reservation.allowance_reserved,
                }) if item.id == reservation.entitlement_id else item
                for item in passes
            ]
        if any(item.reference_id == reference_id and item.kind == "knowledge_index_settlement" for item in self.ledger_by_user.get(reservation.user_id, [])):
            return reservation
        settled_at_ms = _now_ms()
        if reservation.points_reserved:
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
        if self.billing_repository is not None:
            item = self.billing_repository.release_index_quote(quote_id=quote_id, released_at_ms=_now_ms())
            return KnowledgeIndexReservationRecord(**item) if item is not None else None
        reservation = self.index_reservations_by_quote.get(quote_id)
        if reservation is None or reservation.status != "reserved":
            return reservation
        if reservation.billing_source == "pass_allowance" and reservation.entitlement_id:
            passes = self.pass_entitlements_by_user.get(reservation.user_id, [])
            self.pass_entitlements_by_user[reservation.user_id] = [
                TimePassEntitlementRecord(**{
                    **item.__dict__,
                    "knowledge_allowance_locked": max(0, item.knowledge_allowance_locked - reservation.allowance_reserved),
                }) if item.id == reservation.entitlement_id else item
                for item in passes
            ]
        released = KnowledgeIndexReservationRecord(**{**reservation.__dict__, "status": "released", "released_at_ms": _now_ms()})
        self.index_reservations_by_quote[quote_id] = released
        return released

    def reserved_knowledge_index_for_document(self, *, user_id: str, document_version_id: str) -> KnowledgeIndexReservationRecord | None:
        if self.billing_repository is not None:
            item = self.billing_repository.reserved_index_quote_for_document(user_id=user_id, document_version_id=document_version_id)
            return KnowledgeIndexReservationRecord(**item) if item is not None else None
        return next((
            item for item in sorted(
                self.index_reservations_by_quote.values(),
                key=lambda value: (value.created_at_ms, value.reservation_id),
                reverse=True,
            )
            if item.user_id == user_id and item.document_version_id == document_version_id
        ), None)

    def settle_knowledge_index_for_document(self, *, user_id: str, document_version_id: str) -> KnowledgeIndexReservationRecord | None:
        reservation = self.reserved_knowledge_index_for_document(user_id=user_id, document_version_id=document_version_id)
        if reservation is None:
            return None
        return self.settle_knowledge_index(quote_id=reservation.quote_id, reference_id=f"knowledge-index:{document_version_id}")

    def release_knowledge_index_for_document(self, *, user_id: str, document_version_id: str) -> KnowledgeIndexReservationRecord | None:
        reservation = self.reserved_knowledge_index_for_document(user_id=user_id, document_version_id=document_version_id)
        if reservation is None:
            return None
        return self.release_knowledge_index(quote_id=reservation.quote_id)

    def reserve_usage(self, *, user_id: str, usage_id: str, usage_kind: str, wallet_only: bool = False) -> UsageReservationRecord:
        if usage_kind not in {"answer", "screenshot_answer", "realtime_minute", "written_exam_entry"}:
            raise ValueError(f"Unsupported billable usage kind: {usage_kind}")
        self._release_stale_usage_reservations(user_id=user_id)
        self._ensure_welcome_grant(user_id=user_id)
        rate_key = {
            "answer": "answerPoints",
            "screenshot_answer": "screenshotAnswerPoints",
            "realtime_minute": "realtimeMinutePoints",
            "written_exam_entry": "writtenExamPoints",
        }[usage_kind]
        points = int(self.rates()[rate_key])
        created_at_ms = _now_ms()
        usage = {
            "reservation_id": f"usage-reservation-{uuid4().hex}",
            "usage_id": usage_id,
            "user_id": user_id,
            "usage_kind": usage_kind,
            "points_reserved": points,
        }
        if self.billing_repository is not None:
            return UsageReservationRecord(**self.billing_repository.reserve_usage(usage={**usage, "wallet_only": wallet_only}, created_at_ms=created_at_ms))
        existing = self.usage_reservations_by_id.get(usage_id)
        if existing is not None:
            if existing.user_id != user_id or existing.usage_kind != usage_kind:
                raise PermissionError("Billing usage id belongs to a different operation.")
            return existing
        active_pass = None if wallet_only else self._active_pass_payload(user_id=user_id)
        points_reserved = 0 if active_pass is not None else points
        reserved_points = sum(
            item.points_reserved
            for item in self.usage_reservations_by_id.values()
            if item.user_id == user_id and item.status == "reserved"
        ) + sum(
            item.points_reserved
            for item in self.index_reservations_by_quote.values()
            if item.user_id == user_id and item.status == "reserved"
        )
        if points_reserved and self._balance_for_user(user_id=user_id) - reserved_points < points_reserved:
            return UsageReservationRecord(
                **usage,
                billing_source="points",
                status="insufficient_balance",
                created_at_ms=created_at_ms,
            )
        reservation = UsageReservationRecord(
            **{**usage, "points_reserved": points_reserved},
            billing_source="time_pass" if active_pass is not None else "points",
            status="reserved",
            created_at_ms=created_at_ms,
        )
        self.usage_reservations_by_id[usage_id] = reservation
        return reservation

    def settle_usage(self, *, usage_id: str) -> UsageReservationRecord | None:
        if self.billing_repository is not None:
            item = self.billing_repository.settle_usage(usage_id=usage_id, settled_at_ms=_now_ms())
            return UsageReservationRecord(**item) if item is not None else None
        reservation = self.usage_reservations_by_id.get(usage_id)
        if reservation is None or reservation.status != "reserved":
            return reservation
        settled_at_ms = _now_ms()
        reference_id = f"usage:{usage_id}"
        if not any(item.reference_id == reference_id for item in self.ledger_by_user.get(reservation.user_id, [])):
            self.ledger_by_user.setdefault(reservation.user_id, []).append(
                PointsLedgerRecord(
                    id=f"ledger-{uuid4().hex}",
                    user_id=reservation.user_id,
                    kind="pass_usage" if reservation.billing_source == "time_pass" else f"{reservation.usage_kind}_settlement",
                    points=-reservation.points_reserved,
                    created_at_ms=settled_at_ms,
                    reference_id=reference_id,
                    description=(
                        "会员权益实时面试使用"
                        if reservation.billing_source == "time_pass" and reservation.usage_kind == "realtime_minute"
                        else "会员权益回答使用"
                        if reservation.billing_source == "time_pass"
                        else "实时面试分钟积分结算"
                        if reservation.usage_kind == "realtime_minute"
                        else "截图回答积分结算"
                        if reservation.usage_kind == "screenshot_answer"
                        else "笔试模式入场积分结算"
                        if reservation.usage_kind == "written_exam_entry"
                        else "面试回答积分结算"
                    ),
                )
            )
        settled = UsageReservationRecord(**{**reservation.__dict__, "status": "settled", "settled_at_ms": settled_at_ms})
        self.usage_reservations_by_id[usage_id] = settled
        return settled

    def release_usage(self, *, usage_id: str) -> UsageReservationRecord | None:
        if self.billing_repository is not None:
            item = self.billing_repository.release_usage(usage_id=usage_id, released_at_ms=_now_ms())
            return UsageReservationRecord(**item) if item is not None else None
        reservation = self.usage_reservations_by_id.get(usage_id)
        if reservation is None or reservation.status != "reserved":
            return reservation
        released = UsageReservationRecord(**{**reservation.__dict__, "status": "released", "released_at_ms": _now_ms()})
        self.usage_reservations_by_id[usage_id] = released
        return released

    def _release_stale_usage_reservations(self, *, user_id: str) -> int:
        ttl_seconds = max(
            60,
            int(self.settings.billing_usage_reservation_ttl_seconds) if self.settings is not None else 30 * 60,
        )
        released_at_ms = _now_ms()
        stale_before_ms = released_at_ms - ttl_seconds * 1000
        if self.billing_repository is not None:
            return self.billing_repository.release_stale_usage_reservations(
                stale_before_ms=stale_before_ms,
                released_at_ms=released_at_ms,
                user_id=user_id,
            )
        released = 0
        for usage_id, reservation in list(self.usage_reservations_by_id.items()):
            if reservation.user_id != user_id or reservation.status != "reserved" or reservation.created_at_ms >= stale_before_ms:
                continue
            self.usage_reservations_by_id[usage_id] = UsageReservationRecord(
                **{**reservation.__dict__, "status": "released", "released_at_ms": released_at_ms}
            )
            released += 1
        return released

    def _ensure_welcome_grant(self, *, user_id: str) -> None:
        if self.billing_repository is not None:
            self.billing_repository.ensure_welcome_grant(user_id=user_id, points=WELCOME_GRANT_POINTS, created_at_ms=_now_ms())
            return
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

    def _ledger_for_user(self, *, user_id: str) -> list[PointsLedgerRecord]:
        if self.billing_repository is not None:
            ledger = [PointsLedgerRecord(**item) for item in self.billing_repository.list_ledger(user_id=user_id)]
        else:
            ledger = list(self.ledger_by_user.get(user_id, []))
        # PostgreSQL billing and redemption repositories read the same shared
        # points_redemption_ledger table. Only merge the legacy redemption
        # ledger when the unified billing repository is not configured.
        if self.redemption_repository is not None and self.billing_repository is None:
            ledger.extend(self._persistent_ledger_record(item) for item in self.redemption_repository.list_ledger(user_id=user_id))
        unique_by_reference: dict[str, PointsLedgerRecord] = {}
        for item in sorted(ledger, key=lambda value: (value.created_at_ms, value.id), reverse=True):
            # reference_id is the immutable business idempotency key in the
            # shared ledger. Keep the newest copy if a compatibility adapter
            # returns the same physical row more than once.
            unique_by_reference.setdefault(item.reference_id, item)
        return list(unique_by_reference.values())

    def _balance_for_user(self, *, user_id: str) -> int:
        if self.billing_repository is not None:
            transient_balance = self.billing_repository.balance(user_id=user_id)
        else:
            transient_balance = sum(item.points for item in self.ledger_by_user.get(user_id, []))
        persistent_balance = (
            self.redemption_repository.balance(user_id=user_id)
            if self.redemption_repository is not None and self.billing_repository is None
            else 0
        )
        return transient_balance + persistent_balance

    @staticmethod
    def _persistent_ledger_record(item: PersistedPointsLedgerEntry) -> PointsLedgerRecord:
        return PointsLedgerRecord(
            id=item.id,
            user_id=item.user_id,
            kind=item.kind,
            points=item.points,
            created_at_ms=item.created_at_ms,
            reference_id=item.reference_id,
            description=item.description,
        )

    def _persistent_redemption_record(self, item: PersistedPointsRedemption) -> PointsRedemptionRecord:
        return PointsRedemptionRecord(
            redemption_id=item.redemption_id,
            points=item.points,
            new_balance=item.persisted_balance,
            public_hint=item.public_hint,
            redeemed_at_ms=item.redeemed_at_ms,
            ledger_entry=self._persistent_ledger_record(item.ledger_entry),
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
        active = next((item for item in self._passes_for_user(user_id=user_id) if item.starts_at_ms <= now < item.ends_at_ms), None)
        return self._pass_payload(active) if active else None

    def _queued_pass_payloads(self, *, user_id: str) -> list[dict[str, object]]:
        now = _now_ms()
        return [self._pass_payload(item) for item in self._passes_for_user(user_id=user_id) if item.starts_at_ms > now]

    def _passes_for_user(self, *, user_id: str) -> list[TimePassEntitlementRecord]:
        if self.billing_repository is not None:
            return [TimePassEntitlementRecord(**item) for item in self.billing_repository.list_entitlements(user_id=user_id)]
        return sorted(self.pass_entitlements_by_user.get(user_id, []), key=lambda item: item.starts_at_ms)

    def _orders_for_user(self, *, user_id: str) -> list[OfficialCheckoutOrderRecord]:
        if self.billing_repository is not None:
            self.billing_repository.expire_checkout_orders(now_ms=_now_ms(), user_id=user_id)
            return [self._persisted_order(item) for item in self.billing_repository.list_checkout_orders(user_id=user_id)]
        return [
            item for item in sorted(self.checkout_orders_by_id.values(), key=lambda order: order.created_at_ms, reverse=True)
            if item.user_id == user_id
        ]

    @staticmethod
    def _persisted_order(item: dict[str, object]) -> OfficialCheckoutOrderRecord:
        values = dict(item)
        values["product"] = BillingProductRecord(**dict(values["product"]))
        return OfficialCheckoutOrderRecord(**values)

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
            "provider": item.provider,
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
