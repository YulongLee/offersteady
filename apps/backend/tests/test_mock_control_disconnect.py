"""Control endpoint regressions; synthetic sockets/providers, no storage/network."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from starlette.websockets import WebSocketDisconnect

from app.modules import mock_interview as api


async def exercise(monkeypatch, *, receive_error=None, close_error=None, detach_error=None):
    events, pump_started = [], asyncio.Event()
    controller = SimpleNamespace(closed=False)

    async def flush(_):
        pump_started.set()

    async def detach(value):
        assert value is controller
        events.append("detach")
        value.closed = True
        if detach_error:
            raise detach_error

    runtime = SimpleNamespace(attach=AsyncMock(return_value=controller),
        flush_draft=AsyncMock(side_effect=flush), detach=AsyncMock(side_effect=detach))
    monkeypatch.setattr(api, "require_mock_runtime", lambda: runtime)
    monkeypatch.setattr(api, "authentication_service", lambda: SimpleNamespace(
        authenticate_access_token=lambda **_: SimpleNamespace(user_id="synthetic-owner")))

    class Socket:
        calls = 0
        async def accept(self):
            events.append("accept")
        async def receive_text(self):
            self.calls += 1
            if self.calls == 1:
                return json.dumps({"accessToken": "synthetic-token"})
            await pump_started.wait()
            raise receive_error or WebSocketDisconnect(code=1006)
        async def send_json(self, payload):
            raise AssertionError("disconnect must not send another payload")
        async def close(self):
            assert controller.closed
            assert events[-1] == "detach"
            events.append("close")
            if close_error:
                raise close_error

    before = set(asyncio.all_tasks())
    try:
        await api.mock_control(Socket(), "synthetic-session")
    finally:
        runtime.detach.assert_awaited_once_with(controller)
        await asyncio.sleep(0)
        assert not [task for task in asyncio.all_tasks() - before if not task.done()]
    return events


@pytest.mark.parametrize("close_error", [None, RuntimeError("already closed"), WebSocketDisconnect(code=1006)])
@pytest.mark.parametrize("receive_error", [WebSocketDisconnect(code=1001), TimeoutError(), ValueError("synthetic")])
def test_expected_disconnect_closes_after_detach_without_secondary_error(monkeypatch, receive_error, close_error):
    assert asyncio.run(exercise(monkeypatch, receive_error=receive_error, close_error=close_error)) == ["accept", "detach", "close"]


def test_endpoint_cancellation_is_preserved_after_expected_disconnected_close(monkeypatch):
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise(monkeypatch, receive_error=asyncio.CancelledError(),
            close_error=WebSocketDisconnect(code=1006)))


@pytest.mark.parametrize("boundary", ["close", "detach"])
def test_unrelated_cleanup_failures_remain_visible(monkeypatch, boundary):
    failure = LookupError("synthetic-cleanup-failure")
    with pytest.raises(LookupError, match="synthetic-cleanup-failure"):
        asyncio.run(exercise(monkeypatch, **{boundary + "_error": failure}))
