"""Synthetic operation-local material reads; no product database or providers."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import logging
import os
from types import SimpleNamespace
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.document_repository import DocumentRecord
from app.ports.document_processing import VectorSearchMatch
from app.ports.interview_session import SessionBoundDocument
from app.ports.retrieval import RetrievalContext, RetrievalFilter
from app.services.chat_service import ChatService
from app.services.document_repository import InMemoryDocumentRepository
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.knowledge_retrieval import KnowledgeRetrievalService
from app.services.postgres_material_persistence import PostgresDocumentRepository
from app.services.session_service import SessionService


OWNER = "synthetic-batch-owner"


def document(document_id="synthetic-document", **changes):
    return replace(DocumentRecord(
        document_id=document_id, owner_user_id=OWNER, document_kind="knowledge",
        display_name="Synthetic source", file_kind="txt", content_type="text/plain",
        size_bytes=100, object_key="synthetic/not-stored", status="ready",
        knowledge_collection_id="synthetic-collection", processing_requested_at_ms=None,
        deleted_at_ms=None, created_at_ms=1, updated_at_ms=1, summary="Synthetic evidence",
        object_id="synthetic-object", document_version_id="synthetic-version-1", version=1,
        content_fingerprint="synthetic-fingerprint", original_filename="synthetic.txt", index_state="indexed",
    ), **changes)


class CountingDocuments(InMemoryDocumentRepository):
    def __init__(self):
        super().__init__()
        self.single_calls = []

    def get_by_id(self, document_id):
        self.single_calls.append(document_id)
        return super().get_by_id(document_id)


class BatchDocuments(CountingDocuments):
    def __init__(self):
        super().__init__()
        self.batch_calls = []
        self.omit = set()
        self.after_batch = None

    def get_by_ids(self, document_ids):
        self.batch_calls.append(list(document_ids))
        result = {key: replace(self.documents[key]) if key in self.documents else None
                  for key in document_ids if key not in self.omit}
        if self.after_batch is not None:
            self.after_batch()
        return result


def service_fixture(*, edition="cn", mode="interview", documents=None, count=3):
    documents = documents if documents is not None else BatchDocuments()
    settings = Settings(_env_file=None, environment="test", product_edition=edition,
                        database_url=None, redis_url=None)
    sessions = SessionService(settings=settings, document_repository=documents,
                              repository=InMemoryInterviewSessionRepository())
    created = sessions.create_session(user_id=OWNER, title="Synthetic operation")
    records = [documents.save(document(f"synthetic-document-{i}")) for i in range(count)]
    bound = [SessionBoundDocument(
        document_id=record.document_id, document_kind=record.document_kind,
        display_name=record.display_name, status=record.status,
        document_version_id=record.document_version_id, index_state=record.index_state,
        knowledge_collection_id=record.knowledge_collection_id, summary=record.summary,
    ) for record in records]
    binding = replace(created.material_binding, revision=4, knowledge_document_ids=[r.document_id for r in records],
                      bound_documents=bound, confirmed_at_ms=1)
    current = sessions.repository.save_session(replace(created, session_mode=mode, status="live",
                                                       material_binding=binding))
    return sessions, documents, current


def get_session(service, session):
    return service.get_session(user_id=OWNER, session_id=session.session_id)


def metadata_service(documents, edition="cn"):
    result = object.__new__(KnowledgeRetrievalService)
    result.settings = Settings(_env_file=None, environment="test", product_edition=edition,
                               database_url=None, redis_url=None)
    result.document_repository = documents
    return result


def match(document_id="synthetic-document", *, number=0, score=.8):
    return VectorSearchMatch(document_id=document_id, document_kind="knowledge",
                            chunk_id=f"synthetic-chunk-{number}", chunk_index=number,
                            content="Synthetic evidence", score=score,
                            embedding_model="synthetic", rebuild_version=1,
                            metadata={"synthetic": "preserved"})


def metadata_filter():
    return RetrievalFilter(owner_user_id=OWNER, interview_session_id="synthetic-session",
                           document_kinds=["knowledge"], document_ids=["synthetic-document"],
                           document_version_ids=["synthetic-version-1"],
                           knowledge_collection_ids=["synthetic-collection"])


def test_cn_get_session_uses_one_batch_and_preserves_stable_output():
    service, documents, current = service_fixture()
    before = deepcopy(current)
    actual = get_session(service, current)
    assert actual == before
    assert documents.batch_calls == [[r.document_id for r in current.material_binding.bound_documents]]
    assert documents.single_calls == []


def test_cn_get_session_deduplicates_bound_ids_without_changing_bound_order():
    service, documents, current = service_fixture(count=2)
    binding = replace(current.material_binding, bound_documents=[
        current.material_binding.bound_documents[1], current.material_binding.bound_documents[0],
        current.material_binding.bound_documents[1]])
    current = service.repository.save_session(replace(current, material_binding=binding))
    assert get_session(service, current) == current
    assert documents.batch_calls == [["synthetic-document-1", "synthetic-document-0"]]


@pytest.mark.parametrize("edition,mode,batches,singles", [
    ("global", "interview", 0, 3), ("cn", "mock", 0, 0), ("global", "mock", 0, 0),
])
def test_global_and_mock_keep_original_path(edition, mode, batches, singles):
    service, documents, current = service_fixture(edition=edition, mode=mode)
    assert get_session(service, current) == current
    assert len(documents.batch_calls) == batches
    assert len(documents.single_calls) == singles


def test_empty_session_does_not_open_batch_or_document_read():
    service, documents, current = service_fixture(count=0)
    assert get_session(service, current) == current
    assert documents.batch_calls == documents.single_calls == []


def test_repository_without_batch_keeps_unique_id_fallback():
    service, documents, current = service_fixture(documents=CountingDocuments(), count=2)
    binding = replace(current.material_binding, bound_documents=current.material_binding.bound_documents * 2)
    current = service.repository.save_session(replace(current, material_binding=binding))
    assert get_session(service, current) == current
    assert documents.single_calls == ["synthetic-document-0", "synthetic-document-1"]


def test_list_sessions_keeps_existing_seed_and_fallback_contract():
    service, documents, current = service_fixture(count=2)
    assert service.list_sessions(user_id=OWNER) == [current]
    assert documents.batch_calls == []
    assert documents.single_calls == ["synthetic-document-0", "synthetic-document-1"]
    documents.single_calls.clear()
    raw = {key: replace(value) for key, value in documents.documents.items()}
    assert service.list_sessions(user_id=OWNER, document_records=raw) == [current]
    assert documents.batch_calls == documents.single_calls == []


def test_missing_batch_key_stays_absent_without_fallback_revival():
    service, documents, current = service_fixture(count=1)
    documents.omit.add("synthetic-document-0")
    result = get_session(service, current)
    assert result.material_binding.bound_documents[0].status == "deleted"
    assert result.material_binding.bound_documents[0].active is False
    assert documents.single_calls == []


def test_each_get_session_reads_current_version_and_deletion_again():
    service, documents, current = service_fixture(count=1)
    first = get_session(service, current)
    record = documents.documents["synthetic-document-0"]
    documents.save(replace(record, document_version_id="synthetic-version-2", summary="Changed synthetic summary"))
    second = get_session(service, current)
    assert second.material_binding.bound_documents[0].document_version_id == "synthetic-version-2"
    assert second.material_binding.bound_documents[0].summary == "Changed synthetic summary"
    assert first.material_binding.bound_documents[0].document_version_id == "synthetic-version-1"
    documents.save(replace(documents.documents[record.document_id], status="deleted", index_state="deleted"))
    third = get_session(service, current)
    assert third.material_binding.bound_documents[0].active is False
    assert len(documents.batch_calls) == 3
    assert documents.single_calls == []


def test_batch_error_propagates_once_without_single_read_retry():
    service, documents, current = service_fixture(count=1)
    calls = []
    def unavailable(ids):
        calls.append(ids)
        raise RuntimeError("synthetic_batch_unavailable")
    documents.get_by_ids = unavailable
    with pytest.raises(RuntimeError, match="synthetic_batch_unavailable"):
        get_session(service, current)
    assert len(calls) == 1
    assert documents.single_calls == []


@pytest.mark.parametrize("owner,session_id,code", [
    ("synthetic-foreign-owner", None, 403), (OWNER, "synthetic-missing-session", 404),
])
def test_session_authority_is_checked_before_batch(owner, session_id, code):
    service, documents, current = service_fixture()
    with pytest.raises(DomainRequestError) as error:
        service.get_session(user_id=owner, session_id=session_id or current.session_id)
    assert error.value.status_code == code
    assert documents.batch_calls == documents.single_calls == []


def test_cn_metadata_batch_deduplicates_and_preserves_output_and_score_order():
    documents = BatchDocuments()
    documents.save(document())
    matches = [match(number=0, score=.8), match(number=1, score=.9), match(number=2, score=.9)]
    expected = metadata_service(documents, "global")._apply_metadata_filter(matches, filter=metadata_filter())
    documents.single_calls.clear()
    actual = metadata_service(documents)._apply_metadata_filter(iter(matches), filter=metadata_filter())
    assert actual == expected
    assert [item.chunk_id for item in actual] == ["synthetic-chunk-1", "synthetic-chunk-2", "synthetic-chunk-0"]
    assert documents.batch_calls == [["synthetic-document"]]
    assert documents.single_calls == []


def test_cn_metadata_without_batch_reads_each_unique_document_once():
    documents = CountingDocuments()
    documents.save(document())
    matches = [match(number=i) for i in range(6)]
    result = metadata_service(documents)._apply_metadata_filter(matches, filter=metadata_filter())
    assert len(result) == 6
    assert documents.single_calls == ["synthetic-document"]


def test_global_metadata_keeps_original_per_candidate_reads():
    documents = BatchDocuments()
    documents.save(document())
    result = metadata_service(documents, "global")._apply_metadata_filter(
        [match(number=i) for i in range(6)], filter=metadata_filter())
    assert len(result) == 6
    assert documents.batch_calls == []
    assert documents.single_calls == ["synthetic-document"] * 6


@pytest.mark.parametrize("changes", [
    {"owner_user_id": "synthetic-foreign-owner"}, {"status": "deleted"},
    {"index_state": "processing"}, {"document_version_id": "synthetic-version-2"},
    {"document_kind": "resume"}, {"knowledge_collection_id": "synthetic-other-collection"},
])
def test_metadata_authority_and_version_filters_remain(changes):
    documents = BatchDocuments()
    documents.save(document(**changes))
    service = metadata_service(documents)
    assert service._apply_metadata_filter([match()], filter=metadata_filter()) == []
    assert documents.single_calls == []


def test_metadata_missing_batch_entry_is_not_reread_and_next_operation_is_fresh():
    documents = BatchDocuments()
    documents.save(document())
    service = metadata_service(documents)
    documents.omit.add("synthetic-document")
    assert service._apply_metadata_filter([match()], filter=metadata_filter()) == []
    assert documents.single_calls == []
    documents.omit.clear()
    assert len(service._apply_metadata_filter([match()], filter=metadata_filter())) == 1
    documents.save(document(owner_user_id="synthetic-foreign-owner"))
    assert service._apply_metadata_filter([match()], filter=metadata_filter()) == []
    assert len(documents.batch_calls) == 3


def test_metadata_batch_error_is_not_retried_or_masked():
    documents = BatchDocuments()
    documents.get_by_ids = lambda ids: (_ for _ in ()).throw(RuntimeError("synthetic_metadata_unavailable"))
    with pytest.raises(RuntimeError, match="synthetic_metadata_unavailable"):
        metadata_service(documents)._apply_metadata_filter([match()], filter=metadata_filter())
    assert documents.single_calls == []


def test_prefetch_keeps_two_independent_material_reads_and_rejects_late_change():
    sessions, documents, current = service_fixture(count=1)
    service = ChatService(settings=sessions.settings, logger=logging.getLogger("synthetic-batch-prefetch"),
                          session_service=sessions, retrieval_service=SimpleNamespace(),
                          object_storage=SimpleNamespace(), repository=SimpleNamespace(),
                          prompt_template=SimpleNamespace(), prompt_builder=SimpleNamespace(), llm_gateway=SimpleNamespace())
    def retrieve(*, question, **kwargs):
        record = documents.documents["synthetic-document-0"]
        documents.save(replace(record, document_version_id="synthetic-version-2"))
        return RetrievalContext(normalized_question=question, context_text="Synthetic obsolete evidence")
    service._retrieve_context = retrieve
    service.prefetch_question_context(user_id=OWNER, session_id=current.session_id,
                                      question_id="synthetic-question", revision=1, question="Synthetic question")
    assert documents.batch_calls == [["synthetic-document-0"], ["synthetic-document-0"]]
    assert documents.single_calls == []
    assert service._prepared_context == {}


def test_postgres_optional_batch_is_one_statement_current_join_and_explicit_misses(monkeypatch):
    repository = object.__new__(PostgresDocumentRepository)
    calls = []
    expected = document("synthetic-document-b")
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, sql, params): calls.append((sql, params))
        def fetchall(self): return [{**expected.__dict__, "safe_summary": expected.summary}]
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def cursor(self, **kwargs): return Cursor()
    connections = []
    monkeypatch.setattr(repository, "_connect", lambda: connections.append(1) or Connection())
    result = repository.get_by_ids(["synthetic-document-a", "synthetic-document-b", "synthetic-document-a"])
    assert len(connections) == len(calls) == 1
    assert "JOIN material_document_versions v ON v.document_version_id = d.current_version_id" in calls[0][0]
    assert "WHERE d.document_id = ANY(%s)" in calls[0][0]
    assert calls[0][1] == (["synthetic-document-a", "synthetic-document-b"],)
    assert result == {"synthetic-document-a": None, "synthetic-document-b": expected}
    assert repository.get_by_ids([]) == {}
    assert len(connections) == 1


def test_postgres_batch_query_failure_is_not_retried(monkeypatch):
    repository = object.__new__(PostgresDocumentRepository)
    calls = []
    def unavailable():
        calls.append(1)
        raise RuntimeError("synthetic_connection_unavailable")
    monkeypatch.setattr(repository, "_connect", unavailable)
    with pytest.raises(RuntimeError, match="synthetic_connection_unavailable"):
        repository.get_by_ids(["synthetic-document"])
    assert calls == [1]


@pytest.fixture
def isolated_postgres_documents():
    dsn = os.environ.get("OFFERSTEADY_CN_BATCH_TEST_DATABASE_URL", "")
    if not dsn:
        pytest.skip("Dedicated synthetic localhost PostgreSQL not configured")
    params = conninfo_to_dict(dsn)
    assert params.get("host") in {"127.0.0.1", "localhost", "::1"}
    assert params.get("hostaddr") in {None, "127.0.0.1", "localhost", "::1"}
    assert params.get("dbname", "").startswith("synthetic_")
    assert not params.get("service"), "A service alias cannot replace the synthetic target"
    schema = "synthetic_cn_batch_" + uuid4().hex
    with psycopg.connect(dsn) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    settings = Settings(_env_file=None, environment="test", product_edition="cn", redis_url=None,
                        database_url=make_conninfo(dsn, options="-c search_path=" + schema))
    try:
        yield PostgresDocumentRepository(settings)
    finally:
        with psycopg.connect(dsn) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def instrument_postgres_batch(repository, monkeypatch, *, after_select=None):
    original = repository._connect
    connections = []
    statements = []
    class Cursor:
        def __init__(self, actual): self.actual = actual
        def __enter__(self): self.actual.__enter__(); return self
        def __exit__(self, *args): return self.actual.__exit__(*args)
        def __getattr__(self, key): return getattr(self.actual, key)
        def execute(self, statement, params=None):
            statements.append(str(statement).strip().split()[0].upper())
            result = self.actual.execute(statement, params)
            if statements[-1] == "SELECT" and after_select is not None:
                after_select()
            return result
    class Connection:
        def __init__(self, actual): self.actual = actual
        def __enter__(self): self.actual.__enter__(); return self
        def __exit__(self, *args): return self.actual.__exit__(*args)
        def __getattr__(self, key): return getattr(self.actual, key)
        def cursor(self, *args, **kwargs): return Cursor(self.actual.cursor(*args, **kwargs))
    def connect():
        actual = original()
        connections.append(actual)
        return Connection(actual)
    monkeypatch.setattr(repository, "_connect", connect)
    return connections, statements


def test_real_postgres_any_join_and_misses_use_one_closed_read_transaction(isolated_postgres_documents, monkeypatch):
    repository = isolated_postgres_documents
    first = repository.save(document("synthetic-pg-a", object_key="synthetic/pg/a", document_version_id="synthetic-pg-v1"))
    deleted = repository.save(document("synthetic-pg-deleted", object_key="synthetic/pg/deleted", status="deleted",
                                       deleted_at_ms=2, index_state="deleted"))
    connections, statements = instrument_postgres_batch(repository, monkeypatch)
    batch = repository.get_by_ids([first.document_id, "synthetic-pg-missing", deleted.document_id, first.document_id])
    assert list(batch) == [first.document_id, "synthetic-pg-missing", deleted.document_id]
    assert batch[first.document_id] == first
    assert batch[deleted.document_id] == deleted
    assert batch["synthetic-pg-missing"] is None
    assert statements == ["SELECT"]
    assert len(connections) == 1 and connections[0].closed


def test_real_postgres_batch_snapshot_is_current_statement_then_next_call_sees_change(isolated_postgres_documents, monkeypatch):
    repository = isolated_postgres_documents
    first = repository.save(document("synthetic-pg-statement", object_key="synthetic/pg/statement/v1"))
    writer = object.__new__(PostgresDocumentRepository)
    writer.settings = repository.settings
    changed = replace(first, document_version_id="synthetic-pg-statement-v2", object_key="synthetic/pg/statement/v2",
                      version=2, summary="Synthetic second version")
    already_changed = []
    def update_after_statement():
        if not already_changed:
            already_changed.append(1)
            writer.save(changed)
    connections, statements = instrument_postgres_batch(repository, monkeypatch, after_select=update_after_statement)
    original_snapshot = repository.get_by_ids([first.document_id])
    next_snapshot = repository.get_by_ids([first.document_id])
    assert original_snapshot[first.document_id].document_version_id == first.document_version_id
    assert next_snapshot[first.document_id].document_version_id == changed.document_version_id
    assert next_snapshot[first.document_id].summary == changed.summary
    assert statements == ["SELECT", "SELECT"]
    assert len(connections) == 2 and all(connection.closed for connection in connections)


def test_real_postgres_failure_closes_transaction_and_next_read_can_succeed(isolated_postgres_documents, monkeypatch):
    repository = isolated_postgres_documents
    record = repository.save(document("synthetic-pg-recovery", object_key="synthetic/pg/recovery"))
    connections, statements = instrument_postgres_batch(repository, monkeypatch)
    original_sql = repository._select_sql
    monkeypatch.setattr(repository, "_select_sql", lambda where: "SELECT synthetic_absent_column FROM material_documents " + where)
    with pytest.raises(psycopg.Error):
        repository.get_by_ids([record.document_id])
    assert len(connections) == 1 and connections[0].closed
    monkeypatch.setattr(repository, "_select_sql", original_sql)
    assert repository.get_by_ids([record.document_id])[record.document_id] == record
    assert len(connections) == 2 and all(connection.closed for connection in connections)
