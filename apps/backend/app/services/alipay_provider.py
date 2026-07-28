from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from json import dumps
from math import ceil
from textwrap import wrap
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import Settings


@dataclass(frozen=True)
class AlipayNotification:
    order_id: str
    provider_trade_no: str
    amount_cents: int
    paid: bool
    verified: bool


class AlipayPaymentProvider:
    """Official Alipay Open Platform computer-web payment adapter."""

    provider_name = "alipay"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.alipay_app_id
            and self.settings.alipay_app_private_key
            and self.settings.alipay_public_key
            and self.settings.alipay_seller_id
        )

    @property
    def payment_ttl_seconds(self) -> int:
        return self.settings.alipay_payment_ttl_seconds

    def payment_url(
        self,
        *,
        order_id: str,
        product_name: str,
        amount_cents: int,
        channel: str,
        client_ip: str | None = None,
    ) -> str:
        del client_ip
        if not self.enabled:
            raise RuntimeError("支付宝官方支付尚未配置完整商户参数")
        if channel != "alipay":
            raise ValueError("支付宝官方支付仅支持支付宝渠道")
        biz_content = {
            "out_trade_no": order_id,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            "subject": product_name[:256],
            "total_amount": self._format_money(amount_cents),
            "timeout_express": f"{max(1, ceil(self.payment_ttl_seconds / 60))}m",
        }
        params = {
            "app_id": self.settings.alipay_app_id or "",
            "method": "alipay.trade.page.pay",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": self._notify_url(),
            "return_url": self._return_url(),
            "biz_content": dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
        }
        return f"{self.settings.alipay_gateway_url}?{urlencode({**params, 'sign': self._sign(params)})}"

    def parse_notification(self, params: dict[str, str]) -> AlipayNotification:
        signature_verified = self.verify(params)
        identity_verified = (
            params.get("app_id", "") == (self.settings.alipay_app_id or "")
            and params.get("seller_id", "") == (self.settings.alipay_seller_id or "")
        )
        return AlipayNotification(
            order_id=params.get("out_trade_no", ""),
            provider_trade_no=params.get("trade_no", ""),
            amount_cents=self._money_to_cents(params.get("total_amount", "0")),
            paid=params.get("trade_status", "").upper() in {"TRADE_SUCCESS", "TRADE_FINISHED"},
            verified=signature_verified and identity_verified,
        )

    def verify(self, params: dict[str, str]) -> bool:
        signature = params.get("sign", "")
        if not signature or not self.settings.alipay_public_key:
            return False
        try:
            public_key = serialization.load_pem_public_key(
                self._pem(self.settings.alipay_public_key, "PUBLIC KEY")
            )
            public_key.verify(
                b64decode(signature),
                self._canonical(params).encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except (TypeError, ValueError):
            return False
        except Exception:
            return False

    def _sign(self, params: dict[str, str]) -> str:
        if not self.settings.alipay_app_private_key:
            raise RuntimeError("支付宝应用私钥未配置")
        private_key = serialization.load_pem_private_key(
            self._pem(self.settings.alipay_app_private_key, "PRIVATE KEY"),
            password=None,
        )
        signature = private_key.sign(
            self._canonical(params).encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return b64encode(signature).decode("ascii")

    @staticmethod
    def _canonical(params: dict[str, str]) -> str:
        filtered = {
            key: str(value)
            for key, value in params.items()
            if key not in {"sign", "sign_type"} and value is not None and str(value) != ""
        }
        return "&".join(f"{key}={filtered[key]}" for key in sorted(filtered))

    @staticmethod
    def _pem(value: str, label: str) -> bytes:
        normalized = value.strip().replace("\\n", "\n")
        if normalized.startswith("-----BEGIN"):
            return normalized.encode("utf-8")
        body = "".join(normalized.split())
        return f"-----BEGIN {label}-----\n{'\n'.join(wrap(body, 64))}\n-----END {label}-----\n".encode("utf-8")

    def _notify_url(self) -> str:
        return self.settings.alipay_notify_url or "http://127.0.0.1:8000/api/v1/billing/payment-providers/alipay/notify"

    def _return_url(self) -> str:
        return self.settings.alipay_return_url or f"{self.settings.public_web_base_url.rstrip('/')}/app/billing"

    @staticmethod
    def _format_money(amount_cents: int) -> str:
        return f"{Decimal(amount_cents) / Decimal(100):.2f}"

    @staticmethod
    def _money_to_cents(value: str) -> int:
        try:
            amount = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return 0
        return int(amount * 100)
