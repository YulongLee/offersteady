"""Pinned control reads: synthetic identities and an exclusively owned Redis."""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import Mock

import pytest
from redis.exceptions import ResponseError

from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository

from test_cn_control_state_reads import control_fixture, pairing
from test_cn_realtime_entity_state import binding, pair, redis_url


def pinned(repository, record=None, **changes):
    record = record or binding()
    arguments = {
        "device_id": record.device_id,
        "manual_code": record.manual_code,
        "session_id": record.session_id,
        "binding_id": record.binding_id,
    }
    arguments.update(changes)
    return repository.get_pinned_session_desktop_binding(**arguments)


def test_pinned_lookup_reads_the_exact_binding_across_instances(pair):
    first, second, _, _ = pair
    original = first.save_session_desktop_binding(binding())
    newer = first.save_session_desktop_binding(binding(session="newer", owner="another", at=20))
    assert second.get_latest_session_desktop_binding_by_code(manual_code="123456") == newer
    assert pinned(second, original) == original


@pytest.mark.parametrize("field,value", [
    ("device_id", "different-device"),
    ("manual_code", "654321"),
    ("session_id", "different-session"),
    ("binding_id", "different-binding"),
])
def test_pin_must_match_each_requested_identity(pair, field, value):
    first, second, _, _ = pair
    first.save_session_desktop_binding(binding())
    assert pinned(second, **{field: value}) is None


def test_missing_owner_index_is_a_miss_without_recovering_an_unproven_pin(pair):
    first, second, client, _ = pair
    record = first.save_session_desktop_binding(binding())
    client.hdel(first._cn_controls.keys[8], record.session_id)
    before = {key: client.dump(key) for key in first._cn_controls.keys}
    assert pinned(second, record) is None
    assert {key: client.dump(key) for key in first._cn_controls.keys} == before


@pytest.mark.parametrize("corruption", ["record-owner", "record-session", "owner-index"])
def test_inconsistent_owner_or_session_metadata_fails_closed(pair, corruption):
    first, second, client, _ = pair
    record = first.save_session_desktop_binding(binding())
    field = f"{record.owner_user_id}|{record.session_id}"
    if corruption == "record-owner":
        malformed = replace(record, owner_user_id="different-owner")
    elif corruption == "record-session":
        malformed = replace(record, session_id="different-session")
    else:
        client.hset(first._cn_controls.keys[8], record.session_id, "different-owner")
        field = f"different-owner|{record.session_id}"
        malformed = record
    client.hset(first._binding_entity_key, field, first._cn_controls.encode(malformed))
    with pytest.raises(ValueError, match="identity_mismatch"):
        pinned(second, record)


def test_invalid_stored_json_propagates_instead_of_becoming_a_cache_miss(pair):
    first, second, client, _ = pair
    record = first.save_session_desktop_binding(binding())
    client.hset(first._binding_entity_key, f"{record.owner_user_id}|{record.session_id}", "{")
    with pytest.raises((ValueError, ResponseError)):
        pinned(second, record)


@pytest.mark.parametrize("plain_record", [False, True])
def test_pinned_raw_json_preserves_precision_and_nested_wire_shapes(pair, plain_record):
    first, second, client, _ = pair
    capabilities = {
        "largeInteger": 2**53 + 1,
        "confidence": 0.12345678901234568,
        "channels": [],
        "nested": {"items": [], "enabled": True, "optional": None},
    }
    record = first.save_session_desktop_binding(replace(binding(), capabilities=capabilities))
    if plain_record:
        client.hset(first._binding_entity_key, f"{record.owner_user_id}|{record.session_id}",
                    first._cn_controls.encode(record))
    result = pinned(second, record)
    assert result == record
    assert result.capabilities == capabilities
    assert type(result.capabilities["largeInteger"]) is int
    assert type(result.capabilities["channels"]) is list
    assert type(result.capabilities["nested"]["items"]) is list


def test_pinned_reads_do_not_refresh_ttl_seed_indexes_or_activity(pair):
    first, second, client, _ = pair
    record = first.save_session_desktop_binding(binding())
    keys = [key for key in first._cn_controls.keys if client.exists(key)]
    for key in keys:
        client.pexpire(key, 8_000)
    before = {key: client.dump(key) for key in keys}
    lifetimes = {key: client.pttl(key) for key in keys}
    seed_count = second.operational_diagnostics()["entitySeedCount"]
    for _ in range(3):
        assert pinned(second, record) == record
    assert {key: client.dump(key) for key in keys} == before
    assert second.operational_diagnostics()["entitySeedCount"] == seed_count
    for key in keys:
        assert 0 < client.pttl(key) <= lifetimes[key]


def test_retirement_is_visible_to_other_instances_and_survives_late_save_and_restart(pair):
    first, second, _, settings = pair
    original = first.save_session_desktop_binding(binding())
    first.clear_session_runtime(session_id=original.session_id)
    expected = replace(original, status="stale")
    assert pinned(second, original) == expected
    first.save_session_desktop_binding(original)
    assert pinned(second, original) == expected
    restarted = RedisRealtimeSpeechRepository(settings)
    assert pinned(restarted, original) == expected


def install_fast_pin(fixture):
    def read(**arguments):
        return next((record for record in fixture.bindings
                     if record.session_id == arguments["session_id"]
                     and record.binding_id == arguments["binding_id"]
                     and record.device_id == arguments["device_id"]
                     and record.manual_code == arguments["manual_code"]), None)
    getter = Mock(side_effect=read)
    fixture.service.repository.get_pinned_session_desktop_binding = getter
    return getter


def forbid_full_binding_list(**_):
    raise AssertionError("CN exact pin must not scan all bindings")


def test_cn_service_uses_exact_pin_but_keeps_authoritative_projection(monkeypatch):
    fixture = control_fixture(monkeypatch)
    getter = install_fast_pin(fixture)
    fixture.service.repository.list_session_desktop_bindings_for_device = forbid_full_binding_list
    projection = Mock(wraps=fixture.repository.get_control_state)
    monkeypatch.setattr(fixture.repository, "get_control_state", projection)
    result = pairing(fixture, pinned=True)
    assert result["bound"] is True and result["bindingLockState"] == "held"
    assert result["binding"]["bindingId"] == fixture.binding.binding_id
    getter.assert_called_once_with(device_id=fixture.device.device_id,
                                   manual_code=fixture.device.manual_code,
                                   session_id=fixture.record.session_id,
                                   binding_id=fixture.binding.binding_id)
    projection.assert_called_once_with(fixture.record.session_id)
    fixture.documents.get_by_id.assert_not_called()


@pytest.mark.parametrize("condition", ["ended", "deleted", "generation", "heartbeat", "retired"])
def test_exact_pin_keeps_lifecycle_generation_and_freshness_guards(monkeypatch, condition):
    fixture = control_fixture(monkeypatch)
    install_fast_pin(fixture)
    fixture.service.repository.list_session_desktop_bindings_for_device = forbid_full_binding_list
    if condition == "ended":
        fixture.repository.save_session(replace(fixture.record, status="ended"))
    elif condition == "deleted":
        fixture.repository.delete_session(user_id=fixture.record.owner_user_id,
                                          session_id=fixture.record.session_id)
    elif condition == "generation":
        fixture.device_state[0] = replace(fixture.device, generation=fixture.device.generation + 1)
    elif condition == "heartbeat":
        fixture.device_state[0] = replace(fixture.device, last_seen_at_ms=0)
    else:
        fixture.bindings[0] = replace(fixture.binding, status="stale")
    result = pairing(fixture, pinned=True)
    assert result["bound"] is False and result["state"] == "stale-bound"
    assert result["bindingLockState"] == "released"
    fixture.documents.get_by_id.assert_not_called()


def test_live_old_pin_stays_held_until_authoritative_end_then_latest_wins(monkeypatch):
    fixture = control_fixture(monkeypatch)
    install_fast_pin(fixture)
    fixture.service.repository.list_session_desktop_bindings_for_device = forbid_full_binding_list
    newer = fixture.sessions.create_session(user_id="synthetic-new-owner", title="Synthetic newer")
    newer = replace(newer, status="live")
    fixture.repository.save_session(newer)
    fixture.bindings.append(replace(fixture.binding, binding_id="synthetic-new-binding",
                                    session_id=newer.session_id, owner_user_id=newer.owner_user_id))
    first = pairing(fixture, pinned=True)
    assert first["bindingLockState"] == "held"
    assert first["binding"]["sessionId"] == fixture.record.session_id
    fixture.repository.save_session(replace(fixture.record, status="ended"))
    fixture.service._invalidate_control_query_cache()
    result = pairing(fixture, pinned=True)
    assert result["bindingLockState"] == "released"
    assert result["binding"]["sessionId"] == newer.session_id


def test_end_between_pin_read_and_projection_cannot_reactivate_the_session(monkeypatch):
    fixture = control_fixture(monkeypatch)
    def end_before_return(**_):
        fixture.repository.save_session(replace(fixture.record, status="ended"))
        return fixture.binding
    fixture.service.repository.get_pinned_session_desktop_binding = end_before_return
    fixture.service.repository.list_session_desktop_bindings_for_device = forbid_full_binding_list
    result = pairing(fixture, pinned=True)
    assert result["bound"] is False and result["sessionStatus"] == "ended"


def test_fast_lookup_failure_propagates_without_scanning_or_latest_fallback(monkeypatch):
    fixture = control_fixture(monkeypatch)
    fixture.service.repository.get_pinned_session_desktop_binding = Mock(
        side_effect=ValueError("cn_runtime_entity_identity_mismatch"))
    fixture.service.repository.list_session_desktop_bindings_for_device = forbid_full_binding_list
    fixture.service.repository.get_latest_session_desktop_binding_by_code = Mock(
        side_effect=AssertionError("Corrupt metadata must not select another binding"))
    with pytest.raises(ValueError, match="identity_mismatch"):
        pairing(fixture, pinned=True)


@pytest.mark.parametrize("edition,optional_method", [("cn", True), ("global", False), ("global", None)])
def test_global_and_older_repositories_preserve_the_original_list_path(monkeypatch, edition, optional_method):
    fixture = control_fixture(monkeypatch)
    fixture.service.settings = fixture.service.settings.model_copy(update={"product_edition": edition})
    fixture.sessions.settings = fixture.service.settings
    old_list = Mock(wraps=fixture.service.repository.list_session_desktop_bindings_for_device)
    fixture.service.repository.list_session_desktop_bindings_for_device = old_list
    if optional_method:
        fixture.service.repository.get_pinned_session_desktop_binding = Mock(
            side_effect=AssertionError("Global must not enter the CN direct-pin path"))
    elif optional_method is None:
        fixture.service.repository.get_pinned_session_desktop_binding = None
    result = pairing(fixture, pinned=True)
    assert result["bound"] is True and result["bindingLockState"] == "held"
    old_list.assert_called_once_with(device_id=fixture.device.device_id, manual_code=fixture.device.manual_code)
