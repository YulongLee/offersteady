from __future__ import annotations

import base64
import json
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings
from app.services.payment_channel_service import PaymentChannelService
from app.services.wechat_pay_provider import WechatPayProvider


def _keys() -> tuple[str, str, object]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public_pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return private_pem, public_pem, private


class FakePaymentRepository:
    def __init__(self) -> None:
        self.rows = {channel: {"channel": channel, "enabled": False, "config_version": 1, "public_config": {},
                               "secret_config_ciphertext": None, "validation_status": "draft", "validation_errors": [],
                               "updated_by_user_id": None, "updated_at_ms": 0} for channel in ("wechat", "alipay")}

    def list_payment_channel_configs(self): return list(self.rows.values())
    def payment_channel_config(self, *, channel): return self.rows[channel]
    def save_payment_channel_config(self, **values):
        row = self.rows[values["channel"]]
        row.update({key: value for key, value in values.items() if key not in {"channel", "updated_by_user_id"}})
        row["config_version"] += 1
        row["enabled"] = False
        return row
    def set_payment_channel_enabled(self, *, channel, enabled, updated_by_user_id, updated_at_ms):
        del updated_by_user_id, updated_at_ms
        row = self.rows[channel]
        if enabled and row["validation_status"] != "ready": raise ValueError("payment_channel_not_ready")
        row["enabled"] = enabled
        return row


def test_channel_secrets_are_encrypted_masked_and_required_before_activation():
    private_pem, public_pem, _ = _keys()
    repo = FakePaymentRepository()
    service = PaymentChannelService(Settings(admin_encryption_key="unit-test-key"), repo)  # type: ignore[arg-type]
    result = service.save(
        channel="alipay",
        public_config={"appId": "app-1", "sellerId": "seller-1", "gatewayUrl": "https://openapi.alipay.com/gateway.do", "notifyUrl": "https://example.test/notify", "returnUrl": "https://example.test/return"},
        secrets={"appPrivateKey": private_pem, "alipayPublicKey": public_pem}, user_id="admin-1",
    )
    assert result["validationStatus"] == "ready"
    assert result["secretFields"]["appPrivateKey"] == {"configured": True, "masked": "••••••••"}
    assert private_pem not in str(repo.rows["alipay"]["secret_config_ciphertext"])
    assert service.set_enabled(channel="alipay", enabled=True, user_id="admin-1")["enabled"] is True
    incomplete = service.save(channel="wechat", public_config={}, secrets={}, user_id="admin-1")
    assert incomplete["validationStatus"] == "draft"
    try:
        service.set_enabled(channel="wechat", enabled=True, user_id="admin-1")
        raise AssertionError("incomplete channel was enabled")
    except ValueError as exc:
        assert str(exc) == "payment_channel_not_ready"


def test_wechat_notification_signature_identity_and_aes_gcm_decryption():
    merchant_private, platform_public, platform_private = _keys()
    api_key = "0123456789abcdef0123456789abcdef"
    settings = Settings(
        wechat_pay_mch_id="mch-1", wechat_pay_app_id="app-1", wechat_pay_merchant_serial_no="serial-1",
        wechat_pay_merchant_private_key=merchant_private, wechat_pay_platform_public_key=platform_public,
        wechat_pay_api_v3_key=api_key, wechat_pay_notify_url="https://example.test/notify",
    )
    provider = WechatPayProvider(settings)
    nonce = b"123456789012"
    associated = b"transaction"
    resource = json.dumps({"mchid": "mch-1", "appid": "app-1", "out_trade_no": "order-1", "transaction_id": "wx-1", "trade_state": "SUCCESS", "amount": {"total": 3990}}).encode()
    ciphertext = AESGCM(api_key.encode()).encrypt(nonce, resource, associated)
    body = json.dumps({"resource": {"nonce": nonce.decode(), "associated_data": associated.decode(), "ciphertext": base64.b64encode(ciphertext).decode()}}, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = base64.b64encode(platform_private.sign(f"{timestamp}\nnotice-nonce\n{body.decode()}\n".encode(), padding.PKCS1v15(), hashes.SHA256())).decode()
    notification = provider.parse_notification(body, {"wechatpay-timestamp": timestamp, "wechatpay-nonce": "notice-nonce", "wechatpay-signature": signature})
    assert notification.verified is True
    assert notification.paid is True
    assert notification.order_id == "order-1"
    assert notification.amount_cents == 3990

