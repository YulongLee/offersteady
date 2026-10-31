"""Synthetic request-local document reuse; no user data or provider calls."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
import os
from threading import Barrier, Event
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest

from app.core.config import Settings
from app.modules import web
from app.ports.authentication import AuthenticatedRequestContext
from app.ports.document_repository import DocumentRecord
from app.ports.interview_session import SessionBoundDocument
from app.services.document_repository import InMemoryDocumentRepository
from app.services.document_service import DocumentService, InMemoryKnowledgeCollectionStore
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.postgres_material_persistence import PostgresDocumentRepository
from app.services.session_service import SessionService


OWNER = "synthetic-state-read-owner"
NOW = 1_800_000_000_000


def document(document_id="synthetic-doc-a", *, owner=OWNER, **changes):
    return replace(DocumentRecord(
        document_id=document_id, owner_user_id=owner, document_kind="knowledge",
        display_name="Synthetic notes.txt", file_kind="txt", content_type="text/plain",
        size_bytes=18, object_key=f"synthetic/{document_id}", status="ready",
        knowledge_collection_id="synthetic-collection", processing_requested_at_ms=None,
        deleted_at_ms=None, created_at_ms=NOW, updated_at_ms=NOW,
        summary="Synthetic source summary", document_version_id=f"synthetic-version-{document_id}",
        version=1, content_fingerprint="a" * 64, index_state="indexed",
    ), **changes)


class CountingDocuments(InMemoryDocumentRepository):
    def __init__(self):
        super().__init__()
        self.list_calls = 0
        self.get_calls = []
        self.after_list = None

    def list_for_user(self, **kwargs):
        self.list_calls += 1
        records = super().list_for_user(**kwargs)
        if self.after_list:
            self.after_list()
        return records

    def get_by_id(self, document_id):
        self.get_calls.append(document_id)
        return super().get_by_id(document_id)

    def reset_counts(self):
        self.list_calls = 0
        self.get_calls.clear()


def services(*, documents=None, sessions=None, edition="cn"):
    settings = Settings(_env_file=None, environment="test", product_edition=edition,
                        development_user_id=OWNER)
    documents = documents if documents is not None else CountingDocuments()
    sessions = sessions if sessions is not None else InMemoryInterviewSessionRepository()
    document_service = DocumentService(
        storage=SimpleNamespace(), repository=documents,
        knowledge_store=InMemoryKnowledgeCollectionStore(),
    )
    session_service = SessionService(settings=settings, document_repository=documents, repository=sessions)
    return settings, document_service, session_service


def bound_session(service, records, *, owner=OWNER, mode="interview", missing=()):
    created = service.create_session(user_id=owner, title="Synthetic state read")
    bound = [SessionBoundDocument(
        document_id=record.document_id, document_kind=record.document_kind,
        display_name=record.display_name, status=record.status,
        document_version_id=record.document_version_id, index_state=record.index_state,
        knowledge_collection_id=record.knowledge_collection_id, summary=record.summary,
        active=record.status == "ready" and record.index_state in {None, "indexed"},
    ) for record in records]
    bound += [SessionBoundDocument(
        document_id=key, document_kind="knowledge", display_name="Synthetic missing source",
        status="ready", document_version_id="synthetic-missing-version", index_state="indexed",
        active=True,
    ) for key in missing]
    binding = replace(created.material_binding, revision=7,
                      knowledge_document_ids=[item.document_id for item in bound],
                      bound_documents=bound, confirmed_at_ms=NOW)
    record = replace(created, session_mode=mode, material_binding=binding,
                     integration_references=service._build_integration_references(
                         session_id=created.session_id, user_id=owner, material_binding=binding))
    return service.repository.save_session(record)


def test_snapshot_preserves_list_contract_and_raw_duplicate_names():
    _, documents, sessions = services()
    records = [document(f"synthetic-doc-{i}", created_at_ms=NOW + i, updated_at_ms=NOW + i)
               for i in range(3)]
    for record in records:
        documents.repository.save(record)
    expected = documents.list_documents(user_id=OWNER)
    views, raw = documents.list_documents_with_records(user_id=OWNER)
    assert views == expected
    assert len({view.display_name for view in views}) == 3
    assert {record.display_name for record in raw.values()} == {"Synthetic notes.txt"}
    bound_session(sessions, records)
    result = sessions.list_sessions(user_id=OWNER, document_records=raw)
    assert [item.display_name for item in result[0].material_binding.bound_documents] == [
        "Synthetic notes.txt"] * 3
    raw[records[0].document_id].display_name = "Mutated private snapshot"
    assert documents.repository.documents[records[0].document_id].display_name == "Synthetic notes.txt"
    assert all(view.display_name != "Mutated private snapshot" for view in views)


def test_shared_document_reads_drop_without_changing_session_or_list_output():
    _, documents, sessions = services()
    records = [documents.repository.save(document(f"synthetic-doc-{i}")) for i in range(6)]
    for _ in range(24):
        bound_session(sessions, records)
    documents.repository.reset_counts()
    expected_views = documents.list_documents(user_id=OWNER)
    expected_sessions = sessions.list_sessions(user_id=OWNER)
    assert documents.repository.list_calls == 1
    assert Counter(documents.repository.get_calls) == Counter({record.document_id: 1 for record in records})
    documents.repository.reset_counts()
    views, raw = documents.list_documents_with_records(user_id=OWNER)
    actual = sessions.list_sessions(user_id=OWNER, document_records=raw)
    assert views == expected_views
    assert actual == expected_sessions
    assert documents.repository.list_calls == 1
    assert documents.repository.get_calls == []
    assert all(item.material_binding.revision == 7 for item in actual)


@pytest.mark.parametrize("filtered", [False, True])
def test_filtered_deleted_and_absent_references_still_use_authoritative_fallback(filtered):
    _, documents, sessions = services()
    visible = documents.repository.save(document())
    deleted = documents.repository.save(document("synthetic-deleted", status="deleted", deleted_at_ms=NOW))
    for _ in range(5):
        bound_session(sessions, [visible, deleted], missing=("synthetic-absent",))
    expected = sessions.list_sessions(user_id=OWNER)
    documents.repository.reset_counts()
    _, raw = documents.list_documents_with_records(
        user_id=OWNER, document_kind="resume" if filtered else None)
    actual = sessions.list_sessions(user_id=OWNER, document_records=raw)
    assert actual == expected
    expected_reads = ["synthetic-deleted", "synthetic-absent"]
    if filtered:
        expected_reads.insert(0, visible.document_id)
    assert documents.repository.get_calls == expected_reads
    for session in actual:
        assert session.material_binding.bound_documents[1].status == "deleted"
        assert session.material_binding.bound_documents[2].status == "deleted"


@pytest.mark.parametrize("seed_kind", ["foreign", "mismatched-id", "response-view", "null"])
def test_only_owner_and_id_consistent_raw_records_can_seed(seed_kind):
    _, documents, sessions = services()
    current = documents.repository.save(document())
    bound_session(sessions, [current])
    if seed_kind == "foreign":
        value = replace(current, owner_user_id="synthetic-other-owner", summary="Foreign synthetic sentinel")
    elif seed_kind == "mismatched-id":
        value = replace(current, document_id="synthetic-different-document", summary="Mismatched synthetic sentinel")
    elif seed_kind == "response-view":
        value = documents.list_documents(user_id=OWNER)[0]
    else:
        value = None
    result = sessions.list_sessions(user_id=OWNER, document_records={current.document_id: value})
    assert documents.repository.get_calls == [current.document_id]
    assert result[0].material_binding.bound_documents[0].summary == current.summary


@pytest.mark.parametrize("change", [
    {"status": "processing"}, {"status": "failed"}, {"status": "deleting"},
    {"status": "deleted", "deleted_at_ms": NOW + 1}, {"index_state": "disabled"},
    {"document_version_id": "synthetic-version-next", "summary": "New synthetic summary",
     "display_name": "New synthetic name.txt", "knowledge_collection_id": "synthetic-next-collection"},
    None,
])
def test_next_request_observes_version_status_or_deletion(change):
    _, documents, sessions = services()
    current = documents.repository.save(document())
    bound_session(sessions, [current])
    _, first_raw = documents.list_documents_with_records(user_id=OWNER)
    first = sessions.list_sessions(user_id=OWNER, document_records=first_raw)[0]
    if change is None:
        documents.repository.documents.pop(current.document_id)
    else:
        documents.repository.save(replace(current, **change))
    _, next_raw = documents.list_documents_with_records(user_id=OWNER)
    candidate = sessions.list_sessions(user_id=OWNER, document_records=next_raw)[0]
    # The independent original read is still authoritative for the same state.
    expected = sessions.list_sessions(user_id=OWNER)[0]
    assert candidate == expected
    assert first.material_binding.bound_documents[0].active is True
    assert candidate.material_binding.revision == first.material_binding.revision == 7
    assert first_raw[current.document_id].status == "ready"


def test_snapshot_time_is_local_to_one_request_and_never_reused_after_concurrent_delete():
    _, documents, sessions = services()
    current = documents.repository.save(document())
    bound_session(sessions, [current])
    listed, deleted = Event(), Event()

    def pause_after_list():
        listed.set()
        assert deleted.wait(2), "Synthetic delete was not released"

    documents.repository.after_list = pause_after_list
    with ThreadPoolExecutor(max_workers=1) as executor:
        reading = executor.submit(documents.list_documents_with_records, user_id=OWNER)
        assert listed.wait(2)
        documents.repository.save(replace(current, status="deleted", deleted_at_ms=NOW + 1))
        deleted.set()
        _, same_read = reading.result(timeout=2)
    documents.repository.after_list = None
    # A completed list is the current request's read point, not a global cache.
    assert sessions.list_sessions(user_id=OWNER, document_records=same_read)[0].material_binding.bound_documents[0].active
    _, next_read = documents.list_documents_with_records(user_id=OWNER)
    assert current.document_id not in next_read
    assert not sessions.list_sessions(user_id=OWNER, document_records=next_read)[0].material_binding.bound_documents[0].active
    # Formal actions retain their independent original lookup as well.
    assert not sessions.get_session(user_id=OWNER, session_id=sessions.list_sessions(user_id=OWNER)[0].session_id).material_binding.bound_documents[0].active


def test_mock_selected_version_short_circuits_even_when_seed_has_newer_version():
    _, documents, sessions = services()
    current = documents.repository.save(document())
    original = bound_session(sessions, [current], mode="mock")
    documents.repository.save(replace(current, document_version_id="synthetic-version-next", status="deleted"))
    updated = replace(current, document_version_id="synthetic-version-next", status="processing")
    result = sessions.list_sessions(user_id=OWNER, document_records={current.document_id: updated})
    assert result == [original]
    assert documents.repository.get_calls == []


def test_concurrent_owner_snapshots_stay_separate_with_no_cross_request_cache():
    _, documents, sessions = services()
    owners = ["synthetic-owner-a", "synthetic-owner-b"]
    for owner in owners:
        owned = documents.repository.save(document(f"{owner}-document", owner=owner, summary=owner))
        for _ in range(3):
            bound_session(sessions, [owned], owner=owner)
    barrier = Barrier(2)
    documents.repository.after_list = lambda: barrier.wait(timeout=2)

    def read(owner):
        views, raw = documents.list_documents_with_records(user_id=owner)
        result = sessions.list_sessions(user_id=owner, document_records=raw)
        return views, result

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(read, owners))
    for owner, (views, result) in zip(owners, results, strict=True):
        assert len(views) == 1 and views[0].owner_user_id == owner
        assert len(result) == 3 and all(item.owner_user_id == owner for item in result)
        assert all(item.material_binding.bound_documents[0].summary == owner for item in result)
    assert documents.repository.get_calls == []


def test_missing_snapshot_reference_does_not_swallow_authoritative_read_errors(monkeypatch):
    _, documents, sessions = services()
    bound_session(sessions, [], missing=("synthetic-missing",))

    def unavailable(_):
        raise RuntimeError("Synthetic authoritative read unavailable")

    monkeypatch.setattr(documents.repository, "get_by_id", unavailable)
    with pytest.raises(RuntimeError, match="Synthetic authoritative read unavailable"):
        sessions.list_sessions(user_id=OWNER, document_records={})


def state_client(monkeypatch, *, edition="cn", authenticated=True):
    settings, documents, sessions = services(edition=edition)
    current = documents.repository.save(document())
    bound_session(sessions, [current])
    mock = bound_session(sessions, [current], mode="mock")
    app = FastAPI()
    app.include_router(web.router)
    context = AuthenticatedRequestContext(user_id=OWNER, login_id="synthetic-login", auth_session_id="synthetic-auth")
    app.dependency_overrides[web.optional_authenticated_context] = lambda: context if authenticated else None
    app.dependency_overrides[web.document_read_service] = lambda: documents
    app.dependency_overrides[web.session_service] = lambda: sessions
    billing_payload = {"availablePoints": 250, "syntheticMemberDailyResumeQuota": 3}
    billing = SimpleNamespace(state_for_user=lambda **_: object(), state_payload=lambda _: dict(billing_payload),
                              billing_repository=None)
    app.dependency_overrides[web.billing_service] = lambda: billing
    monkeypatch.setattr(web, "authentication_service", lambda: SimpleNamespace(get_current_user=lambda **_: None))
    monkeypatch.setattr(web, "get_settings", lambda: settings)
    monkeypatch.setattr(web, "_release_manifest", lambda: {"version": 1, "entries": []})
    return TestClient(app), documents, sessions, current, mock


@pytest.mark.parametrize("edition,authenticated,expected_gets", [
    ("cn", True, 0), ("global", True, 1), ("cn", False, 0), ("global", False, 0),
])
def test_http_wire_remains_private_and_only_cn_authenticated_path_reuses(monkeypatch, edition, authenticated, expected_gets):
    client, documents, sessions, current, mock = state_client(monkeypatch, edition=edition, authenticated=authenticated)
    if edition == "global" or not authenticated:
        monkeypatch.setattr(documents, "list_documents_with_records", lambda **_: pytest.fail("Non-CN/anonymous snapshot"))
    response = client.get("/web/state")
    assert response.status_code == 200
    state = response.json()["data"]
    assert len(documents.repository.get_calls) == expected_gets
    assert len(state["interviews"]) == int(authenticated)
    assert mock.session_id not in state["contextSelections"]
    assert set(state) == {"interviews", "preparation", "questions", "review", "captureState", "librarySources",
                          "contextSelections", "billing", "speaker", "activeAnswerTask", "account",
                          "knowledgeCollections", "knowledgeDocuments", "releaseManifest"}
    assert "document_records" not in response.text and "raw_records" not in response.text
    assert state["billing"]["syntheticMemberDailyResumeQuota"] == 3
    documents.repository.save(replace(current, status="deleted", deleted_at_ms=NOW + 1))
    next_response = client.get("/web/state")
    assert next_response.status_code == 200
    next_state = next_response.json()["data"]
    assert next_state["librarySources"] == []
    if authenticated:
        selection = next_state["contextSelections"][state["interviews"][0]["id"]]
        assert selection["knowledgeSourceIds"] == [current.document_id]
        assert selection["materialSnapshots"][0]["active"] is False


def test_cn_http_payload_equals_original_global_read_algorithm(monkeypatch):
    client, documents, sessions, current, _ = state_client(monkeypatch)
    second = documents.repository.save(document("synthetic-doc-b", created_at_ms=NOW + 1))
    bound_session(sessions, [current, second])
    before = deepcopy(sessions.repository.sessions)
    monkeypatch.setattr(web, "utc_now_iso", lambda: "2027-01-15T08:00:00+00:00")
    cn = client.get("/web/state").json()["data"]
    sessions.repository.sessions = before
    baseline_settings = Settings(_env_file=None, environment="test", product_edition="global")
    monkeypatch.setattr(web, "get_settings", lambda: baseline_settings)
    baseline = client.get("/web/state").json()["data"]
    assert cn == baseline


@pytest.fixture
def persistent_services():
    dsn = os.environ.get("OFFERSTEADY_STATE_READ_TEST_DATABASE_URL", "")
    if not dsn:
        pytest.skip("Explicit isolated localhost synthetic PostgreSQL required")
    params = conninfo_to_dict(dsn)
    assert params.get("host") in {"localhost", "127.0.0.1", "::1"}
    assert params.get("hostaddr") in {None, "localhost", "127.0.0.1", "::1"}
    assert params.get("dbname", "").startswith("synthetic_"), "Only a dedicated synthetic database is allowed"
    schema = f"synthetic_state_reuse_{uuid4().hex}"
    with psycopg.connect(dsn) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    settings = Settings(_env_file=None, environment="test", database_url=make_conninfo(
        dsn, options=f"-c search_path={schema}"))
    try:
        documents = PostgresDocumentRepository(settings)
        sessions = PostgresInterviewSessionRepository(settings)
        _, document_service, session_service = services(documents=documents, sessions=sessions)
        yield document_service, session_service
    finally:
        PostgresInterviewSessionRepository._schema_ready_for.discard(str(settings.database_url))
        with psycopg.connect(dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def instrument_database(repository, counts, monkeypatch):
    original = repository._connect

    class Cursor:
        def __init__(self, actual): self.actual = actual
        def __enter__(self): self.actual.__enter__(); return self
        def __exit__(self, *args): return self.actual.__exit__(*args)
        def __getattr__(self, key): return getattr(self.actual, key)
        def execute(self, statement, params=None):
            operation = str(statement).strip().split()[0].upper()
            counts["selects" if operation == "SELECT" else "writes"] += 1
            self.actual.execute(statement, params)
            return self

    class Connection:
        def __init__(self, actual): self.actual = actual
        def __enter__(self): self.actual.__enter__(); return self
        def __exit__(self, *args): return self.actual.__exit__(*args)
        def __getattr__(self, key): return getattr(self.actual, key)
        def cursor(self, *args, **kwargs): return Cursor(self.actual.cursor(*args, **kwargs))

    def connect():
        counts["connections"] += 1
        return Connection(original())

    monkeypatch.setattr(repository, "_connect", connect)


def test_persistent_snapshot_reduces_real_connections_and_selects_with_equivalent_results(persistent_services, monkeypatch):
    documents, sessions = persistent_services
    records = [documents.repository.save(document(f"synthetic-pg-doc-{i}", created_at_ms=NOW + i)) for i in range(6)]
    for _ in range(12):
        bound_session(sessions, records)
    counts = Counter(connections=0, selects=0, writes=0)
    instrument_database(documents.repository, counts, monkeypatch)
    instrument_database(sessions.repository, counts, monkeypatch)
    expected_views = documents.list_documents(user_id=OWNER)
    expected = sessions.list_sessions(user_id=OWNER)
    baseline = dict(counts)
    counts.update({key: -value for key, value in counts.items()})
    views, raw = documents.list_documents_with_records(user_id=OWNER)
    candidate = sessions.list_sessions(user_id=OWNER, document_records=raw)
    actual = dict(counts)
    assert views == expected_views and candidate == expected
    assert baseline == {"connections": 8, "selects": 8, "writes": 0}
    assert actual == {"connections": 2, "selects": 2, "writes": 0}
    print({"syntheticSessions": 12, "sharedDocuments": 6, "baseline": baseline, "candidate": actual})


def test_persistent_next_snapshot_observes_version_update_and_deleted_fallback(persistent_services, monkeypatch):
    documents, sessions = persistent_services
    original = documents.repository.save(document("synthetic-pg-freshness"))
    created = bound_session(sessions, [original])
    _, raw = documents.list_documents_with_records(user_id=OWNER)
    first = sessions.list_sessions(user_id=OWNER, document_records=raw)[0]
    changed = documents.repository.save(replace(
        original, document_version_id="synthetic-version-replaced", version=2,
        object_key="synthetic/synthetic-pg-freshness/v2", object_id="synthetic-pg-version-two-object",
        summary="Updated synthetic PG summary"))
    _, next_raw = documents.list_documents_with_records(user_id=OWNER)
    second = sessions.list_sessions(user_id=OWNER, document_records=next_raw)[0]
    assert first.material_binding.bound_documents[0].document_version_id == original.document_version_id
    assert second.material_binding.bound_documents[0].document_version_id == changed.document_version_id
    assert second.material_binding.bound_documents[0].summary == changed.summary
    assert second.material_binding.revision == created.material_binding.revision
    documents.repository.save(replace(changed, status="deleted", deleted_at_ms=NOW + 1))
    _, deleted_raw = documents.list_documents_with_records(user_id=OWNER)
    assert deleted_raw == {}
    counted = Counter(connections=0, selects=0, writes=0)
    instrument_database(documents.repository, counted, monkeypatch)
    ended = sessions.list_sessions(user_id=OWNER, document_records=deleted_raw)[0]
    assert ended.material_binding.bound_documents[0].active is False
    assert ended.material_binding.bound_documents[0].status == "deleted"
    assert counted == {"connections": 1, "selects": 1, "writes": 0}
