from __future__ import annotations

from dataclasses import replace

from app.ports.authentication import (
    AuthSessionRecord,
    AuthenticationRepository,
    ExternalIdentityBindingRecord,
    IdentityProviderKind,
    SmsChallengeRecord,
    UserRecord,
    WechatAuthorizationSessionRecord,
)


class InMemoryAuthenticationRepository(AuthenticationRepository):
    def __init__(self) -> None:
        self.users_by_id: dict[str, UserRecord] = {}
        self.users_by_login_id: dict[str, str] = {}
        self.users_by_provider_subject: dict[tuple[IdentityProviderKind, str], str] = {}
        self.auth_sessions_by_id: dict[str, AuthSessionRecord] = {}
        self.auth_sessions_by_refresh_fingerprint: dict[str, str] = {}
        self.wechat_authorization_sessions_by_id: dict[str, WechatAuthorizationSessionRecord] = {}
        self.wechat_authorization_sessions_by_state: dict[str, str] = {}
        self.sms_challenges_by_id: dict[str, SmsChallengeRecord] = {}
        self.sms_challenges_by_phone_hash: dict[str, list[str]] = {}

    def save_user(self, user: UserRecord) -> UserRecord:
        stored = replace(user)
        self.users_by_id[stored.user_id] = stored
        self.users_by_login_id[stored.login_id.lower()] = stored.user_id
        for binding in stored.bindings:
            self.users_by_provider_subject[(binding.provider, binding.provider_subject)] = stored.user_id
        return replace(stored)

    def get_user_by_login_id(self, login_id: str) -> UserRecord | None:
        user_id = self.users_by_login_id.get(login_id.lower())
        if user_id is None:
            return None
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> UserRecord | None:
        record = self.users_by_id.get(user_id)
        return replace(record) if record else None

    def get_user_by_provider_subject(self, *, provider: IdentityProviderKind, provider_subject: str) -> UserRecord | None:
        user_id = self.users_by_provider_subject.get((provider, provider_subject))
        if user_id is None:
            return None
        return self.get_user(user_id)

    def save_identity_binding(self, binding: ExternalIdentityBindingRecord) -> ExternalIdentityBindingRecord:
        user = self.users_by_id.get(binding.user_id)
        if user is None:
            raise KeyError(binding.user_id)
        active_bindings = [item for item in user.bindings if not (item.provider == binding.provider and item.provider_subject == binding.provider_subject)]
        active_bindings.append(replace(binding))
        updated = replace(user, bindings=active_bindings, updated_at_ms=max(user.updated_at_ms, binding.bound_at_ms))
        self.save_user(updated)
        return replace(binding)

    def save_auth_session(self, session: AuthSessionRecord) -> AuthSessionRecord:
        stored = replace(session)
        previous = self.auth_sessions_by_id.get(stored.auth_session_id)
        if previous is not None and previous.refresh_token_fingerprint != stored.refresh_token_fingerprint:
            self.auth_sessions_by_refresh_fingerprint.pop(previous.refresh_token_fingerprint, None)
        self.auth_sessions_by_id[stored.auth_session_id] = stored
        self.auth_sessions_by_refresh_fingerprint[stored.refresh_token_fingerprint] = stored.auth_session_id
        return replace(stored)

    def get_auth_session(self, auth_session_id: str) -> AuthSessionRecord | None:
        record = self.auth_sessions_by_id.get(auth_session_id)
        return replace(record) if record else None

    def get_auth_session_by_refresh_fingerprint(self, refresh_token_fingerprint: str) -> AuthSessionRecord | None:
        auth_session_id = self.auth_sessions_by_refresh_fingerprint.get(refresh_token_fingerprint)
        if auth_session_id is None:
            return None
        return self.get_auth_session(auth_session_id)

    def list_auth_sessions_for_user(self, *, user_id: str) -> list[AuthSessionRecord]:
        items = [item for item in self.auth_sessions_by_id.values() if item.user_id == user_id]
        return [replace(item) for item in sorted(items, key=lambda item: item.issued_at_ms, reverse=True)]

    def save_wechat_authorization_session(self, session: WechatAuthorizationSessionRecord) -> WechatAuthorizationSessionRecord:
        stored = replace(session)
        self.wechat_authorization_sessions_by_id[stored.auth_request_id] = stored
        self.wechat_authorization_sessions_by_state[stored.state_token] = stored.auth_request_id
        return replace(stored)

    def get_wechat_authorization_session(self, auth_request_id: str) -> WechatAuthorizationSessionRecord | None:
        record = self.wechat_authorization_sessions_by_id.get(auth_request_id)
        return replace(record) if record else None

    def get_wechat_authorization_session_by_state(self, state_token: str) -> WechatAuthorizationSessionRecord | None:
        auth_request_id = self.wechat_authorization_sessions_by_state.get(state_token)
        if auth_request_id is None:
            return None
        return self.get_wechat_authorization_session(auth_request_id)

    def save_sms_challenge(self, challenge: SmsChallengeRecord) -> SmsChallengeRecord:
        stored = replace(challenge)
        self.sms_challenges_by_id[stored.challenge_id] = stored
        ids = self.sms_challenges_by_phone_hash.setdefault(stored.phone_hash, [])
        if stored.challenge_id not in ids:
            ids.append(stored.challenge_id)
        return replace(stored)

    def get_sms_challenge(self, challenge_id: str) -> SmsChallengeRecord | None:
        record = self.sms_challenges_by_id.get(challenge_id)
        return replace(record) if record else None

    def list_sms_challenges_for_phone(self, *, phone_hash: str, since_ms: int | None = None) -> list[SmsChallengeRecord]:
        ids = self.sms_challenges_by_phone_hash.get(phone_hash, [])
        records = [self.sms_challenges_by_id[item] for item in ids if item in self.sms_challenges_by_id]
        if since_ms is not None:
            records = [item for item in records if item.created_at_ms >= since_ms]
        return [replace(item) for item in sorted(records, key=lambda item: item.created_at_ms, reverse=True)]
