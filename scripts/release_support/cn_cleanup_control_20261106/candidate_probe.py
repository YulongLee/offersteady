"""Offline actual-image CN shared-blocking probe; one expectation map.

Run with --network=none --read-only --cap-drop=ALL and server-local settings.
Never enter application lifespan or call a database/provider. Every fixture is
synthetic. Only named synthetic/control/CN-I/O workers may start; all are joined
before success. No production value or synthetic identifier is output.

EXPECTED keys: inventory, python, dependencies, settingsSha256, openapiSha256,
httpPaths and ancillary. The controller must obtain ancillary from the actual
baseline image, then supply its fixed material-upload-formats.json path/SHA.
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
ANCILLARY_PATH = "packages/protocol/src/material-upload-formats.json"
DESKTOP_MANIFEST_SHA256 = "d7b106a6497bce873d67c2c81b045fab520aaa7382296978a8f6a04056e10927"


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
        require(worker.name.startswith(("synthetic-cn-shared-probe", "realtime-control",
            "cn-realtime-ingress", "cn-realtime-lifecycle", "cn-realtime-preparation", "cn-provider-close"))
            or getattr(getattr(worker, "_target", None), "__name__", None) == "_do_shutdown",
            "unapproved_worker_thread")
        WORKERS.append(worker)
        return original_start(worker, *args, **kwargs)
    threading.Thread.start = tracked_start
    import psycopg
    psycopg.connect = psycopg.Connection.connect = psycopg.AsyncConnection.connect = deny


def verify_source(root, expected):
    """Only read/compile inputs. Ancillary SHA must come from the actual baseline.

    The ancillary JSON was outside the original 233-input capture; accepting its
    absence or silently substituting a local checkout would hide image drift.
    """
    actual = {p.relative_to(root).as_posix(): sha(p.read_bytes())
        for directory in ("apps/backend/app", "ai/prompts", "apps/backend/migrations")
        for p in (root / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        and p.suffix != ".pyc" and p.name != ".desktop-release-manifest.lock"}
    actual["apps/backend/pyproject.toml"] = sha((root / "apps/backend/pyproject.toml").read_bytes())
    require(actual == expected["inventory"] and len(actual) == 238, "application_inventory_mismatch")
    compiled = 0
    for path in (root / "apps/backend/app").rglob("*.py"):
        if not path.name.startswith("._"):
            compile(path.read_bytes(), str(path), "exec"); compiled += 1
    require(compiled == 162, "compiled_python_count_changed")
    ancillary = expected.get("ancillary")
    require(isinstance(ancillary, dict) and set(ancillary) == {ANCILLARY_PATH}
        and re.fullmatch(r"[0-9a-f]{64}", str(ancillary[ANCILLARY_PATH])) is not None,
        "baseline_ancillary_expectation_missing")
    path = root / ANCILLARY_PATH
    require(path.is_file() and sha(path.read_bytes()) == ancillary[ANCILLARY_PATH],
        "baseline_ancillary_mismatch")
    manifest_path = root / "apps/backend/app/desktop_release_manifest.json"
    require(sha(manifest_path.read_bytes()) == DESKTOP_MANIFEST_SHA256,
        "companion_release_manifest_changed")
    manifest = json.loads(manifest_path.read_bytes())
    require(len(manifest["entries"]) == 3 and {entry["version"] for entry in manifest["entries"]} == {"1.3.6"},
        "companion_release_version_changed")
    return actual, compiled


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


async def until(predicate, code):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(.001)
    require(predicate(), code)


async def synthetic_voice_lanes(settings, request, control):
    from app.modules.realtime_speech import _disconnect_voice_publisher, _voice_io
    from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor
    executor = CnRealtimeIoExecutor()
    diag = executor.diagnostics()
    require((diag["ingress"]["configuredWorkers"], diag["ingress"]["configuredQueueMax"],
        diag["lifecycle"]["configuredWorkers"], diag["lifecycle"]["configuredQueueMax"]) == (4, 16, 2, 8),
        "cn_io_default_capacity_changed")
    checked = 0
    try:
        for configured in (True, False):
            entered, release = threading.Event(), threading.Event()
            calls = []
            def close(**kwargs):
                calls.append(threading.get_ident()); entered.set()
                require(release.wait(3), "synthetic_close_not_released")
            service = SimpleNamespace(settings=settings, disconnect_publisher=close)
            request.app.state.cn_realtime_io_executor = executor if configured else None
            task = asyncio.create_task(_disconnect_voice_publisher(request, service, token="synthetic-token"))
            try:
                await until(entered.is_set, "synthetic_close_not_started")
                require(not task.done() and len(calls) == 1 and calls[0] != threading.get_ident(),
                    "close_blocked_main_loop")
                require(await asyncio.wait_for(executor.run(lambda: 17, operation_name="ingest_frame"), 1) == 17
                    and await asyncio.wait_for(control.run(lambda: 19), 1) == 19,
                    "close_occupied_ingress_or_control_lane")
                release.set(); await asyncio.wait_for(task, 2)
                require(len(calls) == 1, "close_replayed")
                checked += 1
            finally:
                release.set(); await asyncio.gather(task, return_exceptions=True)
        # Global keeps the original direct call; it must not enter a CN pool.
        original = SimpleNamespace(settings=SimpleNamespace(product_edition="global"))
        identity = await _voice_io(request, original, threading.get_ident, operation_name="ingest_frame")
        require(identity == threading.get_ident(), "global_voice_dispatch_changed")
    finally:
        executor.shutdown()
        request.app.state.cn_realtime_io_executor = None
    return {"voiceNonblockingCases": checked, "voiceDefaultCapacityPassed": True,
        "slowCloseLeavesIngressAndControlAvailable": True, "globalVoiceDispatchUnchanged": True}


async def synthetic_cancel_and_shutdown():
    """Admitted resource cleanup survives cancellation/shutdown without expanding capacity."""
    from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor
    executor = CnRealtimeIoExecutor(ingress_workers=3, ingress_queue_max=0,
        lifecycle_workers=1, lifecycle_queue_max=0)
    entered, release, occupied, release_close = [], threading.Event(), threading.Event(), threading.Event()
    created, cleaned, forbidden = [], [], []
    def close():
        occupied.set(); require(release_close.wait(3), "synthetic_lane_not_released")
    def create(index):
        entered.append(index)
        require(release.wait(3), "synthetic_create_not_released")
        created.append(index); return index
    blocker = asyncio.create_task(executor.run(close, lane="lifecycle", operation_name="publisher_disconnect"))
    owners = [asyncio.create_task(executor.run(lambda i=i: create(i), operation_name="publisher_create",
        on_abandoned_result=lambda result: cleaned.append(result))) for i in range(3)]
    waiters = []
    try:
        await until(lambda: len(entered) == 3 and occupied.is_set(), "synthetic_owners_not_started")
        waiters = [asyncio.create_task(executor.run(lambda: forbidden.append(1), lane="lifecycle",
            operation_name="publisher_disconnect")) for _ in range(3)]
        await until(lambda: executor.diagnostics()["lifecycle"]["waiting"] == 3, "synthetic_waiters_not_started")
        for task in owners: task.cancel("synthetic-original-cancellation")
        await asyncio.sleep(0)
        executor.shutdown()
        for task in waiters: task.cancel()
        await asyncio.gather(*waiters, return_exceptions=True)
        release.set()
        await until(lambda: len(created) == 3, "synthetic_create_did_not_finish")
        await asyncio.sleep(.01)
        for task in owners: task.cancel()
        require(cleaned == [] and not any(task.done() for task in owners)
            and executor.diagnostics()["lifecycle"]["maxPending"] == 1,
            "shutdown_cleanup_capacity_expanded_or_skipped")
        release_close.set(); await blocker
        results = await asyncio.gather(*owners, return_exceptions=True)
        require(all(isinstance(value, asyncio.CancelledError) for value in results)
            and sorted(created) == sorted(cleaned) == [0, 1, 2] and not forbidden,
            "cancelled_creation_replayed_or_cleanup_lost")
        try:
            await executor.run(lambda: forbidden.append(1), operation_name="ingest_frame")
        except RuntimeError:
            pass
        else:
            raise ProbeError("closed_executor_accepted_new_business")
        await asyncio.sleep(0)
        final = executor.diagnostics()
        require(final["cleanupFailed"] == final["outstanding"] == 0 and final["poolsClosed"] == 1
            and final["lifecycle"]["maxPending"] == 1 and final["ingress"]["pending"] == 0
            and final["lifecycle"]["pending"] == 0, "shutdown_resource_or_capacity_contract_changed")
        return {"cancelledResourcesCreated": 3, "cancelledResourcesCleaned": 3,
            "shutdownRejectsNewBusiness": True, "shutdownCleanupCapacityPassed": True}
    finally:
        release.set(); release_close.set()
        await asyncio.gather(blocker, *owners, *waiters, return_exceptions=True)
        executor.shutdown()


def synthetic_metadata_and_modes(settings):
    from app.core.errors import DomainRequestError
    from app.ports.retrieval import RetrievalFilter, RetrievedChunk
    from app.services.knowledge_retrieval import KnowledgeRetrievalService
    from app.services.realtime_speech_service import RealtimeSpeechService
    from app.services.session_mode_guard import require_standard_session
    record = SimpleNamespace(document_id="synthetic-doc", owner_user_id=OWNER, status="ready",
        index_state="indexed", document_kind="knowledge", document_version_id="synthetic-version",
        knowledge_collection_id="synthetic-collection", display_name="Synthetic")
    foreign = SimpleNamespace(**{**vars(record), "owner_user_id": "synthetic-other"})
    values = {"synthetic-doc": record, "synthetic-foreign": foreign, "synthetic-missing": None}
    matches = [RetrievedChunk(document_id=key, document_kind="knowledge", chunk_id=f"synthetic-chunk-{i}",
        chunk_index=i, content="Synthetic content", score=score)
        for i, (key, score) in enumerate([("synthetic-doc", .4), ("synthetic-doc", .9),
            ("synthetic-foreign", .99), ("synthetic-missing", .8)])]
    service = object.__new__(KnowledgeRetrievalService); service.settings = settings
    filter = RetrievalFilter(owner_user_id=OWNER, document_kinds=["knowledge"],
        document_version_ids=["synthetic-version"], knowledge_collection_ids=["synthetic-collection"])
    for batch in (True, False):
        repository = Mock(spec=["get_by_id", "get_by_ids"] if batch else ["get_by_id"])
        repository.get_by_id.side_effect = values.get
        if batch: repository.get_by_ids.side_effect = lambda ids: {key: values.get(key) for key in ids}
        service.document_repository = repository
        result = service._apply_metadata_filter(matches, filter=filter)
        require([item.score for item in result] == [.9, .4]
            and all(item.metadata["ownerUserId"] == OWNER for item in result), "metadata_owner_or_sort_changed")
        require(repository.get_by_id.call_count == (0 if batch else 3)
            and (not batch or repository.get_by_ids.call_args.args == (list(values),)),
            "metadata_unique_read_contract_changed")
    # Actual mode guards, including the service boundary, execute before any
    # real billing/ASR/provider method. Instances deliberately have no such deps.
    require_standard_session(SimpleNamespace(session_mode="interview"))
    require_standard_session(SimpleNamespace(session_mode="written"))
    for mode, code in (("mock", "mock_dedicated_command_required"), ("written", "written_exam_audio_disabled")):
        realtime = object.__new__(RealtimeSpeechService)
        realtime.settings = settings
        realtime._session_activity_lock = threading.Lock()
        realtime._session_cleanup_locks = {}; realtime._session_cleanup_lock_users = {}
        realtime.session_service = SimpleNamespace(get_session=lambda **_: SimpleNamespace(session_mode=mode))
        try:
            realtime.control_capture(user_id=OWNER, session_id=SESSION, action="pause")
        except DomainRequestError as error:
            require(error.status_code == 409 and error.error_code == code, "legacy_mode_error_changed")
        else:
            raise ProbeError("legacy_mode_guard_bypassed")
        require(realtime._session_cleanup_locks == realtime._session_cleanup_lock_users == {},
            "mode_guard_left_cleanup_lock")
    return {"metadataBatchAndFallbackPassed": True, "ordinaryWrittenMockGuardsPassed": True}


def synthetic_loop_monitor():
    from app.platform.cn_realtime_loop_monitor import CnMainLoopMonitor
    monitor = CnMainLoopMonitor(max_samples=3, emit_every=1000)
    for value in [1, 10, 50, 250, 500, float("nan"), float("inf"), -1]: monitor.observe(value)
    values = monitor.summary()
    require(values["sampleCount"] == values["capacity"] == 3 and values["observations"] == 5
        and values["maxMs"] == values["p95Ms"] == 500 and values["over250Ms"] == 2
        and all(type(value) in (int, float) and isfinite(value) and value >= 0 for value in values.values()),
        "loop_monitor_bounds_or_privacy_changed")
    return {"loopMonitorBoundedNumericPassed": True}



def synthetic_pinned_binding(settings):
    # Execute the actual repository/getter/service code with a scripted Redis
    # transport. Actual Lua execution and scale counts were tested separately
    # against an owned localhost Redis; no Redis is contacted by this probe.
    from dataclasses import asdict
    from app.services.cn_realtime_entity_state import CNRealtimeEntityState
    from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
    from app.services import realtime_speech_service as realtime
    costs = []
    for history in (1, 1191, 10000):
        target = fixture(settings)
        target.state.binding = replace(target.state.binding, capabilities={"large": 2**53 + 1, "array": []})
        raw = json.dumps(asdict(target.state.binding))
        calls = []
        class SyntheticRedis:
            def hget(self, key, field):
                calls.append("hget")
                if key == "synthetic-codes" and field == CODE: return DEVICE
                if key == "synthetic-devices" and field == DEVICE: return json.dumps(asdict(target.state.device))
                raise ProbeError("unexpected_pinned_read")
            def hvals(self, key):
                raise ProbeError("pinned_global_scan_forbidden")
        store = object.__new__(CNRealtimeEntityState)
        store.redis = SyntheticRedis(); store._legacy_deadline = None; store.ttl = 300
        store.base = "synthetic-runtime"; store.keys = ["synthetic-key-" + str(i) for i in range(15)]
        def scripted(*, keys, args):
            calls.append("scripted_evalsha")
            require(args[0] == "pinned_binding_lookup" and args[4:] == [SESSION, target.state.binding.binding_id, DEVICE, CODE],
                    "pinned_identity_arguments_changed")
            return [raw, 0]
        store._script = scripted
        repository = object.__new__(RedisRealtimeSpeechRepository)
        repository._cn_controls = store; repository._redis = store.redis
        repository._device_code_index_key = "synthetic-codes"; repository._device_entity_key = "synthetic-devices"
        repository._runtime_lock = threading.RLock()
        repository.desktop_devices_by_id = {}; repository.desktop_devices_by_code = {}
        target.service.repository = repository
        target.service._capture_control_cache = {SESSION: "capturing"}
        with patch.object(realtime, "_now_ms", return_value=NOW):
            result = target.service._compute_desktop_pairing_status(manual_code=CODE, device_id=DEVICE,
                pinned_session_id=SESSION, pinned_binding_id=target.state.binding.binding_id)
        require(result["bound"] is True and result["bindingLockState"] == "held", "pinned_wire_contract_changed")
        require(result["binding"]["capabilities"] == target.state.binding.capabilities, "pinned_precision_changed")
        require(calls == ["hget", "hget", "scripted_evalsha"], "pinned_network_cost_changed")
        target.repository.get_control_state.assert_called_once_with(SESSION)
        target.repository.get_session.assert_not_called()
        costs.append(len(calls))
        retired_raw = store._script
        store._script = lambda **kw: [raw, 1]
        require(repository.get_pinned_session_desktop_binding(device_id=DEVICE, manual_code=CODE,
            session_id=SESSION, binding_id=target.state.binding.binding_id).status == "stale", "pinned_retirement_changed")
        store._script = lambda **kw: ["", -1]
        try:
            repository.get_pinned_session_desktop_binding(device_id=DEVICE, manual_code=CODE,
                session_id=SESSION, binding_id=target.state.binding.binding_id)
        except ValueError as error:
            require(str(error) == "cn_runtime_entity_identity_mismatch", "pinned_identity_error_changed")
        else:
            raise ProbeError("pinned_identity_error_swallowed")
    return {"pinnedSyntheticScaleCases": len(costs), "pinnedPairingTransportCalls": costs,
            "pinnedActualLuaExecutedInImageProbe": False, "pinnedGlobalScanForbidden": True,
            "pinnedIdentityRetirementPrecisionPassed": True}


async def synthetic_cleanup_control(settings, request):
    from collections import deque
    from dataclasses import asdict
    import time
    from app.ports.realtime_speech import AccountDesktopDeviceRecord
    from app.services.cn_realtime_entity_state import CNRealtimeEntityState
    from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
    from app.services import realtime_speech_service as realtime
    from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway, _SourceRealtimeSession
    from app.services.cn_provider_close_executor import CnProviderCloseExecutor
    from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor

    target = fixture(settings)
    binding = replace(target.state.binding, capabilities={"array": [], "precision": 2**53+1})
    account = AccountDesktopDeviceRecord(OWNER, DEVICE, CODE, 1, 2)
    store = object.__new__(CNRealtimeEntityState)
    store._legacy_deadline = None; store.ttl = 300; store.base = "synthetic-runtime"
    store.keys = ["synthetic-key-"+str(i) for i in range(18)]
    calls = []
    def scripted(*, keys, args):
        calls.append(args[0])
        require(args[4:] == [OWNER], "owner_reference_identity_changed")
        record = binding if args[0] == "owner_bindings" else account
        require(args[0] in {"owner_bindings", "owner_accounts"}, "owner_read_operation_changed")
        return [[json.dumps(asdict(record)), 0]]
    store._script = scripted
    repository = object.__new__(RedisRealtimeSpeechRepository)
    repository._cn_controls = store
    require(repository.list_session_desktop_bindings_for_user(user_id=OWNER) == [binding]
        and repository.list_account_desktop_devices(user_id=OWNER) == [account]
        and calls == ["owner_bindings", "owner_accounts"], "owner_read_dispatch_changed")
    # Lua execution and scale budgets are proved by the real local Redis suite;
    # this isolated image probe only verifies the shipped Python dispatch.
    service = object.__new__(realtime.RealtimeSpeechService)
    service.settings = settings
    service.logger = logging.getLogger("synthetic-lightweight-ack")
    service.logger.setLevel(logging.INFO)
    access = Mock()
    service.session_service = SimpleNamespace(get_control_state=access, get_session=deny)
    service._trace_lock = threading.Lock(); service._trace_records = {}; service._trace_order = deque(maxlen=4096)
    service._latest_timing = lambda **kwargs: None
    with patch.object(realtime, "log_event", side_effect=deny):
        for stage in ("transcript-delivery", "transcript-render", "answer-first-render", "screenshot-first-render"):
            event = service.acknowledge_runtime_timing(user_id=OWNER, session_id=SESSION,
                trace_id="synthetic-trace", stage=stage, duration_ms=20)
            require(event.kind == "performance-ack" and event.payload["stage"] == stage, "ack_wire_changed")
    require(access.call_count == 4, "ack_lightweight_authority_missing")

    gateway = DashScopeRealtimeAsrGateway(settings, logging.getLogger("synthetic-close"))
    entered, release = threading.Event(), threading.Event()
    def slow_close():
        entered.set(); require(release.wait(3), "synthetic_physical_close_not_released")
    old = _SourceRealtimeSession(SimpleNamespace(close=slow_close), 16000,
        time.monotonic(), time.monotonic(), SESSION+":microphone", "microphone")
    gateway._source_sessions[SESSION+":microphone"] = old
    try:
        require(gateway.close_source_deferred(session_id=SESSION, source_kind="microphone") == 1,
            "deferred_close_capability_missing")
        await until(entered.is_set, "deferred_close_not_started")
        require(old.closed and not old.accepting_transcript_events
            and SESSION+":microphone" not in gateway._source_sessions, "old_source_not_fenced")
        replacement = Mock()
        gateway._source_sessions[SESSION+":microphone"] = _SourceRealtimeSession(replacement, 16000,
            time.monotonic(), time.monotonic(), SESSION+":microphone", "microphone")
        release.set(); gateway.drain_deferred_closes()
        require(replacement.close.call_count == 0, "old_close_touched_replacement")
    finally:
        release.set(); gateway.close_all_sessions()

    # Both lifecycle workers are occupied; preparation must still progress.
    executor = CnRealtimeIoExecutor()
    ready, finish = [], threading.Event()
    def block():
        ready.append(1); require(finish.wait(3), "synthetic_lifecycle_not_released")
    blockers = [asyncio.create_task(executor.run(block, lane="lifecycle",
        operation_name="publisher_disconnect")) for _ in range(2)]
    create_entered, create_finish, cleaned = threading.Event(), threading.Event(), []
    def create():
        create_entered.set(); require(create_finish.wait(3), "synthetic_prepare_not_released"); return "synthetic-created"
    pending = None
    try:
        await until(lambda: len(ready) == 2, "both_lifecycle_workers_not_occupied")
        require(await asyncio.wait_for(executor.run(lambda: 23, lane="preparation",
            operation_name="publisher_prepare"), 1) == 23, "preparation_blocked_by_lifecycle")
        pending = asyncio.create_task(executor.run(create, lane="preparation",
            operation_name="publisher_create", on_abandoned_result=cleaned.append))
        await until(create_entered.is_set, "preparation_create_not_started")
        pending.cancel(); create_finish.set(); finish.set()
        result = await asyncio.gather(pending, return_exceptions=True)
        require(isinstance(result[0], asyncio.CancelledError) and cleaned == ["synthetic-created"],
            "preparation_cancel_cleanup_lost_or_replayed")
        await asyncio.gather(*blockers)
        diag = executor.diagnostics()["preparation"]
        require((diag["configuredWorkers"], diag["configuredQueueMax"]) == (2, 8), "preparation_capacity_changed")
    finally:
        finish.set(); create_finish.set()
        await asyncio.gather(*blockers, *([pending] if pending is not None else []), return_exceptions=True)
        executor.shutdown()

    # A submit can fail after enqueue. A late queued call must be a no-op.
    closer = CnProviderCloseExecutor(logging.getLogger("synthetic-submit"), workers=1, queue_max=0)
    queued, closed = [], []
    def failed_submit(operation, *args):
        queued.append((operation, args)); raise RuntimeError("synthetic-start-failure")
    try:
        with patch.object(closer._pool, "submit", failed_submit):
            closer.close(lambda: closed.append(1))
            operation, args = queued[0]; operation(*args)
            require(closed == [1] and closer.diagnostics()["pending"] == 0,
                "ambiguous_submit_replayed_close_or_permit")
    finally:
        closer.shutdown()
    return {"ownerScopedReadDispatchPassed": True, "ownerScopedReadActualLuaExecuted": False,
        "lightweightAckStages": 4, "disabledAckDebugSerializationSkipped": True,
        "detachedOldCloseCannotTouchReplacement": True, "preparationIndependentFromBothLifecycleWorkers": True,
        "preparationCancelledResourceCompensatedOnce": True, "ambiguousCloseSubmitExactlyOnce": True}


async def scenarios(settings):
    from fastapi import Request
    from app.services import realtime_speech_service as realtime
    from app.services.realtime_control_executor import RealtimeControlExecutor
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1,
        thread_name_prefix="synthetic-cn-shared-probe"))
    executor = RealtimeControlExecutor(max_workers=1, queue_max=1)
    request = Request({"type": "http", "app": SimpleNamespace(state=SimpleNamespace(realtime_control_executor=executor))})
    try:
        with patch.object(realtime, "_now_ms", return_value=NOW):
            result = await synthetic_device_status(settings, request, executor)
            result["nonblockingExecutorCases"] = await synthetic_loop_responsiveness(settings, request, executor)
        result.update(await synthetic_voice_lanes(settings, request, executor))
        result.update(await synthetic_cancel_and_shutdown())
        result.update(synthetic_metadata_and_modes(settings))
        result.update(synthetic_loop_monitor())
        result.update(synthetic_pinned_binding(settings))
        result.update(await synthetic_cleanup_control(settings, request))
        return result
    finally:
        executor.shutdown()


def main():
    require(isinstance(EXPECTED, dict), "release_expectations_missing")
    install_guards()
    root = Path("/app")
    actual, compiled = verify_source(root, EXPECTED)
    require(platform.python_version() == EXPECTED["python"] == "3.13.15", "python_version_changed")
    deps = dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()))
    require(deps == EXPECTED["dependencies"] and len(deps) == 44, "unapproved_dependency_change")
    sys.path.insert(0, str(root / "apps/backend"))
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    require(settings.product_edition == "cn" and settings.environment == "production", "runtime_region_changed")
    values = settings.model_dump(mode="json")
    require(len(values) == 344 and sha(serialize(values)) == EXPECTED["settingsSha256"], "existing_settings_changed")
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
        "settingsCount": len(values), "poolEnabled": False, "baselineAncillaryUnchanged": True,
        "companionReleaseManifestUnchanged": True, "companionVersion": "1.3.6",
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
