from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import md5
from urllib.parse import urlencode

from app.core.config import Settings


@dataclass(frozen=True)
class MzfpayNotification:
    order_id: str
    provider_trade_no: str
    amount_cents: int
    paid: bool
    verified: bool


class MzfpayPaymentProvider:
    """Small EPay-compatible adapter for mzfpay checkout and notify signing."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.mzfpay_pid and self.settings.mzfpay_key)

    def payment_url(self, *, order_id: str, product_name: str, amount_cents: int, channel: str, client_ip: str | None = None) -> str:
        if not self.settings.mzfpay_pid or not self.settings.mzfpay_key:
            raise RuntimeError("码支付尚未配置商户号或密钥")
        params = {
            "pid": self.settings.mzfpay_pid,
            "type": self._channel_type(channel),
            "out_trade_no": order_id,
            "notify_url": self._notify_url(),
            "return_url": self._return_url(),
            "name": product_name,
            "money": self._format_money(amount_cents),
            "sitename": "面试稳",
            **({"clientip": client_ip} if client_ip else {}),
        }
        signed = self._with_sign(params)
        submit_path = self.settings.mzfpay_submit_path if self.settings.mzfpay_submit_path.startswith("/") else f"/{self.settings.mzfpay_submit_path}"
        return f"{self.settings.mzfpay_base_url.rstrip('/')}{submit_path}?{urlencode(signed)}"

    def parse_notification(self, params: dict[str, str]) -> MzfpayNotification:
        verified = self.verify(params)
        return MzfpayNotification(
            order_id=params.get("out_trade_no", ""),
            provider_trade_no=params.get("trade_no", "") or params.get("api_trade_no", ""),
            amount_cents=self._money_to_cents(params.get("money", "0")),
            paid=params.get("trade_status", "").upper() in {"TRADE_SUCCESS", "SUCCESS", "PAID"},
            verified=verified,
        )

    def verify(self, params: dict[str, str]) -> bool:
        if not self.settings.mzfpay_key:
            return False
        provided = params.get("sign", "")
        if not provided:
            return False
        return provided.lower() == self._sign(params).lower()

    def _with_sign(self, params: dict[str, str]) -> dict[str, str]:
        return {**params, "sign": self._sign(params), "sign_type": "MD5"}

    def _sign(self, params: dict[str, str]) -> str:
        filtered = {
            key: value
            for key, value in params.items()
            if key not in {"sign", "sign_type"} and value is not None and str(value) != ""
        }
        payload = "&".join(f"{key}={filtered[key]}" for key in sorted(filtered))
        return md5(f"{payload}{self.settings.mzfpay_key or ''}".encode("utf-8")).hexdigest()

    def _notify_url(self) -> str:
        return self.settings.mzfpay_notify_url or "http://127.0.0.1:8000/api/v1/billing/payment-providers/mzfpay/notify"

    def _return_url(self) -> str:
        return self.settings.mzfpay_return_url or f"{self.settings.public_web_base_url.rstrip('/')}/app/billing"

    def _channel_type(self, channel: str) -> str:
        return "wxpay" if channel == "wechat" else "alipay"

    def _format_money(self, amount_cents: int) -> str:
        return f"{Decimal(amount_cents) / Decimal(100):.2f}"

    def _money_to_cents(self, value: str) -> int:
        try:
            amount = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            return 0
        return int(amount * 100)
