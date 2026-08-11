from __future__ import annotations

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
    assert "redemptions.generate" in PERMISSIONS_BY_ROLE["finance"]
    assert "redemptions.generate" not in PERMISSIONS_BY_ROLE["support"]
    assert "payments.manage" in PERMISSIONS_BY_ROLE["super_admin"]
    assert "payments.manage" in PERMISSIONS_BY_ROLE["finance"]
    assert "payments.manage" not in PERMISSIONS_BY_ROLE["support"]
    assert "growth.manage" in PERMISSIONS_BY_ROLE["super_admin"]
    assert "growth.manage" in PERMISSIONS_BY_ROLE["operations"]
    assert "growth.manage" not in PERMISSIONS_BY_ROLE["support"]
    assert "appPrivateKey" not in SAFE_DETAIL_KEYS
    assert "apiV3Key" not in SAFE_DETAIL_KEYS
    assert "resume_text" not in SAFE_DETAIL_KEYS
    assert "access_token" not in SAFE_DETAIL_KEYS
    assert "screenshot" not in SAFE_DETAIL_KEYS


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
    assert "totp_secret" not in result
    assert "provisioning_uri" not in result


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


def test_generated_redemption_codes_are_unique_and_plaintext_is_only_returned_once() -> None:
    class RepositoryStub:
        received_codes: list[str] = []

        def create_redemption_batch(self, **values):
            self.received_codes = values["codes"]
            return {
                "batch_id": values["batch_id"],
                "campaign": values["campaign"],
                "points_per_code": values["points"],
                "code_count": len(values["codes"]),
                "expires_at_ms": values["expires_at_ms"],
                "codes": values["codes"],
            }, False

    repository = RepositoryStub()
    service = AdminService(Settings(), repository)  # type: ignore[arg-type]
    principal = type("Principal", (), {"user_id": "synthetic-finance"})()
    result, replay = service.create_redemption_batch(
        principal=principal,  # type: ignore[arg-type]
        idempotency_key="synthetic-key",
        campaign="内测活动",
        reason="用于受控内测发放",
        points=2000,
        quantity=100,
        expires_in_days=30,
    )
    codes = result["codes"]
    assert replay is False
    assert len(codes) == len(set(codes)) == 100
    assert all(len(code) == 19 and len(code.replace("-", "")) == 16 for code in codes)
    assert all(len(code.split("-")) == 4 and all(len(part) == 4 for part in code.split("-")) for code in codes)
    assert repository.received_codes == codes


def test_admin_audit_query_casts_optional_filters_for_postgres() -> None:
    query = AdminRepository.list_audit.__code__.co_consts
    sql = next(value for value in query if isinstance(value, str) and "admin_audit_events" in value)
    assert "%s::TEXT IS NULL" in sql


def test_admin_interview_queries_exclude_deleted_and_share_idle_cutoff() -> None:
    dashboard_constants = AdminRepository.dashboard.__code__.co_consts
    list_constants = AdminRepository.list_sessions.__code__.co_consts
    dashboard_sql = " ".join(value for value in dashboard_constants if isinstance(value, str))
    list_sql = " ".join(value for value in list_constants if isinstance(value, str))

    assert "deleted_at_ms IS NULL" in dashboard_sql
    assert "last_activity_at_ms >= %s" in dashboard_sql
    assert "deleted_at_ms IS NULL" in list_sql
    assert "idle-timeout" in list_sql


def test_admin_list_prefers_masked_sms_identity_over_hashed_login() -> None:
    query = AdminRepository.list_administrators.__code__.co_consts
    sql = next(value for value in query if isinstance(value, str) and "admin_authorizations" in value)
    assert "provider_subject_hint" in sql
    assert "provider = 'sms'" in sql
