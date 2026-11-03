"""Synthetic new-entity gate tests; Redis/SQL/network are never contacted."""
from __future__ import annotations

from copy import deepcopy
import fnmatch
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


SPEC = importlib.util.spec_from_file_location("cn_entity_idle_gate_under_test", Path(__file__).with_name("cn_entity_idle_gate.py"))
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)
NOW = 5_000_000
OLD = NOW - 600_000
SETTINGS = SimpleNamespace(database_url="synthetic-private-database", redis_url="synthetic-private-redis")


def binding(**changes):
    return dict(binding_id="synthetic-binding", owner_user_id="synthetic-owner", session_id="synthetic-session",
                device_id="synthetic-device", manual_code="synthetic-code", display_name="private-display-name",
                capabilities={"channels": []}, bound_at_ms=OLD, last_seen_at_ms=OLD, status="bound", binding_generation=1) | changes


def candidate(**changes):
    return dict(candidate_id="synthetic-candidate", owner_user_id="synthetic-owner", session_id="synthetic-session",
                source_segment_ids=[], text="synthetic-private-question", state="confirmed", reason="synthetic-private-reason",
                confidence=.9, answer_task_id="synthetic-completed-task", created_at_ms=OLD, updated_at_ms=OLD) | changes


def raw(record, kind=None, **overrides):
    if kind:
        return json.dumps({"cn_" + kind + "_schema": 1, "record_json": json.dumps(record), "overrides": overrides})
    return json.dumps(record)


def state(*, with_binding=True, with_candidate=True, envelope=True, retired=False, scoped=True):
    values = {G.OWNERS: {"synthetic-session": "synthetic-owner"}, G.ACTIVITY: {"synthetic-session": "19"}}
    if with_binding:
        values[G.BINDINGS] = {"synthetic-owner|synthetic-session": raw(binding(), "binding" if envelope else None)}
    if with_candidate:
        encoded = raw(candidate(), "candidate" if envelope else None)
        values[G.CANDIDATES] = {"synthetic-candidate": encoded}
        if scoped:
            values[G.SCOPED_PREFIX + "synthetic-session"] = {"synthetic-candidate": encoded}
    if retired:
        values[G.RETIRED] = {"synthetic-session": "1"}
    return values


class FakeRedis:
    def __init__(self, values, *, mutate=None, failure=False):
        self.values = deepcopy(values)
        self.mutate = mutate
        self.failure = failure
        self.passes = 0
        self.closed = False
        self.commands = []

    def hscan_iter(self, key, *, count):
        self.commands.append(("HSCAN", key, count))
        if self.failure:
            raise RuntimeError("synthetic-private-connection-error")
        if key == G.BINDINGS:
            self.passes += 1
            if self.passes == 2 and self.mutate:
                self.mutate(self.values)
        yield from self.values.get(key, {}).items()

    def scan_iter(self, *, match, count):
        self.commands.append(("SCAN", match, count))
        yield from sorted(key for key in self.values if fnmatch.fnmatch(key, match))

    def close(self):
        self.closed = True

    def __getattr__(self, _):
        raise AssertionError("non-read command forbidden")


class Connection:
    def __init__(self, rows, statements):
        self.rows, self.statements = rows, statements

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        assert sql == G.SQL and sql.lstrip().startswith("SELECT")
        self.statements.append((sql, params))
        return SimpleNamespace(fetchall=lambda: self.rows)


def collect(values=None, *, status="ended", updated=OLD, deleted=None, rows=None, mutate=None, failure=False):
    client = FakeRedis(values or {}, mutate=mutate, failure=failure)
    statements, connection_options, redis_options = [], [], []

    def connect(url, **kwargs):
        assert url == SETTINGS.database_url
        assert kwargs == {"connect_timeout": 3, "options": "-c default_transaction_read_only=on -c statement_timeout=3000"}
        connection_options.append(kwargs)
        result = [("synthetic-session", "synthetic-owner", status, updated, deleted)] if rows is None else rows
        return Connection(result, statements)

    def redis_factory(url, **kwargs):
        assert url == SETTINGS.redis_url
        assert kwargs == {"decode_responses": True, "socket_timeout": 3, "socket_connect_timeout": 3}
        redis_options.append(kwargs)
        return client

    counts = G.collect_counts(SETTINGS, now_ms=NOW, connect=connect, redis_factory=redis_factory)
    assert client.closed
    assert set(counts) == set(G.PROTECTED) | set(G.INFORMATIONAL) | {"atMs"}
    assert all(type(value) is int and value >= 0 for value in counts.values())
    assert not any(word in json.dumps(counts) for word in ("synthetic", "private", "redis://"))
    return counts, client, statements


def test_absent_new_entities_are_idle_without_database_or_repository_instantiation():
    counts, client, statements = collect()
    assert not G.blocked(counts)
    assert counts["scannedCnEntityRecords"] == 0
    assert not statements and client.passes == 2
    assert {command[0] for command in client.commands} == {"HSCAN", "SCAN"}


@pytest.mark.parametrize("envelope", [False, True])
@pytest.mark.parametrize("status,updated,deleted", [("ended", OLD, None), ("preparing", OLD, None), ("ended", OLD, NOW)])
def test_retained_historical_records_do_not_permanently_block(envelope, status, updated, deleted):
    counts, _, statements = collect(state(envelope=envelope), status=status, updated=updated, deleted=deleted)
    assert not G.blocked(counts)
    assert counts["cnBoundBindings"] == counts["cnCandidates"] == 1
    assert counts["cnHistoricalEntities"] == 2
    assert len(statements) == 1
    assert statements[0][1] == (["synthetic-session"],)


@pytest.mark.parametrize("status,updated", [("live", OLD), ("preparing", NOW)])
def test_active_cn_binding_and_candidates_block_without_legacy_keys(status, updated):
    counts, _, _ = collect(state(), status=status, updated=updated)
    assert G.blocked(counts)
    assert counts["activeCnBindings"] == counts["activeCnCandidates"] == 1


def test_stale_binding_for_live_session_still_blocks():
    values = state(with_candidate=False)
    values[G.BINDINGS]["synthetic-owner|synthetic-session"] = raw(binding(), "binding", status="stale")
    counts, _, _ = collect(values, status="live")
    assert counts["cnStaleBindings"] == counts["activeCnBindings"] == 1
    assert G.blocked(counts)


@pytest.mark.parametrize("scoped_only", [False, True])
def test_unretired_claim_blocks_even_without_live_sql_or_legacy_tasks(scoped_only):
    values = state(with_binding=False)
    encoded = raw(candidate(), "candidate", answer_task_id="claim:synthetic-claim")
    values[G.CANDIDATES]["synthetic-candidate"] = encoded
    values[G.SCOPED_PREFIX + "synthetic-session"]["synthetic-candidate"] = encoded
    if scoped_only:
        del values[G.CANDIDATES]
    counts, _, _ = collect(values, status="preparing")
    assert counts["pendingCnCandidateClaims"] == 1
    assert G.blocked(counts)


def test_retired_claim_and_binding_cannot_be_considered_live_after_clear():
    values = state(retired=True)
    encoded = raw(candidate(answer_task_id="claim:synthetic-retired-claim"), "candidate")
    values[G.CANDIDATES]["synthetic-candidate"] = encoded
    values[G.SCOPED_PREFIX + "synthetic-session"]["synthetic-candidate"] = encoded
    counts, _, _ = collect(values)
    assert not G.blocked(counts)
    assert counts["cnRetiredBindings"] == counts["cnRetiredCandidates"] == 1


def test_expired_scope_global_only_old_claim_is_unreadable_history_not_permanent_gate():
    values = state(with_binding=False, scoped=False)
    values[G.CANDIDATES]["synthetic-candidate"] = raw(candidate(answer_task_id="claim:synthetic-expired-scope"), "candidate")
    counts, _, _ = collect(values, status="preparing")
    assert counts["cnCandidates"] == 1
    assert counts["pendingCnCandidateClaims"] == counts["activeCnCandidates"] == 0
    assert not G.blocked(counts)


@pytest.mark.parametrize("kind", ["binding", "candidate"])
def test_recent_mutation_on_old_preparing_or_missing_session_blocks(kind):
    values = state(with_binding=kind == "binding", with_candidate=kind == "candidate", scoped=False)
    key = G.BINDINGS if kind == "binding" else G.CANDIDATES
    field = next(iter(values[key]))
    values[key][field] = raw(binding(last_seen_at_ms=NOW) if kind == "binding" else candidate(updated_at_ms=NOW), kind)
    counts, _, _ = collect(values, rows=[])
    assert counts["recentCnEntityWrites"] == 1
    assert G.blocked(counts)


@pytest.mark.parametrize("change", ["revision", "new-binding", "new-scope", "retirement", "delete"])
def test_observed_late_writer_or_cleanup_mutation_blocks(change):
    def mutate(values):
        if change == "revision":
            values[G.ACTIVITY]["synthetic-session"] = "20"
        elif change == "new-binding":
            values[G.BINDINGS]["synthetic-other-owner|synthetic-other-session"] = raw(binding(owner_user_id="synthetic-other-owner", session_id="synthetic-other-session"))
        elif change == "new-scope":
            values[G.SCOPED_PREFIX + "synthetic-other-session"] = {"synthetic-other-candidate": raw(candidate(candidate_id="synthetic-other-candidate", session_id="synthetic-other-session"))}
        elif change == "retirement":
            values[G.RETIRED] = {"synthetic-session": "1"}
        else:
            values.pop(G.CANDIDATES)
    counts, _, _ = collect(state(), mutate=mutate)
    assert counts["cnEntityMutationDetected"] == 1
    assert G.blocked(counts)


@pytest.mark.parametrize("change", ["owner", "owner-missing", "field", "scope", "invalid-json", "future-schema", "override", "candidate-state", "claim-type", "activity", "retirement"])
def test_unknown_malformed_and_owner_conflicts_fail_closed(change):
    values = state()
    if change == "owner":
        values[G.OWNERS]["synthetic-session"] = "synthetic-wrong-owner"
    elif change == "owner-missing":
        del values[G.OWNERS]
    elif change == "field":
        values[G.BINDINGS] = {"synthetic-wrong-field": raw(binding())}
    elif change == "scope":
        values[G.SCOPED_PREFIX + "synthetic-wrong-session"] = values.pop(G.SCOPED_PREFIX + "synthetic-session")
    elif change == "invalid-json":
        values[G.BINDINGS]["synthetic-owner|synthetic-session"] = "synthetic-private-invalid-json"
    elif change == "future-schema":
        values[G.BINDINGS]["synthetic-owner|synthetic-session"] = json.dumps({"cn_binding_schema": 2, "record_json": json.dumps(binding()), "overrides": {}})
    elif change == "override":
        values[G.BINDINGS]["synthetic-owner|synthetic-session"] = raw(binding(), "binding", owner_user_id="synthetic-other-owner")
    elif change in {"candidate-state", "claim-type"}:
        values[G.CANDIDATES]["synthetic-candidate"] = raw(candidate(state="unknown") if change == "candidate-state" else candidate(answer_task_id=1))
    elif change == "activity":
        values[G.ACTIVITY]["synthetic-session"] = "NaN"
    else:
        values[G.RETIRED] = {"synthetic-session": "maybe"}
    counts, _, _ = collect(values)
    assert counts["invalidCnEntityMetadata"] >= 1
    assert G.blocked(counts)


@pytest.mark.parametrize("rows", [
    [("synthetic-session", "synthetic-other-owner", "ended", OLD, None)],
    [("synthetic-session", "synthetic-owner", "ended", True, None)],
    [("synthetic-session", "synthetic-owner", "ended", OLD)],
])
def test_invalid_readonly_sql_projection_fails_closed(rows):
    counts, _, _ = collect(state(), rows=rows)
    assert counts["invalidCnEntityMetadata"] == 1
    assert G.blocked(counts)


def test_unknown_sql_status_and_retirement_live_conflict_fail_closed():
    counts, _, _ = collect(state(), status="unknown-private-status")
    assert counts["unknownCnSessionStates"] > 0 and G.blocked(counts)
    counts, _, _ = collect(state(retired=True), status="live")
    assert counts["invalidCnEntityMetadata"] == 1 and G.blocked(counts)


def test_connection_failure_and_scan_limit_are_fixed_counts(monkeypatch):
    counts, _, _ = collect(state(), failure=True)
    assert counts["cnEntityReadFailures"] == 1 and G.blocked(counts)
    monkeypatch.setattr(G, "MAX_RECORDS", 1)
    counts, _, _ = collect(state())
    assert counts["cnEntityScanLimitExceeded"] == 1 and G.blocked(counts)


@pytest.mark.parametrize("bad", [{}, {name: False for name in G.PROTECTED}, {name: 0 for name in G.PROTECTED} | {G.PROTECTED[0]: -1}])
def test_absent_boolean_and_invalid_aggregate_fields_are_not_idle(bad):
    assert G.blocked(bad)


def test_main_prints_only_fixed_counts_and_correct_failure_exit():
    expected, _, _ = collect(state(), failure=True)
    output = io.StringIO()
    with patch("app.core.config.get_settings", return_value=SETTINGS), patch.object(G, "collect_counts", return_value=expected), patch("sys.stdout", output):
        with pytest.raises(SystemExit) as stopped:
            G.main()
    assert stopped.value.code == 75
    assert json.loads(output.getvalue()) == expected
    assert "synthetic" not in output.getvalue()
