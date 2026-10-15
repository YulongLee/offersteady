"""Read-only CN prefetch probe: no main, lifespan, dependency resolution or IO."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import socket
import sys
import threading

sys.dont_write_bytecode = True

CONFIG_FIELDS = (
    "product_edition", "environment", "api_prefix", "chat_qwen_model", "chat_qwen_base_url",
    "chat_quick_model", "chat_detail_model", "realtime_asr_model", "realtime_asr_ws_url", "realtime_asr_inference_ws_url",
    "realtime_desktop_heartbeat_write_min_interval_seconds",
    "retrieval_candidate_top_k", "retrieval_final_top_k", "retrieval_strategy", "retrieval_reranker_enabled",
    "embedding_model", "rerank_model", "screenshot_vision_model", "mock_interview_enabled",
    "mock_interview_tts_model", "mock_interview_tts_voice", "chat_detail_retrieval_prefetch_enabled",
)
SKIP_NAMES = {".desktop-release-manifest.lock"}


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
    if event in {
        "subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn",
        "socket.connect", "socket.getaddrinfo", "sqlite3.connect",
        "os.mkdir", "os.rename", "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime",
        "os.link", "os.symlink", "os.truncate",
    }:
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
    result = {}
    for path in sorted(root.rglob("*")):
        if (not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc"
                or path.name.startswith("._") or path.name in SKIP_NAMES):
            continue
        require(path.resolve().is_relative_to(root.resolve()), "source_symlink_outside_root")
        result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def method_hashes(source, class_name):
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    lines = source.splitlines(keepends=True)
    result = {}
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = min([node.lineno] + [item.lineno for item in node.decorator_list])
            result[node.name] = digest("".join(lines[start - 1:node.end_lineno]).encode())
    return result


def describe_routes(app_root, api_prefix):
    sys.path.insert(0, str(app_root.parent))
    from fastapi import FastAPI
    from app.api.v1 import api_router
    from app.modules import mock_interview
    application = FastAPI()
    application.include_router(api_router, prefix=api_prefix)
    # Only construct a routing shell. Do not import app.main or enter lifespan,
    # call any endpoint, invoke TestClient or resolve a single dependency.
    schema = application.openapi()
    routes = {path: sorted(methods) for path, methods in schema["paths"].items()}
    mock_sockets = sorted(route.path for route in mock_interview.router.routes
                          if route.__class__.__name__ in {"APIWebSocketRoute", "WebSocketRoute"})
    require("app.main" not in sys.modules, "application_main_imported")
    return {"http": routes, "mockWebSockets": mock_sockets}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", default="/app/apps/backend/app")
    parser.add_argument("--expectations", required=True)
    parser.add_argument("--expected-config-sha", required=True)
    args = parser.parse_args()
    require(re.fullmatch("[0-9a-f]{64}", args.expected_config_sha) is not None, "invalid_expected_config_sha")
    app_root = Path(args.app_root).resolve()
    repo_root = app_root.parents[2]
    expectations = json.loads(Path(args.expectations).read_text())
    require(expectations["schemaVersion"] == 1, "expectation_schema")
    install_guards()
    actual_app = inventory(app_root)
    actual_prompts = inventory(repo_root / "ai/prompts")
    require(actual_app == expectations["app"], "app_source_inventory_mismatch")
    require(actual_prompts == expectations["prompts"], "prompt_inventory_mismatch")
    for relative, expected in expectations["threeSources"].items():
        require(actual_app.get(relative) == expected, "prefetch_source_sha_mismatch")
    for relative, expected in expectations["routeModules"].items():
        require(actual_app.get(relative) == expected, "route_module_mismatch")
    for class_name, expected in expectations["protectedMethods"].items():
        relative = "services/chat_service.py" if class_name == "ChatService" else "services/realtime_speech_service.py"
        actual = method_hashes((app_root / relative).read_text(), class_name)
        require(all(actual.get(name) == value for name, value in expected.items()), "protected_method_mismatch")
    for path in app_root.rglob("*.py"):
        if not path.name.startswith("._"):
            compile(path.read_bytes(), str(path), "exec")
    sys.path.insert(0, str(app_root.parent))
    from app.core.config import Settings, REPO_ROOT
    settings = Settings(_env_file=None)
    require(REPO_ROOT == repo_root, "runtime_repository_root_mismatch")
    require(settings.product_edition == "cn" and settings.environment == "production", "production_edition_mismatch")
    require(all(hasattr(settings, key) for key in CONFIG_FIELDS), "runtime_config_field_missing")
    config_sha = digest(canonical({key: getattr(settings, key) for key in CONFIG_FIELDS}))
    require(config_sha == args.expected_config_sha, "runtime_config_mismatch")
    from app.services.chat_service import _QUESTION_PREFETCH_TTL_MS, _QUESTION_PREFETCH_MAX_KEYS
    from app.services.question_prefetch_scheduler import QuestionPrefetchScheduler
    from app.services.mock_interview_repository import MockInterviewRepository
    require(_QUESTION_PREFETCH_TTL_MS == 60_000 and _QUESTION_PREFETCH_MAX_KEYS == 128, "cache_bounds_mismatch")
    scheduler = QuestionPrefetchScheduler(lambda **_kwargs: None, logger=logging.getLogger("readonly-cn-probe"))
    scheduler_config = {
        "workers": scheduler._worker_limit, "maxKeys": scheduler._max_keys,
        "quietSeconds": scheduler._quiet_seconds, "maxWaitSeconds": scheduler._max_wait_seconds,
        "pendingTtlSeconds": scheduler._pending_ttl_seconds, "stateTtlSeconds": scheduler._state_ttl_seconds,
        "cacheTtlMs": _QUESTION_PREFETCH_TTL_MS, "cacheMaxKeys": _QUESTION_PREFETCH_MAX_KEYS,
    }
    require(scheduler_config == expectations["prefetchConfig"], "prefetch_config_mismatch")
    require(scheduler.diagnostics()["workers"] == 0 and scheduler.diagnostics()["active"] == 0, "probe_started_workers")
    scheduler.shutdown()
    require(MockInterviewRepository.daily_free_limit == 1 and MockInterviewRepository.duration_limit_ms == 3_600_000,
            "mock_policy_mismatch")
    routes = describe_routes(app_root, settings.api_prefix)
    require(routes == expectations["routes"], "runtime_routes_mismatch")
    print(json.dumps({
        "passed": True, "applicationFiles": len(actual_app), "promptFiles": len(actual_prompts),
        "protectedMethods": sum(map(len, expectations["protectedMethods"].values())),
        "routeModuleFiles": len(expectations["routeModules"]), "httpPaths": len(routes["http"]),
        "mockWebSockets": len(routes["mockWebSockets"]),
        "sourceSha": digest(canonical(actual_app)), "promptsSha": digest(canonical(actual_prompts)),
        "routesSha": digest(canonical(routes)), "runtimeConfigSha": config_sha,
        "prefetchConfig": scheduler_config, "cnMockPolicyPreserved": True,
        "networkRequests": 0, "databaseOperations": 0, "fileWrites": 0,
        "subprocesses": 0, "workerThreadsStarted": 0, "mainImported": False,
        "lifespanEntered": False, "dependenciesResolved": False, "privateValuesPrinted": False,
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__,
                          "errorCode": str(exc) if isinstance(exc, ProbeError) else "probe_failed",
                          "privateValuesPrinted": False}, sort_keys=True))
        raise SystemExit(1) from None
