from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
from dataclasses import replace
from time import time
from uuid import uuid4

import jwt

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.core.logging import log_event
from app.ports.authentication import (
    AccessTokenCodecPort,
    AccessTokenPayload,
    AuthSessionRecord,
    AuthenticatedRequestContext,
    AuthenticationRepository,
    ExternalIdentityBindingRecord,
    IdentityProviderKind,
    PasswordHasherPort,
    ProviderAuthorizationEntry,
    ProviderCallbackPayload,
    ProviderIdentityProfile,
    UserRecord,
    SmsChallengeRecord,
    SmsVerificationProviderPort,
    WechatAuthorizationSessionRecord,
    WechatCompatibleProviderMode,
    WechatLoginProviderPort,
)


def _now_ms() -> int:
    return int(time() * 1000)


def _now_seconds() -> int:
    return int(time())


def _safe_user_ref(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]


class PBKDF2PasswordHasher(PasswordHasherPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self.settings.auth_password_hash_iterations,
        )
        return "pbkdf2_sha256${iterations}${salt}${digest}".format(
            iterations=self.settings.auth_password_hash_iterations,
            salt=base64.b64encode(salt).decode("utf-8"),
            digest=base64.b64encode(derived).decode("utf-8"),
        )

    def verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations_token, salt_token, digest_token = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.b64decode(salt_token.encode("utf-8"))
            expected = base64.b64decode(digest_token.encode("utf-8"))
            iterations = int(iterations_token)
        except Exception:
            return False
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(derived, expected)


class JWTAccessTokenCodec(AccessTokenCodecPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def issue_access_token(self, *, payload: AccessTokenPayload) -> str:
        return jwt.encode(payload.__dict__, self.settings.auth_jwt_secret, algorithm="HS256")

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        try:
            decoded = jwt.decode(
                token,
                self.settings.auth_jwt_secret,
                algorithms=["HS256"],
                issuer=self.settings.auth_jwt_issuer,
            )
        except jwt.PyJWTError as exc:
            raise DomainRequestError("authentication", "decode-access-token", "访问令牌无效或已过期。", 401) from exc
        return AccessTokenPayload(
            sub=str(decoded["sub"]),
            sid=str(decoded["sid"]),
            typ="access",
            login_id=str(decoded["login_id"]),
            exp=int(decoded["exp"]),
            iat=int(decoded["iat"]),
            iss=str(decoded["iss"]),
        )


class CompatibleWechatLoginProvider(WechatLoginProviderPort):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def provider_mode(self) -> WechatCompatibleProviderMode:
        mode = "formal" if self.settings.auth_wechat_provider_mode == "formal" else "compatible"
        return WechatCompatibleProviderMode(provider="wechat", mode=mode)

    def create_authorization_entry(self, *, auth_request_id: str, state_token: str, client_label: str) -> ProviderAuthorizationEntry:
        authorization_url = (
            "https://open.weixin.qq.com/connect/qrconnect"
            f"?appid={self.settings.auth_wechat_app_id}"
            f"&redirect_uri={self.settings.auth_wechat_callback_url}"
            "&response_type=code&scope=snsapi_login"
            f"&state={state_token}#wechat_redirect"
        )
        subject_hint = f"wechat-user-{auth_request_id[-6:]}"
        code_hint = f"code-{auth_request_id[-8:]}"
        return ProviderAuthorizationEntry(
            authorization_url=authorization_url,
            qr_code_text=authorization_url,
            provider_subject_hint=subject_hint,
            code_hint=code_hint,
        )

    def exchange_callback(self, *, payload: ProviderCallbackPayload) -> ProviderIdentityProfile:
        suffix = payload.code.removeprefix("code-")[-12:] or hashlib.sha256(payload.code.encode("utf-8")).hexdigest()[:12]
        return ProviderIdentityProfile(
            provider="wechat",
            provider_subject=f"wechat-subject-{suffix}",
            provider_subject_hint=f"微信用户{suffix[-4:]}",
            display_name=f"微信用户{suffix[-4:]}",
            avatar_url=f"https://cdn.offersteady.local/avatar/{suffix}.png",
        )

    def simulate_scan(self, *, auth_request_id: str) -> None:
        return None

    def simulate_authorize(self, *, auth_request_id: str) -> ProviderIdentityProfile:
        suffix = auth_request_id[-10:]
        return ProviderIdentityProfile(
            provider="wechat",
            provider_subject=f"wechat-subject-{suffix}",
            provider_subject_hint=f"微信用户{suffix[-4:]}",
            display_name=f"微信用户{suffix[-4:]}",
            avatar_url=f"https://cdn.offersteady.local/avatar/{suffix}.png",
        )


class AuthenticationService:
    def __init__(
        self,
        *,
        settings: Settings,
        logger: logging.Logger,
        repository: AuthenticationRepository,
        password_hasher: PasswordHasherPort,
        token_codec: AccessTokenCodecPort,
        wechat_provider: WechatLoginProviderPort,
        sms_provider: SmsVerificationProviderPort,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_codec = token_codec
        self.wechat_provider = wechat_provider
        self.sms_provider = sms_provider

    def register_user(self, *, login_id: str, password: str, display_name: str | None, client_label: str) -> tuple[UserRecord, AuthSessionRecord, str, str]:
        normalized_login = login_id.strip().lower()
        if self.repository.get_user_by_login_id(normalized_login) is not None:
            raise DomainRequestError("authentication", "register", "该账号已存在。", 409)
        now_ms = _now_ms()
        user = self.repository.save_user(
            UserRecord(
                user_id=f"user-{uuid4().hex}",
                login_id=normalized_login,
                password_hash=self.password_hasher.hash_password(password),
                display_name=(display_name or normalized_login.split("@", 1)[0] or "OfferSteady 用户").strip(),
                avatar_url=None,
                last_login_provider="password",
                last_login_at_ms=now_ms,
                created_at_ms=now_ms,
                updated_at_ms=now_ms,
            )
        )
        self.repository.save_identity_binding(
            ExternalIdentityBindingRecord(
                binding_id=f"binding-{uuid4().hex}",
                user_id=user.user_id,
                provider="password",
                provider_subject=normalized_login,
                provider_subject_hint=normalized_login,
                display_name=user.display_name,
                status="active",
                bound_at_ms=now_ms,
            )
        )
        user = self._require_user(user.user_id)
        auth_session, access_token, refresh_token = self._issue_auth_session(user=user, client_label=client_label)
        self._log(logging.INFO, "authentication.registered", user_id=user.user_id, auth_session_id=auth_session.auth_session_id, outcome="success")
        return user, auth_session, access_token, refresh_token

    def login(self, *, login_id: str, password: str, client_label: str) -> tuple[UserRecord, AuthSessionRecord, str, str]:
        normalized_login = login_id.strip().lower()
        user = self.repository.get_user_by_login_id(normalized_login)
        if user is None or not self.password_hasher.verify_password(password, user.password_hash):
            self._log(logging.WARNING, "authentication.login_failed", user_id=None, auth_session_id=None, outcome="invalid_credentials", login_id=normalized_login)
            raise DomainRequestError("authentication", "login", "账号或密码不正确。", 401)
        now_ms = _now_ms()
        user = self.repository.save_user(replace(user, last_login_provider="password", last_login_at_ms=now_ms, updated_at_ms=now_ms))
        auth_session, access_token, refresh_token = self._issue_auth_session(user=user, client_label=client_label)
        self._log(logging.INFO, "authentication.logged_in", user_id=user.user_id, auth_session_id=auth_session.auth_session_id, outcome="success")
        return user, auth_session, access_token, refresh_token

    def refresh(self, *, refresh_token: str) -> tuple[UserRecord, AuthSessionRecord, str, str]:
        session = self._require_refresh_session(refresh_token)
        if session.status != "active" or _now_ms() > session.expires_at_ms:
            revoked = self.repository.save_auth_session(replace(session, status="expired" if _now_ms() > session.expires_at_ms else "revoked", revoked_at_ms=_now_ms()))
            raise DomainRequestError("authentication", "refresh", "刷新令牌无效或已过期。", 401)
        user = self._require_user(session.user_id)
        current_ms = _now_ms()
        old_refresh_fp = session.refresh_token_fingerprint
        rotated_token = secrets.token_urlsafe(32)
        rotated_fp = self._refresh_fingerprint(rotated_token)
        rotated = self.repository.save_auth_session(
            replace(
                session,
                refresh_token_fingerprint=rotated_fp,
                last_used_at_ms=current_ms,
                expires_at_ms=current_ms + self.settings.auth_refresh_token_ttl_seconds * 1000,
            )
        )
        access_token = self._issue_access_token(user=user, auth_session=rotated)
        self._log(logging.INFO, "authentication.refreshed", user_id=user.user_id, auth_session_id=rotated.auth_session_id, outcome="success")
        return user, rotated, access_token, rotated_token

    def logout(self, *, auth_context: AuthenticatedRequestContext, logout_all_devices: bool = False) -> list[str]:
        sessions = self.repository.list_auth_sessions_for_user(user_id=auth_context.user_id)
        revoked_ids: list[str] = []
        for session in sessions:
            if session.status != "active":
                continue
            if logout_all_devices or session.auth_session_id == auth_context.auth_session_id:
                revoked = self.repository.save_auth_session(replace(session, status="revoked", revoked_at_ms=_now_ms(), last_used_at_ms=_now_ms()))
                revoked_ids.append(revoked.auth_session_id)
        self._log(logging.INFO, "authentication.logged_out", user_id=auth_context.user_id, auth_session_id=auth_context.auth_session_id, outcome="success")
        return revoked_ids

    def get_current_user(self, *, auth_context: AuthenticatedRequestContext) -> UserRecord:
        return self._require_user(auth_context.user_id)

    def send_sms_code(self, *, phone_number: str, client_label: str) -> SmsChallengeRecord:
        phone_e164 = self._normalize_phone(phone_number)
        phone_hash = self._phone_hash(phone_e164)
        now_ms = _now_ms()
        recent = self.repository.list_sms_challenges_for_phone(phone_hash=phone_hash, since_ms=now_ms - 24 * 60 * 60 * 1000)
        if recent and now_ms - recent[0].created_at_ms < self.settings.auth_sms_send_interval_seconds * 1000:
            raise DomainRequestError("authentication", "sms-send", "验证码发送太频繁，请稍后再试。", 429, "sms_rate_limited")
        if len(recent) >= self.settings.auth_sms_daily_limit:
            raise DomainRequestError("authentication", "sms-send", "今日验证码发送次数已达上限。", 429, "sms_daily_limit_exceeded")
        challenge = SmsChallengeRecord(
            challenge_id=f"sms-challenge-{uuid4().hex}",
            phone_e164=phone_e164,
            phone_hash=phone_hash,
            provider=self.sms_provider.provider_name(),
            status="created",
            provider_biz_id=None,
            provider_request_id=None,
            attempt_count=0,
            max_attempts=self.settings.auth_sms_verify_attempt_limit,
            expires_at_ms=now_ms + self.settings.auth_sms_ttl_seconds * 1000,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
        )
        challenge = self.repository.save_sms_challenge(challenge)
        result = self.sms_provider.send_code(phone_e164=phone_e164, challenge_id=challenge.challenge_id)
        status = "sent" if result.outcome == "sent" else "failed"
        stored = self.repository.save_sms_challenge(replace(
            challenge,
            status=status,
            provider_biz_id=result.provider_biz_id,
            provider_request_id=result.provider_request_id,
            last_error_code=result.error_code,
            updated_at_ms=_now_ms(),
        ))
        self._log(logging.INFO if status == "sent" else logging.WARNING, "authentication.sms_code_sent", user_id=None, auth_session_id=stored.challenge_id, outcome=result.outcome, login_id=phone_e164)
        if result.outcome != "sent":
            raise DomainRequestError("authentication", "sms-send", "短信服务暂时不可用，请稍后重试。", 503, result.error_code or "sms_provider_unavailable")
        return stored

    def verify_sms_login(self, *, challenge_id: str, phone_number: str, code: str, client_label: str) -> tuple[UserRecord, AuthSessionRecord, str, str]:
        phone_e164 = self._normalize_phone(phone_number)
        phone_hash = self._phone_hash(phone_e164)
        challenge = self.repository.get_sms_challenge(challenge_id)
        now_ms = _now_ms()
        if challenge is None or challenge.phone_hash != phone_hash:
            raise DomainRequestError("authentication", "sms-verify", "验证码会话不存在或已失效。", 404, "sms_challenge_not_found")
        if challenge.status in {"verified", "locked"}:
            raise DomainRequestError("authentication", "sms-verify", "验证码会话已失效，请重新获取。", 409, "sms_challenge_consumed")
        if now_ms > challenge.expires_at_ms:
            self.repository.save_sms_challenge(replace(challenge, status="expired", updated_at_ms=now_ms, last_error_code="expired"))
            raise DomainRequestError("authentication", "sms-verify", "验证码已过期，请重新获取。", 401, "sms_challenge_expired")
        if challenge.attempt_count >= challenge.max_attempts:
            self.repository.save_sms_challenge(replace(challenge, status="locked", updated_at_ms=now_ms, last_error_code="attempt_limit"))
            raise DomainRequestError("authentication", "sms-verify", "验证码错误次数过多，请重新获取。", 429, "sms_attempt_limit")
        result = self.sms_provider.verify_code(phone_e164=phone_e164, code=code.strip(), challenge=challenge)
        attempt_count = challenge.attempt_count + (0 if result.outcome == "verified" else 1)
        if result.outcome != "verified":
            status = "locked" if attempt_count >= challenge.max_attempts else challenge.status
            self.repository.save_sms_challenge(replace(challenge, status=status, attempt_count=attempt_count, updated_at_ms=_now_ms(), last_error_code=result.error_code or result.outcome))
            message = "验证码不正确或已过期。" if result.outcome in {"invalid", "expired"} else "短信校验服务暂时不可用，请稍后重试。"
            status_code = 401 if result.outcome in {"invalid", "expired"} else 503
            raise DomainRequestError("authentication", "sms-verify", message, status_code, result.error_code or f"sms_{result.outcome}")
        verified = self.repository.save_sms_challenge(replace(challenge, status="verified", verified_at_ms=_now_ms(), updated_at_ms=_now_ms(), provider_request_id=result.provider_request_id or challenge.provider_request_id))
        user = self._get_or_create_sms_user(phone_e164=phone_e164)
        auth_session, access_token, refresh_token = self._issue_auth_session(user=user, client_label=client_label)
        self._log(logging.INFO, "authentication.sms_logged_in", user_id=user.user_id, auth_session_id=auth_session.auth_session_id, outcome="success", login_id=phone_e164)
        return user, auth_session, access_token, refresh_token

    def create_wechat_authorization_session(self, *, client_label: str) -> WechatAuthorizationSessionRecord:
        now_ms = _now_ms()
        auth_request_id = f"wechat-auth-{uuid4().hex}"
        state_token = secrets.token_urlsafe(24)
        provider_entry = self.wechat_provider.create_authorization_entry(
            auth_request_id=auth_request_id,
            state_token=state_token,
            client_label=client_label.strip() or "web",
        )
        session = WechatAuthorizationSessionRecord(
            auth_request_id=auth_request_id,
            provider="wechat",
            client_label=client_label.strip() or "web",
            state_token=state_token,
            status="waiting",
            authorization_url=provider_entry.authorization_url,
            qr_code_text=provider_entry.qr_code_text,
            expires_at_ms=now_ms + self.settings.auth_wechat_authorization_ttl_seconds * 1000,
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            provider_subject_hint=provider_entry.provider_subject_hint,
            code_hint=provider_entry.code_hint,
        )
        stored = self.repository.save_wechat_authorization_session(session)
        self._log(logging.INFO, "authentication.wechat_session_created", user_id=None, auth_session_id=stored.auth_request_id, outcome="success")
        return stored

    def get_wechat_authorization_session(self, *, auth_request_id: str) -> WechatAuthorizationSessionRecord:
        session = self.repository.get_wechat_authorization_session(auth_request_id)
        if session is None:
            raise DomainRequestError("authentication", "wechat-session", "微信授权会话不存在。", 404)
        if session.status in {"authorized", "failed", "expired"}:
            return session
        if _now_ms() > session.expires_at_ms:
            expired = self.repository.save_wechat_authorization_session(replace(session, status="expired", updated_at_ms=_now_ms(), error_code="expired", error_message="授权会话已过期。"))
            return expired
        return session

    def simulate_wechat_scan(self, *, auth_request_id: str) -> WechatAuthorizationSessionRecord:
        if self.wechat_provider.provider_mode().mode != "compatible":
            raise DomainRequestError("authentication", "wechat-scan", "当前提供方不支持开发态扫码模拟。", 400)
        session = self.get_wechat_authorization_session(auth_request_id=auth_request_id)
        if session.status == "expired":
            raise DomainRequestError("authentication", "wechat-scan", "微信授权会话已过期，请刷新二维码。", 401)
        if session.status == "failed":
            raise DomainRequestError("authentication", "wechat-scan", "微信授权会话已失效，请重新发起授权。", 409)
        if session.status != "waiting":
            return session
        self.wechat_provider.simulate_scan(auth_request_id=auth_request_id)
        return self.repository.save_wechat_authorization_session(replace(session, status="scanned", updated_at_ms=_now_ms()))

    def simulate_wechat_authorize(self, *, auth_request_id: str) -> WechatAuthorizationSessionRecord:
        if self.wechat_provider.provider_mode().mode != "compatible":
            raise DomainRequestError("authentication", "wechat-authorize", "当前提供方不支持开发态授权模拟。", 400)
        session = self.get_wechat_authorization_session(auth_request_id=auth_request_id)
        if session.status == "expired":
            raise DomainRequestError("authentication", "wechat-authorize", "微信授权会话已过期，请刷新二维码。", 401)
        if session.status == "failed":
            raise DomainRequestError("authentication", "wechat-authorize", "微信授权会话已失效，请重新发起授权。", 409)
        if session.status not in {"waiting", "scanned"}:
            return session
        profile = self.wechat_provider.simulate_authorize(auth_request_id=auth_request_id)
        return self._complete_wechat_authorization(session=session, profile=profile, source="compatible-simulated")

    def complete_wechat_callback(self, *, state_token: str, code: str) -> WechatAuthorizationSessionRecord:
        session = self.repository.get_wechat_authorization_session_by_state(state_token)
        if session is None:
            raise DomainRequestError("authentication", "wechat-callback", "微信授权状态无效或已过期。", 401)
        session = self.get_wechat_authorization_session(auth_request_id=session.auth_request_id)
        if session.consumed_at_ms is not None:
            raise DomainRequestError("authentication", "wechat-callback", "微信授权回调已被消费。", 409)
        profile = self.wechat_provider.exchange_callback(payload=ProviderCallbackPayload(state_token=state_token, code=code))
        return self._complete_wechat_authorization(session=session, profile=profile, source="provider-callback")

    def list_auth_sessions(self, *, auth_context: AuthenticatedRequestContext) -> list[AuthSessionRecord]:
        return self.repository.list_auth_sessions_for_user(user_id=auth_context.user_id)

    def authenticate_access_token(self, *, access_token: str) -> AuthenticatedRequestContext:
        payload = self.token_codec.decode_access_token(access_token)
        session = self.repository.get_auth_session(payload.sid)
        if session is None or session.status != "active" or session.user_id != payload.sub:
            raise DomainRequestError("authentication", "authenticate", "登录状态已失效，请重新登录。", 401)
        if _now_ms() > session.expires_at_ms:
            raise DomainRequestError("authentication", "authenticate", "登录状态已失效，请重新登录。", 401)
        self._require_user(payload.sub)
        updated = self.repository.save_auth_session(replace(session, last_used_at_ms=_now_ms()))
        return AuthenticatedRequestContext(user_id=payload.sub, login_id=payload.login_id, auth_session_id=updated.auth_session_id)

    def _issue_auth_session(self, *, user: UserRecord, client_label: str) -> tuple[AuthSessionRecord, str, str]:
        now_ms = _now_ms()
        refresh_token = secrets.token_urlsafe(32)
        auth_session = self.repository.save_auth_session(
            AuthSessionRecord(
                auth_session_id=f"auth-session-{uuid4().hex}",
                user_id=user.user_id,
                client_label=client_label.strip() or "web",
                refresh_token_fingerprint=self._refresh_fingerprint(refresh_token),
                status="active",
                issued_at_ms=now_ms,
                expires_at_ms=now_ms + self.settings.auth_refresh_token_ttl_seconds * 1000,
                last_used_at_ms=now_ms,
            )
        )
        access_token = self._issue_access_token(user=user, auth_session=auth_session)
        return auth_session, access_token, refresh_token

    def _complete_wechat_authorization(self, *, session: WechatAuthorizationSessionRecord, profile: ProviderIdentityProfile, source: str) -> WechatAuthorizationSessionRecord:
        existing = self.repository.get_user_by_provider_subject(provider=profile.provider, provider_subject=profile.provider_subject)
        now_ms = _now_ms()
        created_account = existing is None
        if existing is None:
            user = self.repository.save_user(
                UserRecord(
                    user_id=f"user-{uuid4().hex}",
                    login_id=f"wechat:{profile.provider_subject}",
                    password_hash="external-auth",
                    display_name=profile.display_name.strip() or profile.provider_subject_hint,
                    avatar_url=profile.avatar_url,
                    last_login_provider=profile.provider,
                    last_login_at_ms=now_ms,
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            )
            self.repository.save_identity_binding(
                ExternalIdentityBindingRecord(
                    binding_id=f"binding-{uuid4().hex}",
                    user_id=user.user_id,
                    provider=profile.provider,
                    provider_subject=profile.provider_subject,
                    provider_subject_hint=profile.provider_subject_hint,
                    avatar_url=profile.avatar_url,
                    display_name=profile.display_name,
                    status="active",
                    bound_at_ms=now_ms,
                )
            )
            user = self._require_user(user.user_id)
        else:
            user = self.repository.save_user(replace(
                existing,
                display_name=profile.display_name or existing.display_name,
                avatar_url=profile.avatar_url or existing.avatar_url,
                last_login_provider=profile.provider,
                last_login_at_ms=now_ms,
                updated_at_ms=now_ms,
            ))
        auth_session, access_token, refresh_token = self._issue_auth_session(user=user, client_label=session.client_label)
        updated = self.repository.save_wechat_authorization_session(replace(
            session,
            status="authorized",
            updated_at_ms=now_ms,
            resolved_user_id=user.user_id,
            auth_session_id=auth_session.auth_session_id,
            access_token=access_token,
            refresh_token=refresh_token,
            consumed_at_ms=now_ms,
        ))
        self._log(logging.INFO, "authentication.wechat_authorized", user_id=user.user_id, auth_session_id=auth_session.auth_session_id, outcome="created" if created_account else "reused", login_id=source)
        return updated

    def _get_or_create_sms_user(self, *, phone_e164: str) -> UserRecord:
        provider_subject = self._phone_hash(phone_e164)
        existing = self.repository.get_user_by_provider_subject(provider="sms", provider_subject=provider_subject)
        now_ms = _now_ms()
        display_name = f"用户{phone_e164[-4:]}"
        if existing is None:
            user = self.repository.save_user(
                UserRecord(
                    user_id=f"user-{uuid4().hex}",
                    login_id=f"sms:{provider_subject}",
                    password_hash="external-auth",
                    display_name=display_name,
                    avatar_url=None,
                    last_login_provider="sms",
                    last_login_at_ms=now_ms,
                    created_at_ms=now_ms,
                    updated_at_ms=now_ms,
                )
            )
            self.repository.save_identity_binding(
                ExternalIdentityBindingRecord(
                    binding_id=f"binding-{uuid4().hex}",
                    user_id=user.user_id,
                    provider="sms",
                    provider_subject=provider_subject,
                    provider_subject_hint=self._mask_phone(phone_e164),
                    display_name="手机号登录",
                    status="active",
                    bound_at_ms=now_ms,
                )
            )
            return self._require_user(user.user_id)
        return self.repository.save_user(replace(existing, last_login_provider="sms", last_login_at_ms=now_ms, updated_at_ms=now_ms))

    def _issue_access_token(self, *, user: UserRecord, auth_session: AuthSessionRecord) -> str:
        now_seconds = _now_seconds()
        payload = AccessTokenPayload(
            sub=user.user_id,
            sid=auth_session.auth_session_id,
            typ="access",
            login_id=user.login_id,
            exp=now_seconds + self.settings.auth_access_token_ttl_seconds,
            iat=now_seconds,
            iss=self.settings.auth_jwt_issuer,
        )
        return self.token_codec.issue_access_token(payload=payload)

    def _require_refresh_session(self, refresh_token: str) -> AuthSessionRecord:
        fingerprint = self._refresh_fingerprint(refresh_token)
        session = self.repository.get_auth_session_by_refresh_fingerprint(fingerprint)
        if session is None:
            raise DomainRequestError("authentication", "refresh", "刷新令牌无效或已过期。", 401)
        return session

    def _require_user(self, user_id: str) -> UserRecord:
        user = self.repository.get_user(user_id)
        if user is None:
            raise DomainRequestError("authentication", "user", "用户不存在。", 404)
        return user

    @staticmethod
    def _normalize_phone(phone_number: str) -> str:
        digits = re.sub(r"\D", "", phone_number)
        if digits.startswith("86") and len(digits) == 13:
            digits = digits[2:]
        if not re.fullmatch(r"1[3-9]\d{9}", digits):
            raise DomainRequestError("authentication", "sms-phone", "请输入有效的中国大陆手机号。", 422, "invalid_phone_number")
        return f"+86{digits}"

    def _phone_hash(self, phone_e164: str) -> str:
        secret = self.settings.auth_jwt_secret or "offersteady-dev-jwt-secret"
        return hmac.new(secret.encode("utf-8"), phone_e164.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _mask_phone(phone_e164: str) -> str:
        digits = phone_e164.removeprefix("+86")
        return f"{digits[:3]}****{digits[-4:]}"

    @staticmethod
    def _refresh_fingerprint(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    def _log(
        self,
        level: int,
        event: str,
        *,
        user_id: str | None,
        auth_session_id: str | None,
        outcome: str,
        login_id: str | None = None,
    ) -> None:
        log_event(
            self.logger,
            level,
            settings=self.settings,
            event=event,
            feature="authentication",
            action="auth",
            user_ref=_safe_user_ref(user_id) if user_id else None,
            login_id_hash=hashlib.sha256(login_id.encode("utf-8")).hexdigest()[:12] if login_id else None,
            auth_session_id=auth_session_id,
            outcome=outcome,
        )
