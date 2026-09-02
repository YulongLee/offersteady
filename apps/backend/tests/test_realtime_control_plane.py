from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import logging
from types import MethodType

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import (
    DomainRequestError,
    _control_error_log_sample,
    _control_error_log_state,
    install_exception_handlers,
)
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
