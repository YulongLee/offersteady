"""Bounded reuse through real CN repositories; synthetic local PostgreSQL only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import replace
import asyncio
import json
import os
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.pq import TransactionStatus
from pydantic import ValidationError
from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.platform import cn_hot_database as provider
from app.services.postgres_authentication_repository import PostgresAuthenticationRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.document_repository import InMemoryDocumentRepository
from app.services.session_service import SessionService
from test_authentication_read_path import build_auth_service, seed_auth


DATABASE_URL = os.getenv("OFFERSTEADY_STATE_READ_TEST_DATABASE_URL", "")
local_pg = pytest.mark.skipif(not DATABASE_URL, reason="Explicit isolated local CN control PostgreSQL required")


def configuration(**changes):
    return Settings(_env_file=None, environment="test", product_edition="cn",
                    database_url="postgresql://synthetic-only.invalid/synthetic", cn_hot_database_pool_enabled=True,
                    **changes)


@pytest.fixture(autouse=True)
def close_test_runtime():
    assert provider._entry is None and provider._retiring is None
    yield
    if provider._entry is not None:
        while provider._entry is not None:
            provider.release_cn_hot_database(provider._Activation(provider._entry))
    assert provider._retiring is None


@pytest.fixture
def persistent_repositories():
    info = conninfo_to_dict(DATABASE_URL)
    assert info.get("host") in {"127.0.0.1", "localhost", "::1"}
    assert info.get("dbname") == "synthetic_state" and info.get("port") == "58642"
    schema = f"synthetic_cn_pool_{uuid4().hex}"
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    settings = Settings(_env_file=None, environment="test", product_edition="cn",
        database_url=make_conninfo(DATABASE_URL, options=f"-c search_path={schema}"),
        cn_hot_database_pool_enabled=True, cn_hot_database_pool_max_size=1,
        cn_hot_database_pool_max_waiting=1, cn_hot_database_pool_timeout_seconds=0.08)
    try:
        # Construct before explicit Backend activation: worker-like construction
        # remains on the old short path, including migrations.
        auth = PostgresAuthenticationRepository(settings)
        sessions = PostgresInterviewSessionRepository(settings)
        with auth._connect() as connection:
            connection.execute("CREATE TABLE admin_user_restrictions (user_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
            connection.execute("CREATE TABLE synthetic_pool_writes (number INTEGER PRIMARY KEY)")
        auth_service, _ = build_auth_service(auth)
        user, auth_session, token = seed_auth(auth_service, auth)
        service = SessionService(settings=settings, repository=sessions, document_repository=InMemoryDocumentRepository())
        session = service.create_session(user_id=user.user_id, title="Synthetic pool session")
        yield settings, auth, sessions, auth_service, user, auth_session, token, session
    finally:
        if provider._entry is not None:
            while provider._entry is not None:
                provider.release_cn_hot_database(provider._Activation(provider._entry))
        assert provider._retiring is None
        with psycopg.connect(DATABASE_URL) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def wait_for(predicate):
    end = monotonic() + 2
    while monotonic() < end:
        if predicate():
            return
        sleep(0.005)
    assert predicate(), "Synthetic pool condition did not settle"


@pytest.mark.parametrize("edition,enabled", [("cn", False), ("global", True)])
def test_disabled_and_global_keep_original_connect_parameters(monkeypatch, edition, enabled):
    settings = Settings(_env_file=None, product_edition=edition, database_url="synthetic-no-network",
                        cn_hot_database_pool_enabled=enabled)
    sentinel = object()
    seen = []
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: seen.append((a, kw)) or sentinel)
    assert provider.activate_cn_hot_database(settings) is None
    for cls, suffix in [(PostgresAuthenticationRepository, "authentication"), (PostgresInterviewSessionRepository, "sessions")]:
        repo = cls.__new__(cls)
        repo.settings = settings
        assert repo._connect() is sentinel
        assert seen[-1] == ((settings.database_url,), {"connect_timeout": settings.database_connect_timeout_seconds,
            "application_name": f"{settings.database_application_name}-{suffix}"})
    assert provider.cn_hot_database_diagnostics(settings) == {"active": False}


def test_worker_flag_alone_does_not_activate_a_pool(monkeypatch):
    settings = configuration()
    sentinel = object()
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: sentinel)
    assert provider.cn_hot_repository_connection(settings, "authentication") is None
    for cls in [PostgresAuthenticationRepository, PostgresInterviewSessionRepository]:
        repo = cls.__new__(cls)
        repo.settings = settings
        assert repo._connect() is sentinel
    assert provider._entry is None


@pytest.mark.parametrize("field,value", [
    ("cn_hot_database_pool_max_size", 0), ("cn_hot_database_pool_max_size", 17),
    ("cn_hot_database_pool_max_waiting", 0), ("cn_hot_database_pool_max_waiting", 129),
    ("cn_hot_database_pool_timeout_seconds", 0), ("cn_hot_database_pool_timeout_seconds", 31),
    ("cn_hot_database_pool_timeout_seconds", float("nan")),
])
def test_pool_configuration_is_bounded(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_pool_defaults_are_disabled_and_finite():
    settings = Settings(_env_file=None)
    assert not settings.cn_hot_database_pool_enabled
    assert (settings.cn_hot_database_pool_max_size, settings.cn_hot_database_pool_max_waiting,
            settings.cn_hot_database_pool_timeout_seconds) == (4, 16, 3)


def test_unknown_component_is_not_silently_pooled():
    with pytest.raises(ValueError, match="component_invalid"):
        provider.cn_hot_repository_connection(configuration(), "billing")


def test_configuration_identity_and_repr_do_not_expose_connection_data():
    cfg = provider._configuration(configuration())
    assert cfg is not None and len(cfg.identity) == 64
    assert "synthetic-only" not in repr(cfg) and "postgresql" not in cfg.identity


def test_connect_error_does_not_echo_connection_or_exception_details(monkeypatch):
    def fail(*args, **kwargs):
        raise psycopg.OperationalError("synthetic-private-connection-detail")
    monkeypatch.setattr(psycopg.Connection, "connect", fail)
    with pytest.raises(psycopg.OperationalError) as error:
        provider._SafeConnection.connect("synthetic-private-dsn")
    assert str(error.value) == "cn_hot_database_connect_failed"


@local_pg
def test_hot_repositories_share_one_connection_and_keep_cursor_and_config(persistent_repositories):
    settings, auth, sessions, _, user, auth_session, _, session = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect() as connection:
            pid = connection.info.backend_pid
            assert connection.autocommit is False
            assert connection.execute("SELECT current_schema()").fetchone()[0].startswith("synthetic_cn_pool_")
            assert connection.execute("SHOW application_name").fetchone()[0] == f"{settings.database_application_name}-cn-hot"
        for _ in range(5):
            assert auth.get_access_token_state(auth_session_id=auth_session.auth_session_id, user_id=user.user_id)[1]
            assert sessions.get_control_state(session.session_id).status == session.status
        with sessions._connect() as connection:
            assert connection.info.backend_pid == pid
            assert connection.execute("SELECT 1").fetchone() == (1,)
        stats = provider.cn_hot_database_diagnostics(settings)
        assert stats["pool"]["pool_max"] == 1 and stats["pool"]["connections_num"] == 1
        assert stats["components"]["authentication"]["acquired"] == 6
        assert stats["components"]["sessions"]["acquired"] == 6
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
@pytest.mark.parametrize("ending", ["normal", "explicit-commit", "explicit-rollback", "python-error", "sql-error"])
def test_transaction_endings_preserve_original_effects_and_recover(persistent_repositories, ending):
    settings, auth, *_ = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        try:
            with auth._connect() as connection:
                connection.execute("INSERT INTO synthetic_pool_writes VALUES (1)")
                if ending == "explicit-commit": connection.commit()
                elif ending == "explicit-rollback": connection.rollback()
                elif ending == "python-error": raise RuntimeError("synthetic-body-failure")
                elif ending == "sql-error": connection.execute("SELECT 1/0")
        except (RuntimeError, psycopg.errors.DivisionByZero):
            assert ending in {"python-error", "sql-error"}
        with auth._connect() as connection:
            assert connection.info.transaction_status == TransactionStatus.IDLE
            expected = 1 if ending in {"normal", "explicit-commit"} else 0
            assert connection.execute("SELECT count(*) FROM synthetic_pool_writes").fetchone()[0] == expected
            connection.execute("INSERT INTO synthetic_pool_writes VALUES (2)")
        with auth._connect() as connection:
            assert connection.execute("SELECT count(*) FROM synthetic_pool_writes WHERE number=2").fetchone()[0] == 1
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
@pytest.mark.parametrize("change", ["revoked", "restricted", "session-deleted", "user-deleted"])
def test_pooled_auth_still_observes_next_committed_authority_change(persistent_repositories, monkeypatch, change):
    settings, auth, _, service, user, auth_session, token, _ = persistent_repositories
    monkeypatch.setattr("app.services.authentication_service._now_ms", lambda: auth_session.last_used_at_ms + 1)
    activation = provider.activate_cn_hot_database(settings)
    try:
        assert service.authenticate_access_token(access_token=token).user_id == user.user_id
        with psycopg.connect(settings.database_url) as connection:
            if change == "revoked": connection.execute("UPDATE auth_sessions SET status='revoked' WHERE auth_session_id=%s", (auth_session.auth_session_id,))
            elif change == "restricted": connection.execute("INSERT INTO admin_user_restrictions VALUES (%s, 'active')", (user.user_id,))
            elif change == "session-deleted": connection.execute("DELETE FROM auth_sessions WHERE auth_session_id=%s", (auth_session.auth_session_id,))
            else: connection.execute("DELETE FROM auth_users WHERE user_id=%s", (user.user_id,))
        with pytest.raises(DomainRequestError) as error:
            service.authenticate_access_token(access_token=token)
        assert error.value.status_code in {401, 404}
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
def test_pooled_session_reads_observe_committed_end_and_soft_delete(persistent_repositories):
    settings, _, sessions, *_, session = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        assert sessions.get_control_state(session.session_id).status == session.status
        with psycopg.connect(settings.database_url) as connection:
            connection.execute("UPDATE interview_sessions SET status='ended', session_mode='written', interview_audio_mode='mobile' WHERE session_id=%s", (session.session_id,))
        result = sessions.get_control_state(session.session_id)
        assert (result.status, result.session_mode, result.interview_audio_mode) == ("ended", "written", "mobile")
        with psycopg.connect(settings.database_url) as connection:
            connection.execute("UPDATE interview_sessions SET deleted_at_ms=1 WHERE session_id=%s", (session.session_id,))
        assert sessions.get_control_state(session.session_id) is None
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
def test_wait_timeout_queue_bound_and_no_short_connection_bypass(persistent_repositories):
    from psycopg_pool import PoolTimeout, TooManyRequests
    settings, auth, *_ = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect():
            with ThreadPoolExecutor(max_workers=1) as executor:
                waiter = executor.submit(lambda: auth.get_auth_session("synthetic-absent"))
                wait_for(lambda: provider.cn_hot_database_diagnostics(settings)["pool"].get("requests_waiting") == 1)
                with pytest.raises(TooManyRequests): auth.get_auth_session("synthetic-absent")
                with pytest.raises(PoolTimeout): waiter.result(timeout=2)
        wait_for(lambda: provider.cn_hot_database_diagnostics(settings)["pool"].get("pool_available") == 1)
        assert provider.cn_hot_database_diagnostics(settings)["pool"]["connections_num"] == 1
        assert auth.get_auth_session("synthetic-absent") is None
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
def test_closed_connection_is_replaced_before_the_next_application_statement(persistent_repositories):
    settings, auth, *_ = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect() as connection:
            old_pid = connection.info.backend_pid
            connection.close()
        with auth._connect() as connection:
            assert connection.info.backend_pid != old_pid
            assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
def test_checkout_health_check_replaces_a_server_terminated_idle_connection(persistent_repositories):
    settings, auth, *_ = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect() as connection: old_pid = connection.info.backend_pid
        with psycopg.connect(settings.database_url) as observer:
            observer.execute("SELECT pg_terminate_backend(%s)", (old_pid,))
        with auth._connect() as connection:
            assert connection.info.backend_pid != old_pid
            connection.execute("INSERT INTO synthetic_pool_writes VALUES (9)")
        with auth._connect() as connection:
            assert connection.execute("SELECT count(*) FROM synthetic_pool_writes WHERE number=9").fetchone()[0] == 1
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
@pytest.mark.parametrize("attribute,value", [("autocommit", True), ("read_only", True)])
def test_changed_python_connection_state_is_discarded_on_return(persistent_repositories, attribute, value):
    settings, auth, *_ = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect() as connection:
            old_pid = connection.info.backend_pid
            setattr(connection, attribute, value)
        with auth._connect() as connection:
            assert connection.info.backend_pid != old_pid
            assert connection.autocommit is False and connection.read_only is None
            assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
def test_close_wakes_a_pending_waiter_without_interrupting_held_work(persistent_repositories):
    from psycopg_pool import PoolClosed
    original, auth, *_ = persistent_repositories
    settings = original.model_copy(update={"cn_hot_database_pool_timeout_seconds": 2})
    auth.settings = settings
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect() as connection:
            with ThreadPoolExecutor(max_workers=1) as executor:
                waiter = executor.submit(lambda: auth.get_auth_session("synthetic-absent"))
                wait_for(lambda: provider.cn_hot_database_diagnostics(settings)["pool"].get("requests_waiting") == 1)
                provider.release_cn_hot_database(activation)
                with pytest.raises(PoolClosed): waiter.result(timeout=1)
                assert connection.execute("SELECT 1").fetchone() == (1,)
        assert connection.closed and provider._retiring is None
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
def test_same_configuration_apps_share_references_and_conflicting_options_are_rejected(persistent_repositories):
    settings, auth, *_ = persistent_repositories
    first = provider.activate_cn_hot_database(settings)
    second = provider.activate_cn_hot_database(settings.model_copy())
    try:
        assert first.entry is second.entry
        assert provider.cn_hot_database_diagnostics(settings)["references"] == 2
        different = settings.model_copy(update={"database_url": make_conninfo(settings.database_url, options="-c search_path=public")})
        with pytest.raises(RuntimeError, match="configuration_conflict"):
            provider.activate_cn_hot_database(different)
        with pytest.raises(RuntimeError, match="configuration_conflict"):
            provider.cn_hot_repository_connection(different, "authentication")
        provider.release_cn_hot_database(first)
        assert auth.get_auth_session("synthetic-absent") is None
    finally:
        provider.release_cn_hot_database(first)
        provider.release_cn_hot_database(second)
    with pytest.raises(RuntimeError, match="runtime_closed"): auth._connect()
    fresh = provider.activate_cn_hot_database(settings)
    try: assert auth.get_auth_session("synthetic-absent") is None
    finally: provider.release_cn_hot_database(fresh)


@local_pg
def test_close_keeps_current_borrower_usable_then_closes_on_return_and_bounds_reopen(persistent_repositories):
    settings, auth, *_ = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect() as connection:
            provider.release_cn_hot_database(activation)
            assert not connection.closed and connection.execute("SELECT 1").fetchone() == (1,)
            with pytest.raises(RuntimeError, match="runtime_closed"): auth._connect()
            with pytest.raises(RuntimeError, match="borrowers_returning"): provider.activate_cn_hot_database(settings)
        assert connection.closed
        fresh = provider.activate_cn_hot_database(settings)
        try: assert auth.get_auth_session("synthetic-absent") is None
        finally: provider.release_cn_hot_database(fresh)
    finally:
        provider.release_cn_hot_database(activation)


@local_pg
@pytest.mark.parametrize("startup_fails", [False, True])
def test_outer_lifespan_cleans_up_normal_or_pre_yield_startup_failure(persistent_repositories, startup_fails):
    settings, auth, *_ = persistent_repositories
    @asynccontextmanager
    async def original(_app):
        assert auth.get_auth_session("synthetic-absent") is None
        if startup_fails: raise RuntimeError("synthetic-startup-failure")
        yield
    async def exercise():
        async with provider.with_cn_hot_database_lifespan(original, settings)(None):
            assert provider.cn_hot_database_diagnostics(settings)["active"]
    if startup_fails:
        with pytest.raises(RuntimeError, match="synthetic-startup-failure"): asyncio.run(exercise())
    else: asyncio.run(exercise())
    assert provider._entry is None and provider._retiring is None
    with pytest.raises(RuntimeError, match="runtime_closed"): auth._connect()


@local_pg
@pytest.mark.parametrize("enabled,startup_fails", [(False, False), (True, False), (True, True)])
def test_real_fastapi_lifespan_connects_and_closes_the_selected_runtime(persistent_repositories, monkeypatch, enabled, startup_fails):
    from app import main
    original, auth, *_ = persistent_repositories
    settings = original.model_copy(update={"cn_hot_database_pool_enabled": enabled,
        "admin_enabled": False, "realtime_resource_reaper_enabled": False,
        "mock_interview_enabled": False, "cn_resume_optimizer_enabled": False})
    auth.settings = settings
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    if startup_fails:
        def fail_before_yield(**kwargs):
            assert provider.cn_hot_database_diagnostics(settings)["active"]
            assert auth.get_auth_session("synthetic-absent") is None
            raise RuntimeError("synthetic-real-startup-failure")
        monkeypatch.setattr(main, "RealtimeControlExecutor", fail_before_yield)
    app = main.create_app()
    app.add_api_route("/synthetic-pool-probe", lambda: {
        "recordMissing": auth.get_auth_session("synthetic-absent") is None,
        "poolActive": provider.cn_hot_database_diagnostics(settings)["active"],
    })
    if startup_fails:
        with pytest.raises(RuntimeError, match="synthetic-real-startup-failure"):
            with TestClient(app): pass
    else:
        with TestClient(app) as client:
            response = client.get("/synthetic-pool-probe")
            assert response.status_code == 200
            assert response.json() == {"recordMissing": True, "poolActive": enabled}
    assert provider._entry is None and provider._retiring is None


@local_pg
@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX fork only")
def test_fork_cannot_borrow_or_close_the_parent_pool(persistent_repositories):
    settings, auth, *_ = persistent_repositories
    activation = provider.activate_cn_hot_database(settings)
    try:
        with auth._connect() as connection: parent_backend_pid = connection.info.backend_pid
        read_fd, write_fd = os.pipe()
        child = os.fork()
        if child == 0:
            try:
                os.close(read_fd)
                provider.release_cn_hot_database(activation)
                assert provider.cn_hot_repository_connection(settings, "authentication") is None
                with auth._connect() as connection:
                    result = {"separateBackend": connection.info.backend_pid != parent_backend_pid}
                os.write(write_fd, json.dumps(result).encode())
            finally: os._exit(0)
        os.close(write_fd)
        result = json.loads(os.read(read_fd, 1024))
        os.close(read_fd)
        _, status = os.waitpid(child, 0)
        assert status == 0 and result == {"separateBackend": True}
        with auth._connect() as connection:
            assert connection.info.backend_pid == parent_backend_pid
            assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        provider.release_cn_hot_database(activation)
