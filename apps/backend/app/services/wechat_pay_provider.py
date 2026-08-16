from __future__ import annotations

import base64
import json
import secrets
import time
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature, InvalidTag

from app.core.config import Settings


@dataclass(frozen=True)
class WechatPayNotification:
    order_id: str
    provider_trade_no: str
    amount_cents: int
    paid: bool
    verified: bool


class WechatPayRequestError(RuntimeError):
    """A provider failure safe to persist and expose without response secrets."""

    def __init__(self, provider_code: str, *, status_code: int | None = None) -> None:
        normalized = re.sub(r"[^A-Z0-9_]", "_", provider_code.upper()).strip("_")[:64] or "UNKNOWN"
        self.provider_code = normalized
        self.status_code = status_code
        self.safe_code = f"wechat_native_{status_code or 'network'}_{normalized}".lower()
        super().__init__(self.safe_code)


class WechatPayProvider:
    """Official WeChat Pay API v3 Native adapter."""

    provider_name = "wechat"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return all((self.settings.wechat_pay_mch_id, self.settings.wechat_pay_app_id,
                    self.settings.wechat_pay_merchant_serial_no, self.settings.wechat_pay_merchant_private_key,
                    self.settings.wechat_pay_platform_public_key, self.settings.wechat_pay_api_v3_key,
                    self.settings.wechat_pay_notify_url))

    @property
    def payment_ttl_seconds(self) -> int:
        return self.settings.wechat_pay_payment_ttl_seconds

    def payment_url(self, *, order_id: str, product_name: str, amount_cents: int, channel: str, client_ip: str | None = None) -> str:
        del client_ip
        if not self.enabled:
            raise RuntimeError("微信支付尚未配置完整商户参数")
        if channel != "wechat":
            raise ValueError("微信支付仅支持微信渠道")
        payload = {
            "appid": self.settings.wechat_pay_app_id,
            "mchid": self.settings.wechat_pay_mch_id,
            "description": product_name[:127],
            "out_trade_no": order_id,
            "notify_url": self.settings.wechat_pay_notify_url,
            "time_expire": (datetime.now(timezone.utc) + timedelta(seconds=self.payment_ttl_seconds)).isoformat(timespec="seconds"),
            "amount": {"total": amount_cents, "currency": "CNY"},
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        url = self.settings.wechat_pay_native_url
        authorization = self._authorization("POST", urlparse(url).path, body)
        try:
            response = httpx.post(url, content=body.encode(), headers={"Authorization": authorization, "Accept": "application/json", "Content-Type": "application/json"}, timeout=8.0)
        except httpx.RequestError as exc:
            raise WechatPayRequestError("NETWORK_ERROR") from exc
        if response.status_code >= 400:
            try:
                response_payload = response.json()
                provider_code = str(response_payload.get("code") or f"HTTP_{response.status_code}")
            except (ValueError, TypeError, AttributeError):
                provider_code = f"HTTP_{response.status_code}"
            raise WechatPayRequestError(provider_code, status_code=response.status_code)
        response_body = response.text
        response_timestamp = response.headers.get("Wechatpay-Timestamp", "")
        response_nonce = response.headers.get("Wechatpay-Nonce", "")
        response_signature = response.headers.get("Wechatpay-Signature", "")
        if not self._verify(f"{response_timestamp}\n{response_nonce}\n{response_body}\n", response_signature):
            raise WechatPayRequestError("RESPONSE_SIGNATURE_INVALID")
        code_url = str(response.json().get("code_url", ""))
        if not code_url:
            raise WechatPayRequestError("CODE_URL_MISSING")
        return code_url

    def parse_notification(self, body: bytes, headers: dict[str, str]) -> WechatPayNotification:
        timestamp = headers.get("wechatpay-timestamp", "")
        nonce = headers.get("wechatpay-nonce", "")
        signature = headers.get("wechatpay-signature", "")
        fresh = timestamp.isdigit() and abs(int(time.time()) - int(timestamp)) <= 300
        verified = fresh and self._verify(f"{timestamp}\n{nonce}\n{body.decode()}\n", signature)
        try:
            envelope = json.loads(body)
            resource = envelope["resource"]
            plaintext = AESGCM((self.settings.wechat_pay_api_v3_key or "").encode()).decrypt(
                str(resource["nonce"]).encode(), base64.b64decode(resource["ciphertext"]), str(resource.get("associated_data", "")).encode(),
            )
            data = json.loads(plaintext)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError, InvalidTag):
            return WechatPayNotification("", "", 0, False, False)
        identity_ok = data.get("mchid") == self.settings.wechat_pay_mch_id and data.get("appid") == self.settings.wechat_pay_app_id
        amount = data.get("amount") if isinstance(data.get("amount"), dict) else {}
        return WechatPayNotification(
            order_id=str(data.get("out_trade_no", "")), provider_trade_no=str(data.get("transaction_id", "")),
            amount_cents=int(amount.get("total", 0)), paid=data.get("trade_state") == "SUCCESS", verified=verified and identity_ok,
        )

    def _authorization(self, method: str, path: str, body: str) -> str:
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"
        signature = self._sign(message)
        return (
            'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self.settings.wechat_pay_mch_id}",nonce_str="{nonce}",timestamp="{timestamp}",'
            f'serial_no="{self.settings.wechat_pay_merchant_serial_no}",signature="{signature}"'
        )

    def _sign(self, message: str) -> str:
        key = serialization.load_pem_private_key((self.settings.wechat_pay_merchant_private_key or "").encode(), password=None)
        return base64.b64encode(key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())).decode()

    def _verify(self, message: str, signature: str) -> bool:
        try:
            key = serialization.load_pem_public_key((self.settings.wechat_pay_platform_public_key or "").encode())
            key.verify(base64.b64decode(signature), message.encode(), padding.PKCS1v15(), hashes.SHA256())
            return True
        except (ValueError, TypeError, InvalidSignature):
            return False
