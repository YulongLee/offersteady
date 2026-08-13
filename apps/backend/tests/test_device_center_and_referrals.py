from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.deps import billing_service
from app.services.billing_service import BillingService
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
    assert service.state_for_user(user_id=invitee).balance == 200

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
    assert resolved == {"valid": True, "enabled": True, "rewardPoints": 450}

    activated = unwrap(client.post("/api/v1/billing/referrals/activate", headers=invitee_headers, json={
        "referralCode": inviter_status["referralCode"],
    }))
    assert activated["outcome"] == "activated"
    assert activated["rewardPoints"] == 450
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
    migration = Path("apps/backend/migrations/versions/0025_referral_ledger_constraint_repair_v2.sql").read_text()

    assert all("0025_referral_ledger_constraint_repair_v2.sql" in source for source in repository_sources)
    assert "'referral_credit'" in migration
    assert "'admin_adjustment'" in migration
