from __future__ import annotations

import logging

import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.authentication import SmsSendResult
from app.services.authentication_repository import InMemoryAuthenticationRepository
from app.services.authentication_service import AuthenticationService


class RateLimitedSmsProvider:
    def provider_name(self) -> str:
        return "aliyun-dysmsapi"

    def send_code(self, *, phone_e164: str, challenge_id: str) -> SmsSendResult:
        return SmsSendResult(
            outcome="rate_limited",
            error_code="isv.BUSINESS_LIMIT_CONTROL",
            error_message="触发云通信流控限制",
        )


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
