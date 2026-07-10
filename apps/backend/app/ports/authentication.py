from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


AuthSessionStatus = Literal["active", "revoked", "expired"]
IdentityProviderKind = Literal["password", "wechat", "sms", "prototype", "other"]
WechatAuthorizationStatus = Literal["creating", "waiting", "scanned", "authorized", "expired", "failed"]
SmsChallengeStatus = Literal["created", "sent", "verified", "failed", "expired", "locked"]
SmsProviderOutcome = Literal["sent", "verified", "invalid", "expired", "rate_limited", "provider_unavailable", "failed"]


@dataclass(frozen=True)
class ExternalIdentityBindingRecord:
    binding_id: str
    user_id: str
    provider: IdentityProviderKind
    provider_subject: str
    provider_subject_hint: str
    avatar_url: str | None = None
    display_name: str | None = None
    status: Literal["active", "revoked"] = "active"
    bound_at_ms: int = 0


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    login_id: str
    password_hash: str
    display_name: str
    avatar_url: str | None
    last_login_provider: IdentityProviderKind
    last_login_at_ms: int
    created_at_ms: int
    updated_at_ms: int
    bindings: list[ExternalIdentityBindingRecord] = field(default_factory=list)
    membership_anchor_ref: str | None = None


@dataclass(frozen=True)
class AuthSessionRecord:
    auth_session_id: str
    user_id: str
    client_label: str
    refresh_token_fingerprint: str
    status: AuthSessionStatus
    issued_at_ms: int
    expires_at_ms: int
    last_used_at_ms: int
    revoked_at_ms: int | None = None


@dataclass(frozen=True)
class AccessTokenPayload:
    sub: str
    sid: str
    typ: Literal["access"]
    login_id: str
    exp: int
    iat: int
    iss: str


@dataclass(frozen=True)
class AuthenticatedRequestContext:
    user_id: str
    login_id: str
    auth_session_id: str


@dataclass(frozen=True)
class WechatAuthorizationSessionRecord:
    auth_request_id: str
    provider: IdentityProviderKind
    client_label: str
    state_token: str
    status: WechatAuthorizationStatus
    authorization_url: str
    qr_code_text: str
    expires_at_ms: int
    created_at_ms: int
    updated_at_ms: int
    provider_subject_hint: str
    code_hint: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    resolved_user_id: str | None = None
    auth_session_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    consumed_at_ms: int | None = None


@dataclass(frozen=True)
class SmsChallengeRecord:
    challenge_id: str
    phone_e164: str
    phone_hash: str
    provider: str
    status: SmsChallengeStatus
    provider_biz_id: str | None
    provider_request_id: str | None
    attempt_count: int
    max_attempts: int
    expires_at_ms: int
    created_at_ms: int
    updated_at_ms: int
    last_error_code: str | None = None
    verified_at_ms: int | None = None


@dataclass(frozen=True)
class SmsSendResult:
    outcome: SmsProviderOutcome
    provider_biz_id: str | None = None
    provider_request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0


@dataclass(frozen=True)
class SmsVerifyResult:
    outcome: SmsProviderOutcome
    provider_request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0


@dataclass(frozen=True)
class ProviderIdentityProfile:
    provider: IdentityProviderKind
    provider_subject: str
    provider_subject_hint: str
    display_name: str
    avatar_url: str | None = None


@dataclass(frozen=True)
class ProviderAuthorizationEntry:
    authorization_url: str
    qr_code_text: str
    provider_subject_hint: str
    code_hint: str | None = None


@dataclass(frozen=True)
class ProviderCallbackPayload:
    state_token: str
    code: str


@dataclass(frozen=True)
class WechatCompatibleProviderMode:
    provider: IdentityProviderKind
    mode: Literal["compatible", "formal"]


class PasswordHasherPort(Protocol):
    def hash_password(self, password: str) -> str: ...

    def verify_password(self, password: str, stored_hash: str) -> bool: ...


class AccessTokenCodecPort(Protocol):
    def issue_access_token(self, *, payload: AccessTokenPayload) -> str: ...

    def decode_access_token(self, token: str) -> AccessTokenPayload: ...


class IdentityProviderPort(Protocol):
    def provider_kind(self) -> IdentityProviderKind: ...


class WechatLoginProviderPort(Protocol):
    def provider_mode(self) -> WechatCompatibleProviderMode: ...

    def create_authorization_entry(self, *, auth_request_id: str, state_token: str, client_label: str) -> ProviderAuthorizationEntry: ...

    def exchange_callback(self, *, payload: ProviderCallbackPayload) -> ProviderIdentityProfile: ...

    def simulate_scan(self, *, auth_request_id: str) -> None: ...

    def simulate_authorize(self, *, auth_request_id: str) -> ProviderIdentityProfile: ...


class SmsVerificationProviderPort(Protocol):
    def provider_name(self) -> str: ...

    def send_code(self, *, phone_e164: str, challenge_id: str) -> SmsSendResult: ...

    def verify_code(self, *, phone_e164: str, code: str, challenge: SmsChallengeRecord) -> SmsVerifyResult: ...


class AuthenticationRepository(Protocol):
    def save_user(self, user: UserRecord) -> UserRecord: ...

    def get_user_by_login_id(self, login_id: str) -> UserRecord | None: ...

    def get_user(self, user_id: str) -> UserRecord | None: ...

    def get_user_by_provider_subject(self, *, provider: IdentityProviderKind, provider_subject: str) -> UserRecord | None: ...

    def save_identity_binding(self, binding: ExternalIdentityBindingRecord) -> ExternalIdentityBindingRecord: ...

    def save_auth_session(self, session: AuthSessionRecord) -> AuthSessionRecord: ...

    def get_auth_session(self, auth_session_id: str) -> AuthSessionRecord | None: ...

    def get_auth_session_by_refresh_fingerprint(self, refresh_token_fingerprint: str) -> AuthSessionRecord | None: ...

    def list_auth_sessions_for_user(self, *, user_id: str) -> list[AuthSessionRecord]: ...

    def save_wechat_authorization_session(self, session: WechatAuthorizationSessionRecord) -> WechatAuthorizationSessionRecord: ...

    def get_wechat_authorization_session(self, auth_request_id: str) -> WechatAuthorizationSessionRecord | None: ...

    def get_wechat_authorization_session_by_state(self, state_token: str) -> WechatAuthorizationSessionRecord | None: ...

    def save_sms_challenge(self, challenge: SmsChallengeRecord) -> SmsChallengeRecord: ...

    def get_sms_challenge(self, challenge_id: str) -> SmsChallengeRecord | None: ...

    def list_sms_challenges_for_phone(self, *, phone_hash: str, since_ms: int | None = None) -> list[SmsChallengeRecord]: ...
