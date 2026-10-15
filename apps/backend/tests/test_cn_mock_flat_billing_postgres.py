"""Synthetic-only regression for flat CN pricing and durable wall-clock expiry."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
from time import time
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app.core.config import Settings
from app.services.billing_service import BillingService
from app.services.mock_interview_repository import MockInterviewRepository, round_state
from app.services.postgres_billing_repository import PostgresBillingRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from test_mock_interview_postgres import DATABASE_URL, account, create


pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Isolated PostgreSQL required")
LIMIT = 3_600_000


@pytest.fixture
def repositories():
    # Each scenario gets a disposable schema inside the explicitly configured
    # synthetic database, so bounded recovery scans never see unrelated fixtures.
    schema = f"synthetic_cn_mock_flat_{uuid4().hex}"
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        settings = Settings(_env_file=None, environment="test", database_url=make_conninfo(
            DATABASE_URL, options=f"-c search_path={schema}"))
        sessions = PostgresInterviewSessionRepository(settings)
        billing = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
        yield MockInterviewRepository(settings), billing, sessions
    finally:
        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def start(repo, user, now):
    row = create(repo, user, now=now)
    return repo.transition(user_id=user, session_id=row["session_id"], expected_version=0,
        now_ms=now, move=lambda state: state.start())


def force_phase(repo, user, row, phase, now):
    def operation(record, cursor):
        state = round_state(record)
        if phase != "generating_question":
            state = state.publish_question(state.operation_id, "合成项目怎样验证幂等性？")
        if phase in ("listening", "paused"):
            state = state.listen(state.rounds[-1].question_id, now)
        if phase == "paused":
            state = state.pause()
        record["data"]["state"] = asdict(state)
    return repo.change(user_id=user, session_id=row["session_id"], now_ms=now, operation=operation)


@pytest.mark.parametrize("product", ["pass-1", "pass-7", "pass-30"])
def test_all_active_paid_memberships_receive_exactly_one_free_creation(repositories, product):
    repo, billing, _ = repositories
    user = account(repositories)
    order = billing.create_checkout_order(user_id=user, product_id=product, channel="alipay",
        idempotency_key=uuid4().hex, payment_url="https://synthetic.invalid", expires_at_ms=9_999_999_999_999)
    billing.confirm_checkout_paid(order_id=order.id, amount_cents=order.amount_cents,
        provider_trade_no=f"synthetic-{uuid4().hex}")
    now = int(time()*1000)
    quote = repo.quote(user, now)
    assert quote["activeTimeMember"] and quote["dailyFreeRemaining"] == quote["dailyFreeLimit"] == 1
    assert quote["durationLimitMinutes"] == 60 and quote["minutePoints"] == 0 and quote["nowMs"] == now
    create(repo, user, free=True, now=now)
    assert repo.quote(user, now)["entryPoints"] == 100
    assert repo.quote(user, now)["dailyFreeRemaining"] == 0


def test_admin_membership_and_exact_validity_boundaries(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    # A connection-scoped synthetic table exercises the real admin-entitlement
    # SQL without introducing admin/auth schema or touching other fixtures.
    with repo.transaction(user) as cursor:
        cursor.execute("CREATE TEMP TABLE admin_time_entitlements (user_id TEXT, starts_at_ms BIGINT, ends_at_ms BIGINT)")
        cursor.execute("INSERT INTO admin_time_entitlements VALUES (%s,%s,%s)", (user, now, now+1000))
        assert repo._quote(cursor, user, now-1)["activeTimeMember"] is False
        assert repo._quote(cursor, user, now)["dailyFreeRemaining"] == 1
        assert repo._quote(cursor, user, now+1000)["activeTimeMember"] is False


def test_shanghai_midnight_replenishes_without_charging_cross_day_retry(repositories):
    repo, billing, _ = repositories
    user = account(repositories, member=True)
    before = int(datetime(2026, 10, 15, 23, 59, 59, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp()*1000)
    after = before+1000
    with repo.connect() as conn:
        conn.execute("UPDATE billing_time_pass_entitlements SET starts_at_ms=%s,ends_at_ms=%s WHERE user_id=%s",
            (before-86_400_000, after+86_400_000, user))
    original = create(repo, user, "yesterday", free=True, now=before)
    assert repo.quote(user, before)["dailyFreeRemaining"] == 0
    assert repo.quote(user, after)["quotaDay"] == "2026-10-16"
    assert repo.quote(user, after)["dailyFreeRemaining"] == 1
    assert create(repo, user, "yesterday", free=True, now=after)["session_id"] == original["session_id"]
    assert repo.quote(user, after)["dailyFreeRemaining"] == 1
    create(repo, user, "today", free=True, now=after)
    assert repo.quote(user, after)["dailyFreeRemaining"] == 0
    assert billing.state_for_user(user_id=user).balance == 200


def test_preparation_has_no_deadline_and_start_locks_first_wall_clock(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = create(repo, user, now=now)
    assert repo.duration_deadline(row) is None
    row = repo.expire_duration(user_id=user, session_id=row["session_id"], now_ms=now+10*LIMIT)
    assert round_state(row).phase == "preparing" and repo.duration_deadline(row) is None
    row = repo.transition(user_id=user, session_id=row["session_id"], expected_version=0,
        now_ms=now+10*LIMIT, move=lambda state: state.start())
    assert row["data"]["started_at_ms"] == now+10*LIMIT
    assert repo.duration_deadline(row) == now+11*LIMIT
    restored = MockInterviewRepository(repo.settings)
    assert restored.duration_deadline(restored.get(user_id=user, session_id=row["session_id"])) == now+11*LIMIT


@pytest.mark.parametrize("phase", ["generating_question", "speaking", "listening", "paused"])
def test_duration_expiry_ends_every_active_phase_once_without_refund(repositories, phase):
    repo, billing, sessions = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = force_phase(repo, user, start(repo, user, now), phase, now)
    sid = row["session_id"]
    assert round_state(repo.expire_duration(user_id=user, session_id=sid, now_ms=now+LIMIT-1)).phase == phase
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: repo.expire_duration(user_id=user, session_id=sid, now_ms=now+LIMIT), range(3)))
    assert {round_state(item).operation_id for item in results} == {round_state(results[0]).operation_id}
    assert all(round_state(item).phase == "generating_report" for item in results)
    row = results[0]
    assert row["data"]["end_reason"] == "time_limit" and row["data"]["clock_at_ms"] is None
    assert row["data"]["generation_claim"] is None and row["refunded"] is False
    assert sessions.get_session(sid).status == "ended"
    assert billing.state_for_user(user_id=user).balance == 100


@pytest.mark.parametrize("action", ["control_tick", "transition", "claim", "finish"])
def test_repository_commands_commit_expiry_and_return_report_state(repositories, action):
    repo, _, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = start(repo, user, now)
    sid, op = row["session_id"], round_state(row).operation_id
    if action == "finish":
        row = repo.claim_generation(user_id=user, session_id=sid, operation_id=op, now_ms=now+LIMIT-1)
    if action == "control_tick":
        row = force_phase(repo, user, row, "listening", now)
        row = repo.acquire_control(user_id=user, session_id=sid, now_ms=now+LIMIT-1)
        expired = repo.control_tick(user_id=user, session_id=sid, control_token=row["data"]["control_token"],
            now_ms=now+LIMIT, active=True)
    elif action == "transition":
        expired = repo.transition(user_id=user, session_id=sid, expected_version=-1, now_ms=now+LIMIT,
            move=lambda state: state.retry_generation())
    elif action == "claim":
        expired = repo.claim_generation(user_id=user, session_id=sid, operation_id=op, now_ms=now+LIMIT)
    else:
        expired = repo.finish_generation(user_id=user, session_id=sid, operation_id=op,
            claim_id=row["data"]["generation_claim"], now_ms=now+LIMIT, question="不应保存的迟到题目")
    assert round_state(expired).phase == "generating_report" and expired["data"]["end_reason"] == "time_limit"
    assert not round_state(expired).rounds or round_state(expired).rounds[-1].question != "不应保存的迟到题目"
    assert round_state(repo.get(user_id=user, session_id=sid)).operation_id == round_state(expired).operation_id


def test_expired_late_question_never_replaces_report_and_report_can_finish(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = start(repo, user, now)
    sid, old_op = row["session_id"], round_state(row).operation_id
    old_claim = repo.claim_generation(user_id=user, session_id=sid, operation_id=old_op, now_ms=now+LIMIT-1)
    ended = repo.expire_duration(user_id=user, session_id=sid, now_ms=now+LIMIT)
    op = round_state(ended).operation_id
    claim = repo.claim_generation(user_id=user, session_id=sid, operation_id=op, now_ms=now+LIMIT)
    late = repo.finish_generation(user_id=user, session_id=sid, operation_id=old_op,
        claim_id=old_claim["data"]["generation_claim"], now_ms=now+LIMIT+1, question="不应保存的迟到题目")
    assert round_state(late).operation_id == op and late["data"]["generation_claim"] == claim["data"]["generation_claim"]
    done = repo.finish_generation(user_id=user, session_id=sid, operation_id=op,
        claim_id=claim["data"]["generation_claim"], now_ms=now+LIMIT+1000,
        report={"summary": "合成无证据报告", "overall_score": None})
    assert round_state(done).phase == "completed" and done["data"]["end_reason"] == "time_limit"


def test_reconnect_after_deadline_returns_automatic_report_without_waiting_error(repositories):
    repo, _, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = start(repo, user, now)
    row = repo.acquire_control(user_id=user, session_id=row["session_id"], now_ms=now+LIMIT-1)
    restored = MockInterviewRepository(repo.settings).acquire_control(user_id=user,
        session_id=row["session_id"], now_ms=now+LIMIT)
    assert round_state(restored).phase == "generating_report"
    assert restored["data"]["error"] is None and restored["data"]["end_reason"] == "time_limit"
    assert restored["data"]["control_token"] != row["data"]["control_token"]


@pytest.mark.parametrize("failed", [False, True])
def test_reconnect_resumes_crashed_duration_report_but_does_not_retry_failed_report(repositories, failed):
    repo, billing, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = start(repo, user, now)
    sid = row["session_id"]
    expired = repo.expire_duration(user_id=user, session_id=sid, now_ms=now+LIMIT)
    old_operation = round_state(expired).operation_id
    claim = repo.claim_generation(user_id=user, session_id=sid,
        operation_id=old_operation, now_ms=now+LIMIT)
    old_claim = claim["data"]["generation_claim"]
    if failed:
        repo.finish_generation(user_id=user, session_id=sid, operation_id=old_operation,
            claim_id=old_claim, now_ms=now+LIMIT+1, failed=True)
    restarted = MockInterviewRepository(repo.settings)
    restored = restarted.acquire_control(user_id=user, session_id=sid, now_ms=now+LIMIT+2)
    assert round_state(restored).phase == "generating_report"
    assert restored["data"]["generation_claim"] is None
    assert restored["data"]["generation_claim_until_ms"] == 0
    assert billing.state_for_user(user_id=user).balance == 100
    if failed:
        assert round_state(restored).operation_id == old_operation
        assert restored["data"]["error"] == "generation_unavailable"
    else:
        new_operation = round_state(restored).operation_id
        assert new_operation != old_operation and restored["data"]["error"] is None
        late = repo.finish_generation(user_id=user, session_id=sid, operation_id=old_operation,
            claim_id=old_claim, now_ms=now+LIMIT+3, report={"summary": "不得覆盖的旧报告"})
        assert round_state(late).operation_id == new_operation and late["data"].get("report") is None
        new_claim = restarted.claim_generation(user_id=user, session_id=sid,
            operation_id=new_operation, now_ms=now+LIMIT+3)
        completed = restarted.finish_generation(user_id=user, session_id=sid, operation_id=new_operation,
            claim_id=new_claim["data"]["generation_claim"], now_ms=now+LIMIT+4,
            report={"summary": "合成恢复报告", "overall_score": None})
        assert round_state(completed).phase == "completed"


def test_legacy_start_is_recovered_for_recent_offline_record_and_no_more_minute_charges(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = force_phase(repo, user, start(repo, user, now), "listening", now)
    sid = row["session_id"]
    def legacy(record, cursor):
        for key in ("started_at_ms", "deadline_at_ms", "duration_limit_ms", "end_reason"):
            record["data"].pop(key, None)
        record["data"].update(billed_minutes=7, error="mock_minute_insufficient_balance")
        repo._ledger(cursor, user_id=user, session_id=sid, kind="mock_interview_minute_settlement",
            points=-5, reference=f"mock:{sid}:minute:1", now_ms=now)
    repo.change(user_id=user, session_id=sid, now_ms=now, operation=legacy)
    row = repo.acquire_control(user_id=user, session_id=sid, now_ms=now+LIMIT-5000)
    assert repo.duration_deadline(row) == now+LIMIT
    row = repo.control_tick(user_id=user, session_id=sid, control_token=row["data"]["control_token"],
        now_ms=now+LIMIT-5000, active=True)
    assert repo.interaction_deadline(row) == now+LIMIT and row["data"]["error"] is None
    assert billing.state_for_user(user_id=user).balance == 95 and row["data"]["billed_minutes"] == 7
    # Recent activity and an unexpired control lease cannot conceal time expiry.
    with repo.connect() as conn:
        conn.execute("UPDATE mock_interviews SET updated_at_ms=%s WHERE session_id=%s", (now+LIMIT, sid))
    candidates = repo.recovery_candidates(now_ms=now+LIMIT, limit=2)
    assert any(item["session_id"] == sid for item in candidates)
    row = repo.expire_offline(user_id=user, session_id=sid, now_ms=now+LIMIT)
    assert row["data"]["end_reason"] == "time_limit" and round_state(row).phase == "generating_report"
    assert billing.state_for_user(user_id=user).balance == 95


def test_terminal_fault_refunds_only_actual_settled_legacy_charges_once(repositories):
    repo, billing, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = start(repo, user, now)
    sid = row["session_id"]
    def legacy(record, cursor):
        record["data"]["billed_minutes"] = 7  # Deliberately not the financial source of truth.
        repo._ledger(cursor, user_id=user, session_id=sid, kind="mock_interview_minute_settlement",
            points=-5, reference=f"mock:{sid}:minute:1", now_ms=now)
    row = repo.change(user_id=user, session_id=sid, now_ms=now, operation=legacy)
    for _ in range(3):
        op = round_state(row).operation_id
        claim = repo.claim_generation(user_id=user, session_id=sid, operation_id=op, now_ms=now)
        row = repo.finish_generation(user_id=user, session_id=sid, operation_id=op,
            claim_id=claim["data"]["generation_claim"], now_ms=now, failed=True, provider_fault=True)
    assert row["refunded"] and billing.state_for_user(user_id=user).balance == 200
    repo.compensate_fault(user_id=user, session_id=sid, now_ms=now)
    assert billing.state_for_user(user_id=user).balance == 200
    with repo.connect() as conn:
        ledger = conn.execute("SELECT points FROM points_redemption_ledger WHERE reference_id=%s", (f"mock:{sid}:refund",)).fetchall()
    assert ledger == [{"points": 105}]


@pytest.mark.parametrize("status", ["pending", "active_claim", "active_control", "failed"])
def test_recovery_promptly_finds_only_unowned_pending_time_limit_reports(repositories, status):
    repo, _, _ = repositories
    user = account(repositories)
    now = int(time()*1000)
    row = start(repo, user, now)
    sid = row["session_id"]
    at_deadline = now+LIMIT
    row = repo.expire_duration(user_id=user, session_id=sid, now_ms=at_deadline)
    if status == "active_claim":
        repo.claim_generation(user_id=user, session_id=sid,
            operation_id=round_state(row).operation_id, now_ms=at_deadline)
    elif status == "active_control":
        repo.acquire_control(user_id=user, session_id=sid, now_ms=at_deadline)
    elif status == "failed":
        op = round_state(row).operation_id
        claim = repo.claim_generation(user_id=user, session_id=sid, operation_id=op, now_ms=at_deadline)
        repo.finish_generation(user_id=user, session_id=sid, operation_id=op,
            claim_id=claim["data"]["generation_claim"], now_ms=at_deadline, failed=True)
    scanned = repo.recovery_candidates(now_ms=at_deadline+1)
    assert any(item["session_id"] == sid for item in scanned) is (status == "pending")
    if status == "active_claim":
        # Once the bounded provider claim expires, recovery need not wait for
        # twenty-minute idle expiry. This keeps a restart from stranding reports.
        saved = repo.get(user_id=user, session_id=sid)
        claim_end = saved["data"]["generation_claim_until_ms"]
        assert any(item["session_id"] == sid for item in repo.recovery_candidates(now_ms=claim_end))
    if status == "active_control":
        saved = repo.get(user_id=user, session_id=sid)
        assert any(item["session_id"] == sid for item in repo.recovery_candidates(
            now_ms=saved["data"]["lease_until_ms"]))


def test_pending_time_limit_report_scan_keeps_two_record_bound(repositories):
    repo, _, _ = repositories
    now = int(time()*1000)
    pending = []
    for _ in range(3):
        user = account(repositories)
        row = start(repo, user, now)
        ended = repo.expire_duration(user_id=user, session_id=row["session_id"], now_ms=now+LIMIT)
        pending.append(ended["session_id"])
    candidates = repo.recovery_candidates(now_ms=now+LIMIT+1, limit=100)
    assert len(candidates) == 2 and all(row["session_id"] in pending for row in candidates)
