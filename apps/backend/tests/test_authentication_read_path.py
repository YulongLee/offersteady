"""Synthetic regressions for per-request authority and metadata-only activity writes."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import logging
from time import time

import jwt
import pytest

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.authentication import AccessTokenPayload, AuthSessionRecord, ExternalIdentityBindingRecord, UserRecord
from app.services import authentication_service as authentication_module
from app.services.authentication_repository import InMemoryAuthenticationRepository
from app.services.authentication_service import AuthenticationService, JWTAccessTokenCodec, PBKDF2PasswordHasher
from app.services.sms_verification_provider import FakeSmsVerificationProvider


class CountingAuthenticationRepository(InMemoryAuthenticationRepository):
    def __init__(self):
        super().__init__()
        self.authority_reads = 0
        self.touch_attempts = 0
        self.blocked_users: set[str] = set()

    def get_access_token_state(self, **kwargs):
        self.authority_reads += 1
        return super().get_access_token_state(**kwargs)

    def touch_auth_session(self, session, **kwargs):
        self.touch_attempts += 1
        return super().touch_auth_session(session, **kwargs)

    def get_user(self, user_id):
        return None if user_id in self.blocked_users else super().get_user(user_id)


def build_auth_service(repository=None, *, edition="cn"):
    settings = Settings(_env_file=None, environment="test", product_edition=edition,
        auth_jwt_secret="synthetic-auth-read-jwt-secret-at-least-32-bytes",
        auth_password_hash_iterations=1_000)
    repository = repository if repository is not None else CountingAuthenticationRepository()
    service = AuthenticationService(settings=settings, logger=logging.getLogger("test.synthetic-auth-read"),
        repository=repository, password_hasher=PBKDF2PasswordHasher(settings),
        token_codec=JWTAccessTokenCodec(settings), wechat_provider=None,
        sms_provider=FakeSmsVerificationProvider(settings))
    return service, repository


def seed_auth(service, repository, *, now=None, last_used=None, expires=None):
    now = int(time() * 1_000) if now is None else now
    user = repository.save_user(UserRecord(user_id="synthetic-auth-owner", login_id="synthetic@example.invalid",
        password_hash="external-auth", display_name="Synthetic", avatar_url=None,
        last_login_provider="sms", last_login_at_ms=now, created_at_ms=now, updated_at_ms=now))
    session = repository.save_auth_session(AuthSessionRecord(auth_session_id="synthetic-auth-session",
        user_id=user.user_id, client_label="synthetic-client",
        refresh_token_fingerprint=service._refresh_fingerprint("synthetic-refresh-token"), status="active",
        issued_at_ms=now, expires_at_ms=now + 3_600_000 if expires is None else expires,
        last_used_at_ms=now if last_used is None else last_used))
    return user, session, service._issue_access_token(user=user, auth_session=session)


@pytest.mark.parametrize("edition", ["cn", "global"])
def test_every_valid_request_reads_authority_without_frequent_activity_writes(monkeypatch, edition):
    service, repository = build_auth_service(edition=edition)
    user, session, token = seed_auth(service, repository)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: session.last_used_at_ms + 59_999)
    for _ in range(100):
        context = service.authenticate_access_token(access_token=token)
        assert (context.user_id, context.login_id, context.auth_session_id) == (user.user_id, user.login_id, session.auth_session_id)
    assert repository.authority_reads == 100
    assert repository.touch_attempts == 0
    assert repository.get_auth_session(session.auth_session_id) == session


def test_activity_boundary_writes_only_metadata_without_extending_expiry(monkeypatch):
    service, repository = build_auth_service()
    _, session, token = seed_auth(service, repository)
    now = session.last_used_at_ms + 60_000
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: now)
    service.authenticate_access_token(access_token=token)
    service.authenticate_access_token(access_token=token)
    assert repository.authority_reads == 2 and repository.touch_attempts == 1
    assert repository.get_auth_session(session.auth_session_id) == replace(session, last_used_at_ms=now)


@pytest.mark.parametrize("change", ["revoked", "expired", "deleted", "blocked", "user-deleted", "owner-changed"])
def test_successful_authentication_is_never_cached_across_security_changes(monkeypatch, change):
    service, repository = build_auth_service()
    user, session, token = seed_auth(service, repository)
    now = session.last_used_at_ms + 1
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: now)
    service.authenticate_access_token(access_token=token)
    if change == "deleted":
        repository.auth_sessions_by_id.pop(session.auth_session_id)
    elif change == "user-deleted":
        repository.users_by_id.pop(user.user_id)
    elif change == "blocked":
        repository.blocked_users.add(user.user_id)
    else:
        fields = {"status": change, "revoked_at_ms": now} if change in {"revoked", "expired"} else {"user_id": "synthetic-other-owner"}
        repository.save_auth_session(replace(session, **fields))
    with pytest.raises(DomainRequestError) as failure:
        service.authenticate_access_token(access_token=token)
    assert failure.value.status_code == (404 if change in {"blocked", "user-deleted"} else 401)
    assert repository.authority_reads == 2 and repository.touch_attempts == 0


@pytest.mark.parametrize("claims", [{"typ": "refresh"}, {"typ": "admin"}, {"typ": None}, {"exp": 1}])
def test_invalid_signed_type_or_expiry_is_rejected_before_repository_read(claims):
    service, repository = build_auth_service()
    user, session, _ = seed_auth(service, repository)
    payload = dict(sub=user.user_id, sid=session.auth_session_id, login_id=user.login_id, typ="access",
        iat=int(time()), exp=int(time()) + 600, iss=service.settings.auth_jwt_issuer)
    payload.update(claims)
    token = jwt.encode(payload, service.settings.auth_jwt_secret, algorithm="HS256")
    with pytest.raises(DomainRequestError) as failure:
        service.authenticate_access_token(access_token=token)
    assert failure.value.status_code == 401
    assert repository.authority_reads == repository.touch_attempts == 0


@pytest.mark.parametrize("token", ["", "malformed.jwt.token", "invalid"])
def test_malformed_or_missing_token_never_reads_or_touches(token):
    service, repository = build_auth_service()
    with pytest.raises(DomainRequestError) as failure:
        service.authenticate_access_token(access_token=token)
    assert failure.value.status_code == 401
    assert repository.authority_reads == repository.touch_attempts == 0


def test_wrong_signature_rejects_before_repository_read():
    service, repository = build_auth_service()
    user, session, _ = seed_auth(service, repository)
    token = jwt.encode(dict(sub=user.user_id, sid=session.auth_session_id, login_id=user.login_id,
        typ="access", iat=int(time()), exp=int(time()) + 600, iss=service.settings.auth_jwt_issuer),
        "synthetic-other-signing-secret-at-least-32-bytes", algorithm="HS256")
    with pytest.raises(DomainRequestError) as failure:
        service.authenticate_access_token(access_token=token)
    assert failure.value.status_code == 401 and repository.authority_reads == 0


def test_missing_session_and_mismatched_subject_reject_without_touch():
    service, repository = build_auth_service()
    user, session, _ = seed_auth(service, repository)
    for sid, sub in [("synthetic-absent-session", user.user_id), (session.auth_session_id, "synthetic-other-user")]:
        token = service.token_codec.issue_access_token(payload=AccessTokenPayload(sub=sub, sid=sid, typ="access",
            login_id=user.login_id, iat=int(time()), exp=int(time()) + 600, iss=service.settings.auth_jwt_issuer))
        with pytest.raises(DomainRequestError) as failure:
            service.authenticate_access_token(access_token=token)
        assert failure.value.status_code == 401
    assert repository.touch_attempts == 0


def test_revoked_binding_does_not_add_a_new_access_admission_rule():
    service, repository = build_auth_service()
    user, session, token = seed_auth(service, repository)
    binding = ExternalIdentityBindingRecord(binding_id="synthetic-revoked-binding", user_id=user.user_id,
        provider="sms", provider_subject="synthetic-subject", provider_subject_hint="synthetic", status="revoked")
    repository.save_identity_binding(binding)
    assert service.authenticate_access_token(access_token=token).auth_session_id == session.auth_session_id
    assert repository.get_user(user.user_id).bindings == [binding]


def test_expired_session_is_conditionally_persisted_and_exact_boundary_stays_valid(monkeypatch):
    service, repository = build_auth_service()
    _, session, token = seed_auth(service, repository)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: session.expires_at_ms)
    service.authenticate_access_token(access_token=token)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: session.expires_at_ms + 1)
    with pytest.raises(DomainRequestError) as failure:
        service.authenticate_access_token(access_token=token)
    assert failure.value.status_code == 401
    assert repository.get_auth_session(session.auth_session_id).status == "expired"


@pytest.mark.parametrize("change", ["revoked", "expired", "deleted", "rotated", "expiry-extended", "owner-changed"])
def test_delayed_touch_cannot_resurrect_or_overwrite_security_changes(change):
    service, repository = build_auth_service()
    _, snapshot, _ = seed_auth(service, repository)
    used = snapshot.last_used_at_ms + 60_000
    if change == "deleted":
        repository.auth_sessions_by_id.pop(snapshot.auth_session_id)
        expected = None
    else:
        fields = ({"status": change, "revoked_at_ms": used} if change in {"revoked", "expired"}
            else {"refresh_token_fingerprint": "synthetic-rotated"} if change == "rotated"
            else {"expires_at_ms": snapshot.expires_at_ms + 600_000} if change == "expiry-extended"
            else {"user_id": "synthetic-other-owner"})
        expected = repository.save_auth_session(replace(snapshot, **fields))
    assert repository.touch_auth_session(snapshot, used_at_ms=used, min_interval_ms=60_000) is False
    assert repository.get_auth_session(snapshot.auth_session_id) == expected


def test_concurrent_touches_update_one_row_per_interval():
    service, repository = build_auth_service()
    _, snapshot, _ = seed_auth(service, repository)
    used = snapshot.last_used_at_ms + 60_000
    with ThreadPoolExecutor(max_workers=8) as pool:
        changed = list(pool.map(lambda _: repository.touch_auth_session(snapshot, used_at_ms=used, min_interval_ms=60_000), range(32)))
    assert sum(changed) == 1
    assert repository.get_auth_session(snapshot.auth_session_id) == replace(snapshot, last_used_at_ms=used)


@pytest.mark.parametrize("change", ["refreshed", "revoked", "deleted"])
def test_stale_expiry_observation_cannot_overwrite_current_state(change):
    service, repository = build_auth_service()
    _, snapshot, _ = seed_auth(service, repository, expires=100)
    if change == "deleted":
        repository.auth_sessions_by_id.pop(snapshot.auth_session_id)
        expected = None
    else:
        expected = repository.save_auth_session(replace(snapshot,
            **({"expires_at_ms": 10_000, "refresh_token_fingerprint": "synthetic-new-refresh"}
               if change == "refreshed" else {"status": "revoked", "revoked_at_ms": 150})))
    assert repository.expire_auth_session(snapshot, expired_at_ms=200) is False
    assert repository.get_auth_session(snapshot.auth_session_id) == expected


def test_refresh_rotation_and_logout_stay_authoritative(monkeypatch):
    service, repository = build_auth_service()
    user, snapshot, old_access = seed_auth(service, repository)
    now = snapshot.last_used_at_ms + 60_000
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: now)
    _, refreshed, new_access, new_refresh = service.refresh(refresh_token="synthetic-refresh-token")
    assert repository.touch_auth_session(snapshot, used_at_ms=now, min_interval_ms=60_000) is False
    assert repository.get_auth_session(snapshot.auth_session_id) == refreshed
    with pytest.raises(DomainRequestError):
        service.refresh(refresh_token="synthetic-refresh-token")
    assert service.authenticate_access_token(access_token=old_access).user_id == user.user_id
    context = service.authenticate_access_token(access_token=new_access)
    assert service.logout(auth_context=context) == [snapshot.auth_session_id]
    with pytest.raises(DomainRequestError):
        service.authenticate_access_token(access_token=new_access)
    with pytest.raises(DomainRequestError):
        service.refresh(refresh_token=new_refresh)


def test_repository_read_failure_is_not_authorized(monkeypatch):
    service, repository = build_auth_service()
    _, _, token = seed_auth(service, repository)
    def unavailable(**kwargs):
        raise RuntimeError("synthetic repository unavailable")
    monkeypatch.setattr(repository, "get_access_token_state", unavailable)
    with pytest.raises(RuntimeError, match="synthetic repository unavailable"):
        service.authenticate_access_token(access_token=token)
    assert repository.touch_attempts == 0


def test_metadata_write_failure_retains_existing_error_propagation(monkeypatch):
    service, repository = build_auth_service()
    _, snapshot, token = seed_auth(service, repository)
    monkeypatch.setattr(authentication_module, "_now_ms", lambda: snapshot.last_used_at_ms + 60_000)
    def unavailable(*args, **kwargs):
        raise RuntimeError("synthetic metadata write unavailable")
    monkeypatch.setattr(repository, "touch_auth_session", unavailable)
    with pytest.raises(RuntimeError, match="synthetic metadata write unavailable"):
        service.authenticate_access_token(access_token=token)
    assert repository.get_auth_session(snapshot.auth_session_id) == snapshot


@pytest.mark.skipif(not hasattr(AuthenticationService, "register_global_user"), reason="Global-only source lifecycle")
def test_global_password_change_and_reset_keep_original_access_lifecycle():
    from test_global_password_authentication import build_service, complete_registration
    service, repository = build_service()
    user, current, current_token, _ = complete_registration(service, "synthetic-lifecycle@example.invalid")
    _, other, other_token, _ = service.login_global_user(email=user.login_id,
        password="correct horse battery staple", client_label="synthetic-other-device")
    context = service.authenticate_access_token(access_token=current_token)
    assert service.authenticate_access_token(access_token=other_token).auth_session_id == other.auth_session_id
    service.change_global_password(auth_context=context, current_password="correct horse battery staple",
        new_password="synthetic changed passphrase")
    assert service.authenticate_access_token(access_token=current_token).auth_session_id == current.auth_session_id
    with pytest.raises(DomainRequestError):
        service.authenticate_access_token(access_token=other_token)
    assert repository.touch_auth_session(other, used_at_ms=other.last_used_at_ms + 60_000, min_interval_ms=60_000) is False
    reset = service.send_email_code(email=user.login_id, client_label="web-global", purpose="password_reset")
    _, fresh, fresh_token, _ = service.reset_global_password(challenge_id=reset.challenge_id, email=user.login_id,
        code="123456", password="synthetic recovered passphrase", client_label="synthetic-recovered-device")
    with pytest.raises(DomainRequestError):
        service.authenticate_access_token(access_token=current_token)
    assert repository.touch_auth_session(current, used_at_ms=current.last_used_at_ms + 60_000, min_interval_ms=60_000) is False
    assert service.authenticate_access_token(access_token=fresh_token).auth_session_id == fresh.auth_session_id
