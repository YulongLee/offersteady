from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING
from uuid import uuid4

from app.core.errors import DomainRequestError
from app.core.config import get_settings
from app.material_formats import (
    MaterialFormatId,
    MaterialKind,
    detect_material_format,
    is_material_mime_allowed,
    material_upload_accept,
    material_upload_formats,
    material_upload_label,
)
from app.ports.commercial_hardening import CommercialHardeningRepository, CommercialJobRecord, MaterialArtifactRecord
from app.ports.document_repository import DocumentRecord, DocumentRepository
from app.ports.storage import FileStoragePort
from app.schemas.document_service import (
    CompleteDocumentUploadResponse,
    DocumentProcessingHandoffResponse,
    DocumentRecordResponse,
    DocumentUploadIntentResponse,
    DocumentValidationPolicyResponse,
)
from app.schemas.material_upload import CreatedKnowledgeCollectionResponse
from app.services.material_deletion import InMemoryMaterialDeletionScheduler
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.commercial_hardening import artifact_id, job_id

if TYPE_CHECKING:
    from app.services.document_processing import DocumentProcessingService


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass
class InMemoryKnowledgeCollectionStore:
    collections: dict[str, CreatedKnowledgeCollectionResponse] = field(default_factory=dict)


@dataclass
class DocumentService:
    storage: FileStoragePort
    repository: DocumentRepository
    knowledge_store: InMemoryKnowledgeCollectionStore
    processing_service: DocumentProcessingService | None = None
    deletion_scheduler: InMemoryMaterialDeletionScheduler | None = None
    commercial_repository: CommercialHardeningRepository | None = None
    max_file_size_bytes: int = 20 * 1024 * 1024

    def validation_policy(self) -> DocumentValidationPolicyResponse:
        formats = material_upload_formats()
        return DocumentValidationPolicyResponse(
            maxFileSizeBytes=self.max_file_size_bytes,
            acceptedExtensions=[extension for item in formats for extension in item["extensions"]],
            acceptedMimeTypes=[mime for item in formats for mime in item["mimeTypes"]],
            label=material_upload_label(),
        )

    def _validate_file(self, *, filename: str, content_type: str, size_bytes: int) -> MaterialFormatId:
        if size_bytes > self.max_file_size_bytes:
            raise DomainRequestError("document-service", "create-upload-intent", f"文件大小不能超过 {self.max_file_size_bytes // (1024 * 1024)} MB。")
        file_kind = detect_material_format(filename)
        if file_kind is None or not is_material_mime_allowed(file_kind, content_type):
            raise DomainRequestError("document-service", "create-upload-intent", f"当前仅支持 {material_upload_label()} 文件上传。")
        return file_kind

    def create_upload_intent(
        self,
        *,
        user_id: str,
        document_kind: MaterialKind,
        filename: str,
        content_type: str,
        size_bytes: int,
        knowledge_collection_id: str | None = None,
    ) -> DocumentUploadIntentResponse:
        file_kind = self._validate_file(filename=filename, content_type=content_type, size_bytes=size_bytes)
        reservation = self.storage.create_upload_intent(
            user_id=user_id,
            material_kind=document_kind,
            filename=filename,
            file_kind=file_kind,
            content_type=content_type,
        )
        return DocumentUploadIntentResponse(
            intentId=reservation.intent_id,
            userId=reservation.user_id,
            documentKind=reservation.material_kind,
            filename=reservation.filename,
            fileKind=reservation.file_kind,
            contentType=reservation.content_type,
            objectKey=reservation.object_key,
            uploadMethod=reservation.upload_method,
            uploadUrl=reservation.upload_url,
            uploadFields=reservation.upload_fields,
            issuedAtMs=reservation.issued_at_ms,
            expiresAtMs=reservation.expires_at_ms,
        )

    def save_upload_bytes(
        self,
        *,
        user_id: str,
        intent_id: str,
        object_key: str,
        content_type: str,
        payload: bytes,
    ) -> dict[str, int | str]:
        if len(payload) > self.max_file_size_bytes:
            raise DomainRequestError("document-service", "proxy-upload", f"文件大小不能超过 {self.max_file_size_bytes // (1024 * 1024)} MB。")
        confirmed = self.storage.save_intent_object(
            user_id=user_id,
            intent_id=intent_id,
            object_key=object_key,
            content_type=content_type,
            payload=payload,
            etag=f"proxy:{len(payload)}",
        )
        return {"objectKey": confirmed.object_key, "sizeBytes": confirmed.size_bytes, "etag": confirmed.etag or ""}

    def complete_upload(
        self,
        *,
        user_id: str,
        intent_id: str,
        object_key: str,
        content_type: str,
        size_bytes: int,
        etag: str | None,
        content_sha256: str | None = None,
        knowledge_collection_id: str | None = None,
    ) -> CompleteDocumentUploadResponse:
        confirmed = self.storage.confirm_uploaded_object(
            user_id=user_id,
            intent_id=intent_id,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            etag=etag,
            content_sha256=content_sha256,
        )
        if confirmed.material_kind == "knowledge":
            self._require_collection_access(user_id=user_id, collection_id=knowledge_collection_id)
        if confirmed.document_id:
            existing = self.repository.get_by_id(confirmed.document_id)
            if existing is not None:
                if existing.owner_user_id != user_id:
                    raise DomainRequestError("document-service", "complete-upload", "不能确认其他用户的文档。", 403)
                return CompleteDocumentUploadResponse(document=self._to_response(existing))
        now_ms = confirmed.confirmed_at_ms
        document = self.repository.save(
            DocumentRecord(
                document_id=confirmed.document_id or f"document-{uuid4().hex}",
                owner_user_id=user_id,
                document_kind=confirmed.material_kind,
                display_name=confirmed.filename,
                file_kind=confirmed.file_kind,
                content_type=confirmed.content_type,
                size_bytes=confirmed.size_bytes,
                object_key=confirmed.object_key,
                status="processing_requested",
                knowledge_collection_id=knowledge_collection_id,
                processing_requested_at_ms=now_ms,
                deleted_at_ms=None,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
                summary="文件已上传，后台正在建立可供 AI 使用的文档索引。",
                object_id=confirmed.object_id,
                document_version_id=confirmed.document_version_id,
                version=1,
                content_fingerprint=confirmed.content_fingerprint,
                original_filename=confirmed.filename,
                index_state="queued",
            )
        )
        self._record_original_artifact(document=document, verified_at_ms=now_ms)
        if self.processing_service is not None:
            self.processing_service.submit_document(document)
        return CompleteDocumentUploadResponse(document=self._to_response(document))

    def list_documents(
        self,
        *,
        user_id: str,
        document_kind: MaterialKind | None = None,
        knowledge_collection_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[DocumentRecordResponse]:
        if knowledge_collection_id is not None:
            self._require_collection_access(user_id=user_id, collection_id=knowledge_collection_id)
        return [
            self._to_response(record)
            for record in self.repository.list_for_user(
                user_id=user_id,
                document_kind=document_kind,
                knowledge_collection_id=knowledge_collection_id,
                include_deleted=include_deleted,
            )
        ]

    def get_document(self, *, user_id: str, document_id: str) -> DocumentRecordResponse:
        record = self.repository.get_by_id(document_id)
        if record is None:
            raise DomainRequestError("document-service", "get-document", "文档不存在。", 404)
        if record.owner_user_id != user_id:
            raise DomainRequestError("document-service", "get-document", "不能查看其他用户的文档。", 403)
        return self._to_response(record)

    def delete_document(self, *, user_id: str, document_id: str) -> DocumentRecordResponse:
        record = self.repository.get_by_id(document_id)
        if record is None:
            raise DomainRequestError("document-service", "delete-document", "文档不存在。", 404)
        if record.owner_user_id != user_id:
            raise DomainRequestError("document-service", "delete-document", "不能删除其他用户的文档。", 403)
        if record.status == "deleted":
            return self._to_response(record)
        deleting = DocumentRecord(
            **{**record.__dict__, "status": "deleted", "deleted_at_ms": _now_ms(), "updated_at_ms": _now_ms(), "summary": "文档已删除，不再用于面试或后续处理。"}
        )
        saved = self.repository.save(deleting)
        self._enqueue_deletion_job(document=saved, deleted_at_ms=saved.deleted_at_ms or _now_ms())
        if self.deletion_scheduler is not None:
            self.deletion_scheduler.schedule_document_deletion(document=saved, deleted_at_ms=saved.deleted_at_ms or _now_ms())
        else:
            self.storage.delete_object(object_key=saved.object_key)
        return self._to_response(saved)

    def list_processing_handoffs(self, *, user_id: str | None = None) -> list[DocumentProcessingHandoffResponse]:
        records = self.repository.list_for_user(user_id=user_id, include_deleted=False) if user_id else list(self.repository.documents.values())  # type: ignore[attr-defined]
        handoffs = [record for record in records if record.status in {"processing_requested", "processing", "ready", "failed"}]
        return [
            DocumentProcessingHandoffResponse(
                documentId=record.document_id,
                ownerUserId=record.owner_user_id,
                documentKind=record.document_kind,
                objectKey=record.object_key,
                status=record.status,  # type: ignore[arg-type]
                requestedAtMs=record.processing_requested_at_ms,
            )
            for record in handoffs
        ]

    def create_knowledge_collection(self, *, user_id: str, name: str) -> CreatedKnowledgeCollectionResponse:
        now_ms = _now_ms()
        collection = CreatedKnowledgeCollectionResponse(
            collectionId=f"collection-{uuid4().hex}",
            ownerUserId=user_id,
            name=name,
            createdAtMs=now_ms,
            updatedAtMs=now_ms,
        )
        if hasattr(self.knowledge_store, "save_collection"):
            self.knowledge_store.save_collection(collection)  # type: ignore[attr-defined]
        else:
            self.knowledge_store.collections[collection.collection_id] = collection
        return collection

    def create_pasted_job_description(self, *, user_id: str, text: str, display_name: str | None) -> CompleteDocumentUploadResponse:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise DomainRequestError("job-description", "create-text", "JD 文本不能为空。")
        now_ms = _now_ms()
        document_id = f"document-{uuid4().hex}"
        document_version_id = f"version-{uuid4().hex}"
        key_factory = MaterialObjectKeyFactory(get_settings())
        object_id = key_factory.new_object_id()
        title = (display_name or cleaned_text.splitlines()[0][:48] or "职位 JD 文本").strip()
        markdown = f"# {title}\n\n{cleaned_text}\n"
        payload = markdown.encode("utf-8")
        object_key = key_factory.original_key(
            owner_user_id=user_id,
            document_kind="job_description",
            document_id=document_id,
            document_version_id=document_version_id,
            object_id=object_id,
            file_kind="md",
        )
        self.storage.save_object_bytes(
            object_key=object_key,
            payload=payload,
            content_type="text/markdown; charset=utf-8",
        )
        document = self.repository.save(
            DocumentRecord(
                document_id=document_id,
                owner_user_id=user_id,
                document_kind="job_description",
                display_name=title,
                file_kind="md",
                content_type="text/markdown; charset=utf-8",
                size_bytes=len(payload),
                object_key=object_key,
                status="processing_requested",
                knowledge_collection_id=None,
                processing_requested_at_ms=now_ms,
                deleted_at_ms=None,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
                summary="文本已保存，等待提取岗位职责与技能要求。",
                object_id=object_id,
                document_version_id=document_version_id,
                version=1,
                content_fingerprint=hashlib.sha256(payload).hexdigest(),
                original_filename=f"{title[:80]}.md",
                index_state="queued",
            )
        )
        self._record_original_artifact(document=document, verified_at_ms=now_ms)
        if self.processing_service is not None:
            self.processing_service.submit_document(document)
        return CompleteDocumentUploadResponse(document=self._to_response(document))

    def _record_original_artifact(self, *, document: DocumentRecord, verified_at_ms: int) -> None:
        if self.commercial_repository is None or not document.document_version_id:
            return
        self.commercial_repository.save_artifact(
            MaterialArtifactRecord(
                artifact_id=artifact_id(),
                owner_user_id=document.owner_user_id,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                document_kind=document.document_kind,
                artifact_kind="original",
                object_key=document.object_key,
                sync_status="synced",
                required=True,
                content_type=document.content_type,
                size_bytes=document.size_bytes,
                sha256=document.content_fingerprint,
                verified_at_ms=verified_at_ms,
                created_at_ms=verified_at_ms,
                updated_at_ms=verified_at_ms,
            )
        )

    def _enqueue_deletion_job(self, *, document: DocumentRecord, deleted_at_ms: int) -> None:
        if self.commercial_repository is None:
            return
        object_keys = [document.object_key]
        if document.document_version_id:
            key_factory = MaterialObjectKeyFactory(get_settings())
            object_keys.extend(
                [
                    key_factory.processed_artifact_key(
                        owner_user_id=document.owner_user_id,
                        document_kind=document.document_kind,
                        document_id=document.document_id,
                        document_version_id=document.document_version_id,
                        artifact_kind="normalized_markdown",
                    ),
                    key_factory.processed_artifact_key(
                        owner_user_id=document.owner_user_id,
                        document_kind=document.document_kind,
                        document_id=document.document_id,
                        document_version_id=document.document_version_id,
                        artifact_kind="chunk_manifest",
                    ),
                ]
            )
        self.commercial_repository.enqueue_deletion_job(
            CommercialJobRecord(
                job_id=job_id("deletion"),
                owner_user_id=document.owner_user_id,
                job_kind="deletion",
                status="queued",
                stage="DELETE_REQUESTED",
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                max_retries=3,
                payload={"objectKeys": list(dict.fromkeys(object_keys))},
                created_at_ms=deleted_at_ms,
                updated_at_ms=deleted_at_ms,
                scheduled_after_ms=deleted_at_ms,
            )
        )

    def _require_collection_access(self, *, user_id: str, collection_id: str | None) -> None:
        if not collection_id:
            raise DomainRequestError("knowledge", "document-service", "知识资料上传必须指定资料库。")
        collection = self.knowledge_store.get_collection(collection_id) if hasattr(self.knowledge_store, "get_collection") else self.knowledge_store.collections.get(collection_id)  # type: ignore[attr-defined]
        if collection is None:
            raise DomainRequestError("knowledge", "document-service", "资料库不存在。", 404)
        if collection.owner_user_id != user_id:
            raise DomainRequestError("knowledge", "document-service", "不能把资料写入其他用户的资料库。", 403)

    def _to_response(self, record: DocumentRecord) -> DocumentRecordResponse:
        return DocumentRecordResponse(
            documentId=record.document_id,
            ownerUserId=record.owner_user_id,
            documentKind=record.document_kind,
            displayName=record.display_name,
            fileKind=record.file_kind,
            contentType=record.content_type,
            sizeBytes=record.size_bytes,
            objectKey=record.object_key,
            status=record.status,
            knowledgeCollectionId=record.knowledge_collection_id,
            processingRequestedAtMs=record.processing_requested_at_ms,
            deletedAtMs=record.deleted_at_ms,
            createdAtMs=record.created_at_ms,
            updatedAtMs=record.updated_at_ms,
            summary=record.summary,
            objectId=record.object_id,
            documentVersionId=record.document_version_id,
            version=record.version,
            contentFingerprint=record.content_fingerprint,
            originalFilename=record.original_filename,
            indexState=record.index_state,
        )
