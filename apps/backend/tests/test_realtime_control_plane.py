from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import logging
from types import MethodType, SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import (
    DomainRequestError,
    _control_error_log_sample,
    _control_error_log_state,
    install_exception_handlers,
)
from app.ports.realtime_speech import DesktopDeviceRecord, SessionDesktopBindingRecord
from app.services.realtime_control_executor import RealtimeControlExecutor
from app.services.realtime_speech_service import RealtimeSpeechService


def _control_cache_service() -> RealtimeSpeechService:
    service = object.__new__(RealtimeSpeechService)
    service.settings = Settings(realtime_control_cache_ms=750)
    service._control_query_cache_lock = threading.Lock()
    service._control_query_cache = {}
    service._control_query_inflight = {}
    service._control_query_cache_generation = 0
    service._control_query_cache_hits = 0
    service._control_query_cache_misses = 0
    service._control_query_singleflight_waits = 0
    return service


def test_duplicate_pairing_queries_are_single_flight_and_cached() -> None:
    service = _control_cache_service()
    calls = 0
    calls_lock = threading.Lock()

    def compute(self, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.05)
        return {"registered": True, "bound": False}

    service._compute_desktop_pairing_status = MethodType(compute, service)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(
            lambda _index: service.get_desktop_pairing_status(
                manual_code="123456",
                device_id="synthetic-device",
            ),
            range(8),
        ))

    assert calls == 1
    assert all(result == {"registered": True, "bound": False} for result in results)
    diagnostics = service._control_query_diagnostics()
    assert diagnostics["cacheMisses"] == 1
    assert diagnostics["cacheHits"] == 7
    assert diagnostics["singleflightWaits"] >= 1


def test_pairing_cache_invalidation_forces_authoritative_recompute() -> None:
    service = _control_cache_service()
    calls = 0

    def compute(self, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"revision": calls}

    service._compute_desktop_pairing_status = MethodType(compute, service)
    first = service.get_desktop_pairing_status(manual_code="123456")
    cached = service.get_desktop_pairing_status(manual_code="123456")
    service._invalidate_control_query_cache()
    refreshed = service.get_desktop_pairing_status(manual_code="123456")

    assert first == cached == {"revision": 1}
    assert refreshed == {"revision": 2}


def test_pinned_binding_identity_never_reuses_another_binding_cache_entry() -> None:
    service = _control_cache_service()
    calls = 0

    def compute(self, **kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {
            "sessionId": kwargs.get("pinned_session_id"),
            "bindingId": kwargs.get("pinned_binding_id"),
            "revision": calls,
        }

    service._compute_desktop_pairing_status = MethodType(compute, service)
    first = service.get_desktop_pairing_status(
        manual_code="123456", device_id="device-a", pinned_session_id="session-a", pinned_binding_id="binding-a",
    )
    cached = service.get_desktop_pairing_status(
        manual_code="123456", device_id="device-a", pinned_session_id="session-a", pinned_binding_id="binding-a",
    )
    next_binding = service.get_desktop_pairing_status(
        manual_code="123456", device_id="device-a", pinned_session_id="session-b", pinned_binding_id="binding-b",
    )

    assert first == cached
    assert first["revision"] == 1
    assert next_binding == {"sessionId": "session-b", "bindingId": "binding-b", "revision": 2}
    assert calls == 2


def test_pairing_cache_expires_below_live_binding_poll_interval() -> None:
    service = _control_cache_service()
    service.settings = Settings(realtime_control_cache_ms=50)
    calls = 0

    def compute(self, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"revision": calls}

    service._compute_desktop_pairing_status = MethodType(compute, service)
    first = service.get_desktop_pairing_status(manual_code="123456", device_id="device-a")
    time.sleep(0.06)
    refreshed = service.get_desktop_pairing_status(manual_code="123456", device_id="device-a")

    assert first == {"revision": 1}
    assert refreshed == {"revision": 2}
    assert calls == 2


def test_device_heartbeat_invalidation_preserves_other_device_cache() -> None:
    service = _control_cache_service()
    calls: dict[str, int] = {}

    def compute(self, **kwargs: object) -> dict[str, object]:
        code = str(kwargs["manual_code"])
        calls[code] = calls.get(code, 0) + 1
        return {"manualCode": code, "revision": calls[code]}

    service._compute_desktop_pairing_status = MethodType(compute, service)
    service.get_desktop_pairing_status(manual_code="123456", device_id="device-a")
    service.get_desktop_pairing_status(manual_code="654321", device_id="device-b")
    service._invalidate_control_query_cache(
        manual_code="123456",
        device_id="device-a",
    )

    refreshed = service.get_desktop_pairing_status(
        manual_code="123456",
        device_id="device-a",
    )
    unaffected = service.get_desktop_pairing_status(
        manual_code="654321",
        device_id="device-b",
    )

    assert refreshed["revision"] == 2
    assert unaffected["revision"] == 1
    assert calls == {"123456": 2, "654321": 1}


def test_ordinary_device_heartbeat_does_not_discard_safe_short_cache() -> None:
    service = _control_cache_service()
    calls = 0
    device = DesktopDeviceRecord(
        device_id="device-a",
        manual_code="123456",
        display_name="Synthetic device",
        capabilities={},
        registered_at_ms=1,
        last_seen_at_ms=1,
    )
    service.repository = SimpleNamespace(
        get_desktop_device_by_code=lambda _code: device,
        save_desktop_device=lambda stored: stored,
    )

    def compute(self, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"revision": calls}

    service._compute_desktop_pairing_status = MethodType(compute, service)
    first = service.get_desktop_pairing_status(
        manual_code=device.manual_code,
        device_id=device.device_id,
    )
    service.record_desktop_device_heartbeat(
        device_id=device.device_id,
        manual_code=device.manual_code,
        display_name=device.display_name,
        capabilities={},
    )
    after_heartbeat = service.get_desktop_pairing_status(
        manual_code=device.manual_code,
        device_id=device.device_id,
    )

    assert first == after_heartbeat == {"revision": 1}
    assert calls == 1


def test_pairing_status_reads_bound_session_only_once_per_cache_miss() -> None:
    service = _control_cache_service()
    now_ms = int(time.time() * 1000)
    device = DesktopDeviceRecord(
        device_id="device-a",
        manual_code="123456",
        display_name="Synthetic device",
        capabilities={},
        registered_at_ms=now_ms,
        last_seen_at_ms=now_ms,
    )
    binding = SessionDesktopBindingRecord(
        binding_id="binding-a",
        session_id="session-a",
        owner_user_id="synthetic-user",
        device_id=device.device_id,
        manual_code=device.manual_code,
        display_name=device.display_name,
        capabilities={},
        bound_at_ms=now_ms,
        last_seen_at_ms=now_ms,
    )
    service.repository = SimpleNamespace(
        get_desktop_device_by_code=lambda _code: device,
        get_latest_session_desktop_binding_by_code=lambda **_kwargs: binding,
    )
    session_reads = 0

    def get_session(**_kwargs: object) -> SimpleNamespace:
        nonlocal session_reads
        session_reads += 1
        return SimpleNamespace(status="ended", session_mode="interview")

    service.session_service = SimpleNamespace(get_session=get_session)

    status = service._compute_desktop_pairing_status(
        manual_code=device.manual_code,
        device_id=device.device_id,
    )

    assert status["state"] == "stale-bound"
    assert status["staleReason"] == "session-not-active"
    assert session_reads == 1


def test_control_executor_is_bounded_and_keeps_event_loop_responsive() -> None:
    async def scenario() -> tuple[dict[str, int], int]:
        executor = RealtimeControlExecutor(max_workers=2, queue_max=2)
        ticks = 0

        def blocking_work() -> str:
            time.sleep(0.05)
            return "ok"

        async def ticker() -> None:
            nonlocal ticks
            for _ in range(10):
                await asyncio.sleep(0.01)
                ticks += 1

        try:
            results, _ = await asyncio.gather(
                asyncio.gather(*(executor.run(blocking_work) for _ in range(8))),
                ticker(),
            )
            assert results == ["ok"] * 8
            return executor.diagnostics(), ticks
        finally:
            executor.shutdown()

    diagnostics, ticks = asyncio.run(scenario())
    assert diagnostics["maxActive"] <= 2
    assert diagnostics["submitted"] == diagnostics["completed"] == 8
    assert diagnostics["saturated"] >= 1
    assert ticks == 10


def test_invalid_binding_keeps_legacy_status_and_returns_retry_advice() -> None:
    app = FastAPI()
    install_exception_handlers(
        app,
        settings=Settings(),
        logger=logging.getLogger("synthetic-control-plane-test"),
    )

    @app.get("/synthetic-invalid-binding")
    async def invalid_binding() -> None:
        raise DomainRequestError(
            "realtime-speech",
            "desktop-active-binding",
            "synthetic invalid binding",
            404,
        )

    response = TestClient(app).get("/synthetic-invalid-binding")
    payload = response.json()

    assert response.status_code == 404
    assert response.headers["Retry-After"] == "2"
    assert payload["error"]["details"]["retryAfterMs"] == 2_000


def test_repeated_invalid_binding_diagnostics_are_sampled() -> None:
    _control_error_log_state.clear()
    error = DomainRequestError(
        "realtime-speech",
        "desktop-active-binding",
        "synthetic invalid binding",
        404,
    )

    first = _control_error_log_sample(error)
    repeats = [_control_error_log_sample(error) for _ in range(20)]

    assert first == (True, 0)
    assert all(should_log is False for should_log, _count in repeats)
    assert repeats[-1][1] == 20
