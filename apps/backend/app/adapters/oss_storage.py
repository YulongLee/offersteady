from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass, field
from time import sleep, time
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.material_formats import MaterialFormatId, MaterialKind
from app.ports.storage import ConfirmedUploadObject, FileStoragePort, UploadIntentReservation
from app.services.material_object_keys import MaterialObjectKeyFactory


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass
class AliyunOssStorageAdapter(FileStoragePort):
    settings: Settings
    issued_intents: dict[str, UploadIntentReservation] = field(default_factory=dict)
    deleted_objects: set[str] = field(default_factory=set)
    uploaded_objects: dict[str, bytes] = field(default_factory=dict)

    def _has_real_oss_config(self) -> bool:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        return bool(
            self.settings.oss_access_key_id
            and self.settings.oss_access_key_secret
            and self.settings.oss_bucket
            and self.settings.oss_endpoint
        )

    def _allow_memory_storage(self) -> bool:
        return bool(os.environ.get("PYTEST_CURRENT_TEST") or self.settings.environment == "test")

    def _bucket(self):
        try:
            from oss2 import Auth, Bucket
        except ImportError as exc:
            raise DomainRequestError("object-storage", "oss-sdk", "OSS SDK 未安装，无法写入对象存储。", 500) from exc
        endpoint = (self.settings.oss_endpoint or "").strip()
        if not endpoint.startswith(("http://", "https://")):
            endpoint = f"https://{endpoint}"
        auth = Auth(self.settings.oss_access_key_id, self.settings.oss_access_key_secret)
        return Bucket(auth, endpoint, self.settings.oss_bucket)

    @staticmethod
    def _clean_oss_error(exc: Exception) -> str:
        text = str(exc).strip()
        if "UNEXPECTED_EOF_WHILE_READING" in text or "SSLEOFError" in text:
            return "OSS HTTPS 连接在上传过程中被中断，请检查网络、代理/VPN 或稍后重试。"
        if "Max retries exceeded" in text:
            return "OSS 网络请求多次重试后仍失败，请检查本机到 OSS 的网络连接。"
        if "Name or service not known" in text or "nodename nor servname" in text:
            return "OSS Endpoint 无法解析，请检查 OSS endpoint/region 配置。"
        return "OSS 写入失败，请检查网络或 OSS 配置后重试。"

    def _put_object_with_retry(self, *, object_key: str, payload: bytes, content_type: str):
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                result = self._bucket().put_object(object_key, payload, headers={"Content-Type": content_type})
                if getattr(result, "status", 0) in {200, 201, 204}:
                    return result
                raise DomainRequestError(
                    "object-storage",
                    "save-object",
                    f"OSS 写入失败，状态码 {getattr(result, 'status', 'unknown')}。",
                    502,
                    error_code="oss_write_status_error",
                )
            except DomainRequestError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    sleep(0.35 * (2 ** attempt))
        raise DomainRequestError(
            "object-storage",
            "save-object",
            self._clean_oss_error(last_error) if last_error is not None else "OSS 写入失败，请稍后重试。",
            502,
            error_code="oss_write_network_error",
        ) from last_error

    def _upload_url(self) -> str:
        bucket = (self.settings.oss_bucket or "offersteady-materials").strip()
        endpoint = (self.settings.oss_endpoint or "https://oss-cn-hangzhou.aliyuncs.com").rstrip("/")
        if "://" in endpoint and not endpoint.startswith("https://") and not endpoint.startswith("http://"):
            endpoint = f"https://{endpoint}"
        return f"{endpoint}/{bucket}"

    def _object_key(
        self,
        *,
        user_id: str,
        material_kind: MaterialKind,
        file_kind: MaterialFormatId,
        document_id: str,
        document_version_id: str,
        object_id: str,
    ) -> str:
        key_factory = MaterialObjectKeyFactory(self.settings)
        return key_factory.original_key(
            owner_user_id=user_id,
            document_kind=material_kind,
            document_id=document_id,
            document_version_id=document_version_id,
            object_id=object_id,
            file_kind=file_kind,
        )

    def _sign_policy(self, *, key: str, content_type: str, expires_at_ms: int) -> tuple[str, str]:
        policy = {
            "expiration": f"{expires_at_ms // 1000}",
            "conditions": [
                {"bucket": self.settings.oss_bucket or "offersteady-materials"},
                {"key": key},
                {"Content-Type": content_type},
                ["content-length-range", 0, 20 * 1024 * 1024],
            ],
        }
        encoded = base64.b64encode(json.dumps(policy, separators=(",", ":")).encode("utf-8")).decode("utf-8")
        signature = base64.b64encode(
            hmac.new((self.settings.oss_access_key_secret or "test-access-key-secret").encode("utf-8"), encoded.encode("utf-8"), hashlib.sha1).digest()
        ).decode("utf-8")
        return encoded, signature

    def create_upload_intent(
        self,
        *,
        user_id: str,
        material_kind: MaterialKind,
        filename: str,
        file_kind: MaterialFormatId,
        content_type: str,
    ) -> UploadIntentReservation:
        issued_at_ms = _now_ms()
        expires_at_ms = issued_at_ms + self.settings.oss_upload_intent_ttl_seconds * 1000
        key_factory = MaterialObjectKeyFactory(self.settings)
        document_id = f"document-{uuid4().hex}"
        document_version_id = f"version-{uuid4().hex}"
        object_id = key_factory.new_object_id()
        object_key = self._object_key(
            user_id=user_id,
            material_kind=material_kind,
            file_kind=file_kind,
            document_id=document_id,
            document_version_id=document_version_id,
            object_id=object_id,
        )
        policy, signature = self._sign_policy(key=object_key, content_type=content_type, expires_at_ms=expires_at_ms)
        reservation = UploadIntentReservation(
            intent_id=f"intent-{uuid4().hex}",
            user_id=user_id,
            material_kind=material_kind,
            filename=filename,
            file_kind=file_kind,
            content_type=content_type,
            object_key=object_key,
            upload_url=self._upload_url(),
            upload_fields={
                "key": object_key,
                "OSSAccessKeyId": self.settings.oss_access_key_id or "test-access-key-id",
                "policy": policy,
                "Signature": signature,
                "Content-Type": content_type,
                "success_action_status": "204",
                "x-oss-meta-intent-id": f"intent-{uuid4().hex}",
                "x-oss-meta-document-id": document_id,
                "x-oss-meta-document-version-id": document_version_id,
                "x-oss-meta-object-id": object_id,
            },
            issued_at_ms=issued_at_ms,
            expires_at_ms=expires_at_ms,
            object_id=object_id,
            document_id=document_id,
            document_version_id=document_version_id,
        )
        self.issued_intents[reservation.intent_id] = reservation
        return reservation

    def _validate_upload_intent(
        self,
        *,
        user_id: str,
        intent_id: str,
        object_key: str,
        content_type: str,
        size_bytes: int,
        content_sha256: str | None = None,
    ) -> tuple[UploadIntentReservation, int, str | None]:
        reservation = self.issued_intents.get(intent_id)
        if reservation is None:
            raise DomainRequestError("material-upload", "confirm-upload", "上传意图不存在或已失效，请重新上传。", 404)
        now_ms = _now_ms()
        if reservation.user_id != user_id or reservation.object_key != object_key:
            raise DomainRequestError("material-upload", "confirm-upload", "上传对象与当前用户或上传意图不匹配。", 409)
        if now_ms > reservation.expires_at_ms:
            raise DomainRequestError("material-upload", "confirm-upload", "上传意图已过期，请重新申请上传。", 410)
        if reservation.content_type != content_type:
            raise DomainRequestError("material-upload", "confirm-upload", "上传内容类型与签发的上传意图不一致。", 409)
        if size_bytes > self.settings.material_max_file_size_bytes:
            raise DomainRequestError("material-upload", "confirm-upload", f"文件大小不能超过 {self.settings.material_max_file_size_bytes // (1024 * 1024)} MB。")
        fingerprint = content_sha256.strip().lower() if content_sha256 else None
        if fingerprint and (len(fingerprint) != 64 or any(character not in "0123456789abcdef" for character in fingerprint)):
            raise DomainRequestError("material-upload", "confirm-upload", "文件指纹格式不正确，请重新上传。", 409)
        return reservation, now_ms, fingerprint

    def _remote_object_exists(self, object_key: str) -> bool:
        try:
            self._bucket().head_object(object_key)
            return True
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return False
            raise DomainRequestError("object-storage", "head-object", "OSS 对象校验失败，请稍后重试。", 502) from exc

    def _confirmed_object(
        self,
        *,
        reservation: UploadIntentReservation,
        size_bytes: int,
        etag: str | None,
        confirmed_at_ms: int,
        content_fingerprint: str | None,
    ) -> ConfirmedUploadObject:
        return ConfirmedUploadObject(
            intent_id=reservation.intent_id,
            user_id=reservation.user_id,
            material_kind=reservation.material_kind,
            filename=reservation.filename,
            file_kind=reservation.file_kind,
            content_type=reservation.content_type,
            object_key=reservation.object_key,
            size_bytes=size_bytes,
            etag=etag,
            confirmed_at_ms=confirmed_at_ms,
            object_id=reservation.object_id,
            document_id=reservation.document_id,
            document_version_id=reservation.document_version_id,
            content_fingerprint=content_fingerprint or (etag.strip() if etag else None),
        )

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
    ) -> ConfirmedUploadObject:
        reservation, now_ms, fingerprint = self._validate_upload_intent(
            user_id=user_id,
            intent_id=intent_id,
            object_key=object_key,
            content_type=content_type,
            size_bytes=size_bytes,
            content_sha256=content_sha256,
        )
        if self._has_real_oss_config():
            if not self._remote_object_exists(reservation.object_key):
                raise DomainRequestError("material-upload", "confirm-upload", "OSS 中未找到上传文件，请重新上传。", 409)
        elif self._allow_memory_storage() and reservation.object_key not in self.uploaded_objects:
            self.uploaded_objects[reservation.object_key] = self._placeholder_object_bytes(
                filename=reservation.filename,
                file_kind=reservation.file_kind,
                material_kind=reservation.material_kind,
                object_key=reservation.object_key,
            )
        elif reservation.object_key not in self.uploaded_objects:
            raise DomainRequestError("material-upload", "confirm-upload", "OSS 未配置，无法确认资料上传。", 503)
        return self._confirmed_object(
            reservation=reservation,
            size_bytes=size_bytes,
            etag=etag,
            confirmed_at_ms=now_ms,
            content_fingerprint=fingerprint,
        )

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
    ) -> ConfirmedUploadObject:
        reservation, now_ms, fingerprint = self._validate_upload_intent(
            user_id=user_id,
            intent_id=intent_id,
            object_key=object_key,
            content_type=content_type,
            size_bytes=max(len(payload), 1),
            content_sha256=content_sha256,
        )
        if self._has_real_oss_config():
            self._put_object_with_retry(
                object_key=reservation.object_key,
                payload=payload,
                content_type=reservation.content_type,
            )
        elif not self._allow_memory_storage():
            raise DomainRequestError("object-storage", "save-object", "OSS 未配置，无法保存资料文件。", 503)
        self.uploaded_objects[reservation.object_key] = payload
        return self._confirmed_object(
            reservation=reservation,
            size_bytes=max(len(payload), 1),
            etag=etag or f"proxy:{len(payload)}",
            confirmed_at_ms=now_ms,
            content_fingerprint=fingerprint,
        )

    def delete_object(self, *, object_key: str) -> None:
        self.deleted_objects.add(object_key)
        if self._has_real_oss_config():
            try:
                self._bucket().delete_object(object_key)
            except Exception as exc:
                raise DomainRequestError("object-storage", "delete-object", "OSS 对象删除失败，请稍后重试。", 502) from exc

    def object_exists(self, *, object_key: str) -> bool:
        if object_key.startswith("inline://"):
            return True
        if object_key in self.deleted_objects:
            return False
        if object_key in self.uploaded_objects:
            return True
        if self._has_real_oss_config():
            return self._remote_object_exists(object_key)
        return False

    def load_object_bytes(self, *, object_key: str) -> bytes:
        payload = self.uploaded_objects.get(object_key)
        if payload is not None:
            return payload
        if self._has_real_oss_config():
            try:
                remote = self._bucket().get_object(object_key).read()
            except Exception as exc:
                raise DomainRequestError("object-storage", "load-object", "OSS 上传对象不存在或尚未可读。", 404) from exc
            self.uploaded_objects[object_key] = remote
            return remote
        raise DomainRequestError("object-storage", "load-object", "上传对象不存在或尚未可读。", 404)

    def save_object_bytes(self, *, object_key: str, payload: bytes, content_type: str) -> None:
        if not self._has_real_oss_config():
            self.uploaded_objects[object_key] = payload
            return
        safe_key = re.sub(r"/+", "/", object_key.strip("/"))
        if not safe_key or safe_key.endswith("/"):
            raise DomainRequestError(
                "object-storage",
                "save-object",
                "OSS 对象路径无效，请重新截图上传。",
                400,
                error_code="invalid_oss_object_key",
            )
        self._put_object_with_retry(object_key=safe_key, payload=payload, content_type=content_type)
        self.uploaded_objects[safe_key] = payload

    def create_signed_download_url(self, *, object_key: str, expires_seconds: int) -> str | None:
        if not self._has_real_oss_config():
            return None
        try:
            return self._bucket().sign_url("GET", object_key, expires_seconds)
        except Exception as exc:
            raise DomainRequestError("object-storage", "sign-object", "OSS 截图签名 URL 生成失败，请稍后重试。", 502) from exc

    def _placeholder_object_bytes(self, *, filename: str, file_kind: MaterialFormatId, material_kind: MaterialKind, object_key: str) -> bytes:
        stem = filename.rsplit(".", 1)[0] if "." in filename else filename
        if file_kind == "md":
            return (
                f"# {stem}\n\n"
                f"- material kind: {material_kind}\n"
                f"- source key: `{object_key}`\n\n"
                "这是用于本地 MVP 文档处理链路验证的占位 Markdown 内容。\n"
            ).encode("utf-8")
        if file_kind == "txt":
            return (
                f"{stem}\n\n"
                f"material kind: {material_kind}\n"
                f"source key: {object_key}\n\n"
                "这是用于本地 MVP 文档处理链路验证的占位纯文本内容。"
            ).encode("utf-8")
        if file_kind == "pdf":
            return b"%PDF-1.7\n%OfferSteady placeholder binary content\n"
        if file_kind == "docx":
            return b"PK\x03\x04OfferSteady DOCX placeholder content"
        if file_kind == "doc":
            return b"\xd0\xcf\x11\xe0OfferSteady DOC placeholder content"
        return f"{stem}\n{object_key}".encode("utf-8")
