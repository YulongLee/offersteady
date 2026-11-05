from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from statistics import quantiles
from time import perf_counter
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.errors import install_exception_handlers
from app.main import create_app
from app.modules.screenshot_answer import stream_desktop_capture_requests
from app.services.screenshot_stream_admission import ScreenshotStreamAdmissionCoordinator


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def coordinator(clock: FakeClock, *, max_active: int = 4, max_accepts: int = 3) -> ScreenshotStreamAdmissionCoordinator:
    return ScreenshotStreamAdmissionCoordinator(
        max_active=max_active,
        reconnect_window_seconds=10.0,
        reconnect_max_accepts=max_accepts,
        retry_after_seconds=5,
        clock=clock,
    )


def test_one_device_has_one_token_safe_stream_lease() -> None:
    clock = FakeClock()
    admission = coordinator(clock)

    first = admission.acquire("device-a")
    duplicate = admission.acquire("device-a")

    assert first.admitted is True
    assert duplicate.admitted is False
    assert duplicate.reason == "duplicate"
    assert duplicate.retry_after_ms == 5_000
    assert admission.release(first.lease) is True
    assert admission.release(first.lease) is False

    replacement = admission.acquire("device-a")
    assert replacement.admitted is True
    assert replacement.lease.token != first.lease.token
    assert admission.release(first.lease) is False
    assert admission.diagnostics()["active"] == 1


def test_sequential_reconnects_and_global_capacity_are_bounded() -> None:
    clock = FakeClock()
    admission = coordinator(clock, max_active=2, max_accepts=2)

    first = admission.acquire("device-a")
    assert admission.release(first.lease) is True
    second = admission.acquire("device-a")
    assert admission.release(second.lease) is True
    rate_limited = admission.acquire("device-a")
    assert rate_limited.admitted is False
    assert rate_limited.reason == "reconnect-rate"

    other = admission.acquire("device-b")
    third = admission.acquire("device-c")
    saturated = admission.acquire("device-d")
    assert other.admitted and third.admitted
    assert saturated.admitted is False
    assert saturated.reason == "global-capacity"

    clock.advance(10.1)
    recovered = admission.acquire("device-a")
    assert recovered.admitted is False  # global capacity still protects the process
    assert recovered.reason == "global-capacity"

    metrics = admission.diagnostics()
    assert metrics == {
        "active": 2,
        "maxActive": 2,
        "accepted": 4,
        "released": 2,
        "duplicateDenied": 0,
        "reconnectRateDenied": 1,
        "globalCapacityDenied": 2,
        "configuredMaxActive": 2,
        "retryAfterMs": 5_000,
    }


def test_duplicate_route_is_denied_before_binding_lookup() -> None:
    asyncio.run(_assert_duplicate_route_is_denied_before_binding_lookup())


async def _assert_duplicate_route_is_denied_before_binding_lookup() -> None:
    clock = FakeClock()
    admission = coordinator(clock)
    held = admission.acquire("device-route")
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(screenshot_stream_admission=admission)))

    class RealtimeMustNotRun:
        def get_desktop_capture_binding(self, **_kwargs):
            raise AssertionError("duplicate stream must not enter binding lookup")

    captured: DomainRequestError | None = None
    try:
        await stream_desktop_capture_requests(
            "device-route",
            request,
            manual_code="123456",
            service=SimpleNamespace(),
            realtime=RealtimeMustNotRun(),
        )
    except DomainRequestError as raised:
        captured = raised
    else:
        raise AssertionError("duplicate screenshot stream must be denied")

    assert captured is not None
    assert captured.status_code == 409
    assert captured.error_code == "screenshot_stream_duplicate"
    assert admission.release(held.lease) is True


def test_validation_failure_and_disconnect_release_route_ownership() -> None:
    asyncio.run(_assert_validation_failure_and_disconnect_release_route_ownership())


async def _assert_validation_failure_and_disconnect_release_route_ownership() -> None:
    clock = FakeClock()
    admission = coordinator(clock)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(screenshot_stream_admission=admission)))

    class InvalidRealtime:
        def get_desktop_capture_binding(self, **_kwargs):
            raise DomainRequestError("realtime-speech", "desktop-capture-binding", "invalid", 404)

    try:
        await stream_desktop_capture_requests(
            "device-invalid",
            request,
            manual_code="123456",
            service=SimpleNamespace(),
            realtime=InvalidRealtime(),
        )
    except DomainRequestError:
        pass
    else:
        raise AssertionError("invalid screenshot binding must be denied")
    assert admission.diagnostics()["active"] == 0

    @dataclass
    class Pending:
        request_id: str = "capture-pending"
        status: str = "requested"
        stage: str = "waiting-desktop"

    class ValidRealtime:
        settings = SimpleNamespace(realtime_event_block_ms=1_000)
        session_service = SimpleNamespace(get_session=lambda **_kwargs: SimpleNamespace(status="live"))

        def get_desktop_capture_binding(self, **_kwargs):
            return SimpleNamespace(
                owner_user_id="synthetic-user",
                session_id="synthetic-session",
                binding_generation=7,
            )

        def list_session_events_after(self, **_kwargs):
            return 11, [], True

    class PendingService:
        def get_next_remote_capture_request(self, **_kwargs):
            return Pending()

    class DisconnectingRequest:
        app = SimpleNamespace(state=SimpleNamespace(screenshot_stream_admission=admission))

        async def is_disconnected(self) -> bool:
            return True

    response = await stream_desktop_capture_requests(
        "device-valid",
        DisconnectingRequest(),
        manual_code="654321",
        cursor=0,
        service=PendingService(),
        realtime=ValidRealtime(),
    )
    chunks = [chunk async for chunk in response.body_iterator]
    payload = b"".join(item.encode() if isinstance(item, str) else item for item in chunks).decode()
    assert "event: capture-request" in payload
    assert '"requestId": "capture-pending"' in payload
    assert admission.diagnostics()["active"] == 0


def test_shutdown_releases_all_aggregate_ownership_without_identifiers() -> None:
    clock = FakeClock()
    admission = coordinator(clock)
    admission.acquire("private-device-a")
    admission.acquire("private-device-b")

    admission.shutdown()
    metrics = admission.diagnostics()

    assert metrics["active"] == 0
    assert "private-device-a" not in repr(metrics)
    assert "private-device-b" not in repr(metrics)


def test_denied_stream_response_is_legacy_compatible_and_retryable() -> None:
    app = FastAPI()
    install_exception_handlers(
        app,
        settings=Settings(),
        logger=logging.getLogger("synthetic-screenshot-admission-test"),
    )

    @app.get("/synthetic-screenshot-stream")
    async def denied_stream() -> None:
        raise DomainRequestError(
            "screenshot-answer",
            "desktop-stream-admission",
            "synthetic retry",
            409,
            "screenshot_stream_duplicate",
            retry_after_ms=5_000,
        )

    response = TestClient(app).get("/synthetic-screenshot-stream")
    payload = response.json()

    assert response.status_code == 409
    assert response.headers["Retry-After"] == "5"
    assert payload["error"]["details"]["errorCode"] == "screenshot_stream_duplicate"
    assert payload["error"]["details"]["retryAfterMs"] == 5_000


def test_duplicate_reconnect_storm_is_constant_time_and_bounded() -> None:
    clock = FakeClock()
    admission = coordinator(clock, max_active=64)
    held = admission.acquire("storm-device")
    latencies_ms: list[float] = []

    for _ in range(10_000):
        started = perf_counter()
        decision = admission.acquire("storm-device")
        latencies_ms.append((perf_counter() - started) * 1_000)
        assert decision.admitted is False
        assert decision.reason == "duplicate"

    p95_ms = quantiles(latencies_ms, n=100)[94]
    metrics = admission.diagnostics()
    assert p95_ms < 50
    assert metrics["active"] == 1
    assert metrics["accepted"] == 1
    assert metrics["duplicateDenied"] == 10_000
    assert admission.release(held.lease) is True


def test_cursor_event_delivery_is_preserved_and_releases_lease() -> None:
    asyncio.run(_assert_cursor_event_delivery_is_preserved_and_releases_lease())


async def _assert_cursor_event_delivery_is_preserved_and_releases_lease() -> None:
    clock = FakeClock()
    admission = coordinator(clock)

    class Realtime:
        settings = SimpleNamespace(realtime_event_block_ms=100)
        session_service = SimpleNamespace(get_session=lambda **_kwargs: SimpleNamespace(status="live"))

        def get_desktop_capture_binding(self, **_kwargs):
            return SimpleNamespace(owner_user_id="synthetic-user", session_id="synthetic-session")

        def list_session_events_after(self, **_kwargs):
            return 11, [], True

        def wait_for_session_events_after(self, **_kwargs):
            event = SimpleNamespace(
                kind="screenshot-capture-updated",
                event_id="event-12",
                payload={
                    "deviceId": "device-cursor",
                    "requestId": "capture-cursor",
                    "status": "requested",
                    "stage": "waiting-desktop",
                },
            )
            return 12, [event], True

    class Service:
        def get_next_remote_capture_request(self, **_kwargs):
            return None

    class Request:
        app = SimpleNamespace(state=SimpleNamespace(screenshot_stream_admission=admission))

        def __init__(self) -> None:
            self.disconnect_checks = 0

        async def is_disconnected(self) -> bool:
            self.disconnect_checks += 1
            return self.disconnect_checks > 1

    response = await stream_desktop_capture_requests(
        "device-cursor",
        Request(),
        manual_code="112233",
        cursor=9,
        service=Service(),
        realtime=Realtime(),
    )
    chunks = [chunk async for chunk in response.body_iterator]
    payload = b"".join(item.encode() if isinstance(item, str) else item for item in chunks).decode()

    assert "id: 12" in payload
    assert '"requestId": "capture-cursor"' in payload
    assert '"eventId": "event-12"' in payload
    assert admission.diagnostics()["active"] == 0


def test_runtime_metrics_expose_only_aggregate_screenshot_diagnostics() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/realtime-speech/metrics")
    metrics = response.json()["data"]

    assert metrics["screenshotStreamAdmission"]["active"] == 0
    assert metrics["screenshotStreamAdmission"]["configuredMaxActive"] == 64
    assert metrics["screenshotEventWaitExecutor"]["active"] == 0
    assert metrics["screenshotEventWaitExecutor"]["configuredWorkers"] == 32
    serialized = str(metrics).lower()
    assert "device-cursor" not in serialized
    assert "manual_code" not in serialized
