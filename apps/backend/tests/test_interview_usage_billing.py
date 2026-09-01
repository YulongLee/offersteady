from pathlib import Path

from fastapi.testclient import TestClient

from app.deps import billing_service
from app.main import app
from app.services.billing_service import BillingService, TimePassEntitlementRecord
from app.core.config import Settings


client = TestClient(app)


def test_written_exam_billing_migration_accepts_reservation_and_settlement_kinds() -> None:
    sql = Path("apps/backend/migrations/versions/0037_written_exam_billing_constraints.sql").read_text(encoding="utf8")
    repository = Path("apps/backend/app/services/postgres_billing_repository.py").read_text(encoding="utf8")

    assert "'written_exam_entry'" in sql
    assert "'written_exam_entry_settlement'" in sql
    assert "billing_usage_reservations_usage_kind_check" in sql
    assert "points_redemption_ledger_kind_check" in sql
    assert "points_redemption_ledger_points_check" in sql
    assert "0037_written_exam_billing_constraints.sql" in repository


def test_answer_usage_settles_once_and_changes_balance() -> None:
    service = BillingService()
    user_id = "synthetic-answer-user"

    reservation = service.reserve_usage(user_id=user_id, usage_id="answer-command-1", usage_kind="answer")
    assert reservation.status == "reserved"
    assert service.state_for_user(user_id=user_id).balance == 200

    service.settle_usage(usage_id="answer-command-1")
    service.settle_usage(usage_id="answer-command-1")

    state = service.state_for_user(user_id=user_id)
    assert state.balance == 195
    assert len([item for item in state.ledger if item.reference_id == "usage:answer-command-1"]) == 1


def test_screenshot_failure_releases_without_charging() -> None:
    service = BillingService()
    user_id = "synthetic-screenshot-user"

    reservation = service.reserve_usage(
        user_id=user_id, usage_id="screenshot-command-1", usage_kind="screenshot_answer"
    )
    assert reservation.points_reserved == 15
    service.release_usage(usage_id="screenshot-command-1")

    assert service.state_for_user(user_id=user_id).balance == 200


def test_realtime_minute_settles_once_per_stable_usage_id() -> None:
    service = BillingService()
    user_id = "synthetic-realtime-minute-user"

    first = service.reserve_usage(
        user_id=user_id,
        usage_id="realtime-minute:session-1:0",
        usage_kind="realtime_minute",
    )
    replay = service.reserve_usage(
        user_id=user_id,
        usage_id="realtime-minute:session-1:0",
        usage_kind="realtime_minute",
    )

    assert first.reservation_id == replay.reservation_id
    assert first.points_reserved == 5
    service.settle_usage(usage_id=first.usage_id)
    service.settle_usage(usage_id=first.usage_id)
    state = service.state_for_user(user_id=user_id)
    assert state.balance == 195
    assert len([item for item in state.ledger if item.reference_id == f"usage:{first.usage_id}"]) == 1


def test_realtime_minute_uses_active_pass_without_deducting_points() -> None:
    service = BillingService()
    user_id = "synthetic-realtime-pass-user"
    now_ms = service.now_ms_provider()
    service.pass_entitlements_by_user[user_id] = [TimePassEntitlementRecord(
        id="pass-entitlement-1",
        user_id=user_id,
        product_id="pass-1",
        starts_at_ms=now_ms - 1_000,
        ends_at_ms=now_ms + 60_000,
        order_id="order-1",
        knowledge_allowance_granted=0,
    )]

    reservation = service.reserve_usage(
        user_id=user_id,
        usage_id="realtime-minute:session-pass:0",
        usage_kind="realtime_minute",
    )
    assert reservation.billing_source == "time_pass"
    assert reservation.points_reserved == 0
    service.settle_usage(usage_id=reservation.usage_id)
    assert service.state_for_user(user_id=user_id).balance == 200


def test_written_exam_entry_costs_30_points_even_with_active_pass() -> None:
    service = BillingService()
    user_id = "synthetic-written-exam-user"
    now_ms = service.now_ms_provider()
    service.pass_entitlements_by_user[user_id] = [TimePassEntitlementRecord(
        id="written-pass-entitlement",
        user_id=user_id,
        product_id="pass-1",
        starts_at_ms=now_ms - 1_000,
        ends_at_ms=now_ms + 60_000,
        order_id="written-order",
        knowledge_allowance_granted=0,
    )]

    first = service.reserve_usage(
        user_id=user_id,
        usage_id="written-exam-entry:session-written",
        usage_kind="written_exam_entry",
        wallet_only=True,
    )
    replay = service.reserve_usage(
        user_id=user_id,
        usage_id="written-exam-entry:session-written",
        usage_kind="written_exam_entry",
        wallet_only=True,
    )

    assert first.reservation_id == replay.reservation_id
    assert first.billing_source == "points"
    assert first.points_reserved == 30
    service.settle_usage(usage_id=first.usage_id)
    service.settle_usage(usage_id=first.usage_id)
    assert service.state_for_user(user_id=user_id).balance == 170


def test_written_exam_draft_has_mode_and_confirmed_empty_materials() -> None:
    user_id = "synthetic-written-draft-user"
    response = client.post(
        "/api/v1/sessions",
        json={"userId": user_id, "title": "算法笔试", "sessionMode": "written"},
    )

    response.raise_for_status()
    session = response.json()["data"]
    assert session["sessionMode"] == "written"
    assert session["materialBinding"]["confirmedAtMs"] is not None
    assert session["materialBinding"]["boundDocuments"] == []

    material_response = client.post(
        f"/api/v1/sessions/{session['sessionId']}/materials/confirm",
        json={"userId": user_id, "knowledgeDocumentIds": []},
    )
    assert material_response.status_code == 409
    assert material_response.json()["error"]["details"]["errorCode"] == "written_exam_materials_disabled"


def test_written_exam_start_charges_once_and_rejects_audio_and_quick_answer() -> None:
    user_id = "synthetic-written-live-user"
    manual_code = "731942"
    client.post("/api/v1/realtime-speech/desktop-devices/register", json={
        "deviceId": "device-written-live",
        "manualCode": manual_code,
        "displayName": "合成笔试助手",
        "capabilities": {"screenCapture": True},
    }).raise_for_status()
    session = client.post("/api/v1/sessions", json={
        "userId": user_id,
        "title": "计费隔离笔试",
        "sessionMode": "written",
    }).json()["data"]
    binding = client.post(
        f"/api/v1/realtime-speech/sessions/{session['sessionId']}/desktop-binding",
        json={"userId": user_id, "manualCode": manual_code},
    )
    binding.raise_for_status()
    binding_id = binding.json()["data"]["bindingId"]
    client.post(
        f"/api/v1/realtime-speech/sessions/{session['sessionId']}/web-heartbeat",
        json={"userId": user_id, "bindingId": binding_id, "page": "live"},
    ).raise_for_status()

    first = client.post(f"/api/v1/sessions/{session['sessionId']}/start", json={"userId": user_id})
    replay = client.post(f"/api/v1/sessions/{session['sessionId']}/start", json={"userId": user_id})
    first.raise_for_status()
    replay.raise_for_status()
    assert billing_service().state_for_user(user_id=user_id).balance == 170

    publisher = client.post("/api/v1/realtime-speech/publishers", json={
        "userId": user_id,
        "sessionId": session["sessionId"],
        "sourceKind": "microphone",
        "clientName": "synthetic-written-client",
    })
    assert publisher.status_code == 409
    assert publisher.json()["error"]["details"]["errorCode"] == "written_exam_audio_disabled"

    quick_answer = client.post("/api/v1/live-answer/questions", json={
        "userId": user_id,
        "sessionId": session["sessionId"],
        "question": "不应在笔试模式启动",
        "stream": False,
    })
    assert quick_answer.status_code == 409
    assert billing_service().state_for_user(user_id=user_id).balance == 170

    screenshot = client.post(
        f"/api/v1/screenshot-answer/sessions/{session['sessionId']}/remote-capture-requests",
        json={"userId": user_id, "instruction": "回答当前笔试题"},
    )
    screenshot.raise_for_status()
    assert screenshot.json()["data"]["status"] == "requested"


def test_abandoned_usage_reservation_expires_without_late_charge(monkeypatch) -> None:
    current_ms = 1_000_000
    monkeypatch.setattr("app.services.billing_service._now_ms", lambda: current_ms)
    service = BillingService(Settings(_env_file=None, billing_usage_reservation_ttl_seconds=60))
    user_id = "synthetic-abandoned-usage"

    reservation = service.reserve_usage(user_id=user_id, usage_id="abandoned-answer", usage_kind="answer")
    assert reservation.status == "reserved"

    current_ms += 60_001
    assert service.state_for_user(user_id=user_id).balance == 200
    released = service.settle_usage(usage_id="abandoned-answer")

    assert released is not None
    assert released.status == "released"
    assert service.state_for_user(user_id=user_id).balance == 200
    assert not any(item.reference_id == "usage:abandoned-answer" for item in service.state_for_user(user_id=user_id).ledger)


def test_insufficient_balance_blocks_additional_usage() -> None:
    service = BillingService()
    user_id = "synthetic-low-balance-user"
    for index in range(40):
        usage_id = f"answer-{index}"
        assert service.reserve_usage(user_id=user_id, usage_id=usage_id, usage_kind="answer").status == "reserved"
        service.settle_usage(usage_id=usage_id)

    blocked = service.reserve_usage(user_id=user_id, usage_id="answer-blocked", usage_kind="answer")
    assert blocked.status == "insufficient_balance"
    assert service.state_for_user(user_id=user_id).balance == 0


def test_live_answer_endpoint_settles_answer_points() -> None:
    user_id = "synthetic-live-billing-user"
    created = client.post("/api/v1/sessions", json={"userId": user_id, "title": "积分链路测试"}).json()["data"]
    session_id = created["sessionId"]
    client.post(f"/api/v1/sessions/{session_id}/start", json={"userId": user_id}).raise_for_status()

    response = client.post("/api/v1/live-answer/questions", json={
        "userId": user_id,
        "sessionId": session_id,
        "question": "请简要介绍幂等结算。",
        "stream": False,
        "idempotencyKey": f"test-answer:{session_id}",
    })

    response.raise_for_status()
    assert response.json()["data"]["task"]["status"] == "completed"
    assert billing_service().state_for_user(user_id=user_id).balance == 190
    client.post(f"/api/v1/sessions/{session_id}/end", json={"userId": user_id}).raise_for_status()


def test_realtime_start_requires_first_minute_balance_before_session_goes_live() -> None:
    user_id = "synthetic-realtime-start-insufficient-user"
    service = billing_service()
    for index in range(40):
        usage_id = f"drain-answer:{user_id}:{index}"
        reservation = service.reserve_usage(user_id=user_id, usage_id=usage_id, usage_kind="answer")
        assert reservation.status == "reserved"
        service.settle_usage(usage_id=usage_id)
    created = client.post(
        "/api/v1/sessions",
        json={"userId": user_id, "title": "余额不足不启动实时 ASR"},
    ).json()["data"]

    response = client.post(
        f"/api/v1/sessions/{created['sessionId']}/start",
        json={"userId": user_id},
    )

    assert response.status_code == 402
    session = client.get(
        f"/api/v1/sessions/{created['sessionId']}",
        params={"userId": user_id},
    ).json()["data"]
    assert session["status"] == "preparing"
