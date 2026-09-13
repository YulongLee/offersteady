from __future__ import annotations

import logging

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.authentication import SmsSendResult
from app.services.authentication_service import AuthenticationService, JWTAccessTokenCodec, PBKDF2PasswordHasher
from app.services.sms_verification_provider import FakeSmsVerificationProvider
from app.services.authentication_repository import InMemoryAuthenticationRepository


class RateLimitedSmsProvider:
    def provider_name(self) -> str:
        return "aliyun-dysmsapi"

    def send_code(self, *, phone_e164: str, challenge_id: str) -> SmsSendResult:
        return SmsSendResult(
            outcome="rate_limited",
            error_code="isv.BUSINESS_LIMIT_CONTROL",
            error_message="触发云通信流控限制",
        )


class CounterSmsProvider(FakeSmsVerificationProvider):
    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.send_calls = 0

    def send_code(self, *, phone_e164: str, challenge_id: str) -> SmsSendResult:
        self.send_calls += 1
        return super().send_code(phone_e164=phone_e164, challenge_id=challenge_id)


def build_sms_service(**overrides) -> tuple[AuthenticationService, InMemoryAuthenticationRepository, CounterSmsProvider]:
    settings = Settings(_env_file=None, auth_sms_provider_mode="fake", **overrides)
    provider = CounterSmsProvider(settings)
    repository = InMemoryAuthenticationRepository()
    service = AuthenticationService(
        settings=settings,
        logger=logging.getLogger("test.sms-review-account"),
        repository=repository,
        password_hasher=PBKDF2PasswordHasher(settings),
        token_codec=JWTAccessTokenCodec(settings),
        wechat_provider=None,  # type: ignore[arg-type]
        sms_provider=provider,
        email_provider=None,
    )
    return service, repository, provider


def test_sms_resend_default_matches_provider_minute_limit() -> None:
    assert Settings(_env_file=None).auth_sms_send_interval_seconds == 60


def test_provider_rate_limit_is_a_retryable_user_error() -> None:
    repository = InMemoryAuthenticationRepository()
    service = AuthenticationService(
        settings=Settings(_env_file=None, auth_sms_send_interval_seconds=60),
        logger=logging.getLogger("test.sms-rate-limit"),
        repository=repository,
        password_hasher=None,  # type: ignore[arg-type]
        token_codec=None,  # type: ignore[arg-type]
        wechat_provider=None,  # type: ignore[arg-type]
        sms_provider=RateLimitedSmsProvider(),
    )

    with pytest.raises(DomainRequestError) as captured:
        service.send_sms_code(phone_number="13900001234", client_label="rate-limit-test")

    assert captured.value.status_code == 429
    assert captured.value.error_code == "sms_provider_rate_limited"
    assert "获取过于频繁" in captured.value.message
    stored = next(iter(repository.sms_challenges_by_id.values()))
    assert stored.status == "failed"
    assert stored.last_error_code == "isv.BUSINESS_LIMIT_CONTROL"


def test_provider_rejections_do_not_consume_user_interval_or_daily_quota() -> None:
    repository = InMemoryAuthenticationRepository()
    service = AuthenticationService(
        settings=Settings(
            _env_file=None,
            auth_sms_send_interval_seconds=60,
            auth_sms_daily_limit=1,
        ),
        logger=logging.getLogger("test.sms-provider-rejection-quota"),
        repository=repository,
        password_hasher=None,  # type: ignore[arg-type]
        token_codec=None,  # type: ignore[arg-type]
        wechat_provider=None,  # type: ignore[arg-type]
        sms_provider=RateLimitedSmsProvider(),
    )

    for _attempt in range(2):
        with pytest.raises(DomainRequestError) as captured:
            service.send_sms_code(phone_number="19729630316", client_label="admin-login")
        assert captured.value.error_code == "sms_provider_rate_limited"

    assert len(repository.sms_challenges_by_id) == 2
    assert {record.status for record in repository.sms_challenges_by_id.values()} == {"failed"}


def test_alipay_review_sms_account_supports_fixed_code_and_denies_others() -> None:
    service, repository, provider = build_sms_service(
        auth_sms_send_interval_seconds=0,
        auth_sms_verify_attempt_limit=6,
        alipay_review_login_enabled=True,
        alipay_review_phone="18888888888",
        alipay_review_code="888888",
        auth_sms_fake_code="123456",
    )
    challenge = service.send_sms_code(phone_number="18888888888", client_label="alipay-review")
    assert challenge.status == "sent"
    assert provider.send_calls == 0

    user, _, _, _ = service.verify_sms_login(
        challenge_id=challenge.challenge_id,
        phone_number="18888888888",
        code="888888",
        client_label="alipay-review",
    )
    assert user.last_login_provider == "sms"
    assert user.login_id.startswith("sms:")
    assert len(repository.sms_challenges_by_id) == 1
    assert len(repository.users_by_login_id) == 1

    wrong = service.send_sms_code(phone_number="18888888888", client_label="alipay-review")
    assert wrong.challenge_id != challenge.challenge_id
    with pytest.raises(DomainRequestError) as wrong_code:
        service.verify_sms_login(
            challenge_id=wrong.challenge_id,
            phone_number="18888888888",
            code="123456",
            client_label="alipay-review",
        )
    assert wrong_code.value.status_code == 401
    assert wrong_code.value.error_code == "sms_invalid_code"

    other = service.send_sms_code(phone_number="16600001111", client_label="alipay-review")
    with pytest.raises(DomainRequestError) as other_phone:
        service.verify_sms_login(
            challenge_id=other.challenge_id,
            phone_number="16600001111",
            code="888888",
            client_label="alipay-review",
        )
    assert other_phone.value.status_code == 401
    assert other_phone.value.error_code in {"invalid", "sms_invalid_code", "invalid_code"}

    normal = service.send_sms_code(phone_number="13900001234", client_label="alipay-review-normal")
    normal_user, _, _, _ = service.verify_sms_login(
        challenge_id=normal.challenge_id,
        phone_number="13900001234",
        code="123456",
        client_label="alipay-review-normal",
    )
    assert normal_user.login_id.startswith("sms:")
    assert provider.send_calls == 2


def test_alipay_review_sms_account_can_verify_without_sms_challenge() -> None:
    service, repository, provider = build_sms_service(
        auth_sms_send_interval_seconds=0,
        alipay_review_login_enabled=True,
        alipay_review_phone="18888888888",
        alipay_review_code="888888",
    )

    user, _, _, _ = service.verify_sms_login(
        challenge_id="",
        phone_number="18888888888",
        code="888888",
        client_label="alipay-review",
    )

    assert user.login_id.startswith("sms:")
    assert provider.send_calls == 0
    assert len(repository.users_by_login_id) == 1
    with pytest.raises(DomainRequestError) as wrong_code:
        service.verify_sms_login(challenge_id="", phone_number="18888888888", code="123456", client_label="alipay-review")
    assert wrong_code.value.error_code == "sms_challenge_not_found"


def test_alipay_review_sms_code_fails_when_review_mode_closed() -> None:
    service, repository, _ = build_sms_service(
        auth_sms_send_interval_seconds=0,
        auth_sms_verify_attempt_limit=6,
        alipay_review_login_enabled=False,
        alipay_review_phone="18888888888",
        alipay_review_code="888888",
    )
    challenge = service.send_sms_code(phone_number="18888888888", client_label="alipay-review-disabled")
    with pytest.raises(DomainRequestError) as disabled:
        service.verify_sms_login(
            challenge_id=challenge.challenge_id,
            phone_number="18888888888",
            code="888888",
            client_label="alipay-review-disabled",
        )
    assert disabled.value.status_code == 401
    assert disabled.value.error_code in {"invalid", "invalid_code", "sms_invalid_code"}
    assert challenge.status in {"sent", "created"}
    assert len(repository.sms_challenges_by_id) >= 1
