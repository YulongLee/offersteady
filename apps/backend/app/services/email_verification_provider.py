from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from time import perf_counter
from uuid import uuid4

from app.core.config import Settings
from app.ports.authentication import (
    EmailChallengeRecord,
    EmailSendResult,
    EmailVerificationProviderPort,
    EmailVerifyResult,
)


class DigestEmailVerificationProvider(EmailVerificationProviderPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def verify_code(self, *, email: str, code: str, challenge: EmailChallengeRecord) -> EmailVerifyResult:
        if not challenge.code_digest:
            return EmailVerifyResult(outcome="failed", error_code="email_code_digest_missing")
        candidate = self._code_digest(email=email, challenge_id=challenge.challenge_id, code=code)
        if hmac.compare_digest(candidate, challenge.code_digest):
            return EmailVerifyResult(outcome="verified", provider_request_id=challenge.provider_request_id)
        return EmailVerifyResult(outcome="invalid", provider_request_id=challenge.provider_request_id, error_code="invalid_code")

    def _code_digest(self, *, email: str, challenge_id: str, code: str) -> str:
        pepper = self.settings.auth_email_code_pepper or "offersteady-email-test-pepper"
        message = f"{challenge_id}:{email}:{code}".encode("utf-8")
        return hmac.new(pepper.encode("utf-8"), message, hashlib.sha256).hexdigest()


class FakeEmailVerificationProvider(DigestEmailVerificationProvider):
    def provider_name(self) -> str:
        return "fake"

    def send_code(self, *, email: str, challenge_id: str) -> EmailSendResult:
        code = self.settings.auth_email_fake_code
        return EmailSendResult(
            outcome="sent",
            provider_message_id=f"fake-message-{challenge_id}",
            provider_request_id=f"fake-request-{uuid4().hex}",
            verification_code_digest=self._code_digest(email=email, challenge_id=challenge_id, code=code),
        )


class SmtpEmailVerificationProvider(DigestEmailVerificationProvider):
    def provider_name(self) -> str:
        return "smtp"

    def send_code(self, *, email: str, challenge_id: str) -> EmailSendResult:
        code = f"{secrets.randbelow(1_000_000):06d}"
        message = EmailMessage()
        message["Subject"] = "Your OfferSteady verification code"
        message["From"] = formataddr((self.settings.auth_email_from_name, self._require(self.settings.auth_email_from_address, "from_address")))
        message["To"] = email
        message_id = make_msgid(domain=self.settings.auth_email_from_address.split("@", 1)[-1] if self.settings.auth_email_from_address else None)
        message["Message-ID"] = message_id
        minutes = max(1, self.settings.auth_email_ttl_seconds // 60)
        message.set_content(
            f"Your OfferSteady verification code is {code}.\n\n"
            f"It expires in {minutes} minutes. If you did not request this code, you can ignore this email."
        )
        started = perf_counter()
        try:
            smtp_class = smtplib.SMTP_SSL if self.settings.auth_email_smtp_ssl else smtplib.SMTP
            with smtp_class(self._require(self.settings.auth_email_smtp_host, "smtp_host"), self.settings.auth_email_smtp_port, timeout=10) as server:
                if self.settings.auth_email_smtp_starttls and not self.settings.auth_email_smtp_ssl:
                    server.starttls()
                server.login(
                    self._require(self.settings.auth_email_smtp_username, "smtp_username"),
                    self._require(self.settings.auth_email_smtp_password, "smtp_password"),
                )
                server.send_message(message)
        except Exception as exc:
            return EmailSendResult(
                outcome="provider_unavailable",
                error_code=exc.__class__.__name__,
                latency_ms=int((perf_counter() - started) * 1000),
            )
        return EmailSendResult(
            outcome="sent",
            provider_message_id=message_id,
            provider_request_id=f"smtp-{uuid4().hex}",
            latency_ms=int((perf_counter() - started) * 1000),
            verification_code_digest=self._code_digest(email=email, challenge_id=challenge_id, code=code),
        )

    @staticmethod
    def _require(value: str | None, name: str) -> str:
        if not value:
            raise RuntimeError(f"email_{name}_missing")
        return value
