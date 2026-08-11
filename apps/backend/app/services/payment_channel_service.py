from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from time import time
from typing import Mapping
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.services.alipay_provider import AlipayPaymentProvider
from app.services.postgres_billing_repository import PostgresBillingRepository
from app.services.wechat_pay_provider import WechatPayProvider


PUBLIC_FIELDS = {
    "alipay": ("appId", "sellerId", "gatewayUrl", "notifyUrl", "returnUrl"),
    "wechat": ("mchId", "appId", "merchantSerialNo", "nativeUrl", "notifyUrl"),
}
SECRET_FIELDS = {
    "alipay": ("appPrivateKey", "alipayPublicKey"),
    "wechat": ("merchantPrivateKey", "platformPublicKey", "apiV3Key"),
}


class PaymentChannelService:
    def __init__(self, settings: Settings, repository: PostgresBillingRepository) -> None:
        self.settings = settings
        self.repository = repository

    def list_masked(self) -> list[dict[str, object]]:
        return [self._masked(row) for row in self.repository.list_payment_channel_configs()]

    def available_channels(self) -> list[str]:
        channels: list[str] = []
        for row in self.repository.list_payment_channel_configs():
            _, errors = self._effective_validation(row)
            if bool(row["enabled"]) and not errors:
                channels.append(str(row["channel"]))
        return channels

    def save(self, *, channel: str, public_config: Mapping[str, object], secrets: Mapping[str, object], user_id: str) -> dict[str, object]:
        self._assert_channel(channel)
        current = self.repository.payment_channel_config(channel=channel)
        merged_public = {**dict(current["public_config"]), **self._filtered(public_config, PUBLIC_FIELDS[channel])}
        current_secrets = self._decrypt(str(current["secret_config_ciphertext"])) if current.get("secret_config_ciphertext") else {}
        replacements = {key: str(value).strip() for key, value in secrets.items() if key in SECRET_FIELDS[channel] and str(value).strip()}
        merged_secrets = {**current_secrets, **replacements}
        normalization_errors: list[str] = []
        if channel == "alipay":
            merged_secrets, normalization_errors = self._normalize_alipay_secrets(merged_secrets)
        errors = list(dict.fromkeys([*normalization_errors, *self.validate(channel, merged_public, merged_secrets)]))
        row = self.repository.save_payment_channel_config(
            channel=channel,
            public_config=merged_public,
            secret_config_ciphertext=self._encrypt(merged_secrets) if merged_secrets else None,
            validation_status="ready" if not errors else "draft",
            validation_errors=errors,
            updated_by_user_id=user_id,
            updated_at_ms=int(time() * 1000),
        )
        return self._masked(row)

    def set_enabled(self, *, channel: str, enabled: bool, user_id: str) -> dict[str, object]:
        self._assert_channel(channel)
        row = self.repository.payment_channel_config(channel=channel)
        if enabled and self._effective_validation(row)[1]:
            raise ValueError("payment_channel_not_ready")
        return self._masked(self.repository.set_payment_channel_enabled(
            channel=channel, enabled=enabled, updated_by_user_id=user_id, updated_at_ms=int(time() * 1000),
        ))

    def provider(self, channel: str, *, require_enabled: bool = True) -> AlipayPaymentProvider | WechatPayProvider:
        self._assert_channel(channel)
        row = self.repository.payment_channel_config(channel=channel)
        public, validation_errors = self._effective_validation(row)
        if require_enabled and (not row["enabled"] or validation_errors):
            raise ValueError("payment_channel_disabled")
        secrets = self._decrypt(str(row["secret_config_ciphertext"])) if row.get("secret_config_ciphertext") else {}
        updates = self._settings_updates(channel, public, secrets)
        configured = self.settings.model_copy(update=updates)
        return AlipayPaymentProvider(configured) if channel == "alipay" else WechatPayProvider(configured)

    @staticmethod
    def validate(channel: str, public: Mapping[str, object], secrets: Mapping[str, object]) -> list[str]:
        errors = [f"缺少字段：{key}" for key in (*PUBLIC_FIELDS[channel], *SECRET_FIELDS[channel]) if not str((public if key in PUBLIC_FIELDS[channel] else secrets).get(key, "")).strip()]
        if channel == "alipay":
            seller_id = str(public.get("sellerId", "")).strip()
            if seller_id and re.fullmatch(r"2088\d{12}", seller_id) is None:
                errors.append("sellerId 必须是支付宝签约商户 PID（以 2088 开头的 16 位纯数字）")
        for key in ("notifyUrl", "returnUrl"):
            value = str(public.get(key, ""))
            if value and urlparse(value).scheme != "https":
                errors.append(f"{key} 必须使用 HTTPS")
        api_key = str(secrets.get("apiV3Key", ""))
        if channel == "wechat" and api_key and len(api_key.encode("utf-8")) != 32:
            errors.append("apiV3Key 必须为 32 字节")
        for key in ("appPrivateKey", "merchantPrivateKey"):
            value = str(secrets.get(key, ""))
            if value:
                try:
                    serialization.load_pem_private_key(value.encode(), password=None)
                except (ValueError, TypeError):
                    errors.append(f"{key} 不是有效的 PEM 私钥")
        for key in ("alipayPublicKey", "platformPublicKey"):
            value = str(secrets.get(key, ""))
            if value:
                try:
                    serialization.load_pem_public_key(value.encode())
                except (ValueError, TypeError):
                    errors.append(f"{key} 不是有效的 PEM 公钥")
        return errors

    def _masked(self, row: Mapping[str, object]) -> dict[str, object]:
        channel = str(row["channel"])
        secrets = self._decrypt(str(row["secret_config_ciphertext"])) if row.get("secret_config_ciphertext") else {}
        _, effective_errors = self._effective_validation(row, secrets=secrets)
        acceptance = self.repository.payment_channel_acceptance(channel=channel) if hasattr(self.repository, "payment_channel_acceptance") else {
            "notification": None, "authoritativeQuery": None,
        }
        return {
            "channel": channel,
            "enabled": bool(row["enabled"]),
            "configVersion": int(row["config_version"]),
            "publicConfig": dict(row["public_config"]),
            "secretFields": {key: {"configured": bool(secrets.get(key)), "masked": "••••••••" if secrets.get(key) else ""} for key in SECRET_FIELDS[channel]},
            "validationStatus": "ready" if not effective_errors else "draft",
            "validationErrors": effective_errors,
            "updatedAtMs": int(row["updated_at_ms"]),
            "acceptance": acceptance,
        }

    def _effective_validation(
        self,
        row: Mapping[str, object],
        *,
        secrets: Mapping[str, object] | None = None,
    ) -> tuple[dict[str, object], list[str]]:
        channel = str(row["channel"])
        public = dict(row["public_config"])
        decrypted = dict(secrets) if secrets is not None else (
            self._decrypt(str(row["secret_config_ciphertext"])) if row.get("secret_config_ciphertext") else {}
        )
        persisted_errors = [str(error) for error in row.get("validation_errors", [])]
        return public, list(dict.fromkeys([*persisted_errors, *self.validate(channel, public, decrypted)]))

    def _fernet(self) -> Fernet:
        raw = (self.settings.admin_encryption_key or "").encode()
        if not raw:
            raise RuntimeError("admin_encryption_key_required")
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest()))

    def _encrypt(self, values: Mapping[str, object]) -> str:
        return self._fernet().encrypt(json.dumps(dict(values), ensure_ascii=False).encode()).decode()

    def _decrypt(self, value: str) -> dict[str, str]:
        return dict(json.loads(self._fernet().decrypt(value.encode()).decode()))

    @staticmethod
    def _filtered(values: Mapping[str, object], allowed: tuple[str, ...]) -> dict[str, str]:
        return {key: str(value).strip() for key, value in values.items() if key in allowed}

    @classmethod
    def _normalize_alipay_secrets(cls, values: Mapping[str, object]) -> tuple[dict[str, str], list[str]]:
        normalized = {key: str(value) for key, value in values.items()}
        errors: list[str] = []
        private_value = normalized.get("appPrivateKey", "").strip()
        if private_value:
            try:
                normalized["appPrivateKey"] = cls._canonical_rsa_private_pem(private_value)
            except (ValueError, TypeError, binascii.Error):
                errors.append("appPrivateKey 不是有效的 RSA PEM 私钥")
        public_value = normalized.get("alipayPublicKey", "").strip()
        if public_value:
            try:
                normalized["alipayPublicKey"] = cls._canonical_rsa_public_pem(public_value)
            except (ValueError, TypeError, binascii.Error):
                errors.append("alipayPublicKey 不是有效的 RSA PEM 公钥")
        return normalized, errors

    @staticmethod
    def _canonical_rsa_private_pem(value: str) -> str:
        prepared = value.strip().replace("\\n", "\n")
        if prepared.startswith("-----BEGIN"):
            key = serialization.load_pem_private_key(prepared.encode("utf-8"), password=None)
        else:
            key = serialization.load_der_private_key(
                base64.b64decode("".join(prepared.split()), validate=True),
                password=None,
            )
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("not-rsa-private-key")
        return key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode("ascii")

    @staticmethod
    def _canonical_rsa_public_pem(value: str) -> str:
        prepared = value.strip().replace("\\n", "\n")
        if prepared.startswith("-----BEGIN"):
            key = serialization.load_pem_public_key(prepared.encode("utf-8"))
        else:
            key = serialization.load_der_public_key(base64.b64decode("".join(prepared.split()), validate=True))
        if not isinstance(key, rsa.RSAPublicKey):
            raise ValueError("not-rsa-public-key")
        return key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")

    @staticmethod
    def _assert_channel(channel: str) -> None:
        if channel not in PUBLIC_FIELDS:
            raise ValueError("unsupported_payment_channel")

    @staticmethod
    def _settings_updates(channel: str, public: Mapping[str, object], secrets: Mapping[str, object]) -> dict[str, object]:
        if channel == "alipay":
            return {
                "alipay_app_id": public.get("appId"), "alipay_seller_id": public.get("sellerId"),
                "alipay_gateway_url": public.get("gatewayUrl"), "alipay_notify_url": public.get("notifyUrl"),
                "alipay_return_url": public.get("returnUrl"), "alipay_app_private_key": secrets.get("appPrivateKey"),
                "alipay_public_key": secrets.get("alipayPublicKey"),
            }
        return {
            "wechat_pay_mch_id": public.get("mchId"), "wechat_pay_app_id": public.get("appId"),
            "wechat_pay_merchant_serial_no": public.get("merchantSerialNo"), "wechat_pay_native_url": public.get("nativeUrl"),
            "wechat_pay_notify_url": public.get("notifyUrl"), "wechat_pay_merchant_private_key": secrets.get("merchantPrivateKey"),
            "wechat_pay_platform_public_key": secrets.get("platformPublicKey"), "wechat_pay_api_v3_key": secrets.get("apiV3Key"),
        }
