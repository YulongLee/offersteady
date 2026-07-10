from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from uuid import uuid4

from app.core.errors import DomainRequestError
from app.material_formats import MaterialFormatId, MaterialKind, detect_material_format, is_material_mime_allowed, material_upload_label
from app.ports.storage import FileStoragePort
from app.schemas.material_upload import CreatedKnowledgeCollectionResponse, MaterialSourceRecord, MaterialUploadCompletionResponse, UploadIntentResponse


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass
class InMemoryMaterialStore:
    collections: dict[str, CreatedKnowledgeCollectionResponse] = field(default_factory=dict)


@dataclass
class MaterialIngestionService:
    storage: FileStoragePort
    store: InMemoryMaterialStore

    def _validate_file(self, *, filename: str, content_type: str) -> MaterialFormatId:
        file_kind = detect_material_format(filename)
        if file_kind is None or not is_material_mime_allowed(file_kind, content_type):
            raise DomainRequestError("material-upload", "create-upload-intent", f"当前仅支持 {material_upload_label()} 文件上传。")
        return file_kind

    def create_upload_intent(self, *, user_id: str, material_kind: MaterialKind, filename: str, content_type: str) -> UploadIntentResponse:
        file_kind = self._validate_file(filename=filename, content_type=content_type)
        reservation = self.storage.create_upload_intent(
            user_id=user_id,
            material_kind=material_kind,
            filename=filename,
            file_kind=file_kind,
            content_type=content_type,
        )
        return UploadIntentResponse(
            intent_id=reservation.intent_id,
            user_id=reservation.user_id,
            material_kind=reservation.material_kind,
            upload_method=reservation.upload_method,
            filename=reservation.filename,
            file_kind=reservation.file_kind,
            content_type=reservation.content_type,
            object_key=reservation.object_key,
            upload_url=reservation.upload_url,
            upload_fields=reservation.upload_fields,
            issued_at_ms=reservation.issued_at_ms,
            expires_at_ms=reservation.expires_at_ms,
        )

    def complete_upload(self, *, user_id: str, intent_id: str, object_key: str, content_type: str, size_bytes: int, etag: str | None, collection_id: str | None = None) -> MaterialUploadCompletionResponse:
        confirmed = self.storage.confirm_uploaded_object(
            user_id=user_id,
            intent_id=intent_id,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            etag=etag,
        )
        if confirmed.material_kind == "knowledge":
            if not collection_id:
                raise DomainRequestError("knowledge", "complete-upload", "知识资料上传必须指定资料库。")
            collection = self.store.collections.get(collection_id)
            if collection is None:
                raise DomainRequestError("knowledge", "complete-upload", "资料库不存在。", 404)
            if collection.owner_user_id != user_id:
                raise DomainRequestError("knowledge", "complete-upload", "不能把资料写入其他用户的资料库。", 403)
        source_id = f"{confirmed.material_kind}-source-{uuid4().hex}"
        source = MaterialSourceRecord(
            source_id=source_id,
            owner_user_id=user_id,
            material_kind=confirmed.material_kind,
            display_name=confirmed.filename,
            version="v1",
            processing_state="uploaded",
            updated_at_ms=confirmed.confirmed_at_ms,
            summary="文件已上传，等待服务端处理完成。",
        )
        return MaterialUploadCompletionResponse(
            source=source,
            document_version_id=f"document-{uuid4().hex}" if confirmed.material_kind == "knowledge" else None,
            collection_id=collection_id,
        )

    def create_knowledge_collection(self, *, user_id: str, name: str) -> CreatedKnowledgeCollectionResponse:
        now_ms = _now_ms()
        collection = CreatedKnowledgeCollectionResponse(
            collection_id=f"collection-{uuid4().hex}",
            owner_user_id=user_id,
            name=name,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        self.store.collections[collection.collection_id] = collection
        return collection

    def create_pasted_job_description(self, *, user_id: str, text: str, display_name: str | None) -> MaterialUploadCompletionResponse:
        if not text.strip():
            raise DomainRequestError("job-description", "create-text", "JD 文本不能为空。")
        now_ms = _now_ms()
        source = MaterialSourceRecord(
            source_id=f"job-description-source-{uuid4().hex}",
            owner_user_id=user_id,
            material_kind="job_description",
            display_name=(display_name or text.strip().splitlines()[0][:24] or "职位 JD 文本").strip(),
            version="v1",
            processing_state="processing",
            updated_at_ms=now_ms,
            summary="文本已保存，等待提取岗位职责与技能要求。",
        )
        return MaterialUploadCompletionResponse(source=source)
