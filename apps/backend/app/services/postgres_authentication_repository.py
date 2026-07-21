from __future__ import annotations

from dataclasses import replace
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings
from app.ports.authentication import (
    AuthSessionRecord,
    AuthenticationRepository,
    ExternalIdentityBindingRecord,
    IdentityProviderKind,
    SmsChallengeRecord,
    UserRecord,
    WechatAuthorizationSessionRecord,
)
from app.services.authentication_repository import InMemoryAuthenticationRepository


class PostgresAuthenticationRepository(AuthenticationRepository):
    """Persistent commercial identity repository.

    WeChat authorization attempts are intentionally short-lived and remain in memory;
    account identities, SMS challenges, and issued sessions are authoritative in PostgreSQL.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.transient = InMemoryAuthenticationRepository()
        self._ensure_tables()

    def save_user(self, user: UserRecord) -> UserRecord:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO auth_users (
                  user_id, login_id, password_hash, display_name, avatar_url,
                  last_login_provider, last_login_at_ms, created_at_ms, updated_at_ms,
                  membership_anchor_ref
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (login_id) DO UPDATE SET
                  password_hash = EXCLUDED.password_hash,
                  display_name = EXCLUDED.display_name,
                  avatar_url = EXCLUDED.avatar_url,
                  last_login_provider = EXCLUDED.last_login_provider,
                  last_login_at_ms = EXCLUDED.last_login_at_ms,
                  updated_at_ms = EXCLUDED.updated_at_ms,
                  membership_anchor_ref = COALESCE(EXCLUDED.membership_anchor_ref, auth_users.membership_anchor_ref)
                RETURNING user_id
                """,
                (
                    user.user_id,
                    user.login_id,
                    user.password_hash,
                    user.display_name,
                    user.avatar_url,
                    user.last_login_provider,
                    user.last_login_at_ms,
                    user.created_at_ms,
                    user.updated_at_ms,
                    user.membership_anchor_ref,
                ),
            )
            stored_user_id = str(cursor.fetchone()["user_id"])
            connection.commit()
        stored = self.get_user(stored_user_id)
        if stored is None:
            raise RuntimeError("persisted authentication user could not be reloaded")
        return stored

    def get_user_by_login_id(self, login_id: str) -> UserRecord | None:
        return self._get_user("LOWER(login_id) = LOWER(%s)", (login_id,))

    def get_user(self, user_id: str) -> UserRecord | None:
        return self._get_user("user_id = %s", (user_id,))

    def get_user_by_provider_subject(self, *, provider: IdentityProviderKind, provider_subject: str) -> UserRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT u.* FROM auth_users u
                JOIN auth_identity_bindings b ON b.user_id = u.user_id
                WHERE b.provider = %s AND b.provider_subject = %s AND b.status = 'active'
                """,
                (provider, provider_subject),
            )
            row = cursor.fetchone()
        return self._user_from_row(row) if row else None

    def save_identity_binding(self, binding: ExternalIdentityBindingRecord) -> ExternalIdentityBindingRecord:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO auth_identity_bindings (
                  binding_id, user_id, provider, provider_subject, provider_subject_hint,
                  avatar_url, display_name, status, bound_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (provider, provider_subject) DO UPDATE SET
                  provider_subject_hint = EXCLUDED.provider_subject_hint,
                  avatar_url = EXCLUDED.avatar_url,
                  display_name = EXCLUDED.display_name,
                  status = EXCLUDED.status
                RETURNING *
                """,
                (
                    binding.binding_id,
                    binding.user_id,
                    binding.provider,
                    binding.provider_subject,
                    binding.provider_subject_hint,
                    binding.avatar_url,
                    binding.display_name,
                    binding.status,
                    binding.bound_at_ms,
                ),
            )
            row = cursor.fetchone()
            connection.commit()
        return self._binding_from_row(row)

    def save_auth_session(self, session: AuthSessionRecord) -> AuthSessionRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth_sessions (
                      auth_session_id, user_id, client_label, refresh_token_fingerprint,
                      status, issued_at_ms, expires_at_ms, last_used_at_ms, revoked_at_ms
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (auth_session_id) DO UPDATE SET
                      refresh_token_fingerprint = EXCLUDED.refresh_token_fingerprint,
                      status = EXCLUDED.status,
                      expires_at_ms = EXCLUDED.expires_at_ms,
                      last_used_at_ms = EXCLUDED.last_used_at_ms,
                      revoked_at_ms = EXCLUDED.revoked_at_ms
                    """,
                    (
                        session.auth_session_id,
                        session.user_id,
                        session.client_label,
                        session.refresh_token_fingerprint,
                        session.status,
                        session.issued_at_ms,
                        session.expires_at_ms,
                        session.last_used_at_ms,
                        session.revoked_at_ms,
                    ),
                )
            connection.commit()
        return replace(session)

    def get_auth_session(self, auth_session_id: str) -> AuthSessionRecord | None:
        return self._get_auth_session("auth_session_id = %s", (auth_session_id,))

    def get_auth_session_by_refresh_fingerprint(self, refresh_token_fingerprint: str) -> AuthSessionRecord | None:
        return self._get_auth_session("refresh_token_fingerprint = %s", (refresh_token_fingerprint,))

    def list_auth_sessions_for_user(self, *, user_id: str) -> list[AuthSessionRecord]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM auth_sessions WHERE user_id = %s ORDER BY issued_at_ms DESC", (user_id,))
            rows = cursor.fetchall()
        return [self._auth_session_from_row(row) for row in rows]

    def save_wechat_authorization_session(self, session: WechatAuthorizationSessionRecord) -> WechatAuthorizationSessionRecord:
        return self.transient.save_wechat_authorization_session(session)

    def get_wechat_authorization_session(self, auth_request_id: str) -> WechatAuthorizationSessionRecord | None:
        return self.transient.get_wechat_authorization_session(auth_request_id)

    def get_wechat_authorization_session_by_state(self, state_token: str) -> WechatAuthorizationSessionRecord | None:
        return self.transient.get_wechat_authorization_session_by_state(state_token)

    def save_sms_challenge(self, challenge: SmsChallengeRecord) -> SmsChallengeRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth_sms_challenges (
                      challenge_id, phone_e164, phone_hash, provider, status, provider_biz_id,
                      provider_request_id, attempt_count, max_attempts, expires_at_ms,
                      created_at_ms, updated_at_ms, last_error_code, verified_at_ms
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (challenge_id) DO UPDATE SET
                      status = EXCLUDED.status,
                      provider_biz_id = EXCLUDED.provider_biz_id,
                      provider_request_id = EXCLUDED.provider_request_id,
                      attempt_count = EXCLUDED.attempt_count,
                      updated_at_ms = EXCLUDED.updated_at_ms,
                      last_error_code = EXCLUDED.last_error_code,
                      verified_at_ms = EXCLUDED.verified_at_ms
                    """,
                    (
                        challenge.challenge_id,
                        challenge.phone_e164,
                        challenge.phone_hash,
                        challenge.provider,
                        challenge.status,
                        challenge.provider_biz_id,
                        challenge.provider_request_id,
                        challenge.attempt_count,
                        challenge.max_attempts,
                        challenge.expires_at_ms,
                        challenge.created_at_ms,
                        challenge.updated_at_ms,
                        challenge.last_error_code,
                        challenge.verified_at_ms,
                    ),
                )
            connection.commit()
        return replace(challenge)

    def get_sms_challenge(self, challenge_id: str) -> SmsChallengeRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM auth_sms_challenges WHERE challenge_id = %s", (challenge_id,))
            row = cursor.fetchone()
        return self._sms_challenge_from_row(row) if row else None

    def list_sms_challenges_for_phone(self, *, phone_hash: str, since_ms: int | None = None) -> list[SmsChallengeRecord]:
        params: list[object] = [phone_hash]
        where = "phone_hash = %s"
        if since_ms is not None:
            where += " AND created_at_ms >= %s"
            params.append(since_ms)
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SELECT * FROM auth_sms_challenges WHERE {where} ORDER BY created_at_ms DESC", params)
            rows = cursor.fetchall()
        return [self._sms_challenge_from_row(row) for row in rows]

    def _get_user(self, where: str, params: tuple[object, ...]) -> UserRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SELECT * FROM auth_users WHERE {where}", params)
            row = cursor.fetchone()
        return self._user_from_row(row) if row else None

    def _user_from_row(self, row: dict[str, Any]) -> UserRecord:
        user_id = str(row["user_id"])
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM auth_identity_bindings WHERE user_id = %s ORDER BY bound_at_ms ASC", (user_id,))
            binding_rows = cursor.fetchall()
        return UserRecord(
            user_id=user_id,
            login_id=str(row["login_id"]),
            password_hash=str(row["password_hash"]),
            display_name=str(row["display_name"]),
            avatar_url=row["avatar_url"],
            last_login_provider=row["last_login_provider"],
            last_login_at_ms=int(row["last_login_at_ms"]),
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            bindings=[self._binding_from_row(item) for item in binding_rows],
            membership_anchor_ref=row["membership_anchor_ref"],
        )

    @staticmethod
    def _binding_from_row(row: dict[str, Any]) -> ExternalIdentityBindingRecord:
        return ExternalIdentityBindingRecord(
            binding_id=str(row["binding_id"]),
            user_id=str(row["user_id"]),
            provider=row["provider"],
            provider_subject=str(row["provider_subject"]),
            provider_subject_hint=str(row["provider_subject_hint"]),
            avatar_url=row["avatar_url"],
            display_name=row["display_name"],
            status=row["status"],
            bound_at_ms=int(row["bound_at_ms"]),
        )

    def _get_auth_session(self, where: str, params: tuple[object, ...]) -> AuthSessionRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SELECT * FROM auth_sessions WHERE {where}", params)
            row = cursor.fetchone()
        return self._auth_session_from_row(row) if row else None

    @staticmethod
    def _auth_session_from_row(row: dict[str, Any]) -> AuthSessionRecord:
        return AuthSessionRecord(
            auth_session_id=str(row["auth_session_id"]),
            user_id=str(row["user_id"]),
            client_label=str(row["client_label"]),
            refresh_token_fingerprint=str(row["refresh_token_fingerprint"]),
            status=row["status"],
            issued_at_ms=int(row["issued_at_ms"]),
            expires_at_ms=int(row["expires_at_ms"]),
            last_used_at_ms=int(row["last_used_at_ms"]),
            revoked_at_ms=int(row["revoked_at_ms"]) if row["revoked_at_ms"] is not None else None,
        )

    @staticmethod
    def _sms_challenge_from_row(row: dict[str, Any]) -> SmsChallengeRecord:
        return SmsChallengeRecord(
            challenge_id=str(row["challenge_id"]),
            phone_e164=str(row["phone_e164"]),
            phone_hash=str(row["phone_hash"]),
            provider=str(row["provider"]),
            status=row["status"],
            provider_biz_id=row["provider_biz_id"],
            provider_request_id=row["provider_request_id"],
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
            expires_at_ms=int(row["expires_at_ms"]),
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            last_error_code=row["last_error_code"],
            verified_at_ms=int(row["verified_at_ms"]) if row["verified_at_ms"] is not None else None,
        )

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required for authentication persistence")
        return psycopg.connect(
            self.settings.database_url,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name=f"{self.settings.database_application_name}-authentication",
        )

    def _ensure_tables(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(open(self._migration_path(), encoding="utf8").read())
            connection.commit()

    @staticmethod
    def _migration_path() -> str:
        from app.core.config import REPO_ROOT

        return str(REPO_ROOT / "apps" / "backend" / "migrations" / "versions" / "0006_sms_authentication_service.sql")
