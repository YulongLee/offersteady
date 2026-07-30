from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
from dataclasses import dataclass
from time import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from cryptography.fernet import Fernet

from app.core.config import Settings
from app.services.admin_repository import AdminRepository, now_ms
from app.services.authentication_service import JWTAccessTokenCodec


PERMISSIONS_BY_ROLE: dict[str, frozenset[str]] = {
    "super_admin": frozenset({
        "users.read", "users.suspend", "billing.read", "billing.adjust",
        "payments.reconcile", "materials.read", "materials.retry",
        "sessions.read", "sessions.terminate", "observability.read",
        "audit.read", "admins.manage",
    }),
    "operations": frozenset({
        "users.read", "billing.read", "materials.read", "materials.retry",
        "sessions.read", "sessions.terminate", "observability.read",
    }),
    "support": frozenset({"users.read", "billing.read", "materials.read", "sessions.read"}),
    "finance": frozenset({"users.read", "billing.read", "billing.adjust", "payments.reconcile", "audit.read"}),
    "technical_auditor": frozenset({"materials.read", "sessions.read", "observability.read", "audit.read"}),
}

SAFE_DETAIL_KEYS = frozenset({
    "status", "previous_status", "points", "days", "balance", "provider",
    "order_status", "document_id", "task_id", "session_id", "error_code",
    "idempotent_replay", "role",
})
HIGH_RISK_PERMISSIONS = frozenset({"users.suspend", "billing.adjust", "admins.manage"})


@dataclass(frozen=True)
class AdminPrincipal:
    admin_session_id: str
    user_id: str
    role: str
    permissions: frozenset[str]
    recent_mfa_at_ms: int


class AdminService:
    def __init__(self, settings: Settings, repository: AdminRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.user_token_codec = JWTAccessTokenCodec(settings)

    def assert_ready(self) -> None:
        if not self.settings.admin_enabled:
            raise PermissionError("admin_disabled")
        if not self.settings.admin_session_signing_secret or not self.settings.admin_encryption_key:
            raise PermissionError("admin_security_not_configured")
        if not self.settings.database_url:
            raise PermissionError("admin_database_not_configured")

    def create_admin_session(
        self,
        *,
        user_access_token: str,
        totp_code: str,
        ip_hash: str | None,
        user_agent_hash: str | None,
    ) -> tuple[str, dict[str, Any]]:
        self.assert_ready()
        payload = self.user_token_codec.decode_access_token(user_access_token)
        if not self.repository.validate_user_session(user_id=payload.sub, auth_session_id=payload.sid):
            raise PermissionError("user_session_invalid")
        authorization = self.repository.authorization_for_user(payload.sub)
        if not authorization or authorization["status"] != "active":
            raise PermissionError("admin_authorization_required")
        secret = self.decrypt_secret(str(authorization["totp_secret_ciphertext"]))
        if not self.verify_totp(secret, totp_code):
            raise PermissionError("mfa_invalid")
        role = str(authorization["role"])
        permissions = sorted(PERMISSIONS_BY_ROLE.get(role, frozenset()))
        token = secrets.token_urlsafe(48)
        current = now_ms()
        session_id = f"admin-session-{uuid4().hex}"
        self.repository.create_session({
            "admin_session_id": session_id,
            "authorization_id": authorization["authorization_id"],
            "user_id": payload.sub,
            "token_fingerprint": self.token_fingerprint(token),
            "authorization_version": int(authorization["authorization_version"]),
            "role": role,
            "permissions_json": permissions,
            "issued_at_ms": current,
            "expires_at_ms": current + self.settings.admin_session_ttl_seconds * 1000,
            "recent_mfa_at_ms": current,
            "last_used_at_ms": current,
            "ip_hash": ip_hash,
            "user_agent_hash": user_agent_hash,
        })
        return token, {
            "adminSessionId": session_id,
            "role": role,
            "permissions": permissions,
            "expiresAtMs": current + self.settings.admin_session_ttl_seconds * 1000,
        }

    def authenticate(self, token: str) -> AdminPrincipal:
        self.assert_ready()
        row = self.repository.session_by_fingerprint(self.token_fingerprint(token))
        current = now_ms()
        if (
            not row
            or row["status"] != "active"
            or row["authorization_status"] != "active"
            or int(row["expires_at_ms"]) <= current
            or int(row["authorization_version"]) != int(row["current_authorization_version"])
        ):
            raise PermissionError("admin_session_invalid")
        self.repository.touch_session(str(row["admin_session_id"]))
        permissions = row["permissions_json"]
        if isinstance(permissions, str):
            permissions = json.loads(permissions)
        return AdminPrincipal(
            admin_session_id=str(row["admin_session_id"]),
            user_id=str(row["user_id"]),
            role=str(row["role"]),
            permissions=frozenset(str(item) for item in permissions),
            recent_mfa_at_ms=int(row["recent_mfa_at_ms"]),
        )

    def require_permission(self, principal: AdminPrincipal, permission: str) -> None:
        if permission not in principal.permissions:
            raise PermissionError("admin_permission_denied")
        if permission in HIGH_RISK_PERMISSIONS:
            minimum = now_ms() - self.settings.admin_recent_mfa_ttl_seconds * 1000
            if principal.recent_mfa_at_ms < minimum:
                raise PermissionError("admin_step_up_required")

    def step_up(self, principal: AdminPrincipal, code: str) -> int:
        authorization = self.repository.authorization_for_user(principal.user_id)
        if not authorization:
            raise PermissionError("admin_authorization_required")
        if not self.verify_totp(self.decrypt_secret(str(authorization["totp_secret_ciphertext"])), code):
            raise PermissionError("mfa_invalid")
        return self.repository.step_up_session(principal.admin_session_id)

    def audit(
        self,
        *,
        principal: AdminPrincipal | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        reason: str | None,
        request_id: str,
        result: str,
        details: dict[str, Any] | None = None,
        ip_hash: str | None = None,
        user_agent_hash: str | None = None,
    ) -> dict[str, Any]:
        safe_details = {
            key: value for key, value in (details or {}).items()
            if key in SAFE_DETAIL_KEYS and isinstance(value, (str, int, float, bool, type(None)))
        }
        return self.repository.append_audit({
            "audit_event_id": f"admin-audit-{uuid4().hex}",
            "actor_user_id": principal.user_id if principal else None,
            "actor_role": principal.role if principal else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "reason": reason,
            "request_id": request_id,
            "result": result,
            "safe_details_json": safe_details,
            "source_ip_hash": ip_hash,
            "user_agent_hash": user_agent_hash,
            "created_at_ms": now_ms(),
        })

    def execute_idempotent(
        self,
        *,
        principal: AdminPrincipal,
        action: str,
        key: str,
        callback,
    ) -> tuple[dict[str, Any], bool]:
        existing = self.repository.idempotent_result(actor_user_id=principal.user_id, action=action, key=key)
        if existing is not None:
            return existing, True
        result = callback()
        self.repository.save_idempotent_result(
            actor_user_id=principal.user_id,
            action=action,
            key=key,
            result=result,
        )
        return result, False

    def bootstrap(self, *, login_id: str, role: str) -> tuple[dict[str, Any], str, str]:
        if role not in PERMISSIONS_BY_ROLE:
            raise ValueError("unsupported_admin_role")
        if not self.settings.database_url or not self.settings.admin_encryption_key:
            raise RuntimeError("database and admin encryption key are required")
        user = self.repository.user_by_login(login_id)
        if not user:
            raise LookupError("authentication_user_not_found")
        secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
        authorization = self.repository.upsert_authorization(
            user_id=str(user["user_id"]),
            role=role,
            encrypted_secret=self.encrypt_secret(secret),
            created_by_user_id=None,
        )
        label = quote(str(user["display_name"]))
        issuer = quote("OfferSteady Admin")
        uri = f"otpauth://totp/{issuer}:{label}?secret={secret}&issuer={issuer}&digits=6&period=30"
        return authorization, secret, uri

    def provision_administrator(
        self,
        *,
        login_id: str,
        role: str,
        actor_user_id: str,
    ) -> dict[str, Any]:
        if role not in PERMISSIONS_BY_ROLE:
            raise ValueError("unsupported_admin_role")
        if self.repository.active_administrator_count() == 0:
            raise PermissionError("first_super_admin_requires_server_bootstrap")
        user = self.repository.user_by_login(login_id)
        if not user:
            raise LookupError("authentication_user_not_found")
        secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
        authorization = self.repository.upsert_authorization(
            user_id=str(user["user_id"]),
            role=role,
            encrypted_secret=self.encrypt_secret(secret),
            created_by_user_id=actor_user_id,
        )
        label = quote(str(user["display_name"]))
        issuer = quote("OfferSteady Admin")
        uri = f"otpauth://totp/{issuer}:{label}?secret={secret}&issuer={issuer}&digits=6&period=30"
        return {
            "user_id": str(user["user_id"]),
            "role": str(authorization["role"]),
            "status": str(authorization["status"]),
            "totp_secret": secret,
            "provisioning_uri": uri,
            "enrollment_display_once": True,
        }

    def disable_administrator(
        self,
        *,
        target_user_id: str,
        actor_user_id: str,
    ) -> dict[str, Any]:
        if target_user_id == actor_user_id:
            raise PermissionError("administrator_cannot_disable_self")
        return self.repository.disable_authorization(user_id=target_user_id)

    def encrypt_secret(self, value: str) -> str:
        return self._fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt_secret(self, value: str) -> str:
        return self._fernet().decrypt(value.encode("ascii")).decode("utf-8")

    def _fernet(self) -> Fernet:
        raw = (self.settings.admin_encryption_key or "").encode("utf-8")
        key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
        return Fernet(key)

    def token_fingerprint(self, token: str) -> str:
        secret = (self.settings.admin_session_signing_secret or "").encode("utf-8")
        return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_totp(secret: str, code: str, *, timestamp: int | None = None) -> bool:
        if not code.isdigit() or len(code) != 6:
            return False
        moment = int(time() if timestamp is None else timestamp)
        normalized = secret + "=" * ((8 - len(secret) % 8) % 8)
        key = base64.b32decode(normalized, casefold=True)
        for offset in (-1, 0, 1):
            counter = (moment // 30) + offset
            digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
            index = digest[-1] & 0x0F
            value = (struct.unpack(">I", digest[index:index + 4])[0] & 0x7FFFFFFF) % 1_000_000
            if hmac.compare_digest(f"{value:06d}", code):
                return True
        return False


def hash_client_value(value: str | None, secret: str | None) -> str | None:
    if not value:
        return None
    return hmac.new((secret or "admin").encode(), value.encode(), hashlib.sha256).hexdigest()[:24]
