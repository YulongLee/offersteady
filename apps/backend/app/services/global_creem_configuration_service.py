from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from time import time
from typing import Literal

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.ports.global_commerce import GlobalCommerceRepository


CreemMode = Literal["test", "live"]


@dataclass(frozen=True)
class CreemCredentials:
    api_key: str | None
    webhook_secret: str | None


class GlobalCreemConfigurationService:
    """Keeps Creem credentials server-side and exposes only masked configuration state."""

    def __init__(self, settings: Settings, repository: GlobalCommerceRepository) -> None:
        self.settings = settings
        self.repository = repository

    def effective_credentials(self, mode: CreemMode) -> CreemCredentials:
        row = self.repository.provider_config(mode)
        ciphertext = row.get("credential_ciphertext")
        if ciphertext:
            try:
                values = self._decrypt(str(ciphertext))
            except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
                raise RuntimeError("creem_credentials_unreadable") from exc
            return CreemCredentials(values.get("apiKey") or None, values.get("webhookSecret") or None)
        return self.environment_credentials(mode)

    def active_mode(self) -> CreemMode:
        """Return the only provider mode supported by international commerce."""
        return "live"

    def environment_credentials(self, mode: CreemMode) -> CreemCredentials:
        if mode == "test":
            return CreemCredentials(self.settings.creem_test_api_key, self.settings.creem_test_webhook_secret)
        return CreemCredentials(self.settings.creem_live_api_key, self.settings.creem_live_webhook_secret)

    def save(self, *, mode: CreemMode, api_key: str | None, webhook_secret: str | None, user_id: str) -> dict[str, object]:
        current = self.effective_credentials(mode)
        resolved_api_key = (api_key or "").strip() or current.api_key
        resolved_webhook_secret = (webhook_secret or "").strip() or current.webhook_secret
        if not resolved_api_key or len(resolved_api_key) < 8:
            raise ValueError("Creem API Key 格式不完整")
        if not resolved_webhook_secret or len(resolved_webhook_secret) < 8:
            raise ValueError("Webhook Secret 格式不完整")
        if mode == "test" and not resolved_api_key.startswith("creem_test_"):
            raise ValueError("Test 环境必须使用 creem_test_ 开头的 API Key")
        if mode == "live" and resolved_api_key.startswith("creem_test_"):
            raise ValueError("Live 环境不能使用 Test API Key")
        return self.repository.save_provider_credentials(
            mode=mode,
            credential_ciphertext=self._encrypt({"apiKey": resolved_api_key, "webhookSecret": resolved_webhook_secret}),
            api_key_fingerprint=self._fingerprint(resolved_api_key),
            webhook_secret_fingerprint=self._fingerprint(resolved_webhook_secret),
            updated_by_user_id=user_id,
            updated_at_ms=int(time() * 1000),
        )

    def masked(self, mode: CreemMode) -> dict[str, object]:
        row = self.repository.provider_config(mode)
        credentials = self.effective_credentials(mode)
        return {
            "apiKey": {"configured": bool(credentials.api_key), "fingerprint": self._fingerprint(credentials.api_key)},
            "webhookSecret": {"configured": bool(credentials.webhook_secret), "fingerprint": self._fingerprint(credentials.webhook_secret)},
            "connectionCheckedAtMs": row.get("connection_checked_at_ms"),
            "source": "admin" if row.get("credential_ciphertext") else "environment" if credentials.api_key or credentials.webhook_secret else "none",
        }

    def configured_settings(self, mode: CreemMode) -> Settings:
        credentials = self.effective_credentials(mode)
        updates: dict[str, object] = {"global_commerce_provider_mode": mode}
        if mode == "test":
            updates.update({"creem_test_api_key": credentials.api_key, "creem_test_webhook_secret": credentials.webhook_secret})
        else:
            updates.update({"creem_live_api_key": credentials.api_key, "creem_live_webhook_secret": credentials.webhook_secret})
        return self.settings.model_copy(update=updates)

    def _fernet(self) -> Fernet:
        raw = (self.settings.admin_encryption_key or "").encode()
        if not raw:
            raise RuntimeError("admin_encryption_key_required")
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest()))

    def _encrypt(self, values: dict[str, str]) -> str:
        return self._fernet().encrypt(json.dumps(values, separators=(",", ":")).encode()).decode()

    def _decrypt(self, ciphertext: str) -> dict[str, str]:
        payload = json.loads(self._fernet().decrypt(ciphertext.encode()).decode())
        if not isinstance(payload, dict):
            raise ValueError("creem_credentials_invalid")
        return {str(key): str(value) for key, value in payload.items()}

    @staticmethod
    def _fingerprint(secret: str | None) -> str | None:
        return hashlib.sha256(secret.encode()).hexdigest()[:12] if secret else None
