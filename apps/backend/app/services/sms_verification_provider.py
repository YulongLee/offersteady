from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from time import perf_counter
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.ports.authentication import SmsChallengeRecord, SmsSendResult, SmsVerificationProviderPort, SmsVerifyResult


def _percent_encode(value: str) -> str:
    return quote(value, safe="~-_.")


def _now_iso_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class FakeSmsVerificationProvider(SmsVerificationProviderPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def provider_name(self) -> str:
        return "fake"

    def send_code(self, *, phone_e164: str, challenge_id: str) -> SmsSendResult:
        return SmsSendResult(
            outcome="sent",
            provider_biz_id=f"fake-biz-{challenge_id}",
            provider_request_id=f"fake-request-{uuid4().hex}",
        )

    def verify_code(self, *, phone_e164: str, code: str, challenge: SmsChallengeRecord) -> SmsVerifyResult:
        if code == self.settings.auth_sms_fake_code:
            return SmsVerifyResult(outcome="verified", provider_request_id=f"fake-request-{uuid4().hex}")
        return SmsVerifyResult(outcome="invalid", provider_request_id=f"fake-request-{uuid4().hex}", error_code="invalid_code", error_message="验证码不正确。")


class AliyunDypnsSmsVerificationProvider(SmsVerificationProviderPort):
    """Aliyun Dypnsapi SMS verification provider.

    This provider follows Aliyun's personal-developer SMS verification path:
    the backend uses the system-granted sign name and standard verification
    template from the Phone Number Verification Service console, Aliyun
    generates the code, and OfferSteady verifies the user-entered code through
    CheckSmsVerifyCode. No Aliyun secret or verification code is exposed to the
    browser.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def provider_name(self) -> str:
        return "aliyun-dypnsapi"

    def send_code(self, *, phone_e164: str, challenge_id: str) -> SmsSendResult:
        payload = {
            "Action": "SendSmsVerifyCode",
            "CountryCode": "86",
            "PhoneNumber": phone_e164.removeprefix("+86"),
            "SignName": self._require(self.settings.auth_sms_aliyun_sign_name, "sign_name"),
            "TemplateCode": self._require(self.settings.auth_sms_aliyun_template_code, "template_code"),
            "TemplateParam": json.dumps({"code": "##code##", "min": str(max(1, self.settings.auth_sms_ttl_seconds // 60))}, separators=(",", ":")),
            "CodeType": "1",
            "CodeLength": "6",
            "ValidTime": str(self.settings.auth_sms_ttl_seconds),
            "Interval": str(self.settings.auth_sms_send_interval_seconds),
            "DuplicatePolicy": "1",
            "OutId": challenge_id,
        }
        started = perf_counter()
        try:
            data = self._request(payload)
        except Exception as exc:
            return SmsSendResult(outcome="provider_unavailable", error_code=exc.__class__.__name__, error_message=str(exc), latency_ms=int((perf_counter() - started) * 1000))
        latency_ms = int((perf_counter() - started) * 1000)
        success = str(data.get("Code", "")).upper() in {"OK", "SUCCESS"} or bool(data.get("Success") is True)
        model = self._model(data)
        if success:
            return SmsSendResult(
                outcome="sent",
                provider_biz_id=str(model.get("BizId") or data.get("BizId") or data.get("SmsVerifyCodeId") or challenge_id),
                provider_request_id=self._request_id(data),
                latency_ms=latency_ms,
            )
        return SmsSendResult(outcome=self._provider_outcome(data), provider_request_id=self._request_id(data), error_code=str(data.get("Code") or "provider_failed"), error_message=str(data.get("Message") or "短信发送失败。"), latency_ms=latency_ms)

    def verify_code(self, *, phone_e164: str, code: str, challenge: SmsChallengeRecord) -> SmsVerifyResult:
        payload = {
            "Action": "CheckSmsVerifyCode",
            "CountryCode": "86",
            "PhoneNumber": phone_e164.removeprefix("+86"),
            "VerifyCode": code,
            "OutId": challenge.challenge_id,
        }
        started = perf_counter()
        try:
            data = self._request(payload)
        except Exception as exc:
            return SmsVerifyResult(outcome="provider_unavailable", error_code=exc.__class__.__name__, error_message=str(exc), latency_ms=int((perf_counter() - started) * 1000))
        latency_ms = int((perf_counter() - started) * 1000)
        api_success = str(data.get("Code", "")).upper() in {"OK", "SUCCESS"} or bool(data.get("Success") is True)
        model = self._model(data)
        verify_result = str(model.get("VerifyResult") or "").upper()
        if api_success and verify_result == "PASS":
            return SmsVerifyResult(outcome="verified", provider_request_id=self._request_id(data), latency_ms=latency_ms)
        if api_success:
            return SmsVerifyResult(outcome="invalid", provider_request_id=self._request_id(data), error_code=verify_result or "verify_failed", error_message="验证码校验失败。", latency_ms=latency_ms)
        return SmsVerifyResult(outcome=self._provider_outcome(data), provider_request_id=self._request_id(data), error_code=str(data.get("Code") or "provider_failed"), error_message=str(data.get("Message") or "验证码校验失败。"), latency_ms=latency_ms)

    def _request(self, payload: dict[str, str]) -> dict:
        params = {
            **payload,
            "Version": "2017-05-25",
            "Format": "JSON",
            "RegionId": self.settings.auth_sms_aliyun_region_id,
            "AccessKeyId": self._require(self.settings.auth_sms_aliyun_access_key_id, "access_key_id"),
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": uuid4().hex,
            "SignatureVersion": "1.0",
            "Timestamp": _now_iso_utc(),
        }
        params["Signature"] = self._signature(params)
        with httpx.Client(timeout=10.0) as client:
            response = client.get(self.settings.auth_sms_aliyun_endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}

    def _signature(self, params: dict[str, str]) -> str:
        canonicalized = "&".join(f"{_percent_encode(key)}={_percent_encode(str(params[key]))}" for key in sorted(params))
        string_to_sign = f"GET&%2F&{_percent_encode(canonicalized)}"
        secret = f"{self._require(self.settings.auth_sms_aliyun_access_key_secret, 'access_key_secret')}&"
        digest = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
        return base64.b64encode(digest).decode("utf-8")

    @staticmethod
    def _require(value: str | None, name: str) -> str:
        if not value:
            raise RuntimeError(f"aliyun_sms_{name}_missing")
        return value

    @staticmethod
    def _model(data: dict) -> dict:
        model = data.get("Model")
        if isinstance(model, dict):
            return model
        if isinstance(model, str):
            try:
                parsed = json.loads(model)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @classmethod
    def _request_id(cls, data: dict) -> str:
        model = cls._model(data)
        return str(data.get("RequestId") or model.get("RequestId") or "")

    @staticmethod
    def _provider_outcome(data: dict) -> str:
        code = str(data.get("Code") or data.get("ErrorCode") or "").lower()
        message = str(data.get("Message") or "").lower()
        if "limit" in code or "frequency" in code or "频" in message:
            return "rate_limited"
        if "expire" in code or "过期" in message:
            return "expired"
        if "invalid" in code or "incorrect" in code or "错误" in message:
            return "invalid"
        return "failed"
