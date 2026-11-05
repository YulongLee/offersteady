"""Bounded pinned-state reads against a private disposable Redis, never production."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
from threading import Lock
from time import perf_counter
from unittest.mock import Mock

import pytest

from test_cn_realtime_entity_state import pair, redis_url  # noqa: F401
from test_cn_control_state_reads import control_fixture, pairing


def populated_fixture(pair, monkeypatch, count):
    repository, _, client, _ = pair
    fixture = control_fixture(monkeypatch)
    repository.save_desktop_device(fixture.device)
    records, owners = {}, {}
    for index in range(count - 1):
        item = replace(fixture.binding, binding_id=f"history-binding-{index}", session_id=f"history-session-{index}",
                       owner_user_id=f"history-owner-{index}", device_id=f"history-device-{index}",
                       manual_code=f"{index % 1_000_000:06d}", status="stale")
        records[f"{item.owner_user_id}|{item.session_id}"] = json.dumps(asdict(item))
        owners[item.session_id] = item.owner_user_id
    if records:
        pipeline = client.pipeline()
        pipeline.hset(repository._binding_entity_key, mapping=records)
        pipeline.hset(repository._cn_controls.keys[8], mapping=owners)
        pipeline.execute()
    repository.save_session_desktop_binding(fixture.binding)
    fixture.service.repository = repository
    return fixture, repository, client


@pytest.mark.parametrize("history_count", [1, 1191, 10000])
def test_pinned_lookup_has_fixed_network_cost_with_large_history(pair, monkeypatch, history_count, record_testsuite_property):
    fixture, repository, client = populated_fixture(pair, monkeypatch, history_count)
    assert client.hlen(repository._binding_entity_key) == history_count
    calls = Counter()
    original = repository._redis.execute_command
    original_decode = repository._cn_controls.decode
    decoded = []

    def counted_decode(cls, raw):
        decoded.append(cls)
        return original_decode(cls, raw)

    def counted(command, *args, **kwargs):
        calls[str(command).upper()] += 1
        return original(command, *args, **kwargs)

    monkeypatch.setattr(repository._redis, "execute_command", counted)
    monkeypatch.setattr(repository._cn_controls, "decode", counted_decode)
    projection = Mock(wraps=fixture.repository.get_control_state)
    monkeypatch.setattr(fixture.repository, "get_control_state", projection)
    before = client.info("commandstats")
    started = perf_counter()
    result = pairing(fixture, pinned=True)
    elapsed_ms = (perf_counter() - started) * 1000
    assert result["bindingLockState"] == "held" and result["bound"] is True
    assert result["binding"]["bindingId"] == fixture.binding.binding_id
    assert calls["HVALS"] == 0, dict(calls)
    assert calls["HGETALL"] == calls["HSCAN"] == 0, dict(calls)
    assert calls["HEXISTS"] == 0, dict(calls)
    assert sum(calls.values()) <= 5, dict(calls)
    assert len(decoded) == 1
    projection.assert_called_once_with(fixture.record.session_id)
    after = client.info("commandstats")
    for command in ("hvals", "hgetall", "hscan"):
        key = f"cmdstat_{command}"
        assert after.get(key, {}).get("calls", 0) == before.get(key, {}).get("calls", 0)
    record_testsuite_property(f"pinned_read_history_{history_count}", json.dumps({
        "historyBindings": history_count, "commands": dict(calls), "networkCalls": sum(calls.values()),
        "bindingDecodes": len(decoded), "dbControlReads": projection.call_count,
        "localElapsedMs": round(elapsed_ms, 3), "productionP95Measured": False}))


def test_twelve_mixed_pollers_keep_each_pinned_read_bounded(pair, monkeypatch, record_testsuite_property):
    fixture, repository, client = populated_fixture(pair, monkeypatch, 10000)
    identities = [(fixture.device, fixture.binding)]
    for index in range(1, 12):
        device = replace(fixture.device, device_id=f"idle-poller-{index}", manual_code=f"{800000 + index:06d}")
        repository.save_desktop_device(device)
        link = replace(fixture.binding, session_id=f"ended-poller-{index}", binding_id=f"ended-binding-{index}",
                       device_id=device.device_id, manual_code=device.manual_code, status="stale")
        fixture.repository.save_session(replace(fixture.record, session_id=link.session_id, status="ended"))
        repository.save_session_desktop_binding(link)
        identities.append((device, link))
    calls = Counter()
    call_lock = Lock()
    original = repository._redis.execute_command

    def counted(command, *args, **kwargs):
        with call_lock:
            calls[str(command).upper()] += 1
        return original(command, *args, **kwargs)

    monkeypatch.setattr(repository._redis, "execute_command", counted)

    def poll(index):
        # Bypass the existing cross-request cache deliberately: all 12 reads
        # must exercise the real repository, not receive one cached result.
        device, link = identities[index]
        result = fixture.service._compute_desktop_pairing_status(
            device_id=device.device_id, manual_code=device.manual_code,
            pinned_session_id=link.session_id if link and index % 3 == 0 else None,
            pinned_binding_id=link.binding_id if link and index % 3 == 0 else None)
        state = fixture.sessions.get_control_state(user_id=fixture.record.owner_user_id,
                                                   session_id=fixture.record.session_id)
        assert state.status == "live"
        return result

    before = client.info("commandstats")
    started = perf_counter()
    with ThreadPoolExecutor(max_workers=12) as workers:
        outcomes = list(workers.map(poll, range(12)))
    elapsed_ms = (perf_counter() - started) * 1000
    assert [result["bound"] for result in outcomes] == [True] + [False] * 11
    assert calls["HVALS"] == calls["HGETALL"] == calls["HSCAN"] == calls["HEXISTS"] == 0, dict(calls)
    assert sum(calls.values()) <= 60, dict(calls)
    after = client.info("commandstats")
    for command in ("hvals", "hgetall", "hscan"):
        key = f"cmdstat_{command}"
        assert after.get(key, {}).get("calls", 0) == before.get(key, {}).get("calls", 0)
    record_testsuite_property("twelve_mixed_pollers", json.dumps({
        "pollers": 12, "liveSessions": 1, "idleOrEndedPollers": 11, "historyBindings": 10000,
        "commands": dict(calls), "networkCalls": sum(calls.values()),
        "localElapsedMs": round(elapsed_ms, 3), "productionP95Measured": False}))
