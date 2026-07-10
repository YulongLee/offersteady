from __future__ import annotations

from dataclasses import replace

from app.ports.document_repository import (
    DocumentRecord,
    DocumentRepository,
    PersistedMaterialDocument,
    PersistedMaterialVersion,
)


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self) -> None:
        self.documents: dict[str, DocumentRecord] = {}

    def save(self, document: DocumentRecord) -> DocumentRecord:
        stored = replace(document)
        self.documents[stored.document_id] = stored
        return replace(stored)

    def get_by_id(self, document_id: str) -> DocumentRecord | None:
        record = self.documents.get(document_id)
        return replace(record) if record else None

    def list_for_user(
        self,
        *,
        user_id: str,
        document_kind=None,
        knowledge_collection_id=None,
        include_deleted=False,
    ) -> list[DocumentRecord]:
        records = [record for record in self.documents.values() if record.owner_user_id == user_id]
        if document_kind is not None:
            records = [record for record in records if record.document_kind == document_kind]
        if knowledge_collection_id is not None:
            records = [record for record in records if record.knowledge_collection_id == knowledge_collection_id]
        if not include_deleted:
            records = [record for record in records if record.status != "deleted"]
        return [replace(record) for record in sorted(records, key=lambda item: item.updated_at_ms, reverse=True)]


class InMemoryMaterialDocumentRepository:
    def __init__(self) -> None:
        self.documents: dict[str, PersistedMaterialDocument] = {}
        self.versions: dict[str, PersistedMaterialVersion] = {}

    def save_document(self, document: PersistedMaterialDocument) -> PersistedMaterialDocument:
        stored = replace(document)
        self.documents[stored.document_id] = stored
        return replace(stored)

    def save_version(self, version: PersistedMaterialVersion) -> PersistedMaterialVersion:
        stored = replace(version)
        self.versions[stored.document_version_id] = stored
        document = self.documents.get(stored.document_id)
        if document and document.owner_user_id == stored.owner_user_id:
            self.documents[document.document_id] = replace(
                document,
                current_version_id=stored.document_version_id,
                status=stored.lifecycle_status,
                updated_at_ms=stored.updated_at_ms,
            )
        return replace(stored)

    def get_document_for_user(self, *, owner_user_id: str, document_id: str) -> PersistedMaterialDocument | None:
        record = self.documents.get(document_id)
        if not record or record.owner_user_id != owner_user_id:
            return None
        return replace(record)

    def get_version_for_user(self, *, owner_user_id: str, document_version_id: str) -> PersistedMaterialVersion | None:
        record = self.versions.get(document_version_id)
        if not record or record.owner_user_id != owner_user_id:
            return None
        return replace(record)

    def list_documents_for_user(
        self,
        *,
        owner_user_id: str,
        document_kind=None,
        knowledge_collection_id=None,
        include_deleted=False,
    ) -> list[PersistedMaterialDocument]:
        records = [record for record in self.documents.values() if record.owner_user_id == owner_user_id]
        if document_kind is not None:
            records = [record for record in records if record.document_kind == document_kind]
        if knowledge_collection_id is not None:
            records = [record for record in records if record.knowledge_collection_id == knowledge_collection_id]
        if not include_deleted:
            records = [record for record in records if record.status != "deleted"]
        return [replace(record) for record in sorted(records, key=lambda item: item.updated_at_ms, reverse=True)]

    def list_versions_for_document(
        self,
        *,
        owner_user_id: str,
        document_id: str,
        include_deleted=False,
    ) -> list[PersistedMaterialVersion]:
        records = [
            record for record in self.versions.values()
            if record.owner_user_id == owner_user_id and record.document_id == document_id
        ]
        if not include_deleted:
            records = [record for record in records if record.lifecycle_status != "deleted"]
        return [replace(record) for record in sorted(records, key=lambda item: item.version, reverse=True)]

    def update_version_status(
        self,
        *,
        owner_user_id: str,
        document_version_id: str,
        lifecycle_status=None,
        index_state=None,
        safe_summary=None,
        updated_at_ms: int,
    ) -> PersistedMaterialVersion | None:
        record = self.get_version_for_user(owner_user_id=owner_user_id, document_version_id=document_version_id)
        if not record:
            return None
        next_record = replace(
            record,
            lifecycle_status=lifecycle_status or record.lifecycle_status,
            index_state=index_state or record.index_state,
            safe_summary=safe_summary if safe_summary is not None else record.safe_summary,
            updated_at_ms=updated_at_ms,
        )
        self.versions[next_record.document_version_id] = next_record
        document = self.documents.get(next_record.document_id)
        if document and document.owner_user_id == owner_user_id and document.current_version_id == next_record.document_version_id:
            self.documents[document.document_id] = replace(document, status=next_record.lifecycle_status, updated_at_ms=updated_at_ms)
        return replace(next_record)

    def disable_version(self, *, owner_user_id: str, document_version_id: str, updated_at_ms: int) -> PersistedMaterialVersion | None:
        return self.update_version_status(
            owner_user_id=owner_user_id,
            document_version_id=document_version_id,
            index_state="disabled",
            safe_summary="已停用，不参与后续面试检索。",
            updated_at_ms=updated_at_ms,
        )

    def soft_delete_document(self, *, owner_user_id: str, document_id: str, deleted_at_ms: int) -> PersistedMaterialDocument | None:
        document = self.get_document_for_user(owner_user_id=owner_user_id, document_id=document_id)
        if not document:
            return None
        deleted = replace(document, status="deleted", deleted_at_ms=deleted_at_ms, updated_at_ms=deleted_at_ms)
        self.documents[deleted.document_id] = deleted
        for version in list(self.versions.values()):
            if version.owner_user_id == owner_user_id and version.document_id == document_id:
                self.versions[version.document_version_id] = replace(
                    version,
                    lifecycle_status="deleted",
                    index_state="deleted",
                    deleted_at_ms=deleted_at_ms,
                    updated_at_ms=deleted_at_ms,
                )
        return replace(deleted)
