"""Local-only synthetic PostgreSQL contract and controlled authentication races."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import os
from threading import Event
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.services import authentication_service as authentication_module
from app.services.postgres_authentication_repository import PostgresAuthenticationRepository
from test_authentication_read_path import build_auth_service, seed_auth


DATABASE_URL = os.environ.get("OFFERSTEADY_TEST_AUTH_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Explicit isolated local auth PostgreSQL required")


@pytest.fixture
def auth_repository():
    assert conninfo_to_dict(DATABASE_URL).get("host") in {"localhost", "127.0.0.1", "::1"}, "Auth tests require local synthetic PostgreSQL"
    schema = f"synthetic_auth_read_{uuid4().hex}"
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        settings = Settings(_env_file=None, environment="test", database_url=make_conninfo(
            DATABASE_URL, options=f"-c search_path={schema}"))
        repository = PostgresAuthenticationRepository(settings)
        with repository._connect() as connection:
            connection.execute("CREATE TABLE admin_user_restrictions (user_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        yield repository
    finally:
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def count_database_work(repository, monkeypatch):
    counts = {"connections": 0, "selects": 0, "updates": 0, "updated_rows": 0, "other": 0}
    original_connect = repository._connect

    class CursorProxy:
        def __init__(self, cursor):
            self.cursor = cursor
        def __enter__(self):
            self.cursor.__enter__()
            return self
        def __exit__(self, *args):
            return self.cursor.__exit__(*args)
        def __getattr__(self, name):
            return getattr(self.cursor, name)
        def execute(self, query, params=None):
            self.cursor.execute(query, params)
            operation = str(query).strip().split()[0].upper()
            counts[{"SELECT": "selects", "UPDATE": "updates"}.get(operation, "other")] += 1
            if operation == "UPDATE":
                counts["updated_rows"] += self.cursor.rowcount
            return self

    class ConnectionProxy:
        def __init__(self, connection):
            self.connection = connection
        def __enter__(self):
            self.connection.__enter__()
            return self
        def __exit__(self, *args):
            return self.connection.__exit__(*args)
        def __getattr__(self, name):
            return getattr(self.connection, name)
        def cursor(self, *args, **kwargs):
            return CursorProxy(self.connection.cursor(*args, **kwargs))

    def counted_connect():
        counts["connections"] += 1
        return ConnectionProxy(original_connect())
    monkeypatch.setattr(repository, "_connect", counted_connect)
    return counts


def test_valid_requests_use_one_authoritative_select_and_connection_without_writes(auth_repository, monkeypatch):
    service, repository = build_auth_service(auth_repository)
    user, session, token = seed_auth(service, repository)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: session.last_used_at_ms + 59_999)
    # Full profile conversion would open the old separate bindings connection.
    monkeypatch.setattr(repository, "_user_from_row", lambda row: pytest.fail("Authentication loaded a full user"))
    counts = count_database_work(repository, monkeypatch)
    for _ in range(40):
        assert service.authenticate_access_token(access_token=token).user_id == user.user_id
    assert counts == {"connections": 40, "selects": 40, "updates": 0, "updated_rows": 0, "other": 0}


def test_due_touch_uses_one_additional_connection_and_only_one_activity_update(auth_repository, monkeypatch):
    service, repository = build_auth_service(auth_repository)
    _, snapshot, token = seed_auth(service, repository)
    used = snapshot.last_used_at_ms + 60_000
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: used)
    counts = count_database_work(repository, monkeypatch)
    service.authenticate_access_token(access_token=token)
    service.authenticate_access_token(access_token=token)
    assert counts == {"connections": 3, "selects": 2, "updates": 1, "updated_rows": 1, "other": 0}
    assert repository.get_auth_session(snapshot.auth_session_id) == replace(snapshot, last_used_at_ms=used)


@pytest.mark.parametrize("change", ["restricted", "user-deleted", "session-deleted", "revoked", "expired"])
def test_committed_security_change_is_visible_to_the_next_request(auth_repository, monkeypatch, change):
    service, repository = build_auth_service(auth_repository)
    user, snapshot, token = seed_auth(service, repository)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: snapshot.last_used_at_ms + 1)
    service.authenticate_access_token(access_token=token)
    with repository._connect() as connection:
        if change == "restricted":
            connection.execute("INSERT INTO admin_user_restrictions VALUES (%s, 'active')", (user.user_id,))
        elif change == "user-deleted":
            connection.execute("DELETE FROM auth_users WHERE user_id=%s", (user.user_id,))
        elif change == "session-deleted":
            connection.execute("DELETE FROM auth_sessions WHERE auth_session_id=%s", (snapshot.auth_session_id,))
        else:
            connection.execute("UPDATE auth_sessions SET status=%s,revoked_at_ms=%s WHERE auth_session_id=%s",
                (change, snapshot.last_used_at_ms + 1, snapshot.auth_session_id))
    with pytest.raises(DomainRequestError) as failure:
        service.authenticate_access_token(access_token=token)
    assert failure.value.status_code == (404 if change == "restricted" else 401)


def test_restriction_removal_is_immediately_visible_without_auth_cache(auth_repository, monkeypatch):
    service, repository = build_auth_service(auth_repository)
    user, snapshot, token = seed_auth(service, repository)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: snapshot.last_used_at_ms + 1)
    with repository._connect() as connection:
        connection.execute("INSERT INTO admin_user_restrictions VALUES (%s, 'active')", (user.user_id,))
    with pytest.raises(DomainRequestError):
        service.authenticate_access_token(access_token=token)
    with repository._connect() as connection:
        connection.execute("UPDATE admin_user_restrictions SET status='revoked' WHERE user_id=%s", (user.user_id,))
    assert service.authenticate_access_token(access_token=token).user_id == user.user_id


def test_minimal_schema_without_admin_module_keeps_prior_compatibility(auth_repository):
    service, repository = build_auth_service(auth_repository)
    user, session, token = seed_auth(service, repository)
    with repository._connect() as connection:
        connection.execute("DROP TABLE admin_user_restrictions")
    state, available = repository.get_access_token_state(auth_session_id=session.auth_session_id, user_id=user.user_id)
    assert state == session and available is True
    assert service.authenticate_access_token(access_token=token).user_id == user.user_id


def test_postgres_concurrent_delayed_touches_only_update_one_row(auth_repository):
    service, repository = build_auth_service(auth_repository)
    _, snapshot, _ = seed_auth(service, repository)
    used = snapshot.last_used_at_ms + 60_000
    with ThreadPoolExecutor(max_workers=8) as pool:
        changed = list(pool.map(lambda _: repository.touch_auth_session(snapshot, used_at_ms=used, min_interval_ms=60_000), range(32)))
    assert sum(changed) == 1
    assert repository.get_auth_session(snapshot.auth_session_id) == replace(snapshot, last_used_at_ms=used)


@pytest.mark.parametrize("change", ["revoked", "expired", "deleted", "refreshed", "password-reset"])
def test_committed_security_transaction_wins_over_delayed_touch(auth_repository, monkeypatch, change):
    service, repository = build_auth_service(auth_repository)
    _, snapshot, token = seed_auth(service, repository)
    used = snapshot.last_used_at_ms + 60_000
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: used)
    read_completed, resume_touch = Event(), Event()
    original_touch = repository.touch_auth_session
    touched = []
    def delayed_touch(session, **kwargs):
        read_completed.set()
        assert resume_touch.wait(5), "Synthetic concurrent change did not complete"
        changed = original_touch(session, **kwargs)
        touched.append(changed)
        return changed
    monkeypatch.setattr(repository, "touch_auth_session", delayed_touch)
    with ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(service.authenticate_access_token, access_token=token)
        assert read_completed.wait(5), "Synthetic authentication did not reach touch"
        try:
            if change == "deleted":
                with repository._connect() as connection:
                    connection.execute("DELETE FROM auth_sessions WHERE auth_session_id=%s", (snapshot.auth_session_id,))
                expected = None
            elif change == "refreshed":
                _, expected, _, _ = service.refresh(refresh_token="synthetic-refresh-token")
            else:
                if change == "password-reset":
                    # The real password reset lifecycle commits user credential
                    # replacement and session revocation before the old touch.
                    with repository._connect() as connection:
                        connection.execute("UPDATE auth_users SET password_hash='synthetic-reset-hash' WHERE user_id=%s", (snapshot.user_id,))
                expected = repository.save_auth_session(replace(snapshot, status="revoked" if change == "password-reset" else change, revoked_at_ms=used))
        finally:
            resume_touch.set()
        # This request already passed its authoritative read. Only its metadata
        # write is delayed; the next request must observe the new authority.
        assert request.result(timeout=5).auth_session_id == snapshot.auth_session_id
    assert touched == [False]
    assert repository.get_auth_session(snapshot.auth_session_id) == expected
    if change != "refreshed":
        with pytest.raises(DomainRequestError):
            service.authenticate_access_token(access_token=token)


@pytest.mark.parametrize("change", ["refreshed", "revoked", "deleted"])
def test_old_expiry_snapshot_cannot_overwrite_refresh_or_revocation(auth_repository, change):
    service, repository = build_auth_service(auth_repository)
    _, snapshot, _ = seed_auth(service, repository, expires=100)
    if change == "deleted":
        with repository._connect() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE auth_session_id=%s", (snapshot.auth_session_id,))
        expected = None
    else:
        expected = repository.save_auth_session(replace(snapshot,
            **({"expires_at_ms": 10_000, "refresh_token_fingerprint": "synthetic-rotated-after-expiry"}
               if change == "refreshed" else {"status": "revoked", "revoked_at_ms": 150})))
    assert repository.expire_auth_session(snapshot, expired_at_ms=200) is False
    assert repository.get_auth_session(snapshot.auth_session_id) == expected


def test_expired_session_is_persisted_without_upsert_or_touch(auth_repository, monkeypatch):
    service, repository = build_auth_service(auth_repository)
    _, snapshot, token = seed_auth(service, repository)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: snapshot.expires_at_ms + 1)
    counts = count_database_work(repository, monkeypatch)
    with pytest.raises(DomainRequestError) as failure:
        service.authenticate_access_token(access_token=token)
    assert failure.value.status_code == 401
    assert counts == {"connections": 2, "selects": 1, "updates": 1, "updated_rows": 1, "other": 0}
    assert repository.get_auth_session(snapshot.auth_session_id) == replace(snapshot, status="expired", revoked_at_ms=snapshot.expires_at_ms + 1)
