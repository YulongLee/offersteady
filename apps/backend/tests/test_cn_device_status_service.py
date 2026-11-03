"""Synthetic device-status contracts against the sealed CN running methods."""
from __future__ import annotations

import ast
from contextlib import contextmanager
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
import tarfile
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.interview_session import SessionBoundDocument
from app.ports.realtime_speech import DesktopDeviceRecord, SessionDesktopBindingRecord
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services import realtime_speech_service as realtime_module
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.session_service import SessionService


NOW = 1_800_000_000_000
OWNER = "synthetic-status-owner"
SESSION = "synthetic-status-session"
DEVICE = "synthetic-status-device"
CODE = "123456"


@lru_cache(maxsize=1)
def _sealed_status_methods() -> ast.Module:
    """Use immutable tracked bytes, independently of the new shared builder."""
    root = Path(__file__).resolve().parents[3]
    with tarfile.open(root / "releases/20261102.1/cn/backend-runtime.tar.gz") as archive:
        stream = archive.extractfile("apps/backend/app/services/realtime_speech_service.py")
        assert stream is not None
        tree = ast.parse(stream.read().decode())
    service = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RealtimeSpeechService")
    names = {"get_desktop_active_binding", "_binding_is_active", "_desktop_device_fresh", "publish_device_status"}
    methods = [node for node in service.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in methods} == names
    return ast.Module(body=methods, type_ignores=[])


def status_fixture(monkeypatch, *, baseline=False, status="live", mode="interview", audio="computer", documents=12, edition="cn"):
    clock = [NOW]
    monkeypatch.setattr(realtime_module, "_now_ms", lambda: clock[0])
    monkeypatch.setattr(realtime_module, "uuid4", lambda: SimpleNamespace(hex="synthetic-fixed-event"))
    settings = Settings(_env_file=None, product_edition=edition)
    sessions_repo = InMemoryInterviewSessionRepository()
    # This sealed-path fixture models a single-read-only repository capability.
    # A bare Mock invents the optional get_by_ids method on attribute access.
    documents_repo = Mock(spec=["get_by_id"])
    documents_repo.get_by_id.return_value = None
    sessions = SessionService(settings=settings, repository=sessions_repo, document_repository=documents_repo)
    record = sessions.create_session(user_id=OWNER, title="Synthetic status contract")
    record = replace(record, session_id=SESSION, status=status, session_mode=mode, interview_audio_mode=audio,
        material_binding=replace(record.material_binding, session_id=SESSION, bound_documents=[
            SessionBoundDocument(document_id=f"synthetic-document-{index}", document_kind="knowledge",
                display_name=f"Synthetic document {index}", status="ready") for index in range(documents)
        ]))
    sessions_repo.sessions = {SESSION: record}
    full = Mock(wraps=sessions_repo.get_session)
    control = Mock(wraps=sessions_repo.get_control_state)
    writes = Mock(wraps=sessions_repo.save_session)
    monkeypatch.setattr(sessions_repo, "get_session", full)
    monkeypatch.setattr(sessions_repo, "get_control_state", control)
    monkeypatch.setattr(sessions_repo, "save_session", writes)
    device = DesktopDeviceRecord(device_id=DEVICE, manual_code=CODE, display_name="Synthetic desktop",
        capabilities={"microphone": True}, registered_at_ms=NOW, last_seen_at_ms=NOW)
    binding = SessionDesktopBindingRecord(binding_id="synthetic-status-binding", session_id=SESSION,
        owner_user_id=OWNER, device_id=DEVICE, manual_code=CODE, display_name=device.display_name,
        capabilities=device.capabilities, bound_at_ms=NOW, last_seen_at_ms=NOW)
    state = SimpleNamespace(device=device, binding=binding, direct=True, canonical=True, by_code=True)
    lookups = []

    def device_lookup(code):
        lookups.append(("device", code))
        return state.device if code == CODE else None

    def binding_lookup(*, device_id, manual_code):
        lookups.append(("binding", device_id, manual_code))
        allowed = state.canonical if device_id == DEVICE else state.direct
        return state.binding if allowed else None

    def code_lookup(*, manual_code):
        lookups.append(("code-binding", manual_code))
        return state.binding if state.by_code else None

    save_event = Mock(side_effect=lambda event: event)
    repository = SimpleNamespace(get_desktop_device_by_code=device_lookup,
        get_latest_session_desktop_binding_for_device=binding_lookup,
        get_latest_session_desktop_binding_by_code=code_lookup, save_event=save_event)
    service = object.__new__(RealtimeSpeechService)
    service.settings = settings
    service.session_service = sessions
    service.repository = repository
    if baseline:
        namespace = dict(vars(realtime_module))
        exec(compile(_sealed_status_methods(), "sealed-cn-device-status-methods", "exec"), namespace)
        for method in _sealed_status_methods().body:
            setattr(service, method.name, MethodType(namespace[method.name], service))
    return SimpleNamespace(service=service, baseline=baseline, sessions=sessions, sessions_repo=sessions_repo,
        documents=documents_repo, record=record, full=full, control=control, writes=writes,
        state=state, lookups=lookups, save_event=save_event, clock=clock)


def publish(fixture, *, manual_code=CODE, user_id=OWNER, session_id=SESSION, device_id=DEVICE, **overrides):
    arguments = dict(session_id=session_id, device_id=device_id, capture_state="ready",
        source_health=[], capabilities={})
    arguments.update(overrides)
    if fixture.baseline:
        # The original router resolves a manual-code binding before publication.
        if manual_code is not None:
            binding = fixture.service.get_desktop_active_binding(device_id=device_id, manual_code=manual_code)
            if binding.session_id != session_id:
                raise DomainRequestError("realtime-speech", "device-status",
                    "该设备已连接到另一场面试，请刷新当前连接。", 410, "desktop_binding_replaced")
            user_id = binding.owner_user_id
        return fixture.service.publish_device_status(user_id=user_id, **arguments)
    return fixture.service.publish_cn_device_status(user_id=user_id, manual_code=manual_code, **arguments)


def outcome(call):
    try:
        return "event", call().model_dump(by_alias=True)
    except DomainRequestError as error:
        return "error", vars(error)


@pytest.mark.parametrize("status", ["preparing", "live", "ended"])
@pytest.mark.parametrize("mode", ["interview", "written", "mock"])
@pytest.mark.parametrize("audio", ["computer", "mobile"])
def test_status_matches_sealed_wire_and_reads_no_materials(monkeypatch, status, mode, audio):
    candidate = status_fixture(monkeypatch, status=status, mode=mode, audio=audio)
    result = outcome(lambda: publish(candidate))
    baseline = status_fixture(monkeypatch, baseline=True, status=status, mode=mode, audio=audio)
    assert result == outcome(lambda: publish(baseline))
    assert candidate.control.call_count == (1 if status == "ended" else 2)
    candidate.full.assert_not_called()
    candidate.documents.get_by_id.assert_not_called()
    candidate.writes.assert_not_called()
    assert baseline.full.call_count == (1 if status == "ended" else 2)
    if mode != "mock":
        assert baseline.documents.get_by_id.call_count == (12 if status == "ended" else 24)
        assert baseline.writes.call_count >= 1
    assert candidate.save_event.call_count == (0 if status == "ended" else 1)


@pytest.mark.parametrize("fallback", ["canonical", "code", "same-device-code"])
def test_binding_fallback_order_stripping_and_request_device_payload_match_baseline(monkeypatch, fallback):
    snapshots = []
    for baseline in (False, True):
        fixture = status_fixture(monkeypatch, baseline=baseline)
        fixture.state.direct = False
        requested = " old-device " if fallback != "same-device-code" else f" {DEVICE} "
        fixture.state.canonical = fallback == "canonical"
        result = publish(fixture, manual_code=f" {CODE} ", device_id=requested)
        assert result.payload["deviceId"] == requested
        snapshots.append((result.model_dump(by_alias=True), fixture.lookups))
    assert snapshots[0] == snapshots[1]
    if fallback == "canonical":
        assert snapshots[0][1] == [("device", CODE), ("binding", "old-device", CODE), ("binding", DEVICE, CODE)]
    elif fallback == "code":
        assert snapshots[0][1] == [("device", CODE), ("binding", "old-device", CODE), ("binding", DEVICE, CODE), ("code-binding", CODE)]
    else:
        assert snapshots[0][1] == [("device", CODE), ("binding", DEVICE, CODE), ("code-binding", CODE)]


@pytest.mark.parametrize("invalid", ["device", "binding", "status", "generation", "heartbeat", "missing", "foreign", "replaced"])
def test_invalid_binding_has_original_error_and_no_event(monkeypatch, invalid):
    results = []
    for baseline in (False, True):
        fixture = status_fixture(monkeypatch, baseline=baseline)
        if invalid == "device":
            fixture.state.device = None
        elif invalid == "binding":
            fixture.state.binding = None
        elif invalid == "status":
            fixture.state.binding = replace(fixture.state.binding, status="stale")
        elif invalid == "generation":
            fixture.state.device = replace(fixture.state.device, generation=2)
        elif invalid == "heartbeat":
            fixture.clock[0] += fixture.service.settings.realtime_desktop_heartbeat_ttl_seconds * 1000 + 1
        elif invalid == "missing":
            fixture.sessions_repo.sessions.clear()
        elif invalid == "foreign":
            fixture.state.binding = replace(fixture.state.binding, owner_user_id="synthetic-other-owner")
        results.append(outcome(lambda: publish(fixture, session_id="synthetic-other-session" if invalid == "replaced" else SESSION)))
        fixture.save_event.assert_not_called()
        if not baseline:
            fixture.full.assert_not_called()
            fixture.documents.get_by_id.assert_not_called()
            fixture.writes.assert_not_called()
    assert results[0] == results[1]
    assert results[0][0] == "error"
    assert results[0][1]["status_code"] == (410 if invalid == "replaced" else 404)


@pytest.mark.parametrize("change", ["ended", "deleted", "foreign"])
def test_second_authoritative_read_preserves_concurrent_lifecycle_contract(monkeypatch, change):
    results = []
    for baseline in (False, True):
        fixture = status_fixture(monkeypatch, baseline=baseline)
        original = fixture.sessions.get_session if baseline else fixture.sessions.get_control_state
        calls = 0

        def read_then_mutate(**kwargs):
            nonlocal calls
            calls += 1
            value = original(**kwargs)
            if calls == 1:
                if change == "deleted":
                    fixture.sessions_repo.sessions.clear()
                else:
                    fixture.sessions_repo.sessions[SESSION] = replace(fixture.sessions_repo.sessions[SESSION],
                        **({"status": "ended"} if change == "ended" else {"owner_user_id": "synthetic-other-owner"}))
            return value

        monkeypatch.setattr(fixture.sessions, "get_session" if baseline else "get_control_state", read_then_mutate)
        results.append(outcome(lambda: publish(fixture)))
        assert calls == 2
        assert fixture.save_event.call_count == (1 if change == "ended" else 0)
    assert results[0] == results[1]
    if change != "ended":
        assert results[0][1]["status_code"] == (404 if change == "deleted" else 403)


@pytest.mark.parametrize("change", ["ended", "deleted", "owner", "generation", "binding", "heartbeat"])
def test_no_new_cross_request_permission_cache(monkeypatch, change):
    fixture = status_fixture(monkeypatch)
    publish(fixture)
    if change == "ended":
        fixture.sessions_repo.sessions[SESSION] = replace(fixture.record, status="ended")
    elif change == "deleted":
        fixture.sessions_repo.sessions.clear()
    elif change == "owner":
        fixture.sessions_repo.sessions[SESSION] = replace(fixture.record, owner_user_id="synthetic-other-owner")
    elif change == "generation":
        fixture.state.device = replace(fixture.state.device, generation=2)
    elif change == "binding":
        fixture.state.binding = replace(fixture.state.binding, status="stale")
    else:
        fixture.clock[0] += fixture.service.settings.realtime_desktop_heartbeat_ttl_seconds * 1000 + 1
    with pytest.raises(DomainRequestError):
        publish(fixture)
    assert fixture.save_event.call_count == 1
    fixture.full.assert_not_called()


@pytest.mark.parametrize("legacy", ["live", "ended", "foreign", "missing"])
def test_no_manual_code_final_owner_and_existence_contract(monkeypatch, legacy):
    results = []
    for baseline in (False, True):
        fixture = status_fixture(monkeypatch, baseline=baseline, status="ended" if legacy == "ended" else "live")
        if legacy == "missing":
            fixture.sessions_repo.sessions.clear()
        results.append(outcome(lambda: publish(fixture, manual_code=None,
            user_id="synthetic-other-owner" if legacy == "foreign" else OWNER)))
        assert fixture.lookups == []
        if not baseline:
            fixture.control.assert_called_once_with(SESSION)
            fixture.full.assert_not_called()
            fixture.documents.get_by_id.assert_not_called()
    assert results[0] == results[1]


def test_all_source_health_and_capability_filters_match_sealed_payload(monkeypatch):
    source = dict(sourceId=17, sourceKind="microphone", label="Synthetic label " * 20,
        state="ready", stage="capturing", level="0.25", lastSignalAtMs=1, frameCount=2, lastFrameAtMs=3,
        backendFrameCount=4, lastBackendFrameAtMs=5, pendingFrameCount=6, oldestPendingFrameAgeMs=7,
        droppedFrameCount=8, reconnectCount=9, lastAckAtMs=10, lastReconnectReason="synthetic",
        noiseFloor=0.01, captureProcessor="synthetic", endpointingMode="synthetic", turnState="speaking",
        finalizationReason=None, sourceGeneration=2, terminalPendingSinceMs=11, terminalAgeMs=12,
        terminalResendCount=3, terminalAckAtMs=13, errorCode=None, unexpectedSecret="synthetic-private-field")
    capabilities = dict(platform="macos", architecture="arm64", protocolVersion=2, appVersion="1.3.6",
        microphone="granted", systemAudio="granted", unexpectedSecret="synthetic-private-field", screenCapture=True)
    results = [publish(status_fixture(monkeypatch, baseline=baseline), source_health=[source, {}],
        capabilities=capabilities).model_dump(by_alias=True) for baseline in (False, True)]
    assert results[0] == results[1]
    assert "synthetic-private-field" not in str(results[0])
    assert len(results[0]["payload"]["sourceHealth"][0]["label"]) == 120
    assert results[0]["payload"]["sourceHealth"][0]["level"] == 0.25


def test_invalid_level_does_not_save_or_replay(monkeypatch):
    for baseline in (False, True):
        fixture = status_fixture(monkeypatch, baseline=baseline)
        with pytest.raises(ValueError):
            publish(fixture, source_health=[{"level": "invalid-synthetic-level"}])
        fixture.save_event.assert_not_called()
        assert (fixture.full if baseline else fixture.control).call_count == 2


def test_original_binding_and_publication_and_global_still_read_full_sessions(monkeypatch):
    fixture = status_fixture(monkeypatch)
    fixture.service.get_desktop_active_binding(device_id=DEVICE, manual_code=CODE)
    fixture.service.publish_device_status(user_id=OWNER, session_id=SESSION, device_id=DEVICE,
        capture_state="ready", source_health=[], capabilities={})
    assert fixture.full.call_count == 2
    fixture.control.assert_not_called()
    assert fixture.documents.get_by_id.call_count == 24
    fixture = status_fixture(monkeypatch, edition="global")
    publish(fixture)
    assert fixture.full.call_count == 2
    fixture.control.assert_not_called()


def test_status_does_not_disable_later_material_aware_refresh(monkeypatch):
    fixture = status_fixture(monkeypatch)
    publish(fixture)
    fixture.documents.get_by_id.assert_not_called()
    fixture.writes.assert_not_called()
    refreshed = fixture.sessions.get_session(user_id=OWNER, session_id=SESSION)
    assert fixture.documents.get_by_id.call_count == 12
    assert fixture.writes.call_count >= 1
    assert all(document.status == "deleted" for document in refreshed.material_binding.bound_documents)


def test_retired_session_still_does_not_recreate_event_stream(monkeypatch):
    for baseline in (False, True):
        fixture = status_fixture(monkeypatch, baseline=baseline)
        fixture.service._retired_session_ids = {SESSION}
        assert publish(fixture).kind == "device-status"
        fixture.save_event.assert_not_called()


def test_repository_phase_excludes_projection_and_payload_conversion(monkeypatch):
    fixture = status_fixture(monkeypatch)
    active = []
    observations = []

    @contextmanager
    def phase(name):
        active.append(name)
        try:
            yield
        finally:
            active.pop()

    monkeypatch.setattr(realtime_module, "measure_device_status_phase", phase)
    old_control = fixture.sessions.get_control_state

    def control(**kwargs):
        assert not active
        return old_control(**kwargs)

    monkeypatch.setattr(fixture.sessions, "get_control_state", control)
    old_device = fixture.service.repository.get_desktop_device_by_code

    def device(code):
        observations.append(tuple(active))
        return old_device(code)

    fixture.service.repository.get_desktop_device_by_code = device
    fixture.save_event.side_effect = lambda event: (observations.append(tuple(active)), event)[1]

    class Level:
        def __float__(self):
            assert not active
            return 0.5

    publish(fixture, source_health=[{"level": Level()}])
    assert observations == [("binding_repository",), ("event_repository",)]
