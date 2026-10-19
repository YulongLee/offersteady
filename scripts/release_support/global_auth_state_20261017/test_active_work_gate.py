"""Synthetic read-only gate regressions; no real services or user data."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


PATH = Path(__file__).with_name("active_work_gate.py")
spec = importlib.util.spec_from_file_location("synthetic_active_work_gate", PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
NOW = 1_000_000_000
PRIVATE = "SYNTHETIC_PRIVATE_METADATA"


class Database:
    def __init__(self, values=None, bad_row=None):
        self.values = values or {}
        self.bad_row = bad_row
        self.row = None
        self.calls = []

    def connect(self, url, **kwargs):
        assert "default_transaction_read_only=on" in kwargs["options"]
        assert "statement_timeout=3000" in kwargs["options"]
        assert kwargs["connect_timeout"] == 3
        self.calls.append("CONNECT")
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, sql, parameters=None):
        assert sql.lstrip().startswith("SELECT")
        assert all(word not in sql.upper() for word in ("UPDATE ", "DELETE ", "INSERT ", "ALTER "))
        self.calls.append("SELECT")
        if sql == gate.MATERIAL_TASK_SQL:
            assert parameters == (NOW-86_400_000, NOW-86_400_000)
            self.row = (self.values.get("activeMaterialTasks", 0), self.values.get("ignoredLegacyFailedQueuedTasks", 0))
        else:
            fields = [field for table, field in gate.MATERIAL_TABLES if sql == gate.MATERIAL_JOB_SQL.format(table)]
            assert len(fields) == 1 and parameters is None
            self.row = (self.values.get(fields[0], 0), self.values.get("unknownMaterialJobStatuses", 0))
        return self

    def fetchone(self):
        return self.bad_row if self.bad_row is not None else self.row


class Redis:
    def __init__(self, *, publishers=(), receipts=(), entities=(), receipt_entities=(), requests=None, raw_snapshot=None):
        self.snapshot = raw_snapshot if raw_snapshot is not None else json.dumps({"publishers": list(publishers), "receipts": list(receipts)})
        self.hashes = {gate.PUBLISHERS: list(entities), gate.RECEIPTS: list(receipt_entities)}
        self.requests = requests or {}
        self.calls = []

    def factory(self, url, **kwargs):
        assert kwargs == {"decode_responses": True, "socket_timeout": 3, "socket_connect_timeout": 3}
        return self

    def get(self, key):
        self.calls.append("GET")
        return self.snapshot if key == gate.SNAPSHOT else self.requests.get(key)

    def hscan_iter(self, key, **_kwargs):
        self.calls.append("HSCAN")
        return iter((str(index), json.dumps(value)) for index, value in enumerate(self.hashes[key]))

    def scan_iter(self, **kwargs):
        self.calls.append("SCAN")
        assert kwargs == {"match": gate.CAPTURE_REQUESTS, "count": 100}
        return iter(self.requests)

    def close(self):
        self.calls.append("CLOSE")


def publisher(**changes):
    return {"publisher_id": PRIVATE, "session_id": PRIVATE, "status": "connected", "connected_at_ms": NOW-100,
            "disconnected_at_ms": None, "expires_at_ms": NOW+100, **changes}


def receipt(**changes):
    return {"session_id": PRIVATE, "source_kind": "system", "source_id": PRIVATE, "asr_status": "accepted",
            "received_at_ms": NOW, "frame_count": 1, **changes}


def collect(*, database_values=None, **redis_values):
    database = Database(database_values)
    runtime = Redis(**redis_values)
    counts = gate.collect_counts(SimpleNamespace(database_url=PRIVATE, redis_url=PRIVATE), now_ms=NOW,
                                 connect=database.connect, redis_factory=runtime.factory)
    assert PRIVATE not in json.dumps(counts)
    assert database.calls == ["CONNECT", "SELECT", "SELECT", "SELECT", "SELECT"]
    assert set(runtime.calls) <= {"GET", "HSCAN", "SCAN", "CLOSE"}
    assert runtime.calls[-1] == "CLOSE"
    return counts


def test_empty_runtime_is_idle_and_only_aggregates_are_returned():
    counts = collect()
    assert not gate.blocked(counts)
    assert all(type(value) is int and value == 0 for value in counts.values())


@pytest.mark.parametrize("field", gate.PROTECTED)
def test_any_protected_count_blocks_and_missing_count_fails_closed(field):
    counts = dict.fromkeys(gate.PROTECTED, 0)
    counts[field] = 1
    assert gate.blocked(counts)
    counts.pop(field)
    assert gate.blocked(counts)


@pytest.mark.parametrize("status", sorted(gate.PUBLISHER_ACTIVE))
def test_connected_publishers_block_even_after_connection_token_expiry(status):
    counts = collect(entities=[publisher(status=status, expires_at_ms=NOW-86_400_000)])
    assert counts["connectedDesktopPublishers"] == 1
    assert gate.blocked(counts)


@pytest.mark.parametrize("status", sorted(gate.PUBLISHER_TERMINAL))
def test_terminal_entity_publisher_overrides_connected_legacy_snapshot(status):
    counts = collect(publishers=[publisher()], entities=[publisher(status=status, disconnected_at_ms=NOW)])
    assert not gate.blocked(counts)


def test_new_unconnected_valid_token_blocks_but_expired_unconnected_token_does_not():
    counts = collect(entities=[publisher(connected_at_ms=None)])
    assert counts["availablePublisherTokens"] == 1 and gate.blocked(counts)
    assert not gate.blocked(collect(entities=[publisher(connected_at_ms=None, expires_at_ms=NOW-1)]))


@pytest.mark.parametrize("status", sorted(gate.PUBLISHER_ACTIVE - {"connected"}))
def test_legacy_http_working_publishers_block_without_connection_timestamp_or_valid_token(status):
    counts = collect(entities=[publisher(status=status, connected_at_ms=None, expires_at_ms=NOW-1)])
    assert counts["workingDesktopPublishers"] == 1
    assert gate.blocked(counts)


@pytest.mark.parametrize("changes", [{"status": PRIVATE}, {"status": None}, {"expires_at_ms": None},
                                    {"expires_at_ms": True}, {"connected_at_ms": []}, {"publisher_id": None}])
def test_invalid_publisher_metadata_fails_closed_without_echoing_values(changes):
    assert gate.blocked(collect(entities=[publisher(**changes)]))


@pytest.mark.parametrize("storage", ["receipts", "receipt_entities"])
@pytest.mark.parametrize("status", ["pending", "accepted"])
def test_recent_audio_in_legacy_or_entity_storage_blocks(storage, status):
    counts = collect(**{storage: [receipt(asr_status=status, received_at_ms=NOW-30_000)]})
    assert counts["recentAudioTracks"] == 1 and gate.blocked(counts)


def test_duplicate_audio_storage_is_counted_once_and_expired_or_failed_audio_does_not_block():
    item = receipt()
    assert collect(receipts=[item], receipt_entities=[item])["recentAudioTracks"] == 1
    assert not gate.blocked(collect(receipt_entities=[receipt(received_at_ms=NOW-30_001)]))
    assert not gate.blocked(collect(receipts=[receipt(asr_status="failed")]))


@pytest.mark.parametrize("changes", [{"asr_status": PRIVATE}, {"received_at_ms": None}, {"frame_count": []},
                                    {"source_id": None}])
def test_malformed_receipts_fail_closed(changes):
    assert gate.blocked(collect(receipt_entities=[receipt(**changes)]))


@pytest.mark.parametrize("status", sorted(gate.CAPTURE_ACTIVE))
def test_pending_remote_capture_request_blocks_even_without_answer_task(status):
    counts = collect(requests={PRIVATE: json.dumps({"status": status})})
    assert counts["unfinishedRemoteCaptures"] == 1 and gate.blocked(counts)


@pytest.mark.parametrize("status", sorted(gate.CAPTURE_TERMINAL))
def test_terminal_remote_capture_request_does_not_block(status):
    assert not gate.blocked(collect(requests={PRIVATE: json.dumps({"status": status})}))


@pytest.mark.parametrize("raw", ["[]", "null", PRIVATE, json.dumps({"status": PRIVATE})])
def test_unknown_remote_capture_metadata_fails_closed(raw):
    assert gate.blocked(collect(requests={PRIVATE: raw}))


@pytest.mark.parametrize("field", ["materialProcessingJobs", "materialDeletionJobs", "materialReconcileJobs",
                                  "unknownMaterialJobStatuses", "activeMaterialTasks"])
def test_each_durable_material_activity_blocks(field):
    assert gate.blocked(collect(database_values={field: 1}))


def test_legacy_queued_task_with_old_failed_durable_job_is_reported_but_not_mutated_or_blocked():
    counts = collect(database_values={"ignoredLegacyFailedQueuedTasks": 4})
    assert counts["ignoredLegacyFailedQueuedTasks"] == 4
    assert not gate.blocked(counts)
    assert "related_task_id=t.task_id" in gate.MATERIAL_TASK_SQL
    assert "j.status='failed'" in gate.MATERIAL_TASK_SQL
    assert "current_stage IS NULL" in gate.MATERIAL_TASK_SQL


@pytest.mark.parametrize("raw", ["[]", "null", PRIVATE, '{"publishers":{}}', '{"receipts":{}}'])
def test_invalid_snapshot_fails_closed(raw):
    assert gate.blocked(collect(raw_snapshot=raw))


def test_scan_budget_failure_is_safe_and_closes_redis(monkeypatch):
    monkeypatch.setattr(gate, "MAX_RECORDS", 1)
    runtime = Redis(entities=[publisher()])
    with pytest.raises(ValueError, match="scan limit"):
        gate.collect_counts(SimpleNamespace(database_url=PRIVATE, redis_url=PRIVATE), now_ms=NOW,
                            connect=Database().connect, redis_factory=runtime.factory)
    assert runtime.calls[-1] == "CLOSE"


@pytest.mark.parametrize("bad_row", [(0,), (0, -1), (False, 0)])
def test_bad_aggregate_shapes_fail_closed(bad_row):
    with pytest.raises(ValueError, match="aggregate shape"):
        gate.collect_counts(SimpleNamespace(database_url=PRIVATE, redis_url=PRIVATE), now_ms=NOW,
                            connect=Database(bad_row=bad_row).connect, redis_factory=Redis().factory)


def test_main_catches_read_failure_and_prints_only_safe_count(monkeypatch, capsys):
    def failed(*_args, **_kwargs):
        raise RuntimeError(PRIVATE)
    monkeypatch.setattr(gate, "collect_counts", failed)
    with pytest.raises(SystemExit) as result:
        gate.main()
    assert result.value.code == 75
    output = capsys.readouterr()
    assert json.loads(output.out) == {"metadataReadFailures": 1}
    assert PRIVATE not in output.out + output.err


def test_gate_uses_only_explicit_read_commands_and_never_constructs_business_repositories():
    source = PATH.read_text()
    tree = ast.parse(source)
    calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
             and node.func.value.id in {"connection", "client"}}
    assert calls == {"execute", "get", "hscan_iter", "scan_iter", "close"}
    assert "count(*)" in gate.MATERIAL_TASK_SQL and "count(*)" in gate.MATERIAL_JOB_SQL
    assert "default_transaction_read_only=on" in source
    assert "ensure_tables" not in source and "app.deps" not in source
    assert "mock_interview_repository" not in source
