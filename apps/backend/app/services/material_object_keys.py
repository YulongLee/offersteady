from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings
from app.material_formats import MaterialFormatId, MaterialKind


MaterialArtifactKind = Literal[
    "original",
    "normalized_markdown",
    "chunk_manifest",
    "deletion_marker",
    "temporary_upload",
    "export",
]


def _safe_segment(value: str, *, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._=-]+", "-", value.strip()).strip("-._")
    return cleaned[:120] or fallback


@dataclass(frozen=True)
class MaterialObjectKeyFactory:
    settings: Settings

    def new_object_id(self) -> str:
        return secrets.token_hex(max(8, self.settings.material_object_id_bytes))

    def user_hash(self, owner_user_id: str) -> str:
        payload = f"{self.settings.material_user_hash_salt}:{owner_user_id}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:32]

    def original_key(
        self,
        *,
        owner_user_id: str,
        document_kind: MaterialKind,
        document_id: str,
        document_version_id: str,
        object_id: str,
        file_kind: MaterialFormatId,
    ) -> str:
        return self._join(
            self._document_version_prefix(
                owner_user_id=owner_user_id,
                document_kind=document_kind,
                document_id=document_id,
                document_version_id=document_version_id,
            ),
            "original",
            f"{_safe_segment(object_id, fallback='object')}.{file_kind}",
        )

    def processed_artifact_key(
        self,
        *,
        owner_user_id: str,
        document_kind: MaterialKind,
        document_id: str,
        document_version_id: str,
        artifact_kind: Literal["normalized_markdown", "chunk_manifest"],
    ) -> str:
        filename = {
            "normalized_markdown": "normalized.md",
            "chunk_manifest": "chunks.jsonl",
        }[artifact_kind]
        return self._join(
            self._document_version_prefix(
                owner_user_id=owner_user_id,
                document_kind=document_kind,
                document_id=document_id,
                document_version_id=document_version_id,
            ),
            "processed",
            filename,
        )

    def deletion_marker_key(
        self,
        *,
        owner_user_id: str,
        document_kind: MaterialKind,
        document_id: str,
        document_version_id: str,
        deleted_at_ms: int,
    ) -> str:
        return self._join(
            self._document_version_prefix(
                owner_user_id=owner_user_id,
                document_kind=document_kind,
                document_id=document_id,
                document_version_id=document_version_id,
            ),
            "deleted",
            f"{deleted_at_ms}.json",
        )

    def temporary_upload_key(
        self,
        *,
        owner_user_id: str,
        upload_intent_id: str,
        object_id: str,
        file_kind: MaterialFormatId,
    ) -> str:
        return self._join(
            self._user_prefix(owner_user_id),
            "tmp",
            _safe_segment(upload_intent_id, fallback="intent"),
            f"{_safe_segment(object_id, fallback='object')}.{file_kind}",
        )

    def export_key(
        self,
        *,
        owner_user_id: str,
        export_id: str,
        object_id: str,
        extension: str = "json",
    ) -> str:
        return self._join(
            self._user_prefix(owner_user_id),
            "exports",
            _safe_segment(export_id, fallback="export"),
            f"{_safe_segment(object_id, fallback='object')}.{_safe_segment(extension.lstrip('.'), fallback='json')}",
        )

    def _document_version_prefix(
        self,
        *,
        owner_user_id: str,
        document_kind: MaterialKind,
        document_id: str,
        document_version_id: str,
    ) -> str:
        return self._join(
            self._user_prefix(owner_user_id),
            "documents",
            _safe_segment(document_kind, fallback="material"),
            _safe_segment(document_id, fallback="document"),
            "versions",
            _safe_segment(document_version_id, fallback="version"),
        )

    def _user_prefix(self, owner_user_id: str) -> str:
        environment = self.settings.oss_environment_label or self.settings.environment
        return self._join(
            self.settings.oss_key_prefix,
            _safe_segment(environment, fallback="development"),
            "users",
            self.user_hash(owner_user_id),
        )

    def _join(self, *segments: str) -> str:
        cleaned: list[str] = []
        for segment in segments:
            cleaned.extend(_safe_segment(part, fallback="segment") for part in segment.split("/") if part.strip())
        return "/".join(cleaned)
