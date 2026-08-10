from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timedelta, timezone
from textwrap import wrap

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID

from app.core.config import Settings
from app.services.payment_channel_service import PaymentChannelService
from app.services.wechat_pay_provider import WechatPayProvider


def _keys() -> tuple[str, str, object]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    public_pem = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    return private_pem, public_pem, private


def _pem_body(value: str) -> str:
    return "".join(line for line in value.splitlines() if not line.startswith("-----"))


def _alipay_public_config() -> dict[str, str]:
    return {
        "appId": "app-1",
        "sellerId": "seller-1",
        "gatewayUrl": "https://openapi.alipay.com/gateway.do",
        "notifyUrl": "https://example.test/notify",
        "returnUrl": "https://example.test/return",
    }


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


def test_alipay_accepts_copied_base64_keys_and_persists_canonical_pem() -> None:
    private_pem, public_pem, _ = _keys()
    repository = FakePaymentRepository()
    service = PaymentChannelService(Settings(admin_encryption_key="unit-test-key"), repository)  # type: ignore[arg-type]

    result = service.save(
        channel="alipay",
        public_config=_alipay_public_config(),
        secrets={
            "appPrivateKey": "\n".join(wrap(_pem_body(private_pem), 72)),
            "alipayPublicKey": "\n".join(wrap(_pem_body(public_pem), 72)),
        },
        user_id="admin-1",
    )

    stored = service._decrypt(str(repository.rows["alipay"]["secret_config_ciphertext"]))
    assert result["validationStatus"] == "ready"
    assert stored["appPrivateKey"].startswith("-----BEGIN PRIVATE KEY-----")
    assert stored["alipayPublicKey"].startswith("-----BEGIN PUBLIC KEY-----")
    serialization.load_pem_private_key(stored["appPrivateKey"].encode(), password=None)
    serialization.load_pem_public_key(stored["alipayPublicKey"].encode())


def test_alipay_accepts_copied_pkcs1_private_key_body() -> None:
    _, public_pem, private = _keys()
    pkcs1_private = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    repository = FakePaymentRepository()
    service = PaymentChannelService(Settings(admin_encryption_key="unit-test-key"), repository)  # type: ignore[arg-type]

    result = service.save(
        channel="alipay",
        public_config=_alipay_public_config(),
        secrets={"appPrivateKey": _pem_body(pkcs1_private), "alipayPublicKey": _pem_body(public_pem)},
        user_id="admin-1",
    )

    assert result["validationStatus"] == "ready"


def test_alipay_revalidates_existing_encrypted_base64_draft_without_replacement() -> None:
    private_pem, public_pem, _ = _keys()
    repository = FakePaymentRepository()
    service = PaymentChannelService(Settings(admin_encryption_key="unit-test-key"), repository)  # type: ignore[arg-type]
    repository.rows["alipay"].update({
        "public_config": _alipay_public_config(),
        "secret_config_ciphertext": service._encrypt({
            "appPrivateKey": _pem_body(private_pem),
            "alipayPublicKey": _pem_body(public_pem),
        }),
        "validation_status": "draft",
    })

    result = service.save(channel="alipay", public_config={}, secrets={}, user_id="admin-1")

    assert result["validationStatus"] == "ready"
    stored = service._decrypt(str(repository.rows["alipay"]["secret_config_ciphertext"]))
    assert stored["appPrivateKey"].startswith("-----BEGIN PRIVATE KEY-----")
    assert stored["alipayPublicKey"].startswith("-----BEGIN PUBLIC KEY-----")


def test_alipay_rejects_non_rsa_invalid_and_certificate_material_without_echoing_secrets() -> None:
    ec_private = ec.generate_private_key(ec.SECP256R1())
    ec_private_pem = ec_private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    rsa_private_pem, _, rsa_private = _keys()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "synthetic-alipay-test")])
    now = datetime.now(timezone.utc)
    certificate_pem = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(
        rsa_private.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(now).not_valid_after(
        now + timedelta(days=1)
    ).sign(rsa_private, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode()
    repository = FakePaymentRepository()
    service = PaymentChannelService(Settings(admin_encryption_key="unit-test-key"), repository)  # type: ignore[arg-type]

    result = service.save(
        channel="alipay",
        public_config=_alipay_public_config(),
        secrets={"appPrivateKey": ec_private_pem, "alipayPublicKey": certificate_pem},
        user_id="admin-1",
    )

    assert result["validationStatus"] == "draft"
    assert "appPrivateKey 不是有效的 RSA PEM 私钥" in result["validationErrors"]
    assert "alipayPublicKey 不是有效的 RSA PEM 公钥" in result["validationErrors"]
    assert ec_private_pem not in str(result)
    assert certificate_pem not in str(result)
    assert rsa_private_pem not in str(result)

    invalid = service.save(
        channel="alipay",
        public_config={},
        secrets={"appPrivateKey": "not-a-key", "alipayPublicKey": "also-not-a-key"},
        user_id="admin-1",
    )
    assert invalid["validationStatus"] == "draft"
    assert "not-a-key" not in str(invalid)


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
