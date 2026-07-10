from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.material_formats import MaterialFormatId, MaterialKind


@dataclass(frozen=True)
class UploadIntentReservation:
    intent_id: str
    user_id: str
    material_kind: MaterialKind
    filename: str
    file_kind: MaterialFormatId
    content_type: str
    object_key: str
    upload_url: str
    upload_fields: dict[str, str]
    issued_at_ms: int
    expires_at_ms: int
    object_id: str | None = None
    document_id: str | None = None
    document_version_id: str | None = None
    upload_method: Literal["POST"] = "POST"


@dataclass(frozen=True)
class ConfirmedUploadObject:
    intent_id: str
    user_id: str
    material_kind: MaterialKind
    filename: str
    file_kind: MaterialFormatId
    content_type: str
    object_key: str
    size_bytes: int
    etag: str | None
    confirmed_at_ms: int
    object_id: str | None = None
    document_id: str | None = None
    document_version_id: str | None = None
    content_fingerprint: str | None = None


class FileStoragePort(Protocol):
    def create_upload_intent(
        self,
        *,
        user_id: str,
        material_kind: MaterialKind,
        filename: str,
        file_kind: MaterialFormatId,
        content_type: str,
    ) -> UploadIntentReservation: ...

    def confirm_uploaded_object(
        self,
        *,
        user_id: str,
        intent_id: str,
        object_key: str,
        content_type: str,
        size_bytes: int,
        etag: str | None = None,
        content_sha256: str | None = None,
    ) -> ConfirmedUploadObject: ...

    def save_intent_object(
        self,
        *,
        user_id: str,
        intent_id: str,
        object_key: str,
        content_type: str,
        payload: bytes,
        etag: str | None = None,
        content_sha256: str | None = None,
    ) -> ConfirmedUploadObject: ...

    def delete_object(self, *, object_key: str) -> None: ...

    def object_exists(self, *, object_key: str) -> bool: ...

    def load_object_bytes(self, *, object_key: str) -> bytes: ...

    def save_object_bytes(self, *, object_key: str, payload: bytes, content_type: str) -> None: ...

    def create_signed_download_url(self, *, object_key: str, expires_seconds: int) -> str | None: ...
