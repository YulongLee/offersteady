from __future__ import annotations

import inspect
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import REPO_ROOT, Settings
from app.main import create_app
from app.services.admin_service import HIGH_RISK_PERMISSIONS, PERMISSIONS_BY_ROLE
from app.services.partner_program import (
    PartnerPayoutCipher,
    PartnerProgramRepository,
    commission_cents,
    mask_account_identifier,
    mask_account_name,
    refund_adjustment,
)
from app.services import promotion_analytics_job
from app.services.promotion_repository import PromotionRepository, now_ms


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


def test_partner_defaults_are_safe_and_commercial_rules_are_explicit() -> None:
    settings = Settings(_env_file=None)
    assert settings.partner_program_enabled is False
    assert settings.partner_commission_rate_bps == 2000
    assert settings.partner_eligible_order_days == 90
    assert settings.partner_refund_hold_days == 7
    assert settings.partner_minimum_payout_cents == 10_000
    assert commission_cents(10_000, settings.partner_commission_rate_bps) == 2_000
    assert settings.partner_payout_profile_enabled is False


def test_partner_payout_profile_cipher_is_dedicated_masked_and_fail_closed() -> None:
    secret = "synthetic-dedicated-partner-payout-key-32-bytes"
    cipher = PartnerPayoutCipher(Settings(_env_file=None, partner_payout_encryption_key=secret))
    encrypted = cipher.encrypt("account@example.invalid")
    assert "account@example.invalid" not in encrypted
    assert cipher.decrypt(encrypted) == "account@example.invalid"
    assert mask_account_name("测试用户") == "测***"
    assert mask_account_identifier("account@example.invalid").endswith("alid")
    with pytest.raises(RuntimeError, match="partner_payout_encryption_key_missing"):
        PartnerPayoutCipher(Settings(_env_file=None, partner_payout_encryption_key="short"))


def test_payout_profile_migration_is_additive_versioned_and_keeps_plaintext_out() -> None:
    sql = (Path(REPO_ROOT) / "apps/backend/migrations/versions/0040_partner_payout_operations.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS partner_payout_profiles" in sql
    assert "UNIQUE(partner_user_id, version)" in sql
    assert "payout_profile_id" in sql
    assert "trg_partner_payout_profile_immutable" in sql
    assert "\n  account_name TEXT" not in sql
    assert "\n  account_identifier TEXT" not in sql


def test_refund_adjustment_caps_over_refunds_and_reverses_rounding_residue() -> None:
    first_gross, first_reversal = refund_adjustment(
        original_gross_cents=10_000,
        original_commission_cents=2_000,
        refunded_gross_cents=0,
        reversed_commission_cents=0,
        requested_refund_cents=9_999,
        rate_bps=2_000,
    )
    assert (first_gross, first_reversal) == (9_999, -1_999)
    final_gross, final_reversal = refund_adjustment(
        original_gross_cents=10_000,
        original_commission_cents=2_000,
        refunded_gross_cents=first_gross,
        reversed_commission_cents=first_reversal,
        requested_refund_cents=5_000,
        rate_bps=2_000,
    )
    assert (final_gross, final_reversal) == (1, -1)


def test_refund_adjustment_rejects_sub_cent_commission_until_final_refund() -> None:
    try:
        refund_adjustment(
            original_gross_cents=100,
            original_commission_cents=20,
            refunded_gross_cents=0,
            reversed_commission_cents=0,
            requested_refund_cents=1,
            rate_bps=2_000,
        )
    except ValueError as exc:
        assert str(exc) == "refund_below_commission_precision"
    else:
        raise AssertionError("sub-cent partial commission must not create a zero-value ledger row")


def test_partner_migration_has_idempotency_privacy_and_audit_boundaries() -> None:
    sql = (Path(REPO_ROOT) / "apps/backend/migrations/versions/0039_partner_program.sql").read_text()
    for table in ("partner_profiles", "growth_acquisition_reward_claims", "partner_commission_ledger", "partner_payout_requests"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "UNIQUE(entry_type, source_type, source_id, rule_version)" in sql
    assert "UNIQUE(partner_user_id, period_key)" in sql
    assert "idx_promotion_links_partner_owner" in sql
    assert "trg_partner_ledger_append_only" in sql
    assert "trg_auth_user_partner_link_detach" in sql
    assert "phone" not in sql.lower()


def test_partner_projection_is_not_on_payment_or_interview_hot_paths() -> None:
    projection_source = inspect.getsource(PartnerProgramRepository.project_paid_orders)
    analytics_source = inspect.getsource(promotion_analytics_job.PromotionAnalyticsJob.run_once)
    assert "billing_checkout_orders" in projection_source
    assert "reward_program<>'cash_partner'" in projection_source
    assert "PartnerProgramRepository" in analytics_source
    billing_module = (Path(REPO_ROOT) / "apps/backend/app/modules/billing.py").read_text()
    realtime_module = (Path(REPO_ROOT) / "apps/backend/app/modules/realtime_speech.py").read_text()
    assert "project_paid_orders" not in billing_module
    assert "project_paid_orders" not in realtime_module


def test_partner_claim_is_attached_only_to_registration_identity_claim() -> None:
    claim_source = inspect.getsource(__import__(
        "app.services.promotion_repository", fromlist=["PromotionRepository"]
    ).PromotionRepository.claim_identity)
    create_channel_source = inspect.getsource(__import__(
        "app.services.promotion_repository", fromlist=["PromotionRepository"]
    ).PromotionRepository.create_channel)
    assert "cash_partner" in claim_source
    assert "cash_partner" not in create_channel_source


def test_partner_finance_permission_is_high_risk_and_role_scoped() -> None:
    assert "promotion.payout.manage" in PERMISSIONS_BY_ROLE["finance"]
    assert "promotion.payout.manage" in PERMISSIONS_BY_ROLE["super_admin"]
    assert "promotion.payout.manage" not in PERMISSIONS_BY_ROLE["support"]
    assert "promotion.payout.manage" in HIGH_RISK_PERMISSIONS


def test_partner_payout_transition_returns_previous_state_for_admin_audit() -> None:
    source = inspect.getsource(PartnerProgramRepository.transition_payout)
    route_source = (Path(REPO_ROOT) / "apps/backend/app/api/admin_promotion.py").read_text()
    assert 'updated["previous_status"]' in source
    assert '"previous_status": row["previous_status"]' in route_source


def test_payout_requests_bind_profile_version_and_sensitive_reveal_is_guarded() -> None:
    payout_source = inspect.getsource(PartnerProgramRepository.request_payout)
    route_source = (Path(REPO_ROOT) / "apps/backend/app/api/admin_promotion.py").read_text()
    assert "payout_profile_id" in payout_source
    assert "partner_payout_profile_required" in payout_source
    assert 'permission("promotion.payout.manage")' in route_source
    assert '"Cache-Control": "no-store"' in route_source
    assert 'action="promotion.partner.payout.reveal"' in route_source


def test_partner_reconciliation_remains_outside_payment_and_interview_hot_paths() -> None:
    billing_module = (Path(REPO_ROOT) / "apps/backend/app/modules/billing.py").read_text()
    realtime_module = (Path(REPO_ROOT) / "apps/backend/app/modules/realtime_speech.py").read_text()
    assert "reconciliation_summary" not in billing_module
    assert "list_commission_orders" not in billing_module
    assert "reconciliation_summary" not in realtime_module
    assert "list_commission_orders" not in realtime_module


def test_disabled_partner_status_does_not_require_partner_database() -> None:
    client = TestClient(create_app())
    registration = client.post("/api/v1/auth/register", json={
        "loginId": "partner-disabled@example.test",
        "password": "SyntheticPassword123!",
        "displayName": "Partner Disabled",
        "clientLabel": "partner-test",
    })
    registration.raise_for_status()
    token = registration.json()["data"]["tokens"]["accessToken"]
    response = client.get("/api/v1/partner-program/me", headers={"Authorization": f"Bearer {token}"})
    response.raise_for_status()
    data = response.json()["data"]
    assert data["joined"] is False
    assert data["config"]["enabled"] is False
    assert client.post("/api/v1/partner-program/join", headers={"Authorization": f"Bearer {token}"}, json={
        "agreementVersion": data["config"]["agreementVersion"], "agreementAccepted": True,
    }).status_code == 404


@pytest.fixture(scope="module")
def postgres_partner_repository() -> PartnerProgramRepository:
    if not DATABASE_URL:
        pytest.skip("OFFERSTEADY_TEST_DATABASE_URL is not configured")
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS auth_users (
                 user_id TEXT PRIMARY KEY, login_id TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                 display_name TEXT NOT NULL, avatar_url TEXT NULL, last_login_provider TEXT NOT NULL,
                 last_login_at_ms BIGINT NOT NULL, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL,
                 membership_anchor_ref TEXT NULL
               );
               CREATE TABLE IF NOT EXISTS interview_sessions (
                 session_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, started_at_ms BIGINT NULL
               );
               CREATE TABLE IF NOT EXISTS billing_checkout_orders (
                 order_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, amount_cents INTEGER NOT NULL,
                 currency TEXT NOT NULL, status TEXT NOT NULL, created_at_ms BIGINT NOT NULL, paid_at_ms BIGINT NULL
               );
               ALTER TABLE billing_checkout_orders ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
               ALTER TABLE billing_checkout_orders ADD COLUMN IF NOT EXISTS product_snapshot JSONB;
               ALTER TABLE billing_checkout_orders ADD COLUMN IF NOT EXISTS channel TEXT;
               ALTER TABLE billing_checkout_orders ADD COLUMN IF NOT EXISTS action JSONB;
               ALTER TABLE billing_checkout_orders ADD COLUMN IF NOT EXISTS provider TEXT;
               ALTER TABLE billing_checkout_orders ADD COLUMN IF NOT EXISTS updated_at_ms BIGINT;
               ALTER TABLE billing_checkout_orders ADD COLUMN IF NOT EXISTS expires_at_ms BIGINT;"""
        )
        connection.commit()
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=DATABASE_URL,
        redis_url="redis://synthetic.invalid/0",
        promotion_enabled=True,
        partner_program_enabled=True,
        promotion_visitor_hmac_secret="synthetic-private-hmac-secret-at-least-32-bytes",
        partner_refund_hold_days=0,
        partner_minimum_payout_cents=1,
        admin_max_concurrent_queries=8,
    )
    return PartnerProgramRepository(settings)


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_postgres_partner_closed_loop_is_idempotent_and_concurrency_safe(
    postgres_partner_repository: PartnerProgramRepository,
) -> None:
    repository = postgres_partner_repository
    promotion = PromotionRepository(repository.settings, migrate=False)
    prefix = f"partner_it_{uuid4().hex[:12]}"
    partner_user_id = f"{prefix}_partner"
    acquired_user_id = f"{prefix}_acquired"
    current = now_ms()
    with repository.connect() as connection, connection.cursor() as cursor:
        for user_id in (partner_user_id, acquired_user_id):
            cursor.execute(
                """INSERT INTO auth_users
                   (user_id,login_id,password_hash,display_name,last_login_provider,last_login_at_ms,created_at_ms,updated_at_ms)
                   VALUES (%s,%s,'synthetic','Synthetic Partner Test','test',%s,%s,%s)""",
                (user_id, f"{user_id}@example.invalid", current, current, current),
            )
        connection.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        profiles = list(pool.map(
            lambda _: repository.join(user_id=partner_user_id, agreement_version="2026-09-v1", joined_at_ms=current),
            range(2),
        ))
    assert len({profile["profile_id"] for profile in profiles}) == 1
    profile = profiles[0]

    assert promotion.record_touchpoint({
        "event_id": f"{prefix}_visit", "event_type": "qualified_visit",
        "link_id": profile["promotion_link_id"], "visitor_hmac": f"{prefix}_visitor",
        "click_hmac": f"{prefix}_click", "occurred_at_ms": current,
        "destination_key": "/", "referrer_host": "example.test", "device_class": "desktop",
        "qualification_state": "qualified", "exclusion_reason": None,
    })
    promotion.claim_identity(
        claim_key=f"{prefix}_claim", visitor_hmac=f"{prefix}_visitor", user_id=acquired_user_id,
    )
    order_id = f"{prefix}_order"
    with repository.connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO billing_checkout_orders
               (order_id,user_id,idempotency_key,product_snapshot,amount_cents,currency,channel,status,action,
                provider,created_at_ms,updated_at_ms,paid_at_ms,expires_at_ms)
               VALUES (%s,%s,%s,'{}'::jsonb,10000,'CNY','alipay','paid','{}'::jsonb,'alipay',%s,%s,%s,%s)""",
            (order_id, acquired_user_id, f"{prefix}_idempotency", current, current, current, current + 60_000),
        )
        connection.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        projections = list(pool.map(lambda _: repository.project_paid_orders(projected_at_ms=current + 1), range(2)))
    assert sum(item["inserted"] for item in projections) == 1
    assert repository.dashboard(user_id=partner_user_id, at_ms=current + 1)["balances"]["available_cents"] == 2_000

    def request_payout() -> dict[str, object]:
        try:
            return repository.request_payout(user_id=partner_user_id, requested_at_ms=current + 2)
        except ValueError as exc:
            return {"error": str(exc)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: request_payout(), range(2)))
    requested = next(item for item in outcomes if item.get("status") == "requested")
    assert sum(item.get("error") == "partner_monthly_payout_already_requested" for item in outcomes) == 1
    approved = repository.transition_payout(
        payout_request_id=str(requested["payout_request_id"]), target_status="approved",
        actor_user_id="synthetic-admin", reason="synthetic approval", transitioned_at_ms=current + 3,
    )
    assert approved["status"] == "approved"
    paid = repository.transition_payout(
        payout_request_id=str(requested["payout_request_id"]), target_status="paid",
        actor_user_id="synthetic-admin", reason="synthetic payment",
        payment_reference=f"{prefix}_payment", transitioned_at_ms=current + 4,
    )
    assert paid["status"] == "paid"

    first = repository.record_refund(
        order_id=order_id, refund_reference=f"{prefix}_refund", refunded_cents=5_000,
        actor_user_id="synthetic-admin", occurred_at_ms=current + 5,
    )
    replay = repository.record_refund(
        order_id=order_id, refund_reference=f"{prefix}_refund", refunded_cents=5_000,
        actor_user_id="synthetic-admin", occurred_at_ms=current + 6,
    )
    assert first["ledger_entry_id"] == replay["ledger_entry_id"]
    assert int(first["amount_cents"]) == -1_000
    balances = repository.dashboard(user_id=partner_user_id, at_ms=current + 7)["balances"]
    assert balances["available_cents"] == -1_000
    assert balances["settled_cents"] == 2_000
