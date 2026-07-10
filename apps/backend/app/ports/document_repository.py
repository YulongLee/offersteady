from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.material_formats import MaterialFormatId, MaterialKind


DocumentLifecycleStatus = Literal[
    "pending_upload",
    "uploaded",
    "processing_requested",
    "processing",
    "ready",
    "failed",
    "deleting",
    "deleted",
]
DocumentIndexState = Literal["not_indexed", "queued", "processing", "indexed", "failed", "disabled", "deleted"]


@dataclass
class DocumentRecord:
    document_id: str
    owner_user_id: str
    document_kind: MaterialKind
    display_name: str
    file_kind: MaterialFormatId
    content_type: str
    size_bytes: int
    object_key: str
    status: DocumentLifecycleStatus
    knowledge_collection_id: str | None
    processing_requested_at_ms: int | None
    deleted_at_ms: int | None
    created_at_ms: int
    updated_at_ms: int
    summary: str | None
    object_id: str | None = None
    document_version_id: str | None = None
    version: int | None = None
    content_fingerprint: str | None = None
    original_filename: str | None = None
    index_state: DocumentIndexState | None = None


class DocumentRepository(Protocol):
    def save(self, document: DocumentRecord) -> DocumentRecord: ...

    def get_by_id(self, document_id: str) -> DocumentRecord | None: ...

    def list_for_user(
        self,
        *,
        user_id: str,
        document_kind: MaterialKind | None = None,
        knowledge_collection_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[DocumentRecord]: ...


@dataclass
class PersistedMaterialDocument:
    document_id: str
    owner_user_id: str
    document_kind: MaterialKind
    display_name: str
    current_version_id: str | None
    status: DocumentLifecycleStatus
    knowledge_collection_id: str | None
    created_at_ms: int
    updated_at_ms: int
    deleted_at_ms: int | None


@dataclass
class PersistedMaterialVersion:
    document_version_id: str
    document_id: str
    owner_user_id: str
    document_kind: MaterialKind
    display_name: str
    original_filename: str
    file_kind: MaterialFormatId
    content_type: str
    size_bytes: int
    object_key: str
    object_id: str
    content_fingerprint: str
    version: int
    lifecycle_status: DocumentLifecycleStatus
    index_state: DocumentIndexState
    page_count: int | None
    token_count: int | None
    chunk_count: int | None
    safe_summary: str | None
    knowledge_collection_id: str | None
    created_at_ms: int
    updated_at_ms: int
    deleted_at_ms: int | None


class MaterialDocumentRepository(Protocol):
    def save_document(self, document: PersistedMaterialDocument) -> PersistedMaterialDocument: ...

    def save_version(self, version: PersistedMaterialVersion) -> PersistedMaterialVersion: ...

    def get_document_for_user(self, *, owner_user_id: str, document_id: str) -> PersistedMaterialDocument | None: ...

    def get_version_for_user(self, *, owner_user_id: str, document_version_id: str) -> PersistedMaterialVersion | None: ...

    def list_documents_for_user(
        self,
        *,
        owner_user_id: str,
        document_kind: MaterialKind | None = None,
        knowledge_collection_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[PersistedMaterialDocument]: ...

    def list_versions_for_document(
        self,
        *,
        owner_user_id: str,
        document_id: str,
        include_deleted: bool = False,
    ) -> list[PersistedMaterialVersion]: ...

    def update_version_status(
        self,
        *,
        owner_user_id: str,
        document_version_id: str,
        lifecycle_status: DocumentLifecycleStatus | None = None,
        index_state: DocumentIndexState | None = None,
        safe_summary: str | None = None,
        updated_at_ms: int,
    ) -> PersistedMaterialVersion | None: ...

    def disable_version(
        self,
        *,
        owner_user_id: str,
        document_version_id: str,
        updated_at_ms: int,
    ) -> PersistedMaterialVersion | None: ...

    def soft_delete_document(
        self,
        *,
        owner_user_id: str,
        document_id: str,
        deleted_at_ms: int,
    ) -> PersistedMaterialDocument | None: ...
