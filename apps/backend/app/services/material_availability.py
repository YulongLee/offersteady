from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.document_repository import DocumentRecord
from app.ports.storage import FileStoragePort
from app.services.material_object_keys import MaterialObjectKeyFactory


@dataclass(frozen=True)
class MaterialAvailabilityResult:
    available: bool
    reason_code: str | None = None
    message: str | None = None


class MaterialAvailabilityValidator:
    def __init__(self, *, settings: Settings, storage: FileStoragePort) -> None:
        self.settings = settings
        self.storage = storage
        self.key_factory = MaterialObjectKeyFactory(settings)

    def check(self, document: DocumentRecord) -> MaterialAvailabilityResult:
        if document.status != "ready":
            return self._unavailable("document_not_ready", "资料尚未处理完成，暂不能用于面试。")
        if document.index_state != "indexed":
            return self._unavailable("document_not_indexed", "资料索引尚未完成，暂不能用于面试。")
        if document.deleted_at_ms is not None or document.status == "deleted":
            return self._unavailable("document_deleted", "资料已删除，不能用于面试。")
        return self.check_processed_artifacts(document)

    def check_processed_artifacts(self, document: DocumentRecord) -> MaterialAvailabilityResult:
        if not document.document_version_id:
            return self._unavailable("document_version_missing", "资料版本信息缺失，不能用于面试。")
        if not document.object_key.startswith("inline://") and not self._object_exists(document.object_key):
            return self._unavailable("original_object_missing", "OSS 原文件不可读，请重新上传。")
        normalized_key = self.key_factory.processed_artifact_key(
            owner_user_id=document.owner_user_id,
            document_kind=document.document_kind,
            document_id=document.document_id,
            document_version_id=document.document_version_id,
            artifact_kind="normalized_markdown",
        )
        if not self._object_exists(normalized_key):
            return self._unavailable("normalized_markdown_missing", "解析后的 Markdown 不可读，请重新处理资料。")
        if document.document_kind == "knowledge":
            chunks_key = self.key_factory.processed_artifact_key(
                owner_user_id=document.owner_user_id,
                document_kind=document.document_kind,
                document_id=document.document_id,
                document_version_id=document.document_version_id,
                artifact_kind="chunk_manifest",
            )
            if not self._object_exists(chunks_key):
                return self._unavailable("chunk_manifest_missing", "知识库索引清单不可读，请重新处理资料。")
        return MaterialAvailabilityResult(available=True)

    def require_available(self, document: DocumentRecord, *, feature: str = "material", action: str = "use") -> None:
        result = self.check(document)
        if not result.available:
            raise DomainRequestError(feature, action, result.message or "资料暂不可用。", 400)

    def _object_has_bytes(self, object_key: str) -> bool:
        try:
            return bool(self.storage.load_object_bytes(object_key=object_key))
        except Exception:
            return False

    def _object_has_text(self, object_key: str) -> bool:
        try:
            return bool(self.storage.load_object_bytes(object_key=object_key).decode("utf-8", errors="replace").strip())
        except Exception:
            return False

    def _object_exists(self, object_key: str) -> bool:
        remote_exists = getattr(self.storage, "_remote_object_exists", None)
        has_real_oss = getattr(self.storage, "_has_real_oss_config", None)
        if callable(remote_exists) and callable(has_real_oss) and has_real_oss():
            try:
                return bool(remote_exists(object_key))
            except Exception:
                return False
        return self._object_has_bytes(object_key)

    def _unavailable(self, reason_code: str, message: str) -> MaterialAvailabilityResult:
        return MaterialAvailabilityResult(available=False, reason_code=reason_code, message=message)
