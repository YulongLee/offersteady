"""Synthetic records and a private, disposable localhost Redis only."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

import pytest
from redis import Redis

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.realtime_speech import AccountDesktopDeviceRecord, QuestionCandidateRecord, SessionDesktopBindingRecord, WebSessionHeartbeatRecord, RealtimeEvent, TranscriptSegmentRecord
from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService


@pytest.fixture(scope="module")
def redis_url(tmp_path_factory):
    # Setting this task-specific variable explicitly grants this fixture
    # exclusive use/FLUSHDB of a newly created disposable loopback database.
    # Never point it at an existing developer or product Redis instance.
    owned_external = os.environ.get("OFFERSTEADY_CN_ENTITY_TEST_REDIS_URL")
    if owned_external:
        parsed = urlsplit(owned_external)
        if parsed.scheme != "redis" or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
            raise ValueError("CN entity tests require an exclusive disposable loopback Redis URL")
        yield owned_external
        return
    executable = shutil.which("redis-server")
    if not executable:
        pytest.skip("redis-server is required for real atomic Redis regressions")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    directory = tmp_path_factory.mktemp("cn-runtime-synthetic-redis")
    process = subprocess.Popen([executable, "--bind", "127.0.0.1", "--port", str(port),
                                "--save", "", "--appendonly", "no", "--dir", str(directory)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"redis://127.0.0.1:{port}/0"
    client = Redis.from_url(url)
    try:
        for _ in range(100):
            try:
                if client.ping(): break
            except Exception:
                time.sleep(.01)
        else: raise AssertionError("private synthetic Redis did not start")
        yield url
    finally:
        client.close()
        process.terminate()
        process.wait(timeout=5)


@pytest.fixture
def pair(redis_url):
    client = Redis.from_url(redis_url, decode_responses=True)
    client.flushdb()  # This fixture exclusively created and owns the server.
    settings = Settings(_env_file=None, redis_url=redis_url, database_url=None, product_edition="global", realtime_runtime_ttl_seconds=300)
    first = RedisRealtimeSpeechRepository(settings)
    second = RedisRealtimeSpeechRepository(settings)
    return first, second, client, settings


def candidate(name="q", session="s", owner="u", updated=10):
    return QuestionCandidateRecord(name, session, owner, ["segment"], "Synthetic question?", "confirmed", "auto-confirmed", .95,
                                   created_at_ms=1, updated_at_ms=updated)


def binding(session="s", owner="u", generation=1, at=10):
    return SessionDesktopBindingRecord(f"b-{session}", session, owner, "d", "123456", "Synthetic", {}, at, at,
                                       binding_generation=generation)


def test_entities_are_authoritative_cross_instance_and_never_write_snapshot(pair):
    a, b, client, _ = pair
    a._snapshot = lambda: (_ for _ in ()).throw(AssertionError("CN must not rewrite snapshot"))
    q = a.save_candidate(candidate())
    association = a.save_account_desktop_device(AccountDesktopDeviceRecord("u", "d", "123456", 1, 20))
    link = a.save_session_desktop_binding(binding())
    assert b.get_candidate("q") == q
    assert b.list_candidates_for_session(session_id="s") == [q]
    assert b.get_account_desktop_device(user_id="u", device_id="d") == association
    assert b.get_last_account_desktop_device(user_id="u") == association
    assert b.get_latest_session_desktop_binding_by_code(manual_code="123456") == link
    assert b.list_session_desktop_bindings_for_user(user_id="u") == [link]
    assert client.get(a._snapshot_key) is None
    assert a.operational_diagnostics()["globalSnapshotWriteCount"] == 0


def test_same_millisecond_candidate_cas_claim_has_one_winner(pair):
    a, b, _, _ = pair
    original = a.save_candidate(candidate())
    barrier = threading.Barrier(2)
    def claim(repo, value):
        barrier.wait(timeout=2)
        return repo.compare_and_save_candidate(replace(original, answer_task_id=value), expected=original)
    with ThreadPoolExecutor(2) as workers:
        futures = [workers.submit(claim, a, "claim:a"), workers.submit(claim, b, "claim:b")]
        outcomes = [x.result(timeout=3) for x in futures]
    assert sum(x is not None for x in outcomes) == 1
    winner = next(x for x in outcomes if x is not None)
    assert a.get_candidate("q") == winner
    assert b.compare_and_save_candidate(replace(original, answer_task_id=None), expected=original) is None


def test_candidate_order_owner_and_claim_are_not_overwritten(pair):
    a, b, _, _ = pair
    q = a.save_candidate(candidate(updated=20))
    assert b.save_candidate(replace(q, text="older", updated_at_ms=19)) == q
    claimed = a.compare_and_save_candidate(replace(q, answer_task_id="claim:one"), expected=q)
    refined = b.save_candidate(replace(q, text="refined", updated_at_ms=21))
    assert refined.answer_task_id == claimed.answer_task_id
    with pytest.raises(ValueError, match="identity_mismatch"):
        b.save_candidate(replace(q, owner_user_id="other"))
    assert a.get_candidate("q").owner_user_id == "u"


def test_binding_stale_and_newer_generation_win_late_saves(pair):
    a, b, _, _ = pair
    old = a.save_session_desktop_binding(binding())
    latest = b.save_session_desktop_binding(replace(old, binding_generation=2))
    assert a.save_session_desktop_binding(old) == latest
    stale = a.save_session_desktop_binding(replace(latest, status="stale"))
    assert b.save_session_desktop_binding(latest) == stale
    assert b.get_latest_session_desktop_binding_for_device(device_id="d", manual_code="123456") == stale
    rebound = b.save_session_desktop_binding(replace(stale, bound_at_ms=11, status="bound"))
    assert rebound.status == "bound"


@pytest.mark.parametrize("legacy_ttl", [None, 450])
def test_legacy_seed_never_changes_old_bytes_or_revives_cleared_session(pair, legacy_ttl):
    a, _, client, settings = pair
    client.flushdb()
    q, link = candidate(), binding()
    old = json.dumps({"candidates": [asdict(q)], "bindings": [asdict(link)]})
    client.set(a._snapshot_key, old, ex=legacy_ttl)
    a = RedisRealtimeSpeechRepository(settings)
    assert a.get_candidate("q") == q
    assert a.clear_session_runtime(session_id="s")["cleared_candidates"] == 1
    restarted = RedisRealtimeSpeechRepository(settings)
    assert restarted.get_candidate("q") is None
    assert restarted.list_candidates_for_session(session_id="s") == []
    assert restarted.get_session_desktop_binding(user_id="u", session_id="s").status == "stale"
    assert restarted.save_session_desktop_binding(link).status == "stale"
    with pytest.raises(DomainRequestError): restarted.save_candidate(q)
    assert restarted.compare_and_save_candidate(replace(q, answer_task_id="late"), expected=q) is None
    assert client.get(a._snapshot_key) == old
    marker_ttl = client.ttl(a._cn_controls.keys[7])
    retired_ttl = client.ttl(a._cn_controls.retired)
    assert (marker_ttl == -1 and retired_ttl == -1) if legacy_ttl is None else min(marker_ttl, retired_ttl) >= 448
    # Permanent compatibility guards contain metadata only; content keeps runtime TTL.
    assert 0 < client.ttl(a._binding_entity_key) <= 300


def test_clear_is_idempotent_and_keeps_account_history_and_other_sessions(pair):
    a, b, _, _ = pair
    account = a.save_account_desktop_device(AccountDesktopDeviceRecord("u", "d", "123456", 1, 20))
    a.save_session_desktop_binding(binding())
    a.save_candidate(candidate())
    q2 = b.save_candidate(candidate("q2", session="new"))
    assert a.clear_session_runtime(session_id="s")["cleared_candidates"] == 1
    assert a.clear_session_runtime(session_id="s")["cleared_candidates"] == 0
    assert b.get_candidate("q2") == q2
    assert b.get_account_desktop_device(user_id="u", device_id="d") == account
    assert b.save_session_desktop_binding(binding(session="restart")).status == "bound"


def test_slow_candidate_network_does_not_hold_process_runtime_lock(pair, monkeypatch):
    a, _, _, _ = pair
    entered, finish = threading.Event(), threading.Event()
    original = a._cn_controls.call
    def slow(op, *args):
        if op == "candidate":
            entered.set()
            assert finish.wait(timeout=3)
        return original(op, *args)
    monkeypatch.setattr(a._cn_controls, "call", slow)
    with ThreadPoolExecutor(1) as worker:
        future = worker.submit(a.save_candidate, candidate())
        assert entered.wait(timeout=2)
        assert a._runtime_lock.acquire(timeout=.1)
        a._runtime_lock.release()
        finish.set()
        assert future.result(timeout=3).candidate_id == "q"


def test_retired_heartbeat_and_claim_cannot_recreate_active_page(pair):
    a, b, _, _ = pair
    heartbeat = WebSessionHeartbeatRecord("s", "u", "live", 10, page_instance_id="page", lease_expires_at_ms=100)
    assert a.claim_live_web_session(heartbeat).lease_generation == 1
    assert b.claim_live_web_session(replace(heartbeat, page_instance_id="new")).lease_generation == 2
    a.clear_session_runtime(session_id="s")
    with pytest.raises(DomainRequestError): b.claim_live_web_session(heartbeat)
    assert b.get_active_live_web_session(user_id="u") is None
    assert b.get_web_session_heartbeat(user_id="u", session_id="s") is None


def test_global_keeps_original_snapshot_path(pair):
    _, _, client, settings = pair
    global_repo = RedisRealtimeSpeechRepository(settings.model_copy(update={"product_edition": "cn"}))
    global_repo.save_candidate(candidate())
    assert json.loads(client.get(global_repo._snapshot_key))["candidates"][0]["candidate_id"] == "q"
    assert global_repo.operational_diagnostics()["globalSnapshotWriteCount"] == 1


def test_atomic_activity_across_instances_and_old_stream_cursor(pair):
    a, b, client, _ = pair
    client.xadd("offersteady:realtime:events:s", {"cursor": 41, "event": "{}"})
    q = a.save_candidate(candidate())
    assert a.get_session_activity_version(session_id="s") == 42
    b.save_event(RealtimeEvent("e", "s", "u", "connection-state", {}, 20))
    assert a.get_session_activity_version(session_id="s") == 43
    a.save_candidate(replace(q, updated_at_ms=21))
    assert b.get_session_activity_version(session_id="s") == 44
    transcript = TranscriptSegmentRecord("t", "s", "u", "mic", "microphone", "candidate", 1,
                                         "Synthetic", .9, 1, 2, False, False, 2)
    b.save_transcript(transcript)
    assert a.get_session_activity_version(session_id="s") == 45
    a.clear_session_runtime(session_id="s")
    late = RealtimeEvent("late", "s", "u", "connection-state", {}, 22)
    assert b.save_event(late) == late
    with pytest.raises(DomainRequestError): b.save_transcript(transcript)
    assert not client.exists("offersteady:realtime:events:s")


def test_seed_preserves_legacy_activity_and_missing_binding_index(pair):
    a, _, client, settings = pair
    client.flushdb()
    link = binding()
    client.set(a._snapshot_key, json.dumps({"bindings": [asdict(link)], "activity": {"s": 70}}), ex=300)
    a = RedisRealtimeSpeechRepository(settings)
    a.save_candidate(candidate())
    assert a.get_session_activity_version(session_id="s") == 71
    client.delete(a._latest_binding_code_key, a._latest_binding_device_key)
    restarted = RedisRealtimeSpeechRepository(settings)
    assert restarted.get_latest_session_desktop_binding_by_code(manual_code="123456") == link


def test_removed_candidate_session_index_does_not_defeat_clear(pair):
    a, _, client, _ = pair
    a.save_candidate(candidate())
    client.delete(f"{a._snapshot_key}:candidates:s")
    a.clear_session_runtime(session_id="s")
    assert client.hget(a._cn_controls.candidates, "q") is None


def test_binding_replaced_device_does_not_leave_authoritative_old_index(pair):
    a, b, _, _ = pair
    old = a.save_session_desktop_binding(binding())
    new = b.save_session_desktop_binding(replace(old, device_id="other", manual_code="654321", bound_at_ms=20))
    assert a.get_latest_session_desktop_binding_for_device(device_id="d", manual_code="123456") is None
    assert a.get_latest_session_desktop_binding_by_code(manual_code="654321") == new


def test_seed_and_clear_race_cannot_resurrect_legacy_candidate(pair):
    a, _, client, settings = pair
    client.flushdb()
    client.set(a._snapshot_key, json.dumps({"candidates": [asdict(candidate())]}), ex=300)
    a = RedisRealtimeSpeechRepository(settings)
    barrier = threading.Barrier(2)
    def reload():
        barrier.wait(timeout=2)
        return RedisRealtimeSpeechRepository(settings)
    def clear():
        barrier.wait(timeout=2)
        return a.clear_session_runtime(session_id="s")
    with ThreadPoolExecutor(2) as workers:
        futures = [workers.submit(reload), workers.submit(clear)]
        [f.result(timeout=3) for f in futures]
    final = RedisRealtimeSpeechRepository(settings)
    assert final.get_candidate("q") is None
    assert final.list_candidates_for_session(session_id="s") == []


def test_candidate_failed_io_is_not_applied_to_memory_or_retried(pair, monkeypatch):
    a, _, _, _ = pair
    calls = []
    def fail(*args):
        calls.append(args[0])
        raise ConnectionError("synthetic failure")
    monkeypatch.setattr(a._cn_controls, "call", fail)
    with pytest.raises(ConnectionError): a.save_candidate(candidate())
    assert calls == ["candidate"]
    assert "q" not in a.candidates


def test_cn_network_commands_never_own_runtime_lock(pair, monkeypatch):
    a, _, _, _ = pair
    execute = a._redis.execute_command
    calls = []
    def checked(*args, **kwargs):
        assert not a._runtime_lock._is_owned()
        calls.append(args[0])
        return execute(*args, **kwargs)
    monkeypatch.setattr(a._redis, "execute_command", checked)
    a.save_candidate(candidate())
    a.get_candidate("q")
    a.save_session_desktop_binding(binding())
    a.get_latest_session_desktop_binding_by_code(manual_code="123456")
    a.claim_live_web_session(WebSessionHeartbeatRecord("s", "u", "live", 10, page_instance_id="page"))
    a.save_transcript(TranscriptSegmentRecord("t", "s", "u", "mic", "microphone", "candidate", 1,
                                            "Synthetic", .9, 1, 2, False, False, 2))
    a.save_event(RealtimeEvent("e", "s", "u", "connection-state", {}, 20))
    a.clear_session_runtime(session_id="s")
    assert len(calls) >= 15


def cas_service(*, edition="global", current=None, conflict=True):
    service = object.__new__(RealtimeSpeechService)
    service.settings = SimpleNamespace(product_edition=edition)
    service._auto_answer_claim_lock = threading.Lock()
    service._auto_answer_active_candidates = {}
    initial = current or candidate()
    service._require_candidate = lambda **kwargs: initial
    service.session_service = SimpleNamespace(get_session=lambda **kwargs: SimpleNamespace(
        status="live", auto_answer_enabled=True, auto_answer_enabled_at_ms=0))
    events, saves = [], []
    service._publish_candidate_state = events.append
    def cas(value, *, expected):
        saves.append(("cas", value, expected))
        return None if conflict else value
    service.repository = SimpleNamespace(compare_and_save_candidate=cas,
        save_candidate=lambda value: saves.append(("save", value)) or value,
        get_candidate=lambda candidate_id: replace(initial, answer_task_id="winner"))
    return service, events, saves


def test_service_claim_cas_conflict_preserves_claimed_error_without_event_or_retry():
    service, events, saves = cas_service()
    with pytest.raises(DomainRequestError) as error:
        service.claim_auto_answer_candidate(user_id="u", session_id="s", candidate_id="q")
    assert error.value.error_code == "auto_answer_candidate_claimed"
    assert len(saves) == 1
    assert events == [] and service._auto_answer_active_candidates == {}


def test_service_cas_conflicting_bind_and_release_never_publish_or_overwrite():
    service, events, saves = cas_service(current=replace(candidate(), answer_task_id="claim:old"))
    assert service.bind_auto_answer_candidate(user_id="u", candidate_id="q", claim_id="claim:old", task_id="task").answer_task_id == "winner"
    service.release_auto_answer_candidate(user_id="u", candidate_id="q", claim_id="claim:old")
    assert len(saves) == 2 and events == []


def test_global_candidate_service_never_uses_optional_cn_cas():
    service, events, saves = cas_service(edition="cn")
    result = service.claim_auto_answer_candidate(user_id="u", session_id="s", candidate_id="q")
    assert result.answer_task_id.startswith("claim:")
    assert len(saves) == 1 and saves[0][0] == "save"
    assert len(events) == 1


def test_binding_nested_empty_arrays_and_empty_candidate_sources_keep_wire_shape(pair):
    a, b, _, settings = pair
    caps = {"channels": [], "nested": {"items": []}}
    link = a.save_session_desktop_binding(replace(binding(), capabilities=caps))
    assert link.capabilities == caps
    assert b.get_latest_session_desktop_binding_by_code(manual_code="123456").capabilities == caps
    a.clear_session_runtime(session_id="s")
    restarted = RedisRealtimeSpeechRepository(settings)
    assert restarted.get_session_desktop_binding(user_id="u", session_id="s").capabilities == caps
    assert restarted.save_session_desktop_binding(link).capabilities == caps
    q = b.save_candidate(replace(candidate("empty", session="other"), source_segment_ids=[], confidence=0.12345678901234568))
    assert q.source_segment_ids == [] and a.get_candidate("empty").source_segment_ids == []
    assert q.confidence == 0.12345678901234568
    claimed = a.compare_and_save_candidate(replace(q, answer_task_id="claim:precision"), expected=q)
    assert claimed.confidence == q.confidence


def test_persistent_retired_device_status_preserves_event_response_after_restart(pair):
    a, _, client, settings = pair
    a.clear_session_runtime(session_id="s")
    restarted = RedisRealtimeSpeechRepository(settings)
    service = object.__new__(RealtimeSpeechService)
    service.settings = settings
    service.repository = restarted
    service.session_service = SimpleNamespace(get_session=lambda **kwargs: SimpleNamespace(owner_user_id="u", status="ended"))
    service._frame_worker_lock = threading.Lock()
    service._retired_session_ids = set()  # Restart has no local retired cache.
    response = service.publish_device_status(user_id="u", session_id="s", device_id="d",
        capture_state="stopped", source_health=[], capabilities={})
    assert response.kind == "device-status" and response.payload["deviceId"] == "d"
    assert not client.exists("offersteady:realtime:events:s")
    assert restarted.get_session_activity_version(session_id="s") == 0
    assert restarted.operational_diagnostics()["xaddCount"] == 0


def test_expired_scoped_candidate_is_missing_instead_of_revived_from_global_or_legacy(pair):
    a, _, client, settings = pair
    client.flushdb()
    client.set(a._snapshot_key, json.dumps({"candidates": [asdict(candidate())]}))
    a = RedisRealtimeSpeechRepository(settings)
    client.delete(f"{a._snapshot_key}:candidates:s")
    restarted = RedisRealtimeSpeechRepository(settings)
    assert restarted.get_candidate("q") is None
    assert restarted.list_candidates_for_session(session_id="s") == []


def test_warm_writes_use_one_evalsha_and_script_cache_miss_executes_business_once(pair, monkeypatch):
    a, _, client, _ = pair
    execute = a._redis.execute_command
    commands = []
    def observed(*args, **kwargs):
        commands.append(args[0])
        return execute(*args, **kwargs)
    monkeypatch.setattr(a._redis, "execute_command", observed)
    a.save_candidate(candidate())
    assert commands == ["EVALSHA"]
    commands.clear()
    client.script_flush()  # This fixture owns this private server, no other clients.
    a.save_candidate(replace(candidate(), updated_at_ms=11))
    assert commands == ["EVALSHA", "SCRIPT LOAD", "EVALSHA"]
    assert a.get_session_activity_version(session_id="s") == 2


def test_empty_page_instance_does_not_create_active_live_claim(pair):
    a, b, _, _ = pair
    a.save_web_session_heartbeat(WebSessionHeartbeatRecord("s", "u", "live", 10, page_instance_id=""))
    assert b.get_active_live_web_session(user_id="u") is None


def test_active_session_keeps_original_shared_runtime_lifetime_without_changing_freshness(pair):
    a, b, client, _ = pair
    q = a.save_candidate(candidate())
    link = a.save_session_desktop_binding(binding())
    account = a.save_account_desktop_device(AccountDesktopDeviceRecord("u", "d", "123456", 1, 20))
    keys = [a._cn_controls.candidates, f"{a._snapshot_key}:candidates:s", a._binding_entity_key, a._cn_controls.accounts]
    for key in keys: client.expire(key, 1)
    a.save_web_session_heartbeat(WebSessionHeartbeatRecord("s", "u", "live", 10, page_instance_id="page"))
    assert all(client.ttl(key) >= 298 for key in keys)
    assert b.get_candidate("q") == q
    assert b.get_session_desktop_binding(user_id="u", session_id="s") == link
    assert b.get_account_desktop_device(user_id="u", device_id="d") == account


def test_other_session_activity_cannot_outlive_retirement_guard_or_revive_bound_record(pair):
    a, b, client, settings = pair
    caps = {"channels": [], "nested": {"items": []}}
    a.save_session_desktop_binding(replace(binding(), capabilities=caps))
    a.clear_session_runtime(session_id="s")
    for key in (a._binding_entity_key, a._cn_controls.retired, a._cn_controls.keys[7], a._cn_controls.keys[8]):
        client.expire(key, 1)
    b.save_web_session_heartbeat(WebSessionHeartbeatRecord("other-session", "other-user", "live", 30, page_instance_id="other-page"))
    time.sleep(1.05)
    assert client.ttl(a._cn_controls.retired) >= 297
    restarted = RedisRealtimeSpeechRepository(settings)
    stale = restarted.get_session_desktop_binding(user_id="u", session_id="s")
    assert stale.status == "stale" and stale.capabilities == caps
    # The canonical record itself is stale even if guard metadata is lost.
    client.delete(a._cn_controls.retired)
    again = RedisRealtimeSpeechRepository(settings)
    assert again.get_session_desktop_binding(user_id="u", session_id="s").status == "stale"
    assert again.get_latest_session_desktop_binding_by_code(manual_code="123456").status == "stale"


def test_legacy_binding_keys_stay_byte_identical_and_old_protocol_decodable(pair):
    a, _, client, settings = pair
    client.flushdb()
    old = binding()
    newer = replace(old, binding_generation=2, capabilities={"channels": [], "nested": {"items": []}})
    base = a._snapshot_key
    snapshot = json.dumps({"bindings": [asdict(old)]})
    raw = json.dumps(asdict(newer))
    old_keys = {f"{base}:entities:bindings:v1": {"u|s": raw},
                f"{base}:indexes:binding-devices:v1": {"d|123456": raw},
                f"{base}:indexes:binding-codes:v1": {"123456": raw}}
    client.set(base, snapshot, ex=300)
    for key, mapping in old_keys.items(): client.hset(key, mapping=mapping)
    a = RedisRealtimeSpeechRepository(settings)
    assert a.get_session_desktop_binding(user_id="u", session_id="s") == newer
    a.save_session_desktop_binding(replace(newer, last_seen_at_ms=25))
    a.clear_session_runtime(session_id="s")
    assert client.get(base) == snapshot
    assert client.ttl(a._cn_controls.keys[7]) == -1
    assert client.ttl(a._cn_controls.retired) == -1
    for key, expected in old_keys.items():
        assert client.hgetall(key) == expected
        assert all(SessionDesktopBindingRecord(**json.loads(value)) == newer for value in expected.values())


def test_binding_indexes_share_lifetime_and_missing_indexes_repair_once(pair):
    a, _, client, _ = pair
    link = a.save_session_desktop_binding(binding())
    for key in (a._binding_entity_key, a._latest_binding_code_key, a._latest_binding_device_key): client.expire(key, 1)
    a.save_web_session_heartbeat(WebSessionHeartbeatRecord("s", "u", "live", 30, page_instance_id="page"))
    assert min(client.ttl(key) for key in (a._binding_entity_key, a._latest_binding_code_key, a._latest_binding_device_key)) >= 298
    client.delete(a._latest_binding_code_key, a._latest_binding_device_key)
    def scans(): return client.info("commandstats").get("cmdstat_hvals", {}).get("calls", 0)
    before = scans()
    assert a.get_latest_session_desktop_binding_by_code(manual_code="123456") == link
    repaired = scans()
    assert repaired == before + 1
    assert a.get_latest_session_desktop_binding_by_code(manual_code="123456") == link
    assert a.get_latest_session_desktop_binding_for_device(device_id="d", manual_code="123456") == link
    assert scans() == repaired
