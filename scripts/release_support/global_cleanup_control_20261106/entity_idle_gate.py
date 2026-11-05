"""Read-only supplement for the CN entity protocol; output aggregates only.

Run in a pinned Backend image with its private runtime environment. No business
repository is constructed: doing so could seed Redis. Existing seven gates,
TCP ownership and single-writer checks remain mandatory and are not replaced.
"""
from __future__ import annotations

import json
import time

import psycopg
import redis


BASE = "offersteady:realtime:runtime:v2"
BINDINGS = BASE + ":entities:cn-bindings:v1"
CANDIDATES = BASE + ":entities:candidates:v1"
OWNERS = BASE + ":entities:session-owners:v1"
RETIRED = BASE + ":entities:retired-sessions:v1"
ACTIVITY = BASE + ":activity"
SCOPED_PREFIX = BASE + ":candidates:"
MAX_RECORDS = 20_000
RECENT_MS = 30_000
PREPARING_RECENT_MS = 120_000
SQL = """SELECT session_id, owner_user_id, status, updated_at_ms, deleted_at_ms
 FROM interview_sessions WHERE session_id = ANY(%s)"""
PROTECTED = (
    "activeCnBindings", "activeCnCandidates", "pendingCnCandidateClaims",
    "recentCnEntityWrites", "unknownCnSessionStates", "invalidCnEntityMetadata",
    "cnEntityReadFailures", "cnEntityScanLimitExceeded", "cnEntityMutationDetected",
)
INFORMATIONAL = (
    "cnBoundBindings", "cnStaleBindings", "cnRetiredBindings", "cnCandidates",
    "cnRetiredCandidates", "cnHistoricalEntities", "scannedCnEntityRecords",
)


class _Invalid(ValueError):
    pass


class _Limit(ValueError):
    pass


def _text(value):
    if not isinstance(value, str) or not value:
        raise _Invalid()
    return value


def _timestamp(value):
    if type(value) is not int or value < 0:
        raise _Invalid()
    return value


def _json(raw):
    def reject(_):
        raise _Invalid()
    try:
        value = json.loads(raw, parse_constant=reject)
    except (ValueError, TypeError):
        raise _Invalid() from None
    if not isinstance(value, dict):
        raise _Invalid()
    return value


def _record(raw, kind):
    value = _json(raw)
    marker = "cn_binding_schema" if kind == "binding" else "cn_candidate_schema"
    if marker in value:
        if set(value) != {marker, "record_json", "overrides"} or type(value[marker]) is not int or value[marker] != 1:
            raise _Invalid()
        if not isinstance(value["record_json"], str) or not isinstance(value["overrides"], dict):
            raise _Invalid()
        allowed = {"status"} if kind == "binding" else {"state", "reason", "answer_task_id", "updated_at_ms"}
        if not set(value["overrides"]) <= allowed:
            raise _Invalid()
        original = _json(value["record_json"])
        original.update(value["overrides"])
        value = original
    elif "cn_candidate_schema" in value or "cn_binding_schema" in value:
        raise _Invalid()
    result = {key: _text(value.get(key)) for key in ("session_id", "owner_user_id")}
    if kind == "binding":
        for key in ("binding_id", "device_id", "manual_code"):
            _text(value.get(key))
        result["at_ms"] = max(_timestamp(value.get("bound_at_ms")), _timestamp(value.get("last_seen_at_ms")))
        if value.get("status") not in {"bound", "stale"}:
            raise _Invalid()
        if type(value.get("binding_generation")) is not int or value["binding_generation"] < 1:
            raise _Invalid()
        result["status"] = value["status"]
    else:
        result["candidate_id"] = _text(value.get("candidate_id"))
        result["at_ms"] = max(_timestamp(value.get("created_at_ms")), _timestamp(value.get("updated_at_ms")))
        if value.get("state") not in {"needs-confirmation", "confirmed", "dismissed"}:
            raise _Invalid()
        claim = value.get("answer_task_id")
        if claim is not None and (not isinstance(claim, str) or not claim or claim == "claim:"):
            raise _Invalid()
        result.update(state=value["state"], claim=bool(claim and claim.startswith("claim:")))
    return result


def _read_state(client):
    """Bound scans and preserve raw values only in memory for race detection."""
    seen = 0
    state = {}

    def read_hash(key):
        nonlocal seen
        values = {}
        for field, raw in client.hscan_iter(key, count=100):
            seen += 1
            if seen > MAX_RECORDS:
                raise _Limit()
            values[_text(field)] = raw
        state[key] = values

    for key in (BINDINGS, CANDIDATES, OWNERS, RETIRED, ACTIVITY):
        read_hash(key)
    keys = set()
    for key in client.scan_iter(match=SCOPED_PREFIX + "*", count=100):
        key = _text(key)
        if not key.startswith(SCOPED_PREFIX) or not key[len(SCOPED_PREFIX):]:
            raise _Invalid()
        keys.add(key)
        if len(keys) > MAX_RECORDS:
            raise _Limit()
    for key in sorted(keys):
        read_hash(key)
    return state, seen


def _metadata(state):
    owners = {sid: _text(uid) for sid, uid in state[OWNERS].items()}
    retired = set()
    for sid, marker in state[RETIRED].items():
        if marker != "1":
            raise _Invalid()
        retired.add(sid)
    for value in state[ACTIVITY].values():
        if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
            raise _Invalid()
    bindings = []
    candidates = {}
    scoped_candidates = set()
    for field, raw in state[BINDINGS].items():
        record = _record(raw, "binding")
        if field != record["owner_user_id"] + "|" + record["session_id"]:
            raise _Invalid()
        bindings.append(record)
    for key, values in state.items():
        if key != CANDIDATES and not key.startswith(SCOPED_PREFIX):
            continue
        for field, raw in values.items():
            record = _record(raw, "candidate")
            if field != record["candidate_id"] or key != CANDIDATES and key != SCOPED_PREFIX + record["session_id"]:
                raise _Invalid()
            previous = candidates.get(field)
            if previous is not None and previous != record:
                raise _Invalid()
            candidates[field] = record
            if key != CANDIDATES:
                scoped_candidates.add(field)
    for record in (*bindings, *candidates.values()):
        if owners.get(record["session_id"]) != record["owner_user_id"]:
            raise _Invalid()
    # The application requires a surviving scoped value for a candidate read.
    # Another session may renew the global hash after this scope expired; such
    # a global-only historical claim must not block every later idle rollback.
    return bindings, [record | {"readable": cid in scoped_candidates} for cid, record in candidates.items()], retired


def _sessions(settings, ids, connect):
    if not ids:
        return {}
    records = {}
    with connect(settings.database_url, connect_timeout=3,
                 options="-c default_transaction_read_only=on -c statement_timeout=3000") as connection:
        rows = connection.execute(SQL, (sorted(ids),)).fetchall()
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 5:
            raise _Invalid()
        sid, uid, status, updated, deleted = row
        _text(sid); _text(uid); _timestamp(updated)
        if deleted is not None:
            _timestamp(deleted)
        if sid not in ids or sid in records or not isinstance(status, str):
            raise _Invalid()
        records[sid] = (uid, status, updated, deleted)
    return records


def collect_counts(settings, *, now_ms, connect=psycopg.connect, redis_factory=redis.Redis.from_url):
    counts = dict.fromkeys((*PROTECTED, *INFORMATIONAL), 0)
    counts["atMs"] = _timestamp(now_ms)
    client = None
    try:
        client = redis_factory(settings.redis_url, decode_responses=True,
                               socket_timeout=3, socket_connect_timeout=3)
        before, counts["scannedCnEntityRecords"] = _read_state(client)
        bindings, candidates, retired = _metadata(before)
        rows = _sessions(settings, {r["session_id"] for r in (*bindings, *candidates)}, connect)

        def session_state(record):
            sid = record["session_id"]
            row = rows.get(sid)
            if row is None:
                return False
            uid, status, updated, deleted = row
            if uid != record["owner_user_id"]:
                raise _Invalid()
            if status not in {"preparing", "live", "ended"}:
                counts["unknownCnSessionStates"] += 1
                return False
            active = deleted is None and (status == "live" or status == "preparing" and updated > now_ms - PREPARING_RECENT_MS)
            if sid in retired and active:
                raise _Invalid()
            return active

        for record in bindings:
            counts["cnBoundBindings" if record["status"] == "bound" else "cnStaleBindings"] += 1
            active = session_state(record)
            counts["activeCnBindings"] += int(active)
            if record["session_id"] in retired:
                counts["cnRetiredBindings"] += 1
            elif record["status"] == "bound":
                counts["recentCnEntityWrites"] += int(record["at_ms"] >= now_ms - RECENT_MS)
            if not active:
                counts["cnHistoricalEntities"] += 1
        for record in candidates:
            counts["cnCandidates"] += 1
            active = session_state(record)
            if record["session_id"] in retired:
                counts["cnRetiredCandidates"] += 1
            else:
                counts["activeCnCandidates"] += int(active and record["readable"])
                counts["pendingCnCandidateClaims"] += int(record["claim"] and record["readable"])
                counts["recentCnEntityWrites"] += int(record["at_ms"] >= now_ms - RECENT_MS)
            if not active:
                counts["cnHistoricalEntities"] += 1
        after, _ = _read_state(client)
        counts["cnEntityMutationDetected"] = int(before != after)
    except _Limit:
        counts["cnEntityScanLimitExceeded"] += 1
    except _Invalid:
        counts["invalidCnEntityMetadata"] += 1
    except Exception:
        counts["cnEntityReadFailures"] += 1
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                counts["cnEntityReadFailures"] += 1
    return counts


def blocked(counts):
    return any(type(counts.get(field)) is not int or counts[field] != 0 for field in PROTECTED)


def main():
    try:
        from app.core.config import get_settings
        counts = collect_counts(get_settings(), now_ms=int(time.time() * 1000))
    except Exception:
        counts = dict.fromkeys((*PROTECTED, *INFORMATIONAL), 0)
        counts.update(atMs=int(time.time() * 1000), cnEntityReadFailures=1)
    print(json.dumps(counts, separators=(",", ":")), flush=True)
    raise SystemExit(75 if blocked(counts) else 0)


if __name__ == "__main__":
    main()
