"""Actual-image CN mock probe, injected expectations and synthetic services only.

Run with docker --network=none --read-only --cap-drop=ALL and the existing
server-local environment. No lifespan, external database, provider, user data or
write is used. Actual synthetic cleanup workers are counted, not reported as 0.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import re
import socket
import sys
from threading import Event
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

EXPECTED = None  # RELEASE_EXPECTATIONS

sys.dont_write_bytecode = True
WORKERS = []


class ProbeError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise ProbeError(code)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def serialize(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def deny(*args, **kwargs):
    raise ProbeError("external_io_forbidden")


def install_guards():
    def audit(event, args):
        if event in {"subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn",
            "socket.connect", "socket.getaddrinfo", "sqlite3.connect", "os.mkdir", "os.rename",
            "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime", "os.link", "os.symlink", "os.truncate"}:
            deny()
        if event == "open" and len(args) >= 3 and isinstance(args[2], int):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                deny()
    sys.addaudithook(audit)
    socket.socket.connect = socket.socket.connect_ex = deny
    socket.create_connection = socket.getaddrinfo = deny
    original_start = threading.Thread.start
    def tracked_start(worker, *args, **kwargs):
        allowed = (worker.name.startswith(("synthetic-mock-probe", "mock-asr-close"))
            or getattr(getattr(worker, "_target", None), "__name__", None) == "_do_shutdown")
        require(allowed, "unapproved_worker_thread")
        WORKERS.append(worker)
        return original_start(worker, *args, **kwargs)
    threading.Thread.start = tracked_start
    import psycopg
    psycopg.connect = psycopg.Connection.connect = psycopg.AsyncConnection.connect = deny


def runtime_fixture(settings, edition="cn"):
    from app.services.mock_interview_audio import MockInterviewAudio
    from app.services.mock_interview_rounds import MockRoundState
    from app.services.mock_interview_runtime import MockController, MockInterviewRuntime
    from app.services.mock_interview_repository import round_state
    from app.services.realtime_speech_service import RealtimeSpeechService
    state = MockRoundState().start()
    state = state.publish_question(state.operation_id, "合成问题：如何处理重试？")
    state = state.listen(state.rounds[-1].question_id, 1000)
    row = {"session_id": "synthetic-probe-session", "owner_user_id": "synthetic-probe-owner",
        "billing_class": "points", "refunded": False, "created_at_ms": 1000,
        "data": {"title": "Synthetic mock", "target_role": "Synthetic role", "state": asdict(state),
            "resume_id": "synthetic-resume", "resume_version": "synthetic-v1", "billable_ms": 0,
            "billed_minutes": 0, "clock_at_ms": 1000, "control_token": "synthetic-token",
            "lease_until_ms": 16_000, "started_at_ms": 1000, "deadline_at_ms": 3_601_000,
            "duration_limit_ms": 3_600_000, "end_reason": None}}
    repo = Mock()
    repo.settings = settings.model_copy(update={"product_edition": edition})
    repo.duration_deadline.side_effect = lambda record: record["data"]["deadline_at_ms"]
    def tick(*, active=None, **_):
        if active is not None:
            row["data"]["clock_at_ms"] = 1000 if active else None
        return deepcopy(row)
    repo.control_tick.side_effect = tick
    def transition(*, move, **_):
        following = move(round_state(row))
        row["data"]["state"] = asdict(following)
        row["data"]["clock_at_ms"] = 1000 if following.phase == "listening" else None
        return deepcopy(row)
    repo.transition.side_effect = transition
    repo.get.side_effect = lambda **_: deepcopy(row)
    device = SimpleNamespace(device_id="synthetic-device", generation=1,
        capabilities={"protocolVersion": "2.0", "mockInterviewProtocol": 1, "microphone": "granted"})
    binding = SimpleNamespace(device_id=device.device_id, binding_generation=1, status="bound", manual_code="000000",
        session_id=row["session_id"], owner_user_id=row["owner_user_id"])
    realtime = Mock()
    realtime.session_service.get_session.return_value = SimpleNamespace(session_mode="mock", status="live")
    realtime.get_desktop_binding.return_value = binding
    realtime.get_desktop_capture_binding.return_value = binding
    realtime.repository.get_desktop_device_by_code.return_value = device
    realtime._desktop_device_fresh.return_value = True
    realtime._permission_status.side_effect = RealtimeSpeechService._permission_status
    gateway = Mock()
    audio = MockInterviewAudio(gateway_factory=lambda: gateway, now_ms=lambda: 1000)
    runtime = MockInterviewRuntime(repo, None, None, None, audio, realtime, now_ms=lambda: 1000)
    runtime._generate = Mock()
    controller = MockController(row["owner_user_id"], row["session_id"], "synthetic-token", row, AsyncMock())
    runtime.controllers[controller.session_id] = controller
    return runtime, controller, gateway, device


async def synthetic_runtime(settings):
    from app.core.errors import DomainRequestError
    from app.services.mock_interview_repository import round_state
    checked = 0
    for edition in ("cn", "global"):
        runtime, controller, gateway, device = runtime_fixture(settings, edition)
        started, release = Event(), Event()
        def close(**_):
            started.set()
            require(release.wait(5), "synthetic_native_close_timed_out")
        gateway.close_session.side_effect = close
        state = round_state(controller.record)
        old = runtime.audio.open(session_id=controller.session_id, owner_id=controller.user_id,
            device_id=device.device_id, epoch=state.capture_epoch, deadline_ms=2000, sink=lambda *_: None)
        submission = dict(action="submit", version=state.version, question_id=state.rounds[-1].question_id,
            answer="合成已确认回答", submission_id="synthetic-submission")
        task = asyncio.create_task(runtime.command(controller, **submission))
        try:
            # Keep the sole general worker available for synthetic repository
            # reads; waiting on Event there would starve the command itself.
            async with asyncio.timeout(2):
                while not started.is_set():
                    await asyncio.sleep(0.001)
            if edition == "cn":
                await asyncio.wait_for(asyncio.shield(task), 2)
                require(runtime._generate.call_count == 1 and old.revoked and not old.closed, "cn_submit_waited_for_close")
                require(controller.record["data"]["clock_at_ms"] is None, "submit_clock_not_stopped")
                require(controller.send.call_args.args[0]["session"]["state"]["phase"] == "generating_question", "generating_state_missing")
                await runtime.command(controller, **submission)
                require(runtime._generate.call_count == 1, "duplicate_submission_generated_again")
            else:
                await asyncio.sleep(0)
                require(not task.done() and not runtime._generate.called, "global_wait_policy_changed")
            require(len(runtime._capture_closes) == 1, "actual_native_close_untracked")
            require(device.capabilities["microphone"] == "granted", "permission_rewritten")
            release.set()
            await asyncio.wait_for(task, 2)
            await runtime._drain_capture_closes(controller.capture_closes)
            require(old.closed and not runtime._capture_closes and not runtime.audio._closing, "native_resources_not_released")
            # Exercise actual owner/binding/permission gates without storage I/O.
            device.capabilities["microphone"] = "unknown"
            try:
                runtime.validate_device(controller.user_id, controller.session_id)
            except DomainRequestError as exc:
                require(exc.error_code == ("mock_microphone_checking" if edition == "cn" else "mock_microphone_required"), "unknown_permission_policy_changed")
            else:
                raise ProbeError("unknown_permission_authorized")
            device.capabilities["microphone"] = "denied"
            try:
                runtime.validate_device(controller.user_id, controller.session_id)
            except DomainRequestError as exc:
                require(exc.error_code == "mock_microphone_required", "denied_permission_policy_changed")
            else:
                raise ProbeError("denied_permission_authorized")
            checked += 1
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
            await runtime.shutdown()
    # Probe the real endpoint's final-close and replacement ownership branch.
    from app.modules import mock_interview as route
    from starlette.websockets import WebSocketDisconnect
    for replacement in (False, True):
        runtime, controller, _, device = runtime_fixture(settings)
        replacement_registration = (device.device_id, AsyncMock())
        class Disconnected:
            async def accept(self): pass
            async def receive_text(self): return json.dumps({"deviceId": device.device_id, "manualCode": "000000"})
            async def send_json(self, value): pass
            async def receive(self):
                if replacement: runtime.desktops[controller.session_id] = replacement_registration
                return {"type": "websocket.disconnect"}
            async def close(self): raise WebSocketDisconnect(code=1006)
        original = route.require_mock_runtime
        route.require_mock_runtime = lambda: runtime
        try:
            await route.mock_microphone(Disconnected(), controller.session_id)
            require((runtime.desktops.get(controller.session_id) is replacement_registration) if replacement
                    else controller.session_id not in runtime.desktops, "microphone_replacement_ownership_failed")
            checked += 1
        finally:
            route.require_mock_runtime = original
            await runtime.shutdown()
    return checked


async def synthetic_provider(settings):
    import httpx
    from app.services.mock_interview_generation import MockInterviewGenerator, MockGenerationUnavailable
    from app.services.mock_interview_diagnostics import MockGenerationDiagnostics
    calls, events = [], []
    class Capture(logging.Handler):
        def emit(self, record):
            events.append(json.loads(record.getMessage()))
    logger = logging.getLogger("offersteady.backend")
    old = (logger.handlers[:], logger.level, logger.propagate)
    logger.handlers = [Capture()]; logger.setLevel(logging.INFO); logger.propagate = False
    synthetic = settings.model_copy(update={"chat_qwen_api_key": "synthetic-key", "chat_qwen_base_url": "https://synthetic.invalid"})
    private = "synthetic-private-probe-marker"
    async def transport(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"question": "合成问题：如何处理重试？", "focus": "可靠性"}, ensure_ascii=False)}}]})
        return httpx.Response(503, text=private)
    generator = MockInterviewGenerator(synthetic, transport=httpx.MockTransport(transport))
    try:
        question = await generator.question(resume=private, target_role="Synthetic", rounds=())
        require(question.question == "合成问题：如何处理重试？", "synthetic_question_validation_failed")
        try:
            await generator.question(resume=private, target_role="Synthetic", rounds=())
        except MockGenerationUnavailable as exc:
            require(exc.error_category == "provider_http_error", "safe_provider_category_missing")
        else:
            raise ProbeError("synthetic_http_failure_not_rejected")
        require(len(calls) == 2, "provider_retry_policy_changed")
        require(events and private not in json.dumps(events), "diagnostic_sensitive_content_leaked")
        require(any(e.get("stage") == "provider_request" and e.get("error_code") == "provider_http_error" for e in events), "provider_failure_diagnostic_missing")
        require(all(re.fullmatch(r"[0-9a-f]{32}", e.get("diagnostic_id", "")) for e in events), "diagnostic_trace_invalid")
        # Direct Global generator use must not enable the CN diagnostic stream.
        global_generator = MockInterviewGenerator(synthetic.model_copy(update={"product_edition": "global"}), transport=httpx.MockTransport(transport))
        previous = len(events)
        try:
            await global_generator.question(resume=private, target_role="Synthetic", rounds=())
        except MockGenerationUnavailable:
            pass
        require(len(events) == previous and len(calls) == 3, "global_diagnostic_or_provider_behavior_changed")
        return {"syntheticProviderRequests": len(calls), "externalProviderRequests": 0, "diagnosticPrivacyPassed": True}
    finally:
        logger.handlers, logger.level, logger.propagate = old


async def scenarios(settings):
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1, thread_name_prefix="synthetic-mock-probe"))
    runtime = await synthetic_runtime(settings)
    provider = await synthetic_provider(settings)
    return {"syntheticRuntimeCases": runtime, **provider}


def main():
    require(isinstance(EXPECTED, dict), "release_expectations_missing")
    install_guards()
    root = Path("/app")
    actual = {p.relative_to(root).as_posix(): sha(p.read_bytes())
        for directory in ("apps/backend/app", "ai/prompts", "apps/backend/migrations")
        for p in (root / directory).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name != ".desktop-release-manifest.lock"}
    actual["apps/backend/pyproject.toml"] = sha((root / "apps/backend/pyproject.toml").read_bytes())
    require(actual == EXPECTED["inventory"], "application_inventory_mismatch")
    compiled = 0
    for path in (root / "apps/backend/app").rglob("*.py"):
        if not path.name.startswith("._"):
            compile(path.read_bytes(), str(path), "exec"); compiled += 1
    require(platform.python_version() == EXPECTED["python"], "python_version_changed")
    deps = dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()))
    require(deps == EXPECTED["dependencies"], "unapproved_dependency_change")
    sys.path.insert(0, str(root / "apps/backend"))
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    require(settings.product_edition == "cn" and settings.environment == "production", "runtime_region_changed")
    require(sha(serialize(settings.model_dump(mode="json"))) == EXPECTED["settingsSha256"], "existing_settings_changed")
    require(settings.cn_hot_database_pool_enabled is False, "existing_pool_setting_changed")
    from app import main as application
    schema = application.app.openapi()
    require(sha(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()) == EXPECTED["openapiSha256"], "openapi_changed")
    require(len(schema["paths"]) == EXPECTED["httpPaths"] == 203, "api_routes_changed")
    from app.services.mock_interview_repository import MockInterviewRepository
    require(MockInterviewRepository.daily_free_limit == 1 and MockInterviewRepository.duration_limit_ms == 3_600_000, "cn_mock_policy_changed")
    logger = logging.getLogger("offersteady.backend")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    result = asyncio.run(scenarios(settings))
    for worker in WORKERS:
        worker.join(timeout=3)
    require(not any(worker.is_alive() for worker in WORKERS), "synthetic_worker_not_released")
    print(json.dumps({"passed": True, "image": os.environ.get("OFFERSTEADY_RELEASE_PROBE_IMAGE"),
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
