"""Read-only Global auth/state runtime probe; no main, lifecycle or external IO."""
from __future__ import annotations
import argparse
import ast
from dataclasses import replace
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import socket
import sys
import threading
import time

sys.dont_write_bytecode = True


class ProbeError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise ProbeError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def deny(*_args, **_kwargs):
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


def inventory(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
            and p.name != ".desktop-release-manifest.lock"}


def function_nodes(source):
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[node.name + "." + method.name] = method
    return result


def node_hashes(source):
    lines = source.splitlines(keepends=True)
    return {name: digest("".join(lines[min([n.lineno] + [d.lineno for d in n.decorator_list])-1:n.end_lineno]).encode())
            for name, n in function_nodes(source).items()}


def describe_routes(app_root, prefix):
    sys.path.insert(0, str(app_root.parent))
    from fastapi import FastAPI
    from app.api.v1 import api_router
    from app.modules import mock_interview
    shell = FastAPI()
    shell.include_router(api_router, prefix=prefix)
    schema = shell.openapi()
    return {"http": {path: sorted(methods) for path, methods in schema["paths"].items()},
            "mockWebSockets": sorted(r.path for r in mock_interview.router.routes if r.__class__.__name__ in {"APIWebSocketRoute", "WebSocketRoute"})}, schema


def synthetic_auth_check(settings):
    from app.core.errors import DomainRequestError
    from app.ports.authentication import AuthSessionRecord, UserRecord
    from app.services.authentication_repository import InMemoryAuthenticationRepository
    from app.services.authentication_service import AuthenticationService, JWTAccessTokenCodec, PBKDF2PasswordHasher
    import jwt
    synthetic = settings.model_copy(update={"auth_jwt_secret": "synthetic-runtime-probe-signing-key-32bytes", "auth_password_hash_iterations": 1000})
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
        password_hasher=PBKDF2PasswordHasher(synthetic), token_codec=codec, wechat_provider=None, sms_provider=None)
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
    claims = dict(sub=user.user_id, sid=session.auth_session_id, login_id=user.login_id,
                  typ="refresh", iat=now // 1000, exp=now // 1000 + 600, iss=synthetic.auth_jwt_issuer)
    try:
        codec.decode_access_token(jwt.encode(claims, synthetic.auth_jwt_secret, algorithm="HS256"))
    except DomainRequestError as exc:
        require(exc.status_code == 401, "token_type_status")
    else:
        raise ProbeError("wrong_token_type_authorized")


def global_policy_check(settings, app_root, expected):
    from app.services.global_mock_interview_repository import GlobalMockInterviewRepository
    from app.services.question_prefetch_scheduler import QuestionPrefetchScheduler
    from app.services.chat_service import _QUESTION_PREFETCH_TTL_MS, _QUESTION_PREFETCH_MAX_KEYS
    from app.modules import web
    # Do not construct a repository: execute the unchanged quote on fixed,
    # entirely synthetic cursor rows, without a connection or migration.
    repo = object.__new__(GlobalMockInterviewRepository)
    class Cursor:
        def __init__(self):
            self.rows = iter([{"entitlement_id": "synthetic"}, None, {"used": 2}, {"saved": 0}])
            self.queries = []
        def execute(self, query, params=None):
            self.queries.append(query)
        def fetchone(self):
            return next(self.rows)
    cursor = Cursor()
    quote = repo._quote(cursor, "synthetic-global-probe-owner", 1_800_000_000_000)
    require(quote["eligible"] and quote["dailyLimit"] == 3 and quote["dailyFreeRemaining"] == 1
        and quote["entryPoints"] == 0 and quote["minutePoints"] == 0 and quote["timezone"] == "UTC", "global_mock_policy_mismatch")
    require(any("duration_days>=7" in q for q in cursor.queries)
        and all("wallet" not in q and "points_ledger" not in q for q in cursor.queries), "regional_commercial_mismatch")
    require(getattr(repo, "duration_limit_ms", None) is None, "cn_deadline_introduced")
    require(settings.global_mock_interview_enabled is False, "global_mock_flag_changed")
    manifest = web._published_desktop_manifest()
    require(manifest is not None and len(manifest["entries"]) == 3
        and all(e["version"] == "1.3.5" for e in manifest["entries"]), "global_desktop_manifest_changed")
    require(web._published_desktop_manifest_path() == app_root / "global_desktop_release_manifest.json", "desktop_region_changed")
    scheduler = QuestionPrefetchScheduler(lambda **_kwargs: None, logger=logging.getLogger("readonly-global-probe"))
    config = {"workers": scheduler._worker_limit, "maxKeys": scheduler._max_keys,
        "quietSeconds": scheduler._quiet_seconds, "maxWaitSeconds": scheduler._max_wait_seconds,
        "pendingTtlSeconds": scheduler._pending_ttl_seconds, "stateTtlSeconds": scheduler._state_ttl_seconds,
        "cacheTtlMs": _QUESTION_PREFETCH_TTL_MS, "cacheMaxKeys": _QUESTION_PREFETCH_MAX_KEYS}
    require(config == expected["prefetchConfig"], "prefetch_config_mismatch")
    require(scheduler.diagnostics()["workers"] == 0 and scheduler.diagnostics()["active"] == 0, "probe_started_workers")
    scheduler.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", default="/app/apps/backend/app")
    parser.add_argument("--expectations", required=True)
    parser.add_argument("--expected-config-sha", required=True)
    args = parser.parse_args()
    require(re.fullmatch("[0-9a-f]{64}", args.expected_config_sha), "invalid_config_sha")
    app_root = Path(args.app_root).resolve()
    repo_root = app_root.parents[2]
    expected = json.loads(Path(args.expectations).read_text())
    require(expected["schemaVersion"] == 1, "expectation_schema")
    install_guards()
    actual_app = inventory(app_root)
    actual_prompts = inventory(repo_root / "ai/prompts")
    require(actual_app == expected["app"], "application_inventory_mismatch")
    require(actual_prompts == expected["prompts"], "prompt_inventory_mismatch")
    for path, hashes in expected["protectedNodes"].items():
        actual = node_hashes((app_root / path).read_text())
        require(all(actual.get(k) == v for k, v in hashes.items()), "protected_node_mismatch")
    for path, sha in expected["prefetchSources"].items():
        require(actual_app.get(path) == sha, "prefetch_source_mismatch")
    for path, names in expected["syncStateNodes"].items():
        actual = function_nodes((app_root / path).read_text())
        require(all(type(actual.get(n)) is ast.FunctionDef for n in names), "async_state_handler")
    for path in app_root.rglob("*.py"):
        if not path.name.startswith("._"):
            compile(path.read_bytes(), str(path), "exec")
    sys.path.insert(0, str(app_root.parent))
    from app.core.config import Settings, REPO_ROOT
    settings = Settings(_env_file=None)
    require(REPO_ROOT == repo_root and settings.product_edition == "global" and settings.environment == "production", "runtime_region_or_root")
    require(digest(canonical({k: getattr(settings, k) for k in expected["runtimeConfigFields"]})) == args.expected_config_sha, "runtime_config_mismatch")
    routes, schema = describe_routes(app_root, settings.api_prefix)
    require(routes == expected["routes"], "routes_mismatch")
    require(digest(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()) == expected["openapiSha"], "openapi_mismatch")
    from app.services.chat_service import _QUESTION_PREFETCH_TTL_MS, _QUESTION_PREFETCH_MAX_KEYS
    require(_QUESTION_PREFETCH_TTL_MS == 60_000 and _QUESTION_PREFETCH_MAX_KEYS == 128, "prefetch_bounds_mismatch")
    global_policy_check(settings, app_root, expected)
    synthetic_auth_check(settings)
    require("app.main" not in sys.modules, "application_main_imported")
    print(json.dumps({"passed": True, "applicationFiles": len(actual_app), "promptFiles": len(actual_prompts),
        "protectedNodes": sum(map(len, expected["protectedNodes"].values())), "httpPaths": len(routes["http"]),
        "mockWebSockets": len(routes["mockWebSockets"]), "routesSha": digest(canonical(routes)), "openapiSha": expected["openapiSha"],
        "runtimeConfigSha": args.expected_config_sha, "syntheticAuthPassed": True, "syncStateNodes": 8,
        "globalMockPolicyPreserved": True, "globalMockEnabled": False, "globalDesktopVersion": "1.3.5",
        "networkRequests": 0, "databaseOperations": 0, "fileWrites": 0,
        "workerThreadsStarted": 0, "mainImported": False, "lifespanEntered": False, "dependenciesResolved": False,
        "privateValuesPrinted": False}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__,
            "errorCode": str(exc) if isinstance(exc, ProbeError) else "probe_failed", "privateValuesPrinted": False}))
        raise SystemExit(1) from None
