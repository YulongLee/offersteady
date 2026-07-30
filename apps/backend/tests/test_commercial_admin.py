from __future__ import annotations

import base64
import hashlib
import hmac
import struct

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
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
