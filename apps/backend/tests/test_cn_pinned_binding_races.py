"""Deterministic interleavings with synthetic data and private loopback Redis."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest

from test_cn_realtime_entity_state import binding, pair, redis_url  # noqa: F401


@pytest.mark.parametrize("change", ["retire", "rebind"])
def test_change_before_atomic_lookup_cannot_return_the_previous_live_pin(pair, monkeypatch, change):
    writer, reader, _, _ = pair
    old = writer.save_session_desktop_binding(binding())
    entered, release = Event(), Event()
    original = reader._cn_controls.call

    def delayed(op, *args):
        if op == "pinned_binding_lookup":
            entered.set()
            assert release.wait(timeout=3)
        return original(op, *args)

    monkeypatch.setattr(reader._cn_controls, "call", delayed)
    with ThreadPoolExecutor(max_workers=1) as workers:
        future = workers.submit(reader.get_pinned_session_desktop_binding,
                                device_id=old.device_id, manual_code=old.manual_code,
                                session_id=old.session_id, binding_id=old.binding_id)
        assert entered.wait(timeout=2)
        try:
            if change == "retire":
                writer.clear_session_runtime(session_id=old.session_id)
            else:
                writer.save_session_desktop_binding(replace(old, binding_id="new-binding", bound_at_ms=old.bound_at_ms + 1))
        finally:
            release.set()
        result = future.result(timeout=3)
    if change == "retire":
        assert result is not None and result.status == "stale"
        assert writer.save_session_desktop_binding(old).status == "stale"
    else:
        assert result is None
        current = reader.get_pinned_session_desktop_binding(device_id=old.device_id, manual_code=old.manual_code,
                                                           session_id=old.session_id, binding_id="new-binding")
        assert current is not None and current.status == "bound"
