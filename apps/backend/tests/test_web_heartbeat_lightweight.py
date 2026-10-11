"""Synthetic regression coverage; no product users or provider requests."""
from dataclasses import fields, replace
import os
import threading
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.interview_session import SessionBoundDocument, SessionHeartbeatState
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.session_service import SessionService

NOW = 1_800_000_000_000


def fixture_service(monkeypatch, *, status="live", documents=3):
    monkeypatch.setattr("app.services.session_service._now_ms", lambda: NOW)
    monkeypatch.setattr("app.services.realtime_speech_service._now_ms", lambda: NOW)
    settings = Settings(_env_file=None, interview_idle_warning_seconds=60,
                        interview_idle_timeout_seconds=120, realtime_web_heartbeat_ttl_seconds=45)
    repository = InMemoryInterviewSessionRepository()
    document_repository = Mock()
    document_repository.get_by_id.return_value = None
    sessions = SessionService(settings=settings, repository=repository, document_repository=document_repository)
    created = sessions.create_session(user_id="synthetic-owner", title="合成心跳面试")
    bound = [SessionBoundDocument(document_id=f"synthetic-material-{i}", document_kind="knowledge",
             display_name=f"Synthetic material {i}", status="ready") for i in range(documents)]
    record = replace(created, status=status, started_at_ms=NOW-10_000 if status != "preparing" else None,
                     material_binding=replace(created.material_binding, bound_documents=bound))
    repository.save_session(record)
    realtime = object.__new__(RealtimeSpeechService)
    realtime.settings = settings
    realtime.session_service = sessions
    realtime.repository = InMemoryRealtimeSpeechRepository()
    realtime._session_activity_lock = threading.Lock()
    realtime._session_last_activity_ms = {}
    realtime._session_owners = {}
    realtime.terminate_session_for_admin = Mock()
    return realtime, sessions, repository, document_repository, record


def heartbeat(service, record, **kwargs):
    return service.record_web_session_heartbeat(user_id=kwargs.pop("user_id", record.owner_user_id),
        session_id=record.session_id, binding_id=None, page=kwargs.pop("page", "live"), **kwargs)


@pytest.mark.parametrize("status", ["preparing", "live"])
def test_heartbeat_reads_once_and_never_refreshes_materials(monkeypatch, status):
    realtime, _, repository, documents, record = fixture_service(monkeypatch, status=status, documents=25)
    projection = Mock(wraps=repository.get_heartbeat_state)
    monkeypatch.setattr(repository, "get_heartbeat_state", projection)
    monkeypatch.setattr(repository, "get_session", Mock(side_effect=AssertionError("full read")))
    monkeypatch.setattr(repository, "save_session", Mock(side_effect=AssertionError("session write")))
    result = heartbeat(realtime, record, page_instance_id="synthetic-page")
    assert result.session_id == record.session_id and result.seen_at_ms == NOW
    assert result.lease_expires_at_ms == NOW + 45_000
    projection.assert_called_once_with(record.session_id)
    documents.get_by_id.assert_not_called()
    assert repository.sessions[record.session_id] == record


@pytest.mark.parametrize("offset", [0, 59_999, 60_000, 119_999, 120_000])
@pytest.mark.parametrize("status", ["preparing", "live", "ended"])
def test_idle_boundaries_match_existing_calculation(monkeypatch, offset, status):
    _, sessions, _, _, record = fixture_service(monkeypatch, status=status, documents=0)
    old = sessions.idle_status(user_id=record.owner_user_id, session_id=record.session_id, at_ms=NOW+offset)
    new = sessions.heartbeat_idle_status(user_id=record.owner_user_id, session_id=record.session_id, at_ms=NOW+offset)
    assert new == old


@pytest.mark.parametrize("missing, user, expected", [(False, "other-owner", 403), (True, "synthetic-owner", 404)])
def test_denied_heartbeat_does_not_touch_activity_or_lease(monkeypatch, missing, user, expected):
    realtime, _, repository, documents, record = fixture_service(monkeypatch)
    if missing:
        repository.sessions.clear()
    realtime.repository.save_web_session_heartbeat = Mock()
    realtime.repository.claim_live_web_session = Mock()
    with pytest.raises(DomainRequestError) as error:
        heartbeat(realtime, record, user_id=user, page_instance_id="page")
    assert error.value.status_code == expected
    assert realtime._session_owners == realtime._session_last_activity_ms == {}
    realtime.repository.save_web_session_heartbeat.assert_not_called()
    realtime.repository.claim_live_web_session.assert_not_called()
    documents.get_by_id.assert_not_called()


def test_end_is_seen_on_next_heartbeat_without_cache(monkeypatch):
    realtime, _, repository, _, record = fixture_service(monkeypatch)
    first = heartbeat(realtime, record, page_instance_id="page")
    repository.save_session(replace(record, status="ended"))
    with pytest.raises(DomainRequestError) as error:
        heartbeat(realtime, record, page_instance_id="page")
    assert error.value.status_code == 409 and error.value.error_code == "realtime_session_ended"
    assert realtime.repository.get_active_live_web_session(user_id=record.owner_user_id) == first
    realtime.terminate_session_for_admin.assert_not_called()


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_expired_heartbeat_keeps_original_cleanup_and_error(monkeypatch, cleanup_fails):
    realtime, _, repository, _, record = fixture_service(monkeypatch)
    repository.save_session(replace(record, last_activity_at_ms=NOW-120_000))
    if cleanup_fails:
        realtime.terminate_session_for_admin.side_effect = RuntimeError("synthetic cleanup fault")
    with pytest.raises(RuntimeError if cleanup_fails else DomainRequestError) as error:
        heartbeat(realtime, record, page_instance_id="page")
    realtime.terminate_session_for_admin.assert_called_once_with(
        user_id=record.owner_user_id, session_id=record.session_id, reason="idle-timeout")
    assert realtime.repository.get_active_live_web_session(user_id=record.owner_user_id) is None
    if not cleanup_fails:
        assert error.value.error_code == "realtime_session_ended"


def test_preparation_keeps_live_lease_and_live_claim_renews(monkeypatch):
    realtime, _, _, _, record = fixture_service(monkeypatch)
    first = heartbeat(realtime, record, page_instance_id="page-a")
    renewed = heartbeat(realtime, record, page_instance_id="page-a")
    assert renewed.lease_generation == first.lease_generation
    preparation = heartbeat(realtime, record, page="preparation")
    assert preparation == renewed
    replacement = heartbeat(realtime, record, page_instance_id="page-b")
    # Preserve the repository's current generation semantics, not a new rule.
    assert replacement.page_instance_id == "page-b"
    assert replacement.lease_generation >= renewed.lease_generation


def test_full_session_reads_still_refresh_changed_material(monkeypatch):
    realtime, sessions, _, documents, record = fixture_service(monkeypatch, documents=1)
    heartbeat(realtime, record)
    documents.get_by_id.assert_not_called()
    refreshed = sessions.get_session(user_id=record.owner_user_id, session_id=record.session_id)
    documents.get_by_id.assert_called_once_with("synthetic-material-0")
    assert refreshed.material_binding.bound_documents[0].active is False


def test_projection_contains_only_five_lifecycle_fields(monkeypatch):
    _, _, repository, _, record = fixture_service(monkeypatch)
    state = repository.get_heartbeat_state(record.session_id)
    assert isinstance(state, SessionHeartbeatState)
    assert {field.name for field in fields(state)} == {
        "session_id", "owner_user_id", "status", "started_at_ms", "last_activity_at_ms"}


def test_postgres_query_is_parameterized_projected_and_soft_delete_filtered(monkeypatch):
    repository = object.__new__(PostgresInterviewSessionRepository)
    connection = Mock()
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor.fetchone.return_value = None
    connection.cursor.return_value = cursor
    monkeypatch.setattr(repository, "_connect", Mock(return_value=connection))
    assert repository.get_heartbeat_state("synthetic-session") is None
    query, params = cursor.execute.call_args.args
    assert "SELECT *" not in query and "json" not in query.lower()
    assert "deleted_at_ms IS NULL" in query and params == ("synthetic-session",)
    repository._connect.assert_called_once()


@pytest.mark.skipif(not os.getenv("OFFERSTEADY_TEST_DATABASE_URL"), reason="Isolated PostgreSQL required")
def test_real_postgres_projection_excludes_deleted_and_sees_fresh_state(monkeypatch):
    database = os.environ["OFFERSTEADY_TEST_DATABASE_URL"]
    schema = "synthetic_heartbeat_" + uuid4().hex
    repository = object.__new__(PostgresInterviewSessionRepository)
    with psycopg.connect(database, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            connection.execute("""CREATE TABLE interview_sessions (
                session_id text PRIMARY KEY, owner_user_id text, status text,
                started_at_ms bigint, last_activity_at_ms bigint, deleted_at_ms bigint,
                material_binding_json jsonb)""")
            connection.execute("INSERT INTO interview_sessions VALUES (%s,%s,%s,%s,%s,NULL,%s)",
                ("synthetic-session", "synthetic-owner", "live", NOW, NOW, '{"synthetic":"unused"}'))
            monkeypatch.setattr(repository, "_connect", lambda: psycopg.connect(database, options=f"-c search_path={schema}"))
            assert repository.get_heartbeat_state("synthetic-session").status == "live"
            connection.execute("UPDATE interview_sessions SET status='ended'")
            assert repository.get_heartbeat_state("synthetic-session").status == "ended"
            connection.execute("UPDATE interview_sessions SET deleted_at_ms=%s", (NOW,))
            assert repository.get_heartbeat_state("synthetic-session") is None
            assert repository.get_heartbeat_state("missing") is None
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
