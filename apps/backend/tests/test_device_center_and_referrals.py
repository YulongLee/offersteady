from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
import psycopg
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.deps import billing_service
from app.services.billing_service import BillingService
from app.services.authentication_repository import InMemoryAuthenticationRepository
from app.ports.authentication import UserRecord
from app.services.postgres_billing_repository import PostgresBillingRepository
from app.services.postgres_authentication_repository import PostgresAuthenticationRepository
from app.services.postgres_points_redemption_repository import PostgresPointsRedemptionRepository


def unwrap(response):
    response.raise_for_status()
    return response.json()["data"]


def register_user(client: TestClient, label: str) -> tuple[str, dict[str, str]]:
    login_id = f"{label}-{uuid4().hex}@example.test"
    result = unwrap(client.post("/api/v1/auth/register", json={
        "loginId": login_id,
        "password": "SyntheticPassword123!",
        "displayName": label,
        "clientLabel": "device-referral-test",
    }))
    return result["user"]["userId"], {"Authorization": f"Bearer {result['tokens']['accessToken']}"}


def test_device_center_lists_only_real_devices_for_authenticated_account() -> None:
    client = TestClient(create_app())
    owner_user_id, owner_headers = register_user(client, "device-owner")
    other_user_id, other_headers = register_user(client, "device-other")
    manual_code = str(int(uuid4().hex[:6], 16) % 900000 + 100000)
    device_id = f"device-{uuid4().hex}"
    unwrap(client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": device_id,
        "manualCode": manual_code,
        "displayName": "合成测试 Mac",
        "capabilities": {
            "platformVersion": "macOS 15.0",
            "microphone": "granted",
            "systemAudio": "granted",
            "screenCapture": "denied",
        },
    }))
    session = unwrap(client.post("/api/v1/sessions", headers=owner_headers, json={
        "userId": owner_user_id,
        "title": "设备中心测试",
    }))
    unwrap(client.post(
        f"/api/v1/realtime-speech/sessions/{session['sessionId']}/desktop-binding",
        headers=owner_headers,
        json={"userId": owner_user_id, "manualCode": manual_code},
    ))

    devices = unwrap(client.get("/api/v1/realtime-speech/desktop-devices", headers=owner_headers))
    assert len(devices) == 1
    assert devices[0]["deviceId"] == device_id
    assert devices[0]["maskedManualCode"] == f"••••{manual_code[-2:]}"
    assert manual_code not in str(devices)
    assert devices[0]["online"] is True
    assert devices[0]["permissionStatus"]["microphone"] == "granted"
    assert devices[0]["permissionStatus"]["screenCapture"] == "denied"
    assert devices[0]["activeInterview"]["sessionId"] == session["sessionId"]

    assert unwrap(client.get("/api/v1/realtime-speech/desktop-devices", headers=other_headers)) == []
    assert owner_user_id != other_user_id
    assert client.get("/api/v1/realtime-speech/desktop-devices").status_code == 401


def test_referral_service_enforces_one_activation_and_ledger_credit() -> None:
    service = BillingService(Settings(_env_file=None, environment="test", public_web_base_url="https://example.test"))
    inviter = "synthetic-inviter"
    invitee = "synthetic-invitee"
    other_inviter = "synthetic-other-inviter"
    inviter_status = service.referral_status(user_id=inviter)
    other_status = service.referral_status(user_id=other_inviter)
    assert inviter_status["shareUrl"].startswith("https://example.test/invite/")
    assert inviter_status["referralCode"] not in inviter
    assert service.referral_status(user_id=inviter)["referralCode"] == inviter_status["referralCode"]

    service.update_growth_referral_settings(enabled=True, reward_points=500, updated_by_user_id="synthetic-admin")
    activated = service.activate_referral(invitee_user_id=invitee, referral_code=str(inviter_status["referralCode"]))
    assert activated["outcome"] == "activated"
    assert activated["rewardPoints"] == 500
    assert service.state_for_user(user_id=inviter).balance == 700
    assert len([entry for entry in service.state_for_user(user_id=inviter).ledger if entry.kind == "referral_credit"]) == 1
    assert service.state_for_user(user_id=invitee).balance == 700
    assert len([entry for entry in service.state_for_user(user_id=invitee).ledger if entry.kind == "referral_invitee_credit"]) == 1
    assert activated["inviterRewardPoints"] == 500
    assert activated["inviteeRewardPoints"] == 500

    replay = service.activate_referral(invitee_user_id=invitee, referral_code=str(inviter_status["referralCode"]))
    assert replay["outcome"] == "activated"
    assert replay["replayed"] is True
    assert service.state_for_user(user_id=inviter).balance == 700
    assert service.activate_referral(invitee_user_id=invitee, referral_code=str(other_status["referralCode"]))["outcome"] == "already-activated"
    assert service.activate_referral(invitee_user_id=inviter, referral_code=str(inviter_status["referralCode"]))["outcome"] == "self-referral"
    assert service.activate_referral(invitee_user_id="unknown", referral_code="not-a-real-code")["outcome"] == "invalid-code"

    summary = service.referral_status(user_id=inviter)
    assert summary["inviteCount"] == 1
    assert summary["totalRewardPoints"] == 500
    assert "synthetic-invitee" not in str(summary)


def test_referral_disabled_keeps_history_and_blocks_new_activation() -> None:
    service = BillingService(Settings(_env_file=None, environment="test"))
    inviter_status = service.referral_status(user_id="disabled-inviter")
    assert service.activate_referral(invitee_user_id="disabled-invitee", referral_code=str(inviter_status["referralCode"]))["outcome"] == "disabled"
    service.update_growth_referral_settings(enabled=True, reward_points=300, updated_by_user_id="admin")
    assert service.activate_referral(invitee_user_id="disabled-invitee", referral_code=str(inviter_status["referralCode"]))["outcome"] == "activated"
    service.update_growth_referral_settings(enabled=False, reward_points=800, updated_by_user_id="admin")
    assert service.activate_referral(invitee_user_id="second-invitee", referral_code=str(inviter_status["referralCode"]))["outcome"] == "disabled"
    assert service.referral_status(user_id="disabled-inviter")["totalRewardPoints"] == 300


def test_referral_activation_uses_inclusive_three_day_registration_window() -> None:
    registered_at_ms = 2_000_000_000_000
    clock_ms = [registered_at_ms]
    authentication = InMemoryAuthenticationRepository()

    def add_user(user_id: str, created_at_ms: int) -> None:
        authentication.save_user(UserRecord(
            user_id=user_id,
            login_id=f"{user_id}@example.test",
            password_hash="synthetic-hash",
            display_name=user_id,
            avatar_url=None,
            last_login_provider="password",
            last_login_at_ms=created_at_ms,
            created_at_ms=created_at_ms,
            updated_at_ms=created_at_ms,
        ))

    add_user("window-inviter", registered_at_ms)
    add_user("boundary-invitee", registered_at_ms)
    add_user("expired-invitee", registered_at_ms)
    service = BillingService(
        Settings(_env_file=None, environment="test"),
        authentication_repository=authentication,
        now_ms_provider=lambda: clock_ms[0],
    )
    code = str(service.referral_status(user_id="window-inviter")["referralCode"])
    service.update_growth_referral_settings(
        enabled=True,
        reward_points=600,
        invitee_reward_points=300,
        updated_by_user_id="synthetic-admin",
    )

    clock_ms[0] = registered_at_ms + 72 * 60 * 60 * 1000
    boundary_status = service.referral_status(user_id="boundary-invitee")
    assert boundary_status["eligibleToActivate"] is True
    boundary = service.activate_referral(invitee_user_id="boundary-invitee", referral_code=code)
    assert boundary["outcome"] == "activated"
    assert boundary["inviterRewardPoints"] == 600
    assert boundary["inviteeRewardPoints"] == 300

    clock_ms[0] += 1
    expired_status = service.referral_status(user_id="expired-invitee")
    assert expired_status["eligibleToActivate"] is False
    assert expired_status["activationEligibilityReason"] == "activation-window-expired"
    expired = service.activate_referral(invitee_user_id="expired-invitee", referral_code=code)
    assert expired["outcome"] == "activation-window-expired"
    assert service.state_for_user(user_id="expired-invitee").balance == 200


def test_referral_rejects_missing_authoritative_registration_time() -> None:
    authentication = InMemoryAuthenticationRepository()
    service = BillingService(
        Settings(_env_file=None, environment="test"),
        authentication_repository=authentication,
        now_ms_provider=lambda: 2_000_000_000_000,
    )
    inviter_status = service.referral_status(user_id="legacy-inviter")
    service.update_growth_referral_settings(enabled=True, reward_points=500, invitee_reward_points=500, updated_by_user_id="admin")
    status = service.referral_status(user_id="legacy-invitee")
    assert status["eligibleToActivate"] is False
    assert status["activationEligibilityReason"] == "registration-time-unavailable"
    assert service.activate_referral(
        invitee_user_id="legacy-invitee",
        referral_code=str(inviter_status["referralCode"]),
    )["outcome"] == "registration-time-unavailable"


def test_referral_http_flow_requires_login_and_returns_only_safe_summary() -> None:
    client = TestClient(create_app())
    inviter_user_id, inviter_headers = register_user(client, "http-inviter")
    invitee_user_id, invitee_headers = register_user(client, "http-invitee")
    billing_service().update_growth_referral_settings(enabled=True, reward_points=450, updated_by_user_id="test-admin")

    assert client.get("/api/v1/billing/referrals/me").status_code == 401
    inviter_status = unwrap(client.get("/api/v1/billing/referrals/me", headers=inviter_headers))
    assert inviter_status["rewardPoints"] == 450
    assert inviter_user_id not in inviter_status["shareUrl"]
    resolved = unwrap(client.get(f"/api/v1/billing/referrals/{inviter_status['referralCode']}"))
    assert resolved == {
        "valid": True,
        "enabled": True,
        "rewardPoints": 450,
        "inviterRewardPoints": 450,
        "inviteeRewardPoints": 450,
        "activationWindowDays": 3,
    }

    activated = unwrap(client.post("/api/v1/billing/referrals/activate", headers=invitee_headers, json={
        "referralCode": inviter_status["referralCode"],
    }))
    assert activated["outcome"] == "activated"
    assert activated["rewardPoints"] == 450
    assert activated["inviteeRewardPoints"] == 450
    invitee_billing = unwrap(client.get("/api/v1/billing/state", headers=invitee_headers))
    assert invitee_billing["balance"] == 650
    assert len([entry for entry in invitee_billing["ledger"] if entry["kind"] == "referral_invitee_credit"]) == 1
    assert invitee_user_id not in str(unwrap(client.get("/api/v1/billing/referrals/me", headers=inviter_headers)))


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_postgres_referral_activation_is_concurrency_safe() -> None:
    settings = Settings(_env_file=None, environment="test", database_url=DATABASE_URL)
    service = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
    inviter = f"postgres-inviter-{uuid4().hex}"
    invitee = f"postgres-invitee-{uuid4().hex}"
    code = str(service.referral_status(user_id=inviter)["referralCode"])
    service.update_growth_referral_settings(enabled=True, reward_points=500, updated_by_user_id="postgres-admin")
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: BillingService(settings, billing_repository=PostgresBillingRepository(settings)).activate_referral(invitee_user_id=invitee, referral_code=code), range(4)))
    assert all(item["outcome"] == "activated" for item in outcomes)
    restarted = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
    assert restarted.referral_status(user_id=inviter)["inviteCount"] == 1
    assert len([entry for entry in restarted.state_for_user(user_id=inviter).ledger if entry.kind == "referral_credit"]) == 1
    assert len([entry for entry in restarted.state_for_user(user_id=invitee).ledger if entry.kind == "referral_invitee_credit"]) == 1


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_postgres_referral_rolls_back_both_rewards_when_invitee_ledger_fails() -> None:
    settings = Settings(_env_file=None, environment="test", database_url=DATABASE_URL)
    service = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
    inviter = f"rollback-inviter-{uuid4().hex}"
    invitee = f"rollback-invitee-{uuid4().hex}"
    code = str(service.referral_status(user_id=inviter)["referralCode"])
    service.update_growth_referral_settings(
        enabled=True,
        reward_points=500,
        invitee_reward_points=300,
        updated_by_user_id="rollback-admin",
    )
    suffix = uuid4().hex
    function_name = f"reject_invitee_reward_{suffix}"
    trigger_name = f"reject_invitee_reward_{suffix}"
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(f"""
            CREATE FUNCTION {function_name}() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF NEW.kind = 'referral_invitee_credit' AND NEW.user_id = '{invitee}' THEN
                RAISE EXCEPTION 'synthetic invitee reward failure';
              END IF;
              RETURN NEW;
            END;
            $$
        """)
        cursor.execute(f"""
            CREATE TRIGGER {trigger_name}
            BEFORE INSERT ON points_redemption_ledger
            FOR EACH ROW EXECUTE FUNCTION {function_name}()
        """)
        connection.commit()
    try:
        with pytest.raises(psycopg.errors.RaiseException):
            service.activate_referral(invitee_user_id=invitee, referral_code=code)
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM growth_referral_activations WHERE invitee_user_id = %s", (invitee,))
            assert cursor.fetchone()[0] == 0
            cursor.execute("SELECT COUNT(*) FROM points_redemption_ledger WHERE user_id IN (%s, %s) AND kind IN ('referral_credit', 'referral_invitee_credit')", (inviter, invitee))
            assert cursor.fetchone()[0] == 0
    finally:
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON points_redemption_ledger")
            cursor.execute(f"DROP FUNCTION IF EXISTS {function_name}()")
            connection.commit()


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_postgres_redemption_repository_initialization_preserves_referral_credit() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=DATABASE_URL,
        redemption_code_pepper="synthetic-referral-schema-order-pepper",
    )
    billing = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
    inviter = f"schema-order-inviter-{uuid4().hex}"
    first_invitee = f"schema-order-invitee-{uuid4().hex}"
    second_invitee = f"schema-order-second-{uuid4().hex}"
    code = str(billing.referral_status(user_id=inviter)["referralCode"])
    billing.update_growth_referral_settings(enabled=True, reward_points=321, updated_by_user_id="schema-order-admin")
    assert billing.activate_referral(invitee_user_id=first_invitee, referral_code=code)["outcome"] == "activated"

    PostgresAuthenticationRepository(settings)
    PostgresPointsRedemptionRepository(settings)

    restarted = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
    assert restarted.activate_referral(invitee_user_id=second_invitee, referral_code=code)["outcome"] == "activated"
    rewards = [entry for entry in restarted.state_for_user(user_id=inviter).ledger if entry.kind == "referral_credit"]
    assert len(rewards) == 2
    assert sum(entry.points for entry in rewards) == 642


def test_all_ledger_initializers_include_latest_referral_constraint_repair() -> None:
    repository_sources = [
        Path("apps/backend/app/services/postgres_billing_repository.py").read_text(),
        Path("apps/backend/app/services/postgres_points_redemption_repository.py").read_text(),
        Path("apps/backend/app/services/admin_repository.py").read_text(),
    ]
    migration = Path("apps/backend/migrations/versions/0029_early_referral_mutual_rewards.sql").read_text()

    assert all("0029_early_referral_mutual_rewards.sql" in source for source in repository_sources)
    assert "'referral_credit'" in migration
    assert "'referral_invitee_credit'" in migration
    assert "'admin_adjustment'" in migration
