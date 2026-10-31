"""Synthetic control reads; no production identities, documents or providers."""
from __future__ import annotations

from collections import Counter
from dataclasses import FrozenInstanceError, fields, replace
import json
import os
from pathlib import Path
from threading import Lock
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.interview_session import SessionBoundDocument, SessionControlState
from app.ports.document_repository import DocumentRecord
from app.ports.realtime_speech import DesktopDeviceRecord, SessionDesktopBindingRecord
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.postgres_material_persistence import PostgresDocumentRepository
from app.services.realtime_speech_service import RealtimeSpeechService
from app.services.session_service import SessionService


NOW = 1_800_000_000_000
OWNER = "synthetic-control-owner"


def control_fixture(monkeypatch, *, status="live", mode="interview", audio="computer", documents=8):
    clock = [NOW]
    monkeypatch.setattr("app.services.realtime_speech_service._now_ms", lambda: clock[0])
    monkeypatch.setattr("app.services.session_service._now_ms", lambda: clock[0])
    settings = Settings(_env_file=None, product_edition="cn", realtime_control_cache_ms=50)
    repository = InMemoryInterviewSessionRepository()
    document_repository = Mock()
    document_repository.get_by_id.return_value = None
    sessions = SessionService(settings=settings, repository=repository, document_repository=document_repository)
    record = sessions.create_session(user_id=OWNER, title="Synthetic control read")
    materials = [SessionBoundDocument(document_id=f"synthetic-material-{i}", document_kind="knowledge",
        display_name=f"Synthetic material {i}", status="ready") for i in range(documents)]
    record = replace(record, status=status, session_mode=mode, interview_audio_mode=audio,
        started_at_ms=NOW - 1_000 if status != "preparing" else None,
        material_binding=replace(record.material_binding, bound_documents=materials))
    repository.save_session(record)
    device = DesktopDeviceRecord(device_id="synthetic-device", manual_code="123456", display_name="Synthetic device",
        capabilities={"microphone": True}, registered_at_ms=NOW, last_seen_at_ms=NOW)
    binding = SessionDesktopBindingRecord(binding_id="synthetic-binding", session_id=record.session_id,
        owner_user_id=OWNER, device_id=device.device_id, manual_code=device.manual_code,
        display_name=device.display_name, capabilities=device.capabilities, bound_at_ms=NOW, last_seen_at_ms=NOW)
    bindings = [binding]
    device_state = [device]
    service = object.__new__(RealtimeSpeechService)
    service.settings = settings
    service.session_service = sessions
    service.repository = SimpleNamespace(
        get_desktop_device_by_code=lambda code: device_state[0] if code == device.manual_code else None,
        get_latest_session_desktop_binding_by_code=lambda **_: bindings[-1] if bindings else None,
        list_session_desktop_bindings_for_device=lambda **_: list(bindings),
        list_events_for_session=lambda **_: [],
    )
    service._capture_control_cache = {record.session_id: "capturing"}
    service._control_query_cache_lock = Lock()
    service._control_query_cache = {}
    service._control_query_inflight = {}
    service._control_query_cache_generation = 0
    service._control_query_cache_hits = 0
    service._control_query_cache_misses = 0
    service._control_query_singleflight_waits = 0
    return SimpleNamespace(service=service, sessions=sessions, repository=repository, documents=document_repository,
        record=record, device=device, binding=binding, bindings=bindings, device_state=device_state, clock=clock)


def pairing(fixture, *, pinned=False):
    return fixture.service.get_desktop_active_connection(device_id=fixture.device.device_id,
        manual_code=fixture.device.manual_code,
        pinned_session_id=fixture.record.session_id if pinned else None,
        pinned_binding_id=fixture.binding.binding_id if pinned else None)


@pytest.mark.parametrize("status", ["preparing", "live", "ended"])
@pytest.mark.parametrize("mode", ["interview", "written", "mock"])
@pytest.mark.parametrize("audio", ["computer", "mobile"])
def test_cn_binding_wire_equals_full_read_for_all_modes(monkeypatch, status, mode, audio):
    fixture = control_fixture(monkeypatch, status=status, mode=mode, audio=audio)
    control = Mock(wraps=fixture.repository.get_control_state)
    full = Mock(wraps=fixture.repository.get_session)
    writes = Mock(wraps=fixture.repository.save_session)
    monkeypatch.setattr(fixture.repository, "get_control_state", control)
    monkeypatch.setattr(fixture.repository, "get_session", full)
    monkeypatch.setattr(fixture.repository, "save_session", writes)
    candidate = pairing(fixture)
    control.assert_called_once_with(fixture.record.session_id)
    full.assert_not_called()
    writes.assert_not_called()
    fixture.documents.get_by_id.assert_not_called()
    fixture.service.settings = fixture.service.settings.model_copy(update={"product_edition": "global"})
    fixture.service._invalidate_control_query_cache()
    baseline = pairing(fixture)
    assert candidate == baseline
    full.assert_called_once_with(fixture.record.session_id)
    assert control.call_count == 1
    assert candidate["authoritative"] is True and candidate["refreshAfterMs"] == 10_000
    if status == "preparing":
        assert candidate["captureState"] == "ready"
    elif status == "live":
        assert candidate["captureState"] == ("paused" if mode == "written" else "capturing")


def test_cn_paused_capture_and_pinned_read_have_one_projection(monkeypatch):
    fixture = control_fixture(monkeypatch)
    fixture.service._capture_control_cache[fixture.record.session_id] = "paused"
    projection = Mock(wraps=fixture.repository.get_control_state)
    monkeypatch.setattr(fixture.repository, "get_control_state", projection)
    result = pairing(fixture, pinned=True)
    assert result["captureState"] == "paused" and result["bindingLockState"] == "held"
    assert result["binding"]["bindingId"] == fixture.binding.binding_id
    projection.assert_called_once_with(fixture.record.session_id)


@pytest.mark.parametrize("change", ["ended", "deleted", "written", "mobile"])
def test_next_eligible_control_read_sees_current_lifecycle_and_mode(monkeypatch, change):
    fixture = control_fixture(monkeypatch)
    assert pairing(fixture)["bound"] is True
    if change == "deleted":
        fixture.repository.delete_session(user_id=OWNER, session_id=fixture.record.session_id)
    else:
        updates = {"status": "ended"} if change == "ended" else {"session_mode": "written"} if change == "written" else {"interview_audio_mode": "mobile"}
        fixture.repository.save_session(replace(fixture.record, **updates))
    fixture.clock[0] += 51  # Preserve the pre-existing 50ms pairing-cache boundary.
    current = pairing(fixture)
    if change in {"ended", "deleted"}:
        assert current["state"] == "stale-bound" and current["bound"] is False
        assert current["sessionStatus"] == ("missing" if change == "deleted" else "ended")
    elif change == "written":
        assert current["sessionMode"] == "written" and current["captureState"] == "paused"
    else:
        assert current["interviewAudioMode"] == "mobile"
    fixture.documents.get_by_id.assert_not_called()


def test_projection_is_immutable_and_excludes_personal_and_material_fields(monkeypatch):
    fixture = control_fixture(monkeypatch)
    state = fixture.sessions.get_control_state(user_id=OWNER, session_id=fixture.record.session_id)
    assert isinstance(state, SessionControlState)
    assert {field.name for field in fields(state)} == {"session_id", "owner_user_id", "status", "session_mode", "interview_audio_mode"}
    with pytest.raises(FrozenInstanceError):
        state.status = "ended"


@pytest.mark.parametrize("user,missing,expected", [("synthetic-other", False, 403), (OWNER, True, 404)])
def test_control_projection_preserves_service_owner_and_missing_errors(monkeypatch, user, missing, expected):
    fixture = control_fixture(monkeypatch)
    if missing:
        fixture.repository.sessions.clear()
    with pytest.raises(DomainRequestError) as error:
        fixture.sessions.get_control_state(user_id=user, session_id=fixture.record.session_id)
    assert error.value.status_code == expected
    fixture.documents.get_by_id.assert_not_called()


def test_foreign_binding_stays_missing_and_matches_original_error_conversion(monkeypatch):
    fixture = control_fixture(monkeypatch)
    fixture.bindings[0] = replace(fixture.binding, owner_user_id="synthetic-other")
    cn = pairing(fixture)
    assert cn["sessionStatus"] == "missing" and cn["bound"] is False
    fixture.service.settings = fixture.service.settings.model_copy(update={"product_edition": "global"})
    fixture.service._invalidate_control_query_cache()
    assert pairing(fixture) == cn


@pytest.mark.parametrize("stale", ["generation", "offline", "binding-status"])
def test_generation_heartbeat_and_stale_binding_contract_stays_equivalent(monkeypatch, stale):
    fixture = control_fixture(monkeypatch)
    if stale == "generation":
        fixture.device_state[0] = replace(fixture.device, generation=2)
    elif stale == "offline":
        fixture.device_state[0] = replace(fixture.device, last_seen_at_ms=NOW - 120_000)
    else:
        fixture.bindings[0] = replace(fixture.binding, status="stale")
    cn = pairing(fixture)
    assert cn["bound"] is False and cn["state"] == "stale-bound"
    fixture.service.settings = fixture.service.settings.model_copy(update={"product_edition": "global"})
    fixture.service._invalidate_control_query_cache()
    assert pairing(fixture) == cn


def test_pinned_live_binding_remains_held_until_ended_then_latest_is_selected(monkeypatch):
    fixture = control_fixture(monkeypatch)
    newer = fixture.sessions.create_session(user_id="synthetic-new-owner", title="Synthetic newer binding")
    newer = replace(newer, status="live")
    fixture.repository.save_session(newer)
    fixture.bindings.append(replace(fixture.binding, binding_id="synthetic-new-binding", session_id=newer.session_id, owner_user_id=newer.owner_user_id))
    first = pairing(fixture, pinned=True)
    assert first["bindingLockState"] == "held" and first["binding"]["sessionId"] == fixture.record.session_id
    fixture.repository.save_session(replace(fixture.record, status="ended"))
    fixture.service._invalidate_control_query_cache()
    next_binding = pairing(fixture, pinned=True)
    assert next_binding["bindingLockState"] == "released" and next_binding["binding"]["sessionId"] == newer.session_id


def test_formal_material_aware_read_keeps_authoritative_document_refresh(monkeypatch):
    fixture = control_fixture(monkeypatch, documents=3)
    pairing(fixture)
    fixture.documents.get_by_id.assert_not_called()
    current = fixture.sessions.get_session(user_id=OWNER, session_id=fixture.record.session_id)
    assert fixture.documents.get_by_id.call_count == 3
    assert all(not document.active and document.status == "deleted" for document in current.material_binding.bound_documents)


@pytest.mark.parametrize("raw_mode,raw_audio", [(None, None), ("", ""), ("written", "mobile")])
def test_postgres_projection_query_and_legacy_mode_defaults(monkeypatch, raw_mode, raw_audio):
    repository = object.__new__(PostgresInterviewSessionRepository)
    connection = Mock()
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    cursor = Mock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    cursor.fetchone.return_value = {"session_id": "synthetic-session", "owner_user_id": OWNER, "status": "live", "session_mode": raw_mode, "interview_audio_mode": raw_audio}
    connection.cursor.return_value = cursor
    monkeypatch.setattr(repository, "_connect", Mock(return_value=connection))
    state = repository.get_control_state("synthetic-session")
    assert state.session_mode == (raw_mode or "interview")
    assert state.interview_audio_mode == (raw_audio or "computer")
    query, params = cursor.execute.call_args.args
    assert "SELECT *" not in query and "json" not in query.lower()
    assert "deleted_at_ms IS NULL" in query and params == ("synthetic-session",)
    repository._connect.assert_called_once()


@pytest.mark.skipif(not os.getenv("OFFERSTEADY_TEST_DATABASE_URL"), reason="Dedicated synthetic PostgreSQL required")
@pytest.mark.parametrize("documents_changed", [False, True])
def test_actual_postgres_control_path_reduces_queries_writes_and_large_row_reads(monkeypatch, documents_changed):
    database = os.environ["OFFERSTEADY_TEST_DATABASE_URL"]
    schema = "synthetic_cn_control_" + uuid4().hex
    fixture = control_fixture(monkeypatch, documents=6)
    repository = object.__new__(PostgresInterviewSessionRepository)
    counts = Counter()
    executed_queries = []
    timings = {"connect": [], "sqlExecute": []}
    measure = [False]

    class CountingCursor(psycopg.Cursor):
        def execute(self, query, params=None, **kwargs):
            counts[str(query).strip().split()[0].upper()] += 1
            executed_queries.append(str(query))
            started = perf_counter()
            try:
                return super().execute(query, params, **kwargs)
            finally:
                if measure[0]:
                    timings["sqlExecute"].append((perf_counter() - started) * 1_000)

    def connect():
        counts["connections"] += 1
        started = perf_counter()
        result = psycopg.connect(database, options=f"-c search_path={schema}", cursor_factory=CountingCursor)
        if measure[0]:
            timings["connect"].append((perf_counter() - started) * 1_000)
        return result

    with psycopg.connect(database, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            admin.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            # Include complete production-shaped data to exercise the original decoder.
            admin.execute("""CREATE TABLE interview_sessions (
                session_id text PRIMARY KEY, owner_user_id text, title text, session_mode text,
                interview_audio_mode text, status text, continue_target text, interview_language text,
                programming_required boolean, programming_language text, auto_answer_enabled boolean,
                auto_answer_enabled_at_ms bigint, material_binding_json jsonb, config_snapshot_json jsonb,
                usage_totals_json jsonb, integration_references_json jsonb, restart_of_session_id text,
                started_at_ms bigint, ended_at_ms bigint, created_at_ms bigint, updated_at_ms bigint,
                last_activity_at_ms bigint, deleted_at_ms bigint)""")
            monkeypatch.setattr(repository, "_connect", connect)
            documents = object.__new__(PostgresDocumentRepository)
            monkeypatch.setattr(documents, "_connect", connect)
            documents._ensure_tables()
            if not documents_changed:
                current_materials = []
                for item in fixture.record.material_binding.bound_documents:
                    document = documents.save(DocumentRecord(document_id=item.document_id, owner_user_id=OWNER,
                        document_kind="knowledge", display_name=item.display_name, file_kind="txt",
                        content_type="text/plain", size_bytes=1, object_key=item.document_id, status="ready",
                        knowledge_collection_id=None, processing_requested_at_ms=None, deleted_at_ms=None,
                        created_at_ms=NOW, updated_at_ms=NOW, summary=None, index_state="indexed"))
                    current_materials.append(replace(item, document_version_id=document.document_version_id, index_state="indexed"))
                fixture.record = replace(fixture.record, material_binding=replace(fixture.record.material_binding, bound_documents=current_materials))
            repository.save_session(fixture.record)
            fixture.sessions.repository = repository
            fixture.sessions.document_repository = documents
            document_reads = Mock(wraps=documents.get_by_id)
            monkeypatch.setattr(documents, "get_by_id", document_reads)
            # Compare unchanged materials and stale bindings whose documents are now absent.
            counts.clear()
            fixture.service.settings = fixture.service.settings.model_copy(update={"product_edition": "global"})
            baseline = pairing(fixture)
            baseline_counts = dict(counts)
            baseline_documents = document_reads.call_count
            repository.save_session(fixture.record)
            document_reads.reset_mock()
            counts.clear()
            executed_queries.clear()
            fixture.service.settings = fixture.service.settings.model_copy(update={"product_edition": "cn"})
            fixture.service._invalidate_control_query_cache()
            candidate = pairing(fixture)
            candidate_counts = dict(counts)
            assert baseline == candidate
            assert baseline_documents == 6 and document_reads.call_count == 0
            # Preserve the existing full-read path, including its double save after material changes.
            assert baseline_counts == ({"connections": 9, "SELECT": 7, "INSERT": 2} if documents_changed else {"connections": 7, "SELECT": 7})
            assert candidate_counts == {"connections": 1, "SELECT": 1}
            assert all("json" not in query.lower() and "SELECT *" not in query for query in executed_queries)
            benchmark = None
            sample_count = int(os.getenv("OFFERSTEADY_CONTROL_READ_BENCHMARK_SAMPLES", "0"))
            assert 0 <= sample_count <= 120
            if sample_count and not documents_changed:
                def describe(values):
                    ordered = sorted(values)
                    return {"count": len(values), "p50Ms": round(ordered[(len(ordered) - 1) // 2], 3),
                        "p95Ms": round(ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)], 3), "maxMs": round(max(values), 3)}

                benchmark = {"samplesPerGroup": sample_count, "concurrency": 1, "syntheticBoundDocuments": 6,
                    "pairingCacheBypassedForBothGroups": True, "groups": []}
                for label, edition, expected_connections in [("originalFullRead", "global", sample_count * 7), ("cnControlProjection", "cn", sample_count)]:
                    fixture.service.settings = fixture.service.settings.model_copy(update={"product_edition": edition})
                    counts.clear()
                    for values in timings.values():
                        values.clear()
                    operations = []
                    measure[0] = True
                    try:
                        for _ in range(sample_count):
                            fixture.service._invalidate_control_query_cache()
                            started = perf_counter()
                            actual = pairing(fixture)
                            operations.append((perf_counter() - started) * 1_000)
                            assert actual == candidate
                    finally:
                        measure[0] = False
                    assert counts == {"connections": expected_connections, "SELECT": expected_connections}
                    benchmark["groups"].append({"method": label, "operations": describe(operations),
                        "connect": describe(timings["connect"]), "sqlExecute": describe(timings["sqlExecute"]),
                        "connections": counts["connections"], "selects": counts["SELECT"], "writes": 0, "errors": 0})
                benchmark["limits"] = ["Local sequential same-container comparison with short connections in both groups; pool disabled.",
                    "Connect and SQL metrics count individual phases, not paired operation critical paths; do not add their percentiles.",
                    "Materials-changed group is a separate single-operation resource comparison; not reset per timed operation.",
                    "No production API P95 forecast."]
            # Consecutive fresh physical reads see changes, deletion and owner checks.
            admin.execute("UPDATE interview_sessions SET session_mode='written',interview_audio_mode='mobile'")
            current = fixture.sessions.get_control_state(user_id=OWNER, session_id=fixture.record.session_id)
            assert current.session_mode == "written" and current.interview_audio_mode == "mobile"
            with pytest.raises(DomainRequestError) as foreign:
                fixture.sessions.get_control_state(user_id="synthetic-other", session_id=fixture.record.session_id)
            assert foreign.value.status_code == 403
            admin.execute("UPDATE interview_sessions SET deleted_at_ms=%s", (NOW,))
            assert repository.get_control_state(fixture.record.session_id) is None
            with pytest.raises(DomainRequestError) as deleted:
                fixture.sessions.get_control_state(user_id=OWNER, session_id=fixture.record.session_id)
            assert deleted.value.status_code == 404
            report = {"synthetic": True, "sameBindingWire": True,
                "materialsChanged": documents_changed,
                "fullRead": {"connections": baseline_counts["connections"], "selects": baseline_counts["SELECT"], "sessionWrites": baseline_counts.get("INSERT", 0), "documentReads": baseline_documents, "selectsLargeJsonFields": True},
                "controlProjection": {"connections": candidate_counts["connections"], "selects": candidate_counts["SELECT"], "sessionWrites": candidate_counts.get("INSERT", 0), "documentReads": 0, "selectsLargeJsonFields": False},
                "limits": ["Synthetic sessions and documents; all queries/counts use actual local PostgreSQL repositories.", "No production latency or full application P95 claim."]}
            if benchmark:
                report["benchmark"] = benchmark
            evidence = os.getenv("OFFERSTEADY_CONTROL_READ_EVIDENCE")
            if evidence:
                target = Path(evidence)
                previous = json.loads(target.read_text()) if target.exists() else {"scenarios": []}
                previous["scenarios"] = [scenario for scenario in previous["scenarios"] if scenario["materialsChanged"] != documents_changed] + [report]
                target.write_text(json.dumps(previous, indent=2) + "\n")
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
