from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.authentication import AuthenticatedRequestContext, UserRecord
from app.services.authentication_repository import InMemoryAuthenticationRepository
from app.services.authentication_service import AuthenticationService, JWTAccessTokenCodec, PBKDF2PasswordHasher
from app.services.email_verification_provider import FakeEmailVerificationProvider
from app.services.postgres_authentication_repository import PostgresAuthenticationRepository
from app.services.sms_verification_provider import FakeSmsVerificationProvider


def build_service(*, edition: str = "global", **overrides) -> tuple[AuthenticationService, InMemoryAuthenticationRepository]:
    settings = Settings(
        _env_file=None,
        product_edition=edition,
        auth_email_enabled=True,
        auth_email_provider_mode="fake",
        auth_email_code_pepper="synthetic-global-password-pepper",
        auth_email_send_interval_seconds=0,
        **overrides,
    )
    repository = InMemoryAuthenticationRepository()
    return AuthenticationService(
        settings=settings,
        logger=logging.getLogger("test.global-password"),
        repository=repository,
        password_hasher=PBKDF2PasswordHasher(settings),
        token_codec=JWTAccessTokenCodec(settings),
        wechat_provider=None,  # type: ignore[arg-type]
        sms_provider=FakeSmsVerificationProvider(settings),
        email_provider=FakeEmailVerificationProvider(settings),
    ), repository


def complete_registration(service: AuthenticationService, email: str = "candidate@example.com"):
    challenge = service.send_email_code(email=email, client_label="web-global", purpose="registration")
    return service.register_global_user(
        challenge_id=challenge.challenge_id,
        email=email,
        code="123456",
        password="correct horse battery staple",
        client_label="web-global",
    )


def test_global_registration_uses_argon2_and_password_login_reuses_user() -> None:
    service, _ = build_service()
    user, _, _, _ = complete_registration(service)
    assert user.password_hash.startswith("$argon2id$")

    repeated, _, access_token, refresh_token = service.login_global_user(
        email="CANDIDATE@example.com",
        password="correct horse battery staple",
        client_label="web-global",
    )
    assert repeated.user_id == user.user_id
    assert access_token and refresh_token

    with pytest.raises(DomainRequestError) as invalid:
        service.login_global_user(email="candidate@example.com", password="wrong password", client_label="web-global")
    assert invalid.value.error_code == "invalid_global_credentials"


def test_purpose_bound_code_cannot_be_replayed_for_registration() -> None:
    service, _ = build_service()
    reset = service.send_email_code(email="new@example.com", client_label="web-global", purpose="password_reset")
    with pytest.raises(DomainRequestError) as mismatch:
        service.register_global_user(
            challenge_id=reset.challenge_id, email="new@example.com", code="123456",
            password="a sufficiently long passphrase", client_label="web-global",
        )
    assert mismatch.value.error_code == "email_challenge_not_found"


def test_existing_passwordless_user_sets_password_without_new_user_id() -> None:
    service, repository = build_service()
    now = 1
    original = repository.create_user(UserRecord(
        user_id="legacy-code-user", login_id="legacy@example.com", password_hash="external-auth",
        display_name="Legacy", avatar_url=None, last_login_provider="email",
        last_login_at_ms=now, created_at_ms=now, updated_at_ms=now,
    ))
    assert original is not None
    assert original.password_hash == "external-auth"

    setup = service.send_email_code(email="legacy@example.com", client_label="web-global", purpose="password_setup")
    migrated, *_ = service.setup_global_password(
        challenge_id=setup.challenge_id, email="legacy@example.com", code="123456",
        password="my long migrated password", client_label="web-global",
    )
    assert migrated.user_id == original.user_id
    assert migrated.password_hash.startswith("$argon2id$")
    assert len(repository.users_by_id) == 1


def test_legacy_email_code_endpoint_cannot_create_new_global_account() -> None:
    service, repository = build_service()
    challenge = service.send_email_code(email="bypass@example.com", client_label="web-global")
    with pytest.raises(DomainRequestError) as blocked:
        service.verify_email_login(challenge_id=challenge.challenge_id, email="bypass@example.com", code="123456", client_label="web-global")
    assert blocked.value.error_code == "global_legacy_email_login_unavailable"
    assert repository.get_user_by_login_id("bypass@example.com") is None


def test_reset_revokes_old_sessions_and_change_keeps_current_session() -> None:
    service, repository = build_service()
    user, first_session, *_ = complete_registration(service, "security@example.com")
    _, second_session, *_ = service.login_global_user(email=user.login_id, password="correct horse battery staple", client_label="other-device")

    reset = service.send_email_code(email=user.login_id, client_label="web-global", purpose="password_reset")
    reset_user, reset_session, *_ = service.reset_global_password(
        challenge_id=reset.challenge_id, email=user.login_id, code="123456",
        password="new password after recovery", client_label="recovered-device",
    )
    assert repository.get_auth_session(first_session.auth_session_id).status == "revoked"  # type: ignore[union-attr]
    assert repository.get_auth_session(second_session.auth_session_id).status == "revoked"  # type: ignore[union-attr]
    assert repository.get_auth_session(reset_session.auth_session_id).status == "active"  # type: ignore[union-attr]

    _, other_session, *_ = service.login_global_user(email=user.login_id, password="new password after recovery", client_label="other-device")
    service.change_global_password(
        auth_context=AuthenticatedRequestContext(user_id=reset_user.user_id, login_id=reset_user.login_id, auth_session_id=reset_session.auth_session_id),
        current_password="new password after recovery",
        new_password="another secure password value",
    )
    assert repository.get_auth_session(reset_session.auth_session_id).status == "active"  # type: ignore[union-attr]
    assert repository.get_auth_session(other_session.auth_session_id).status == "revoked"  # type: ignore[union-attr]


def test_password_policy_and_domestic_isolation() -> None:
    service, _ = build_service()
    challenge = service.send_email_code(email="weak@example.com", client_label="web-global", purpose="registration")
    with pytest.raises(DomainRequestError) as weak:
        service.register_global_user(challenge_id=challenge.challenge_id, email="weak@example.com", code="123456", password="too short", client_label="web-global")
    assert weak.value.error_code == "password_too_short"

    domestic, _ = build_service(edition="cn")
    with pytest.raises(DomainRequestError) as unavailable:
        domestic.login_global_user(email="user@example.com", password="correct horse battery staple", client_label="web-global")
    assert unavailable.value.error_code == "global_password_auth_disabled"


def test_unverified_legacy_password_routes_are_disabled_only_for_global() -> None:
    global_service, _ = build_service()
    with pytest.raises(DomainRequestError) as blocked:
        global_service.register_user(login_id="unsafe@example.com", password="correct horse battery staple", display_name=None, client_label="web")
    assert blocked.value.error_code == "legacy_password_route_disabled"

    domestic, _ = build_service(edition="cn")
    domestic_user, *_ = domestic.register_user(login_id="domestic-user", password="domestic-password", display_name=None, client_label="web")
    assert domestic_user.login_id == "domestic-user"


def test_valid_legacy_pbkdf2_hash_is_upgraded_after_global_login() -> None:
    service, repository = build_service()
    legacy_hasher = PBKDF2PasswordHasher(Settings(_env_file=None, product_edition="cn"))
    repository.create_user(UserRecord(
        user_id="legacy-pbkdf2-user", login_id="legacy-hash@example.com",
        password_hash=legacy_hasher.hash_password("legacy secure password"),
        display_name="Legacy", avatar_url=None, last_login_provider="password",
        last_login_at_ms=1, created_at_ms=1, updated_at_ms=1,
    ))
    user, *_ = service.login_global_user(email="legacy-hash@example.com", password="legacy secure password", client_label="web-global")
    assert user.password_hash.startswith("$argon2id$")


def test_global_login_throttles_by_account_and_origin() -> None:
    service, _ = build_service(auth_global_login_attempt_limit=2)
    for _ in range(2):
        with pytest.raises(DomainRequestError) as invalid:
            service.login_global_user(email="unknown@example.com", password="not the password", client_label="web-global", request_origin="203.0.113.4")
        assert invalid.value.error_code == "invalid_global_credentials"
    with pytest.raises(DomainRequestError) as limited:
        service.login_global_user(email="unknown@example.com", password="not the password", client_label="web-global", request_origin="203.0.113.4")
    assert limited.value.error_code == "global_login_rate_limited"


def test_global_password_migration_is_additive_and_purpose_bound() -> None:
    migration = Path(__file__).parents[1] / "migrations/versions/0041_global_password_authentication.sql"
    sql = migration.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS purpose" in sql
    assert "DEFAULT 'login'" in sql
    assert "DROP TABLE" not in sql.upper()


@pytest.mark.parametrize("purpose", ["registration", "password_setup", "password_reset"])
def test_postgres_email_challenge_mapping_preserves_global_purpose(purpose: str) -> None:
    mapped = PostgresAuthenticationRepository._email_challenge_from_row({
        "challenge_id": "email-challenge-persistent",
        "email_hash": "synthetic-email-hash",
        "masked_email": "ca*******@example.com",
        "provider": "fake",
        "status": "sent",
        "provider_message_id": None,
        "provider_request_id": None,
        "attempt_count": 0,
        "max_attempts": 5,
        "expires_at_ms": 2_000,
        "created_at_ms": 1_000,
        "updated_at_ms": 1_000,
        "last_error_code": None,
        "verified_at_ms": None,
        "code_digest": "synthetic-code-digest",
        "purpose": purpose,
    })

    assert mapped.purpose == purpose
