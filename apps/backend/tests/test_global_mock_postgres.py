"""Run only against a disposable Global DB; CN billing tables must not exist."""
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_mock_interview_repository import GlobalMockInterviewRepository
from app.services.mock_interview_repository import round_state
from app.services.postgres_global_commerce_repository import PostgresGlobalCommerceRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository

URL = os.getenv("OFFERSTEADY_TEST_GLOBAL_PRACTICE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="Disposable Global practice DB required")
NOW = 1_800_000_000_000


@pytest.fixture(scope="module")
def repos():
    settings = Settings(_env_file=None, environment="test", product_edition="global", database_url=URL)
    sessions = PostgresInterviewSessionRepository(settings)
    commerce = GlobalCommerceService(settings, PostgresGlobalCommerceRepository(settings))
    repo = GlobalMockInterviewRepository(settings)
    yield repo, commerce, sessions
    with repo.connect() as conn:
        for name in ("points_redemption_ledger", "billing_time_pass_entitlements", "billing_usage_reservations"):
            assert conn.execute("SELECT to_regclass(%s) AS name", (name,)).fetchone()["name"] is None


def member(commerce):
    user = "synthetic-" + uuid4().hex
    entitlement = commerce.grant_purchase(user_id=user, offer_code="global-pro-weekly", source_kind="admin", source_id=user, starts_at_ms=NOW-1)
    return user, entitlement


def create(repo, user, key, now=NOW):
    return repo.create(user_id=user, idempotency_key=key, title="Synthetic practice", target_role="Backend engineer", expected_billing_class="daily_pass_free", now_ms=now)


def finish(repo, user, row, now=NOW):
    def operation(record, cursor):
        ending = round_state(record).end()
        record["data"]["state"] = asdict(ending.complete(ending.operation_id))
        cursor.execute("UPDATE interview_sessions SET status='ended',continue_target='history' WHERE session_id=%s", (row["session_id"],))
    return repo.change(user_id=user, session_id=row["session_id"], now_ms=now, operation=operation)


def test_atomic_slot_and_idempotency_without_domestic_tables(repos):
    repo, commerce, sessions = repos
    user, _ = member(commerce)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: create(repo, user, "same"), range(5)))
    assert len({r["session_id"] for r in results}) == 1
    assert sessions.get_session(results[0]["session_id"]).interview_language == "en-US"
    def attempt(key):
        try: return create(repo, user, key)
        except DomainRequestError as error: return error.error_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        competing = list(pool.map(attempt, ["a", "b", "c", "d"]))
    assert sum(isinstance(r, dict) for r in competing) == 1
    assert competing.count("mock_history_full") == 3
    assert repo.quote(user, NOW)["dailyFreeRemaining"] == 1


def test_daily_quota_survives_deletion_and_rolls_over_utc(repos):
    repo, commerce, _ = repos
    user, _ = member(commerce)
    for index in range(3):
        row = create(repo, user, str(index))
        finish(repo, user, row)
        repo.delete(user_id=user, session_id=row["session_id"], now_ms=NOW)
    assert repo.quote(user, NOW)["savedCount"] == 0
    with pytest.raises(DomainRequestError) as error:
        create(repo, user, "fourth")
    assert error.value.error_code == "global_mock_daily_limit"
    assert repo.quote(user, NOW)["timezone"] == "UTC"
    assert create(repo, user, "next-day", NOW+86_400_000)
    assert repo.quote(user, NOW+86_400_000)["dailyFreeRemaining"] == 2


def test_last_daily_allowance_is_atomic_even_with_two_empty_slots(repos):
    repo, commerce, _ = repos
    user, _ = member(commerce)
    for index in range(2):
        row = create(repo, user, str(index))
        finish(repo, user, row)
        repo.delete(user_id=user, session_id=row["session_id"], now_ms=NOW)
    def attempt(index):
        try: return create(repo, user, f"last-{index}")
        except DomainRequestError as error: return error.error_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempt, range(4)))
    assert sum(isinstance(row, dict) for row in results) == 1
    assert results.count("global_mock_daily_limit") == 3
    assert repo.quote(user, NOW)["dailyFreeRemaining"] == 0


def test_global_fair_use_restriction_is_preserved(repos):
    from app.services.global_commerce_repository import FairUseDecision
    repo, commerce, _ = repos
    user, _ = member(commerce)
    commerce.repository.save_fair_use_decision(FairUseDecision(
        decision_id="synthetic-"+uuid4().hex, user_id=user, status="restricted",
        reason_code="synthetic", evidence={}, restrict_new_sessions=True,
        effective_at_ms=NOW-1, expires_at_ms=NOW+60_000))
    with pytest.raises(DomainRequestError) as error:
        create(repo, user, "restricted")
    assert error.value.error_code == "global_fair_use_restricted"
    assert repo.quote(user, NOW)["dailyFreeRemaining"] == 3


def test_ineligible_creation_and_expired_preparation_start(repos):
    repo, commerce, _ = repos
    with pytest.raises(DomainRequestError) as error:
        create(repo, "synthetic-free-" + uuid4().hex, "denied")
    assert error.value.error_code == "global_practice_membership_required"
    user, entitlement = member(commerce)
    row = create(repo, user, "preparing")
    commerce.repository.update_entitlement(replace(entitlement, status="revoked"))
    with pytest.raises(DomainRequestError) as error:
        repo.transition(user_id=user, session_id=row["session_id"], expected_version=0, now_ms=NOW, move=lambda state: state.start())
    assert error.value.error_code == "global_practice_membership_required"
    assert round_state(repo.get(user_id=user, session_id=row["session_id"])).phase == "preparing"


def test_active_practice_is_free_after_expiry_and_fault_restores_once(repos):
    repo, commerce, _ = repos
    user, entitlement = member(commerce)
    row = create(repo, user, "active")
    sid = row["session_id"]
    row = repo.transition(user_id=user, session_id=sid, expected_version=0, now_ms=NOW, move=lambda state: state.start())
    claim = repo.claim_generation(user_id=user, session_id=sid, operation_id=round_state(row).operation_id, now_ms=NOW)
    row = repo.finish_generation(user_id=user, session_id=sid, operation_id=round_state(row).operation_id, claim_id=claim["data"]["generation_claim"], now_ms=NOW, question="How did you validate the synthetic project?")
    commerce.repository.update_entitlement(replace(entitlement, status="expired"))
    row = repo.acquire_control(user_id=user, session_id=sid, now_ms=NOW)
    for offset in range(0, 80_001, 10_000):
        row = repo.control_tick(user_id=user, session_id=sid, control_token=row["data"]["control_token"], now_ms=NOW+offset, active=True)
    assert row["data"]["billable_ms"] == 80_000 and row["data"]["billed_minutes"] == 0
    user2, _ = member(commerce)
    failed = create(repo, user2, "fault")
    failed = repo.transition(user_id=user2, session_id=failed["session_id"], expected_version=0, now_ms=NOW, move=lambda state: state.start())
    for _ in range(3):
        op = round_state(failed).operation_id
        claim = repo.claim_generation(user_id=user2, session_id=failed["session_id"], operation_id=op, now_ms=NOW)
        failed = repo.finish_generation(user_id=user2, session_id=failed["session_id"], operation_id=op, claim_id=claim["data"]["generation_claim"], now_ms=NOW, failed=True, provider_fault=True)
    assert failed["refunded"] and round_state(failed).phase == "completed"
    for _ in range(2):
        repo.compensate_fault(user_id=user2, session_id=failed["session_id"], now_ms=NOW)
    assert repo.quote(user2, NOW)["dailyFreeRemaining"] == 3
