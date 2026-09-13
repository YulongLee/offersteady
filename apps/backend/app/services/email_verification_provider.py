from __future__ import annotations

import hashlib
import hmac
from html import escape
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
            "OfferSteady\n"
            "Your verification code\n\n"
            f"Use this code to continue: {code}\n\n"
            f"This code expires in {minutes} minutes. For your security, never share it with anyone.\n\n"
            "If you did not request this email, you can safely ignore it.\n\n"
            "— The OfferSteady team\n"
            "https://offersteady.com"
        )
        message.add_alternative(self._html_body(code=code, minutes=minutes), subtype="html")
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

    def _html_body(self, *, code: str, minutes: int) -> str:
        """Return a self-contained HTML email that works without external assets."""
        brand_name = escape(self.settings.auth_email_from_name or "OfferSteady")
        safe_code = escape(code)
        safe_minutes = escape(str(minutes))
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your {brand_name} verification code</title>
  </head>
  <body style="margin:0;background:#f3f6f5;color:#17211f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">Your {brand_name} verification code is ready.</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f3f6f5;">
      <tr>
        <td align="center" style="padding:40px 16px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;">
            <tr>
              <td style="padding:0 8px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td align="center" valign="middle" style="width:38px;height:38px;border-radius:11px;background:#087f67;color:#ffffff;font-size:18px;font-weight:800;">O</td>
                    <td style="padding-left:11px;color:#17211f;font-size:17px;font-weight:750;letter-spacing:-.2px;">{brand_name}</td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="background:#ffffff;border:1px solid #dce7e3;border-radius:18px;padding:40px 38px 34px;box-shadow:0 8px 24px rgba(15,45,37,.06);">
                <p style="margin:0 0 10px;color:#087f67;font-size:11px;font-weight:800;letter-spacing:1.6px;text-transform:uppercase;">Account security</p>
                <h1 style="margin:0;color:#17211f;font-size:28px;line-height:1.2;letter-spacing:-.6px;">Your verification code</h1>
                <p style="margin:16px 0 0;color:#53615d;font-size:15px;line-height:1.65;">Enter the one-time code below to continue to your OfferSteady account.</p>
                <div style="margin:28px 0 24px;padding:20px 16px;border:1px solid #b9e5d6;border-radius:14px;background:#effaf6;text-align:center;">
                  <div style="color:#53615d;font-size:11px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;">One-time code</div>
                  <div style="margin-top:8px;color:#075c4b;font-size:34px;line-height:1.15;font-weight:800;letter-spacing:8px;">{safe_code}</div>
                </div>
                <p style="margin:0;color:#53615d;font-size:13px;line-height:1.65;">This code expires in <strong style="color:#17211f;">{safe_minutes} minutes</strong>. Never share it with anyone, including someone claiming to be from OfferSteady.</p>
                <div style="height:1px;background:#e8efed;margin:28px 0 22px;"></div>
                <p style="margin:0;color:#788681;font-size:12px;line-height:1.65;">If you did not request this code, no action is needed. Your account remains secure.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:22px 8px 0;color:#8a9793;font-size:11px;line-height:1.7;text-align:center;">This is an automated message from {brand_name}.<br><a href="https://offersteady.com" style="color:#087f67;text-decoration:none;">offersteady.com</a></td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    @staticmethod
    def _require(value: str | None, name: str) -> str:
        if not value:
            raise RuntimeError(f"email_{name}_missing")
        return value
