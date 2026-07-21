from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.material_formats import MaterialKind
from app.ports.document_processing import EmbeddedChunk, VectorSearchMatch, VectorStorePort
from app.ports.document_repository import DocumentRecord, DocumentRepository
from app.schemas.material_upload import CreatedKnowledgeCollectionResponse


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_tables()

    def save(self, document: DocumentRecord) -> DocumentRecord:
        fingerprint = document.content_fingerprint or hashlib.sha256(document.object_key.encode("utf-8")).hexdigest()
        version_id = document.document_version_id or f"version-{document.document_id}"
        object_id = document.object_id or hashlib.sha256(f"{document.document_id}:{version_id}".encode("utf-8")).hexdigest()[:32]
        version = document.version or 1
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO material_documents (document_id, owner_user_id, document_kind, display_name, current_version_id, status, knowledge_collection_id, created_at_ms, updated_at_ms, deleted_at_ms)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (document_id) DO UPDATE SET display_name = EXCLUDED.display_name, current_version_id = EXCLUDED.current_version_id, status = EXCLUDED.status, knowledge_collection_id = EXCLUDED.knowledge_collection_id, updated_at_ms = EXCLUDED.updated_at_ms, deleted_at_ms = EXCLUDED.deleted_at_ms
                    """,
                    (document.document_id, document.owner_user_id, document.document_kind, document.display_name, version_id, document.status, document.knowledge_collection_id, document.created_at_ms, document.updated_at_ms, document.deleted_at_ms),
                )
                cursor.execute(
                    """
                    INSERT INTO material_document_versions (document_version_id, document_id, owner_user_id, document_kind, display_name, original_filename, file_kind, content_type, size_bytes, object_key, object_id, content_fingerprint, version, lifecycle_status, index_state, page_count, token_count, chunk_count, safe_summary, knowledge_collection_id, created_at_ms, updated_at_ms, deleted_at_ms)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,NULL,NULL,%s,%s,%s,%s,%s)
                    ON CONFLICT (document_version_id) DO UPDATE SET display_name = EXCLUDED.display_name, lifecycle_status = EXCLUDED.lifecycle_status, index_state = EXCLUDED.index_state, safe_summary = EXCLUDED.safe_summary, knowledge_collection_id = EXCLUDED.knowledge_collection_id, updated_at_ms = EXCLUDED.updated_at_ms, deleted_at_ms = EXCLUDED.deleted_at_ms
                    """,
                    (version_id, document.document_id, document.owner_user_id, document.document_kind, document.display_name, document.original_filename or document.display_name, document.file_kind, document.content_type, document.size_bytes, document.object_key, object_id, fingerprint, version, document.status, document.index_state or "queued", document.summary, document.knowledge_collection_id, document.created_at_ms, document.updated_at_ms, document.deleted_at_ms),
                )
            connection.commit()
        return replace(document, document_version_id=version_id, object_id=object_id, version=version, content_fingerprint=fingerprint)

    def get_by_id(self, document_id: str) -> DocumentRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(self._select_sql("WHERE d.document_id = %s"), (document_id,))
            row = cursor.fetchone()
        return self._row_to_record(row) if row else None

    def list_for_user(self, *, user_id: str, document_kind: MaterialKind | None = None, knowledge_collection_id: str | None = None, include_deleted: bool = False) -> list[DocumentRecord]:
        clauses = ["d.owner_user_id = %s"]
        params: list[Any] = [user_id]
        if document_kind is not None:
            clauses.append("d.document_kind = %s")
            params.append(document_kind)
        if knowledge_collection_id is not None:
            clauses.append("d.knowledge_collection_id = %s")
            params.append(knowledge_collection_id)
        if not include_deleted:
            clauses.append("d.status <> 'deleted'")
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(self._select_sql("WHERE " + " AND ".join(clauses)) + " ORDER BY d.updated_at_ms DESC", params)
            rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    def _select_sql(self, where_sql: str) -> str:
        return f"""
            SELECT d.document_id, d.owner_user_id, d.document_kind, d.display_name, d.status, d.knowledge_collection_id, d.created_at_ms, d.updated_at_ms, d.deleted_at_ms,
                   v.document_version_id, v.file_kind, v.content_type, v.size_bytes, v.object_key, v.object_id, v.content_fingerprint, v.version, v.original_filename, v.index_state, v.safe_summary
            FROM material_documents d
            JOIN material_document_versions v ON v.document_version_id = d.current_version_id
            {where_sql}
        """

    def _row_to_record(self, row: dict[str, Any]) -> DocumentRecord:
        return DocumentRecord(
            document_id=row["document_id"],
            owner_user_id=row["owner_user_id"],
            document_kind=row["document_kind"],
            display_name=row["display_name"],
            file_kind=row["file_kind"],
            content_type=row["content_type"],
            size_bytes=int(row["size_bytes"]),
            object_key=row["object_key"],
            status=row["status"],
            knowledge_collection_id=row["knowledge_collection_id"],
            processing_requested_at_ms=None,
            deleted_at_ms=row["deleted_at_ms"],
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            summary=row["safe_summary"],
            object_id=row["object_id"],
            document_version_id=row["document_version_id"],
            version=int(row["version"]),
            content_fingerprint=row["content_fingerprint"],
            original_filename=row["original_filename"],
            index_state=row["index_state"],
        )

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required")
        return psycopg.connect(self.settings.database_url, connect_timeout=self.settings.database_connect_timeout_seconds, application_name=self.settings.database_application_name)

    def _ensure_tables(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE TABLE IF NOT EXISTS material_documents (document_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, document_kind TEXT NOT NULL, display_name TEXT NOT NULL, current_version_id TEXT NULL, status TEXT NOT NULL, knowledge_collection_id TEXT NULL, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL, deleted_at_ms BIGINT NULL)")
                cursor.execute("CREATE TABLE IF NOT EXISTS material_document_versions (document_version_id TEXT PRIMARY KEY, document_id TEXT NOT NULL, owner_user_id TEXT NOT NULL, document_kind TEXT NOT NULL, display_name TEXT NOT NULL, original_filename TEXT NOT NULL, file_kind TEXT NOT NULL, content_type TEXT NOT NULL, size_bytes BIGINT NOT NULL, object_key TEXT NOT NULL UNIQUE, object_id TEXT NOT NULL, content_fingerprint TEXT NOT NULL, version INTEGER NOT NULL, lifecycle_status TEXT NOT NULL, index_state TEXT NOT NULL, page_count INTEGER NULL, token_count INTEGER NULL, chunk_count INTEGER NULL, safe_summary TEXT NULL, knowledge_collection_id TEXT NULL, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL, deleted_at_ms BIGINT NULL)")
            connection.commit()


class PostgresKnowledgeCollectionStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_table()

    @property
    def collections(self) -> dict[str, CreatedKnowledgeCollectionResponse]:
        return {item.collection_id: item for item in self.list_collections()}

    def get_collection(self, collection_id: str) -> CreatedKnowledgeCollectionResponse | None:
        return self.collections.get(collection_id)

    def save_collection(self, collection: CreatedKnowledgeCollectionResponse) -> CreatedKnowledgeCollectionResponse:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO material_knowledge_collections (collection_id, owner_user_id, name, created_at_ms, updated_at_ms) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (collection_id) DO UPDATE SET name = EXCLUDED.name, updated_at_ms = EXCLUDED.updated_at_ms",
                    (collection.collection_id, collection.owner_user_id, collection.name, collection.created_at_ms, collection.updated_at_ms),
                )
            connection.commit()
        return collection

    def list_collections(self) -> list[CreatedKnowledgeCollectionResponse]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT collection_id, owner_user_id, name, created_at_ms, updated_at_ms FROM material_knowledge_collections ORDER BY updated_at_ms DESC")
            rows = cursor.fetchall()
        return [CreatedKnowledgeCollectionResponse(collectionId=row["collection_id"], ownerUserId=row["owner_user_id"], name=row["name"], createdAtMs=int(row["created_at_ms"]), updatedAtMs=int(row["updated_at_ms"])) for row in rows]

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required")
        return psycopg.connect(self.settings.database_url, connect_timeout=self.settings.database_connect_timeout_seconds, application_name=f"{self.settings.database_application_name}-collections")

    def _ensure_table(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE TABLE IF NOT EXISTS material_knowledge_collections (collection_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, name TEXT NOT NULL, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL)")
            connection.commit()


class PostgresRuntimeVectorStore(VectorStorePort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_table()

    def upsert_document_chunks(self, *, document_id: str, document_kind: MaterialKind, chunks: list[EmbeddedChunk], embedding_model: str, rebuild_version: int) -> int:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM material_runtime_vector_chunks WHERE document_id = %s", (document_id,))
                for chunk in chunks:
                    metadata = dict(chunk.metadata)
                    cursor.execute(
                        "INSERT INTO material_runtime_vector_chunks (chunk_row_id, owner_user_id, document_id, document_version_id, document_kind, knowledge_collection_id, chunk_id, chunk_index, content, vector_json, embedding_model, rebuild_version, metadata_json, created_at_ms) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,(extract(epoch from now()) * 1000)::bigint)",
                        (f"{document_id}:{rebuild_version}:{chunk.chunk_id}", metadata.get("ownerUserId") or "", document_id, metadata.get("documentVersionId") or "", document_kind, metadata.get("knowledgeCollectionId") or None, chunk.chunk_id, chunk.index, chunk.content, Jsonb(chunk.vector), embedding_model, rebuild_version, Jsonb(metadata)),
                    )
            connection.commit()
        return len(chunks)

    def next_rebuild_version(self, *, document_id: str) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(rebuild_version), 0) + 1 FROM material_runtime_vector_chunks WHERE document_id = %s", (document_id,))
            row = cursor.fetchone()
        return int(row[0] if row else 1)

    def search_similar(self, *, query_vector: list[float], top_k: int, document_kinds: list[MaterialKind] | None = None, document_ids: list[str] | None = None, knowledge_collection_ids: list[str] | None = None) -> list[VectorSearchMatch]:
        clauses: list[str] = []
        params: list[Any] = []
        if document_kinds:
            clauses.append("document_kind = ANY(%s)")
            params.append(document_kinds)
        if document_ids:
            clauses.append("document_id = ANY(%s)")
            params.append(document_ids)
        if knowledge_collection_ids:
            clauses.append("knowledge_collection_id = ANY(%s)")
            params.append(knowledge_collection_ids)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SELECT document_id, document_kind, chunk_id, chunk_index, content, vector_json, embedding_model, rebuild_version, metadata_json FROM material_runtime_vector_chunks {where}", params)
            rows = cursor.fetchall()
        matches = [VectorSearchMatch(document_id=row["document_id"], document_kind=row["document_kind"], chunk_id=row["chunk_id"], chunk_index=int(row["chunk_index"]), content=row["content"], score=self._cosine_similarity(query_vector, list(row["vector_json"] or [])), embedding_model=row["embedding_model"], rebuild_version=int(row["rebuild_version"]), metadata=dict(row["metadata_json"] or {})) for row in rows]
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[: max(1, top_k)]

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required")
        return psycopg.connect(self.settings.database_url, connect_timeout=self.settings.database_connect_timeout_seconds, application_name=f"{self.settings.database_application_name}-vectors")

    def _ensure_table(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute("CREATE TABLE IF NOT EXISTS material_runtime_vector_chunks (chunk_row_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, document_id TEXT NOT NULL, document_version_id TEXT NOT NULL, document_kind TEXT NOT NULL, knowledge_collection_id TEXT NULL, chunk_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, content TEXT NOT NULL, vector_json JSONB NOT NULL, embedding_model TEXT NOT NULL, rebuild_version INTEGER NOT NULL, metadata_json JSONB NOT NULL, created_at_ms BIGINT NOT NULL)")
            connection.commit()

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        numerator = sum(left[index] * right[index] for index in range(size))
        left_norm = math.sqrt(sum(value * value for value in left[:size]))
        right_norm = math.sqrt(sum(value * value for value in right[:size]))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
