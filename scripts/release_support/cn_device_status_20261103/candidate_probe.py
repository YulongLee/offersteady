"""Offline actual-image CN device-status probe; one injected expectation map.

Run with --network=none --read-only --cap-drop=ALL and server-local settings.
Never enter application lifespan or call a database/provider. Every fixture is
synthetic. Only explicitly named synthetic/control workers may start, and all
are joined before success. No production value or synthetic identifier is output.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import importlib.metadata
import json
import logging
from math import isfinite
import os
from pathlib import Path
import platform
import re
import socket
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

EXPECTED = None  # RELEASE_EXPECTATIONS

sys.dont_write_bytecode = True
WORKERS = []
OWNER, SESSION, DEVICE, CODE = ("synthetic-probe-owner", "synthetic-probe-session",
    "synthetic-probe-device", "000000")
NOW = 1_800_000_000_000


class ProbeError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise ProbeError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def serialize(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def deny(*args, **kwargs):
    raise ProbeError("external_io_forbidden")


def install_guards():
    def audit(event, args):
        if event in {"subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn",
            "socket.connect", "socket.getaddrinfo", "socket.sendto", "sqlite3.connect", "os.mkdir",
            "os.rename", "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime",
            "os.link", "os.symlink", "os.truncate"}:
            deny()
        if event == "open" and len(args) >= 3 and isinstance(args[2], int):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                deny()
    sys.addaudithook(audit)
    socket.socket.connect = socket.socket.connect_ex = deny
    socket.create_connection = socket.getaddrinfo = deny
    original_start = threading.Thread.start
    def tracked_start(worker, *args, **kwargs):
        require(worker.name.startswith(("synthetic-device-status-probe", "realtime-control"))
            or getattr(getattr(worker, "_target", None), "__name__", None) == "_do_shutdown",
            "unapproved_worker_thread")
        WORKERS.append(worker)
        return original_start(worker, *args, **kwargs)
    threading.Thread.start = tracked_start
    import psycopg
    psycopg.connect = psycopg.Connection.connect = psycopg.AsyncConnection.connect = deny


def forbid_lifespan(application):
    application.router.lifespan_context = deny
    application.router.startup = deny


def fixture(settings, *, edition="cn"):
    from app.ports.interview_session import SessionBoundDocument
    from app.ports.realtime_speech import DesktopDeviceRecord, SessionDesktopBindingRecord
    from app.services.interview_session_repository import InMemoryInterviewSessionRepository
    from app.services.realtime_speech_service import RealtimeSpeechService
    from app.services.session_service import SessionService
    repository = InMemoryInterviewSessionRepository()
    documents = Mock()
    documents.get_by_id.return_value = None
    selected = settings.model_copy(update={"product_edition": edition})
    sessions = SessionService(settings=selected, repository=repository, document_repository=documents)
    record = sessions.create_session(user_id=OWNER, title="Synthetic device status")
    record = replace(record, session_id=SESSION, status="live", material_binding=replace(
        record.material_binding, session_id=SESSION, bound_documents=[SessionBoundDocument(
            document_id=f"synthetic-material-{i}", document_kind="knowledge", display_name="Synthetic",
            status="ready") for i in range(12)]))
    repository.sessions = {SESSION: record}
    repository.get_session = Mock(wraps=repository.get_session)
    repository.get_control_state = Mock(wraps=repository.get_control_state)
    repository.save_session = Mock(wraps=repository.save_session)
    device = DesktopDeviceRecord(device_id=DEVICE, manual_code=CODE, display_name="Synthetic desktop",
        capabilities={}, registered_at_ms=NOW, last_seen_at_ms=NOW)
    binding = SessionDesktopBindingRecord(binding_id="synthetic-probe-binding", session_id=SESSION,
        owner_user_id=OWNER, device_id=DEVICE, manual_code=CODE, display_name="Synthetic desktop",
        capabilities={}, bound_at_ms=NOW, last_seen_at_ms=NOW)
    state = SimpleNamespace(device=device, binding=binding, fallback=False)
    def lookup(*, device_id, manual_code):
        return state.binding if not state.fallback else None
    events = Mock(side_effect=lambda event: event)
    service = object.__new__(RealtimeSpeechService)
    service.settings, service.session_service = selected, sessions
    service.repository = SimpleNamespace(get_desktop_device_by_code=lambda code: state.device,
        get_latest_session_desktop_binding_for_device=Mock(side_effect=lookup),
        get_latest_session_desktop_binding_by_code=Mock(side_effect=lambda **_: state.binding),
        save_event=events)
    return SimpleNamespace(service=service, sessions=sessions, repository=repository,
        documents=documents, record=record, state=state, events=events)


async def invoke(target, request, *, manual=True, session_id=SESSION, user_id=None, device_id=DEVICE):
    from app.modules.realtime_speech import publish_device_status
    from app.ports.authentication import AuthenticatedRequestContext
    from app.schemas.realtime_speech import RealtimeDeviceStatusRequest
    command = RealtimeDeviceStatusRequest(deviceId=device_id, captureState="ready", userId=user_id,
        manualCode=CODE if manual else None, sourceHealth=[{"sourceId": "synthetic-private-source",
            "label": "synthetic-private-content" * 10, "level": .2, "privateExtra": "must-filter"}],
        capabilities={"platform": "synthetic", "appVersion": "1.3.6", "privateExtra": "must-filter"})
    auth = None if manual else AuthenticatedRequestContext(OWNER, "synthetic-login", "synthetic-auth")
    return await publish_device_status(session_id, request, command, auth, target.service)


async def expect_error(call, status, error_code=None):
    from app.core.errors import DomainRequestError
    try:
        await call
    except DomainRequestError as error:
        require(error.status_code == status and (error_code is None or error.error_code == error_code),
            "synthetic_error_contract_changed")
    else:
        raise ProbeError("synthetic_invalid_status_authorized")


def require_lightweight(target, *, controls, events):
    require(target.repository.get_control_state.call_count == controls
        and target.repository.get_session.call_count == 0
        and target.documents.get_by_id.call_count == 0
        and target.repository.save_session.call_count == 0
        and target.events.call_count == events, "device_status_read_or_event_contract_changed")


async def synthetic_device_status(settings, request, executor):
    from app.platform import cn_device_status_timing as timing
    from app.core.logging import configure_logging
    samples = []
    class Capture(logging.Handler):
        def emit(self, record):
            samples.append(record.getMessage())
    logger = configure_logging(settings.model_copy(update={"log_level": "INFO"}))
    original = (logger.handlers[:], logger.level, logger.propagate)
    logger.handlers = [Capture()]; logger.propagate = False
    try:
        require(timing._logger.isEnabledFor(logging.INFO), "timing_logger_not_configured")
        timing._sample_counter = 19
        target = fixture(settings)
        result = await invoke(target, request)
        require(result.success and result.data["kind"] == "device-status", "device_status_event_missing")
        payload = result.data["payload"]
        require(payload["deviceId"] == DEVICE and payload["captureState"] == "ready"
            and len(payload["sourceHealth"][0]["label"]) == 120
            and "privateExtra" not in payload["sourceHealth"][0]
            and "privateExtra" not in payload["capabilities"], "device_status_payload_changed")
        require_lightweight(target, controls=2, events=1)
        require(len(samples) == 1 and samples[0].startswith("cn_device_status_timing "), "timing_sample_missing")
        sample = json.loads(samples[0].split(" ", 1)[1])
        labels = {"schema", "sample_every", "queue_ms", "work_ms", "worker_failed"} | {
            f"{phase}_{suffix}" for phase in timing._PHASES for suffix in ("ms", "count")}
        require(set(sample) == labels and all(type(v) in (int, float) and isfinite(v) and v >= 0
            for v in sample.values()) and sample["binding_repository_count"] == 2
            and sample["event_repository_count"] == 1, "timing_sample_fields_changed")
        require(all(marker not in samples[0] for marker in (OWNER, SESSION, DEVICE, CODE,
            "synthetic-private", "must-filter")), "timing_private_content_leaked")
        require(await executor.run(lambda: timing._current_trace.get()) is None, "timing_worker_scope_leaked")
        checked = 1
        for invalid in ("generation", "heartbeat", "owner", "missing", "replaced"):
            target = fixture(settings)
            if invalid == "generation": target.state.device = replace(target.state.device, generation=2)
            elif invalid == "heartbeat": target.state.device = replace(target.state.device,
                last_seen_at_ms=NOW - settings.realtime_desktop_heartbeat_ttl_seconds * 1000 - 1)
            elif invalid == "owner": target.state.binding = replace(target.state.binding, owner_user_id="synthetic-other")
            elif invalid == "missing": target.repository.sessions.clear()
            await expect_error(invoke(target, request, session_id="synthetic-replaced" if invalid == "replaced" else SESSION),
                410 if invalid == "replaced" else 404, "desktop_binding_replaced" if invalid == "replaced" else None)
            require(target.events.call_count == 0 and target.repository.get_session.call_count == 0
                and target.documents.get_by_id.call_count == 0, "invalid_status_saved_or_loaded_materials")
            checked += 1
        target = fixture(settings); target.state.fallback = True
        await invoke(target, request, device_id="synthetic-old-device")
        require(target.service.repository.get_latest_session_desktop_binding_for_device.call_count == 2
            and target.service.repository.get_latest_session_desktop_binding_by_code.call_count == 1,
            "binding_fallback_order_changed")
        require_lightweight(target, controls=2, events=1); checked += 1
        for change in ("ended", "deleted"):
            target = fixture(settings)
            original_read = target.sessions.get_control_state
            calls = 0
            def mutate_after_read(**kwargs):
                nonlocal calls
                calls += 1
                value = original_read(**kwargs)
                if calls == 1:
                    if change == "deleted": target.repository.sessions.clear()
                    else: target.repository.sessions[SESSION] = replace(target.record, status="ended")
                return value
            target.sessions.get_control_state = mutate_after_read
            if change == "deleted": await expect_error(invoke(target, request), 404)
            else: await invoke(target, request)
            require_lightweight(target, controls=2, events=int(change == "ended")); checked += 1
        target = fixture(settings)
        await invoke(target, request, manual=False)
        require_lightweight(target, controls=1, events=1)
        await expect_error(invoke(target, request, manual=False, user_id="synthetic-other"), 403)
        require_lightweight(target, controls=1, events=1); checked += 1
        timing._sample_counter = 19
        before = len(samples)
        target = fixture(settings, edition="global")
        await invoke(target, request)
        require(target.repository.get_session.call_count == 2 and target.repository.get_control_state.call_count == 0
            and target.documents.get_by_id.call_count > 0 and target.events.call_count == 1
            and len(samples) == before and timing._sample_counter == 19, "global_original_status_path_changed")
        return {"syntheticStatusCases": checked + 1, "controlReadsPerValidManualStatus": 2,
            "fullSessionReadsPerValidManualStatus": 0, "materialReadsPerValidManualStatus": 0,
            "eventsPerValidManualStatus": 1, "timingPrivacyPassed": True, "globalOriginalPathPassed": True}
    finally:
        logger.handlers, logger.level, logger.propagate = original


async def synthetic_loop_responsiveness(settings, request, executor):
    from app.platform import cn_device_status_timing as timing
    checked = 0
    for configured in (True, False):
        started, release = threading.Event(), threading.Event()
        target = fixture(settings)
        original = target.service.repository.get_desktop_device_by_code
        worker_ids = []
        def slow(code):
            worker_ids.append(threading.get_ident()); started.set()
            require(release.wait(3), "event_loop_could_not_release_slow_repository")
            return original(code)
        target.service.repository.get_desktop_device_by_code = slow
        request.app.state.realtime_control_executor = executor if configured else None
        # Select a non-sampled request to check the real modulo gate and avoid
        # incidental INFO on stdout; this does not replace the timing wrapper.
        timing._sample_counter = 0
        task = asyncio.create_task(invoke(target, request))
        try:
            async with asyncio.timeout(2):
                while not started.is_set(): await asyncio.sleep(.001)
            require(not task.done() and worker_ids[0] != threading.get_ident(), "sync_repository_blocked_event_loop")
            release.set()
            await asyncio.wait_for(task, 2)
            require_lightweight(target, controls=2, events=1)
            checked += 1
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
    request.app.state.realtime_control_executor = executor
    return checked


async def scenarios(settings):
    from fastapi import Request
    from app.services import realtime_speech_service as realtime
    from app.services.realtime_control_executor import RealtimeControlExecutor
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1,
        thread_name_prefix="synthetic-device-status-probe"))
    executor = RealtimeControlExecutor(max_workers=1, queue_max=1)
    request = Request({"type": "http", "app": SimpleNamespace(state=SimpleNamespace(realtime_control_executor=executor))})
    try:
        with patch.object(realtime, "_now_ms", return_value=NOW):
            result = await synthetic_device_status(settings, request, executor)
            result["nonblockingExecutorCases"] = await synthetic_loop_responsiveness(settings, request, executor)
        return result
    finally:
        executor.shutdown()


def main():
    require(isinstance(EXPECTED, dict), "release_expectations_missing")
    install_guards()
    root = Path("/app")
    actual = {p.relative_to(root).as_posix(): sha(p.read_bytes())
        for directory in ("apps/backend/app", "ai/prompts", "apps/backend/migrations")
        for p in (root / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        and p.suffix != ".pyc" and p.name != ".desktop-release-manifest.lock"}
    actual["apps/backend/pyproject.toml"] = sha((root / "apps/backend/pyproject.toml").read_bytes())
    require(actual == EXPECTED["inventory"] and len(actual) == 233, "application_inventory_mismatch")
    compiled = 0
    for path in (root / "apps/backend/app").rglob("*.py"):
        if not path.name.startswith("._"):
            compile(path.read_bytes(), str(path), "exec"); compiled += 1
    require(compiled == 157, "compiled_python_count_changed")
    require(platform.python_version() == EXPECTED["python"] == "3.13.15", "python_version_changed")
    deps = dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()))
    require(deps == EXPECTED["dependencies"] and len(deps) == 44, "unapproved_dependency_change")
    sys.path.insert(0, str(root / "apps/backend"))
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    require(settings.product_edition == "cn" and settings.environment == "production", "runtime_region_changed")
    require(sha(serialize(settings.model_dump(mode="json"))) == EXPECTED["settingsSha256"], "existing_settings_changed")
    require(settings.cn_hot_database_pool_enabled is False, "existing_pool_setting_changed")
    from app import main as application
    forbid_lifespan(application.app)
    schema = application.app.openapi()
    require(sha(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()) == EXPECTED["openapiSha256"], "openapi_changed")
    require(len(schema["paths"]) == EXPECTED["httpPaths"] == 203, "api_routes_changed")
    from app.platform.cn_hot_database import cn_hot_database_diagnostics
    require(cn_hot_database_diagnostics(settings)["active"] is False, "pool_activated_unexpectedly")
    result = asyncio.run(scenarios(settings))
    for worker in WORKERS: worker.join(timeout=3)
    require(not any(worker.is_alive() for worker in WORKERS), "synthetic_worker_not_released")
    image = os.environ.get("OFFERSTEADY_RELEASE_PROBE_IMAGE", "")
    print(json.dumps({"passed": True, "image": image if re.fullmatch(r"sha256:[0-9a-f]{64}", image) else None,
        "runtimeFiles": len(actual), "compiledPython": compiled, "python": platform.python_version(),
        "dependencyCount": len(deps), "dependenciesUnchanged": True, "existingSettingsUnchanged": True,
        "settingsSha256": EXPECTED["settingsSha256"], "openapiSha256": EXPECTED["openapiSha256"], "httpPaths": len(schema["paths"]),
        "workerThreadsStarted": len(WORKERS), "allSyntheticWorkersReleased": True, "databaseOperations": 0,
        "networkRequests": 0, "fileWrites": 0, "lifespanEntered": False, "privateValuesPrinted": False, **result}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__,
            "errorCode": str(exc) if isinstance(exc, ProbeError) else "probe_failed", "privateValuesPrinted": False}))
        raise SystemExit(1) from None
