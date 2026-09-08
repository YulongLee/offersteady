from __future__ import annotations

import logging
from dataclasses import replace

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.services.authentication_repository import InMemoryAuthenticationRepository
from app.services.authentication_service import AuthenticationService, JWTAccessTokenCodec, PBKDF2PasswordHasher
from app.services.email_verification_provider import FakeEmailVerificationProvider, SmtpEmailVerificationProvider
from app.services.sms_verification_provider import FakeSmsVerificationProvider


def build_service(**overrides) -> tuple[AuthenticationService, InMemoryAuthenticationRepository]:
    settings = Settings(
        _env_file=None,
        auth_email_enabled=True,
        auth_email_provider_mode="fake",
        auth_email_code_pepper="synthetic-email-pepper-for-tests",
        **overrides,
    )
    repository = InMemoryAuthenticationRepository()
    service = AuthenticationService(
        settings=settings,
        logger=logging.getLogger("test.email-authentication"),
        repository=repository,
        password_hasher=PBKDF2PasswordHasher(settings),
        token_codec=JWTAccessTokenCodec(settings),
        wechat_provider=None,  # type: ignore[arg-type]
        sms_provider=FakeSmsVerificationProvider(settings),
        email_provider=FakeEmailVerificationProvider(settings),
    )
    return service, repository


def test_email_code_creates_account_is_one_time_and_reuses_identity() -> None:
    service, repository = build_service(auth_email_send_interval_seconds=1)
    sent = service.send_email_code(email="Candidate@Example.com", client_label="web-global")
    assert sent.masked_email == "ca*******@example.com"
    assert sent.code_digest and "123456" not in sent.code_digest

    user, _, access_token, _ = service.verify_email_login(
        challenge_id=sent.challenge_id, email="candidate@example.com", code="123456", client_label="web-global"
    )
    assert user.login_id == "candidate@example.com"
    assert user.last_login_provider == "email"
    assert user.bindings[0].provider == "email"
    assert access_token

    with pytest.raises(DomainRequestError) as consumed:
        service.verify_email_login(challenge_id=sent.challenge_id, email="candidate@example.com", code="123456", client_label="web-global")
    assert consumed.value.error_code == "email_challenge_consumed"

    repository.save_email_challenge(replace(repository.get_email_challenge(sent.challenge_id), created_at_ms=1, updated_at_ms=1))  # type: ignore[arg-type]
    second = service.send_email_code(email="candidate@example.com", client_label="web-global")
    repeated_user, *_ = service.verify_email_login(
        challenge_id=second.challenge_id, email="candidate@example.com", code="123456", client_label="web-global"
    )
    assert repeated_user.user_id == user.user_id


def test_email_code_rejects_invalid_expired_and_limited_attempts() -> None:
    service, repository = build_service(auth_email_verify_attempt_limit=2)
    sent = service.send_email_code(email="test.user@example.org", client_label="web-global")
    for expected_code in ("invalid_code", "invalid_code"):
        with pytest.raises(DomainRequestError) as invalid:
            service.verify_email_login(challenge_id=sent.challenge_id, email="test.user@example.org", code="000000", client_label="web-global")
        assert invalid.value.error_code == expected_code
    assert repository.get_email_challenge(sent.challenge_id).status == "locked"  # type: ignore[union-attr]

    expired_service, expired_repository = build_service()
    expired = expired_service.send_email_code(email="expired@example.org", client_label="web-global")
    expired_repository.save_email_challenge(replace(expired, expires_at_ms=1))
    with pytest.raises(DomainRequestError) as expiration:
        expired_service.verify_email_login(challenge_id=expired.challenge_id, email="expired@example.org", code="123456", client_label="web-global")
    assert expiration.value.error_code == "email_challenge_expired"


def test_email_send_limits_and_disabled_default() -> None:
    service, _ = build_service(auth_email_send_interval_seconds=60)
    service.send_email_code(email="limited@example.net", client_label="web-global")
    with pytest.raises(DomainRequestError) as limited:
        service.send_email_code(email="limited@example.net", client_label="web-global")
    assert limited.value.error_code == "email_rate_limited"

    settings = Settings(_env_file=None, auth_email_enabled=False)
    disabled = AuthenticationService(
        settings=settings, logger=logging.getLogger("test.email-disabled"),
        repository=InMemoryAuthenticationRepository(), password_hasher=PBKDF2PasswordHasher(settings),
        token_codec=JWTAccessTokenCodec(settings), wechat_provider=None,  # type: ignore[arg-type]
        sms_provider=FakeSmsVerificationProvider(settings), email_provider=FakeEmailVerificationProvider(settings),
    )
    with pytest.raises(DomainRequestError) as unavailable:
        disabled.send_email_code(email="user@example.com", client_label="web-global")
    assert unavailable.value.error_code == "email_auth_disabled"


def test_email_daily_send_limit_excludes_provider_failures() -> None:
    service, repository = build_service(auth_email_send_interval_seconds=0, auth_email_daily_limit=2)
    first = service.send_email_code(email="daily@example.net", client_label="web-global")
    second = service.send_email_code(email="daily@example.net", client_label="web-global")
    assert first.status == second.status == "sent"
    with pytest.raises(DomainRequestError) as limited:
        service.send_email_code(email="daily@example.net", client_label="web-global")
    assert limited.value.error_code == "email_daily_limit_exceeded"
    assert len(repository.email_challenges_by_id) == 2


def test_production_email_provider_configuration_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.deps as deps

    settings = Settings(_env_file=None, environment="production", auth_email_enabled=True, auth_email_provider_mode="fake")
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    deps.email_verification_provider.cache_clear()
    with pytest.raises(RuntimeError, match="requires SMTP provider mode"):
        deps.email_verification_provider()
    deps.email_verification_provider.cache_clear()

    incomplete_smtp = Settings(_env_file=None, environment="production", auth_email_enabled=True, auth_email_provider_mode="smtp")
    monkeypatch.setattr(deps, "get_settings", lambda: incomplete_smtp)
    with pytest.raises(RuntimeError, match="configuration is incomplete"):
        deps.email_verification_provider()
    deps.email_verification_provider.cache_clear()


def test_smtp_provider_supports_implicit_tls_without_starttls(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append(f"connect:{port}:{timeout}")

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        def starttls(self) -> None:
            calls.append("starttls")

        def login(self, username: str, password: str) -> None:
            calls.append("login")

        def send_message(self, message) -> None:  # noqa: ANN001
            calls.append("send")

    import app.services.email_verification_provider as provider_module

    monkeypatch.setattr(provider_module.smtplib, "SMTP_SSL", FakeSmtp)
    settings = Settings(
        _env_file=None,
        auth_email_enabled=True,
        auth_email_provider_mode="smtp",
        auth_email_code_pepper="synthetic-email-pepper-for-tests",
        auth_email_smtp_host="smtp.example.test",
        auth_email_smtp_port=465,
        auth_email_smtp_username="synthetic-user",
        auth_email_smtp_password="synthetic-password",
        auth_email_smtp_ssl=True,
        auth_email_smtp_starttls=False,
        auth_email_from_address="noreply@example.test",
    )
    result = SmtpEmailVerificationProvider(settings).send_code(email="candidate@example.test", challenge_id="email-challenge-tls")
    assert result.outcome == "sent"
    assert calls == ["connect:465:10", "login", "send"]
