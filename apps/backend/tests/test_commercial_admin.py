from __future__ import annotations

import base64
import hashlib
import hmac
import struct

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.admin_repository import AdminRepository
from app.services.admin_service import AdminService, PERMISSIONS_BY_ROLE, SAFE_DETAIL_KEYS


def test_admin_is_disabled_and_hidden_by_default() -> None:
    get_settings.cache_clear()
    client = TestClient(create_app())
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 404


def test_admin_role_permissions_are_deny_by_default() -> None:
    assert "billing.adjust" not in PERMISSIONS_BY_ROLE["support"]
    assert "admins.manage" not in PERMISSIONS_BY_ROLE["finance"]
    assert "admins.manage" in PERMISSIONS_BY_ROLE["super_admin"]
    assert "resume_text" not in SAFE_DETAIL_KEYS
    assert "access_token" not in SAFE_DETAIL_KEYS
    assert "screenshot" not in SAFE_DETAIL_KEYS


def test_totp_verification_accepts_current_window_and_rejects_invalid_code() -> None:
    secret = "JBSWY3DPEHPK3PXP"
    timestamp = 1_780_000_000
    normalized = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(normalized)
    counter = timestamp // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    index = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[index:index + 4])[0] & 0x7FFFFFFF) % 1_000_000
    code = f"{value:06d}"
    assert AdminService.verify_totp(secret, code, timestamp=timestamp)
    assert not AdminService.verify_totp(secret, "000000", timestamp=timestamp)


def test_admin_secrets_are_not_ready_when_unconfigured() -> None:
    class RepositoryStub:
        pass

    service = AdminService(Settings(admin_enabled=True), RepositoryStub())  # type: ignore[arg-type]
    try:
        service.assert_ready()
    except PermissionError as exc:
        assert str(exc) == "admin_security_not_configured"
    else:
        raise AssertionError("admin service must not start without dedicated secrets")


def test_admin_domain_command_is_idempotent() -> None:
    class RepositoryStub:
        def __init__(self) -> None:
            self.results: dict[tuple[str, str, str], dict[str, object]] = {}

        def idempotent_result(self, *, actor_user_id: str, action: str, key: str):
            return self.results.get((actor_user_id, action, key))

        def save_idempotent_result(
            self, *, actor_user_id: str, action: str, key: str, result: dict[str, object]
        ) -> None:
            self.results[(actor_user_id, action, key)] = result

    repository = RepositoryStub()
    service = AdminService(Settings(), repository)  # type: ignore[arg-type]
    principal = type("Principal", (), {"user_id": "synthetic-admin"})()
    calls = 0

    def command() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"status": "applied"}

    first, first_replay = service.execute_idempotent(
        principal=principal, action="billing.adjust.points", key="same-key", callback=command
    )
    second, second_replay = service.execute_idempotent(
        principal=principal, action="billing.adjust.points", key="same-key", callback=command
    )
    assert first == second == {"status": "applied"}
    assert first_replay is False
    assert second_replay is True
    assert calls == 1


def test_browser_admin_provisioning_requires_existing_bootstrap_and_registered_user() -> None:
    class RepositoryStub:
        active_count = 0

        def active_administrator_count(self) -> int:
            return self.active_count

        def user_by_login(self, login_id: str):
            if login_id != "19700000000":
                return None
            return {"user_id": "synthetic-user", "display_name": "测试管理员"}

        def upsert_authorization(self, **values):
            return {"role": values["role"], "status": "active"}

    repository = RepositoryStub()
    settings = Settings(admin_encryption_key="synthetic-encryption-key")
    service = AdminService(settings, repository)  # type: ignore[arg-type]
    try:
        service.provision_administrator(
            login_id="19700000000",
            role="operations",
            actor_user_id="super-admin",
        )
    except PermissionError as exc:
        assert str(exc) == "first_super_admin_requires_server_bootstrap"
    else:
        raise AssertionError("browser flow must not create the first administrator")

    repository.active_count = 1
    result = service.provision_administrator(
        login_id="19700000000",
        role="operations",
        actor_user_id="super-admin",
    )
    assert result["status"] == "active"
    assert result["role"] == "operations"
    assert result["enrollment_display_once"] is True
    assert str(result["provisioning_uri"]).startswith("otpauth://totp/")


def test_administrator_cannot_disable_self() -> None:
    service = AdminService(Settings(), object())  # type: ignore[arg-type]
    try:
        service.disable_administrator(
            target_user_id="same-admin",
            actor_user_id="same-admin",
        )
    except PermissionError as exc:
        assert str(exc) == "administrator_cannot_disable_self"
    else:
        raise AssertionError("administrator must not disable their own authorization")


def test_admin_phone_lookup_uses_the_same_irreversible_identity_as_sms_login() -> None:
    repository = object.__new__(AdminRepository)
    repository.settings = Settings(auth_jwt_secret="synthetic-jwt-secret")
    direct, sms_login = repository._login_candidates("19700000000")
    assert direct == "19700000000"
    assert sms_login.startswith("sms:")
    assert "19700000000" not in sms_login
    assert len(sms_login) == 68
