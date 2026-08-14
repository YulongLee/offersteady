from dataclasses import replace

from app.core.config import REPO_ROOT, Settings
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.session_service import SessionService


class EmptyDocumentRepository:
    def get_by_id(self, document_id):
        return None


def service() -> tuple[SessionService, InMemoryInterviewSessionRepository]:
    repository = InMemoryInterviewSessionRepository()
    return SessionService(
        settings=Settings(
            interview_idle_warning_seconds=18 * 60,
            interview_idle_timeout_seconds=20 * 60,
        ),
        document_repository=EmptyDocumentRepository(),
        repository=repository,
    ), repository


def test_idle_state_warns_then_expires_without_polling_activity() -> None:
    sessions, repository = service()
    created = sessions.create_session(user_id="idle-user", title="合成面试")
    live = sessions.start_session(user_id="idle-user", session_id=created.session_id)
    baseline = 1_800_000_000_000
    repository.sessions[live.session_id] = replace(live, last_activity_at_ms=baseline, updated_at_ms=baseline)

    warning = sessions.idle_status(user_id="idle-user", session_id=live.session_id, at_ms=baseline + 18 * 60 * 1000)
    expired = sessions.idle_status(user_id="idle-user", session_id=live.session_id, at_ms=baseline + 20 * 60 * 1000)

    assert warning["state"] == "warning"
    assert expired["state"] == "expired"


def test_preparing_session_never_expires_before_it_has_started() -> None:
    sessions, repository = service()
    created = sessions.create_session(user_id="preparing-user", title="尚未开始的面试")
    baseline = 1_800_000_000_000
    repository.sessions[created.session_id] = replace(created, last_activity_at_ms=baseline, updated_at_ms=baseline)

    idle = sessions.idle_status(
        user_id="preparing-user",
        session_id=created.session_id,
        at_ms=baseline + 24 * 60 * 60 * 1000,
    )

    assert idle["state"] == "active"
    assert sessions.list_idle_live_sessions(user_id="preparing-user", at_ms=baseline + 24 * 60 * 60 * 1000) == []


def test_unstarted_session_repair_migration_is_narrow_and_one_time() -> None:
    migration = REPO_ROOT / "apps/backend/migrations/versions/0028_restore_unstarted_interviews.sql"
    sql = migration.read_text(encoding="utf8")

    assert "status = 'ended'" in sql
    assert "started_at_ms IS NULL" in sql
    assert "deleted_at_ms IS NULL" in sql
    assert "status = 'preparing'" in sql


def test_continue_refreshes_live_activity_and_end_is_idempotent() -> None:
    sessions, _ = service()
    created = sessions.create_session(user_id="continue-user", title="合成面试")
    live = sessions.start_session(user_id="continue-user", session_id=created.session_id)
    continued = sessions.continue_session(user_id="continue-user", session_id=live.session_id)
    first_end = sessions.end_session(user_id="continue-user", session_id=live.session_id)
    second_end = sessions.end_session(user_id="continue-user", session_id=live.session_id)

    assert continued.last_activity_at_ms >= live.last_activity_at_ms
    assert first_end.status == second_end.status == "ended"
    assert first_end.ended_at_ms == second_end.ended_at_ms


def test_idle_listing_is_bounded_and_user_scoped() -> None:
    sessions, repository = service()
    first = sessions.start_session(
        user_id="first-user",
        session_id=sessions.create_session(user_id="first-user", title="第一场").session_id,
    )
    second = sessions.start_session(
        user_id="second-user",
        session_id=sessions.create_session(user_id="second-user", title="第二场").session_id,
    )
    repository.sessions[first.session_id] = replace(first, last_activity_at_ms=1)
    repository.sessions[second.session_id] = replace(second, last_activity_at_ms=1)

    idle = sessions.list_idle_live_sessions(user_id="first-user", at_ms=2_000_000)

    assert [item.session_id for item in idle] == [first.session_id]
