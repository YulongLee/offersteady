"""Offline actual-image probe. A release builder replaces EXPECTED once.

Uses production Settings only to compare a digest; values never leave the host.
Never enters application lifespan, starts threads, opens DB or calls providers.
"""
from __future__ import annotations

import ast
from dataclasses import fields, replace
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import socket
import sys
import threading
import time
from types import SimpleNamespace

EXPECTED = None  # RELEASE_EXPECTATIONS

sys.dont_write_bytecode = True


class ProbeError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise ProbeError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def deny(*args, **kwargs):
    raise ProbeError("external_io_forbidden")


def audit(event, args):
    if event in {"subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn",
                 "socket.connect", "socket.getaddrinfo", "sqlite3.connect", "os.mkdir", "os.rename",
                 "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime", "os.link", "os.symlink", "os.truncate"}:
        deny()
    if event == "open" and len(args) >= 3 and isinstance(args[2], int):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            deny()


def install_guards():
    sys.addaudithook(audit)
    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    socket.create_connection = deny
    socket.getaddrinfo = deny
    threading.Thread.start = deny
    import psycopg
    psycopg.connect = deny
    psycopg.Connection.connect = deny
    psycopg.AsyncConnection.connect = deny


def synthetic_auth(settings):
    from app.core.errors import DomainRequestError
    from app.ports.authentication import AuthSessionRecord, UserRecord
    from app.services.authentication_repository import InMemoryAuthenticationRepository
    from app.services.authentication_service import AuthenticationService, JWTAccessTokenCodec
    synthetic = settings.model_copy(update={"auth_jwt_secret": "synthetic-runtime-probe-signing-key-32bytes"})
    codec = JWTAccessTokenCodec(synthetic)
    repo = InMemoryAuthenticationRepository()
    now = int(time.time() * 1000)
    user = repo.save_user(UserRecord(user_id="synthetic-probe-owner", login_id="synthetic@example.invalid",
        password_hash="synthetic-unused", display_name="Synthetic", avatar_url=None,
        last_login_provider="sms", last_login_at_ms=now, created_at_ms=now, updated_at_ms=now))
    session = repo.save_auth_session(AuthSessionRecord(auth_session_id="synthetic-probe-session", user_id=user.user_id,
        client_label="synthetic-probe", refresh_token_fingerprint="synthetic-refresh", status="active",
        issued_at_ms=now, expires_at_ms=now + 600_000, last_used_at_ms=now))
    service = AuthenticationService(settings=synthetic, logger=logging.getLogger("readonly-probe"), repository=repo,
        password_hasher=None, token_codec=codec, wechat_provider=None, sms_provider=None)
    token = service._issue_access_token(user=user, auth_session=session)
    require(service.authenticate_access_token(access_token=token).user_id == user.user_id, "valid_access_rejected")
    require(repo.get_auth_session(session.auth_session_id) == session, "activity_window_changed")
    used = now + 60_000
    require(repo.touch_auth_session(session, used_at_ms=used, min_interval_ms=60_000), "metadata_touch_failed")
    require(not repo.touch_auth_session(session, used_at_ms=used, min_interval_ms=60_000), "duplicate_activity_write")
    revoked = repo.save_auth_session(replace(session, status="revoked", revoked_at_ms=now))
    require(not repo.touch_auth_session(session, used_at_ms=used, min_interval_ms=60_000), "revoked_session_touched")
    require(repo.get_auth_session(session.auth_session_id) == revoked, "security_state_overwritten")
    try:
        service.authenticate_access_token(access_token=token)
    except DomainRequestError as exc:
        require(exc.status_code == 401, "revoked_access_status")
    else:
        raise ProbeError("revoked_access_authorized")


def synthetic_control_and_documents(settings):
    from app.core.errors import DomainRequestError
    from app.ports.document_repository import DocumentRecord
    from app.ports.interview_session import SessionBoundDocument, SessionControlState
    from app.services.document_repository import InMemoryDocumentRepository
    from app.services.document_service import DocumentService, InMemoryKnowledgeCollectionStore
    from app.services.interview_session_repository import InMemoryInterviewSessionRepository
    from app.services.session_service import SessionService
    owner, now = "synthetic-control-owner", 1_800_000_000_000

    class Documents(InMemoryDocumentRepository):
        reads = 0

        def get_by_id(self, document_id):
            self.reads += 1
            return super().get_by_id(document_id)

    documents, repository = Documents(), InMemoryInterviewSessionRepository()
    service = SessionService(settings=settings, repository=repository, document_repository=documents)
    for i in range(6):
        documents.save(DocumentRecord(document_id=f"synthetic-doc-{i}", owner_user_id=owner,
            document_kind="knowledge", display_name="Synthetic notes.txt", file_kind="txt", content_type="text/plain",
            size_bytes=18, object_key=f"synthetic/{i}", status="ready", knowledge_collection_id="synthetic-collection",
            processing_requested_at_ms=None, deleted_at_ms=None, created_at_ms=now, updated_at_ms=now,
            summary="Synthetic source summary", document_version_id=f"synthetic-version-{i}", version=1,
            content_fingerprint="a" * 64, index_state="indexed"))
    document_service = DocumentService(storage=SimpleNamespace(), repository=documents,
        knowledge_store=InMemoryKnowledgeCollectionStore())
    expected_views = document_service.list_documents(user_id=owner)
    views, raw = document_service.list_documents_with_records(user_id=owner)
    require(views == expected_views and len(raw) == 6, "document_snapshot_contract_changed")
    records = []
    for i in range(12):
        session = service.create_session(user_id=owner, title="Synthetic state read")
        bound = [SessionBoundDocument(document_id=d.document_id, document_kind=d.document_kind,
            display_name=d.display_name, status=d.status, document_version_id=d.document_version_id,
            index_state=d.index_state, knowledge_collection_id=d.knowledge_collection_id,
            summary=d.summary, active=True) for d in raw.values()]
        binding = replace(session.material_binding, revision=7,
            knowledge_document_ids=[d.document_id for d in bound], bound_documents=bound, confirmed_at_ms=now)
        records.append(repository.save_session(replace(session, material_binding=binding,
            integration_references=service._build_integration_references(session_id=session.session_id,
                user_id=owner, material_binding=binding))))
    expected = service.list_sessions(user_id=owner)
    require(documents.reads == 6, "baseline_document_reads_unexpected")
    documents.reads = 0
    candidate = service.list_sessions(user_id=owner, document_records=raw)
    require(candidate == expected and documents.reads == 0, "request_document_reuse_failed")
    session = records[0]
    state = service.get_control_state(user_id=owner, session_id=session.session_id)
    require(isinstance(state, SessionControlState) and {f.name for f in fields(state)} == {
        "session_id", "owner_user_id", "status", "session_mode", "interview_audio_mode"}, "control_projection_changed")
    require(documents.reads == 0, "control_read_loaded_materials")
    for mode in ("interview", "written", "mock"):
        for status in ("preparing", "live", "ended"):
            for audio in ("computer", "mobile"):
                repository.save_session(replace(session, session_mode=mode, status=status, interview_audio_mode=audio))
                state = service.get_control_state(user_id=owner, session_id=session.session_id)
                require((state.session_mode, state.status, state.interview_audio_mode) == (mode, status, audio), "control_lifecycle_stale")
    try:
        service.get_control_state(user_id="synthetic-other", session_id=session.session_id)
    except DomainRequestError as exc:
        require(exc.status_code == 403, "control_owner_status_changed")
    else:
        raise ProbeError("control_foreign_owner_authorized")
    repository.delete_session(user_id=owner, session_id=session.session_id)
    try:
        service.get_control_state(user_id=owner, session_id=session.session_id)
    except DomainRequestError as exc:
        require(exc.status_code == 404, "control_deleted_status_changed")
    else:
        raise ProbeError("control_deleted_returned")


def main():
    require(isinstance(EXPECTED, dict), "release_expectations_missing")
    install_guards()
    root = Path("/app")
    actual = {p.relative_to(root).as_posix(): digest(p.read_bytes())
        for directory in ("apps/backend/app", "ai/prompts", "apps/backend/migrations")
        for p in (root / directory).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        and p.name != ".desktop-release-manifest.lock"}
    actual["apps/backend/pyproject.toml"] = digest((root / "apps/backend/pyproject.toml").read_bytes())
    require(actual == EXPECTED["inventory"], "application_inventory_mismatch")
    compiled = 0
    for p in (root / "apps/backend/app").rglob("*.py"):
        if not p.name.startswith("._"):
            compile(p.read_bytes(), str(p), "exec")
            compiled += 1
    require(platform.python_version() == EXPECTED["python"], "python_version_changed")
    deps = dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()))
    require(deps == EXPECTED["dependencies"] | {"psycopg-pool": "3.3.3"}, "unapproved_dependency_change")
    import psycopg_pool
    require(psycopg_pool.__version__ == "3.3.3", "pool_dependency_mismatch")
    sys.path.insert(0, str(root / "apps/backend"))
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    require(settings.product_edition == "cn" and settings.environment == "production", "runtime_region_changed")
    values = settings.model_dump(mode="json")
    defaults = {"cn_hot_database_pool_enabled": False, "cn_hot_database_pool_max_size": 4,
        "cn_hot_database_pool_max_waiting": 16, "cn_hot_database_pool_timeout_seconds": 3.0}
    require({k: values[k] for k in defaults} == defaults, "pool_not_disabled")
    original = {k: v for k, v in values.items() if k not in defaults}
    serialize = lambda v: json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    require(digest(serialize(original)) == EXPECTED["baselineSettingsSha256"], "existing_settings_changed")
    from app import main as application
    schema = application.app.openapi()
    require(digest(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()) == EXPECTED["openapiSha256"], "openapi_changed")
    synthetic_auth(settings)
    synthetic_control_and_documents(settings)
    from app.platform.cn_hot_database import cn_hot_database_diagnostics
    require(cn_hot_database_diagnostics(settings)["active"] is False, "pool_activated_unexpectedly")
    from app.services.mock_interview_repository import MockInterviewRepository
    require(MockInterviewRepository.daily_free_limit == 1 and MockInterviewRepository.duration_limit_ms == 3_600_000, "cn_mock_policy_changed")
    print(json.dumps({"passed": True, "image": os.environ.get("OFFERSTEADY_RELEASE_PROBE_IMAGE"),
        "runtimeFiles": len(actual), "compiledPython": compiled, "python": platform.python_version(),
        "dependencyCount": len(deps), "onlyAddedDependency": "psycopg-pool==3.3.3",
        "settingsSha256": digest(serialize(values)), "existingSettingsUnchanged": True,
        "openapiSha256": EXPECTED["openapiSha256"], "httpPaths": len(schema["paths"]),
        "syntheticAuthRevocationPassed": True, "syntheticDocumentReusePassed": True,
        "syntheticControlAuthorityPassed": True, "poolEnabled": False, "poolActive": False,
        "databaseOperations": 0, "networkRequests": 0, "fileWrites": 0, "workerThreadsStarted": 0,
        "lifespanEntered": False, "privateValuesPrinted": False}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__,
            "errorCode": str(exc) if isinstance(exc, ProbeError) else "probe_failed", "privateValuesPrinted": False}))
        raise SystemExit(1) from None
