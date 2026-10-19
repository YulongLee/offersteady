"""Synthetic metadata only; the gate must never mutate repositories or Redis."""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


PATH = Path(__file__).with_name("extra_idle_gate.py")
spec = importlib.util.spec_from_file_location("synthetic_extra_idle_gate", PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
NOW = 1_000_000
PRIVATE = "SYNTHETIC_PRIVATE_METADATA"


class Database:
    def __init__(self, values):
        self.row = tuple(values.get(field, 0) for field in gate.MOCK_FIELDS)
        self.calls = []

    def __call__(self, url, **kwargs):
        assert "default_transaction_read_only=on" in kwargs["options"]
        assert "statement_timeout=3000" in kwargs["options"]
        self.calls.append(("connect", url, kwargs))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, sql, parameters):
        assert sql.lstrip().startswith("SELECT")
        assert parameters == (NOW-120000, NOW, NOW-120000, NOW, NOW-120000, NOW, NOW)
        self.calls.append(("SELECT",))
        return self

    def fetchone(self):
        return self.row


class Redis:
    def __init__(self, *, heartbeats=(), entities=(), tasks=None, raw_snapshot=None):
        self.snapshot = raw_snapshot if raw_snapshot is not None else json.dumps({"heartbeats": list(heartbeats)})
        self.entities = list(entities)
        self.tasks = tasks or {}
        self.calls = []

    def factory(self, *_args, **_kwargs):
        return self

    def get(self, key):
        self.calls.append("GET")
        return self.snapshot if key == "offersteady:realtime:runtime:v2" else self.tasks.get(key)

    def hscan_iter(self, key, **_kwargs):
        self.calls.append("HSCAN")
        return iter((str(index), json.dumps(value)) for index, value in enumerate(self.entities))

    def close(self):
        self.calls.append("CLOSE")

    def scan_iter(self, *, match, **_kwargs):
        self.calls.append("SCAN")
        return iter(key for key in self.tasks if key.startswith(match[:-1]))


def collect(*, database_values=None, **redis_values):
    database = Database(database_values or {})
    redis = Redis(**redis_values)
    result = gate.collect_counts(SimpleNamespace(database_url=PRIVATE, redis_url=PRIVATE), now_ms=NOW,
                                 connect=database, redis_factory=redis.factory)
    assert PRIVATE not in json.dumps(result)
    assert set(redis.calls) <= {"GET", "HSCAN", "SCAN", "CLOSE"}
    return result


@pytest.mark.parametrize("field", gate.PROTECTED)
def test_every_protected_positive_count_blocks(field):
    assert gate.blocked({field: 1})


def test_old_unleased_preparing_does_not_permanently_block():
    counts = collect(database_values={"mockOldPreparingWithoutLease": 8})
    assert counts["mockOldPreparingWithoutLease"] == 8
    assert not gate.blocked(counts)


@pytest.mark.parametrize("field", ["mockPreparingProtected", "mockGeneratingQuestion", "mockSpeaking",
                                  "mockListening", "mockPaused", "mockGeneratingReport", "mockUnknownPhase"])
def test_database_activity_is_counted_and_blocks(field):
    assert gate.blocked(collect(database_values={field: 1}))


@pytest.mark.parametrize("page,field", [("live", "livePageLeases"), ("preparation", "preparationPageLeases"),
                                      (PRIVATE, "unknownPageLeases")])
def test_all_effective_page_leases_block_and_duplicate_storage_is_deduplicated(page, field):
    record = {"session_id": PRIVATE, "page_instance_id": PRIVATE, "page": page, "lease_expires_at_ms": NOW}
    counts = collect(heartbeats=[record], entities=[record])
    assert counts[field] == 1
    assert gate.blocked(counts)


def test_expired_page_lease_is_not_activity():
    counts = collect(heartbeats=[{"page": "preparation", "lease_expires_at_ms": NOW-1}])
    assert not gate.blocked(counts)


@pytest.mark.parametrize("kind,status", [("chat", "queued"), ("chat", "streaming"),
    ("screenshot", "queued"), ("screenshot", "processing-images"), ("screenshot", "vision-running"),
    ("screenshot", "streaming")])
def test_every_real_pending_task_status_is_protected(kind, status):
    counts = collect(tasks={f"offersteady:live:{kind}:v1:task:{PRIVATE}": json.dumps({"status": status})})
    assert counts[f"unfinished{kind.title()}Tasks"] == 1
    assert gate.blocked(counts)


@pytest.mark.parametrize("kind", ["chat", "screenshot"])
@pytest.mark.parametrize("status", ["completed", "failed", "cancelled"])
def test_terminal_tasks_do_not_block(kind, status):
    counts = collect(tasks={f"offersteady:live:{kind}:v1:task:{PRIVATE}": json.dumps({"status": status})})
    assert not gate.blocked(counts)


@pytest.mark.parametrize("kind", ["chat", "screenshot"])
@pytest.mark.parametrize("status", [PRIVATE, None, []])
def test_unknown_status_fails_closed_without_echoing_value(kind, status):
    counts = collect(tasks={f"offersteady:live:{kind}:v1:task:{PRIVATE}": json.dumps({"status": status})})
    assert counts[f"unknown{kind.title()}TaskStatuses"] == 1
    assert gate.blocked(counts)


@pytest.mark.parametrize("raw", [PRIVATE, "[]", "null"])
def test_invalid_runtime_metadata_fails_closed(raw):
    counts = collect(raw_snapshot=raw)
    assert counts["invalidRuntimeMetadata"] == 1
    assert gate.blocked(counts)


def test_gate_has_only_explicit_read_commands_and_aggregate_sql():
    source = PATH.read_text()
    tree = ast.parse(source)
    calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
             and node.func.value.id in {"connection", "client"}}
    assert calls == {"execute", "get", "hscan_iter", "scan_iter", "close"}
    assert "count(*)" in gate.SQL and "SELECT" in gate.SQL
    assert not any(word in gate.SQL.upper() for word in ("INSERT ", "UPDATE ", "DELETE ", "ALTER ", "DROP "))
    assert "default_transaction_read_only=on" in source


@pytest.mark.parametrize("bad", [None, [], [0], [0] * 10 + [-1], [0] * 10 + [True]])
def test_database_aggregate_shape_is_rejected(bad):
    database = Database({})
    database.row = bad
    with pytest.raises(ValueError, match="aggregate shape"):
        gate.collect_counts(SimpleNamespace(database_url=PRIVATE, redis_url=PRIVATE), now_ms=NOW,
                            connect=database, redis_factory=Redis().factory)


def test_missing_protected_field_fails_closed():
    counts = collect()
    del counts[gate.PROTECTED[0]]
    assert gate.blocked(counts)
