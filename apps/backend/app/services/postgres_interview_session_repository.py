from __future__ import annotations

from dataclasses import asdict
from threading import Lock
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import REPO_ROOT, Settings
from app.ports.interview_session import (
    ConversationContextEntry,
    IntegrationReference,
    InterviewSessionRecord,
    InterviewSessionRepository,
    InterviewLanguage,
    SessionBoundDocument,
    SessionConfigSnapshot,
    SessionMaterialBinding,
    SessionUsageRecord,
    SessionUsageTotals,
)
from app.services.postgres_migrations import apply_sql_migrations


class PostgresInterviewSessionRepository(InterviewSessionRepository):
    _schema_lock = Lock()
    _schema_ready_for: set[str] = set()

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        database_key = str(settings.database_url or "")
        with self._schema_lock:
            if database_key not in self._schema_ready_for:
                self._ensure_tables()
                self._schema_ready_for.add(database_key)

    def save_session(self, session: InterviewSessionRecord) -> InterviewSessionRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interview_sessions (
                      session_id, owner_user_id, title, status, continue_target,
                      interview_language,
                      material_binding_json, config_snapshot_json, usage_totals_json,
                      integration_references_json, restart_of_session_id, started_at_ms,
                      ended_at_ms, created_at_ms, updated_at_ms, last_activity_at_ms, deleted_at_ms
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL)
                    ON CONFLICT (session_id) DO UPDATE SET
                      owner_user_id = EXCLUDED.owner_user_id,
                      title = EXCLUDED.title,
                      status = EXCLUDED.status,
                      continue_target = EXCLUDED.continue_target,
                      interview_language = EXCLUDED.interview_language,
                      material_binding_json = EXCLUDED.material_binding_json,
                      config_snapshot_json = EXCLUDED.config_snapshot_json,
                      usage_totals_json = EXCLUDED.usage_totals_json,
                      integration_references_json = EXCLUDED.integration_references_json,
                      restart_of_session_id = EXCLUDED.restart_of_session_id,
                      started_at_ms = EXCLUDED.started_at_ms,
                      ended_at_ms = EXCLUDED.ended_at_ms,
                      updated_at_ms = EXCLUDED.updated_at_ms,
                      last_activity_at_ms = EXCLUDED.last_activity_at_ms,
                      deleted_at_ms = NULL
                    """,
                    (
                        session.session_id,
                        session.owner_user_id,
                        session.title,
                        session.status,
                        session.continue_target,
                        session.interview_language,
                        Jsonb(asdict(session.material_binding)),
                        Jsonb(asdict(session.config_snapshot)),
                        Jsonb(asdict(session.usage_totals)),
                        Jsonb([asdict(item) for item in session.integration_references]),
                        session.restart_of_session_id,
                        session.started_at_ms,
                        session.ended_at_ms,
                        session.created_at_ms,
                        session.updated_at_ms,
                        session.last_activity_at_ms,
                    ),
                )
            connection.commit()
        return session

    def get_session(self, session_id: str) -> InterviewSessionRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM interview_sessions WHERE session_id = %s AND deleted_at_ms IS NULL", (session_id,))
            row = cursor.fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions_for_user(self, *, user_id: str, status=None) -> list[InterviewSessionRecord]:
        params: list[Any] = [user_id]
        where = "owner_user_id = %s AND deleted_at_ms IS NULL"
        if status is not None:
            where += " AND status = %s"
            params.append(status)
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SELECT * FROM interview_sessions WHERE {where} ORDER BY updated_at_ms DESC", params)
            rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]

    def touch_activity(self, *, user_id: str, session_id: str, activity_at_ms: int) -> InterviewSessionRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE interview_sessions
                SET updated_at_ms = %s, last_activity_at_ms = %s
                WHERE owner_user_id = %s AND session_id = %s
                  AND status <> 'ended' AND deleted_at_ms IS NULL
                RETURNING *
                """,
                (activity_at_ms, activity_at_ms, user_id, session_id),
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_session(row) if row else self.get_session(session_id)

    def update_language_if_preparing(
        self, *, user_id: str, session_id: str, interview_language: InterviewLanguage, updated_at_ms: int
    ) -> InterviewSessionRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE interview_sessions
                SET interview_language = %s, updated_at_ms = %s, last_activity_at_ms = %s
                WHERE owner_user_id = %s AND session_id = %s
                  AND status = 'preparing' AND deleted_at_ms IS NULL
                RETURNING *
                """,
                (interview_language, updated_at_ms, updated_at_ms, user_id, session_id),
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_session(row) if row else None

    def start_if_not_ended(
        self, *, user_id: str, session_id: str, started_at_ms: int
    ) -> InterviewSessionRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE interview_sessions
                SET status = 'live', continue_target = 'live',
                    started_at_ms = COALESCE(started_at_ms, %s),
                    updated_at_ms = %s, last_activity_at_ms = %s
                WHERE owner_user_id = %s AND session_id = %s
                  AND status <> 'ended' AND deleted_at_ms IS NULL
                RETURNING *
                """,
                (started_at_ms, started_at_ms, started_at_ms, user_id, session_id),
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_session(row) if row else None

    def list_idle_live_sessions(self, *, before_ms: int, limit: int, user_id: str | None = None) -> list[InterviewSessionRecord]:
        params: list[Any] = [before_ms]
        owner_filter = ""
        if user_id is not None:
            owner_filter = " AND owner_user_id = %s"
            params.append(user_id)
        params.append(max(1, limit))
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"""
                SELECT * FROM interview_sessions
                WHERE status = 'live' AND deleted_at_ms IS NULL
                  AND last_activity_at_ms < %s{owner_filter}
                ORDER BY last_activity_at_ms ASC
                LIMIT %s
                """,
                params,
            )
            rows = cursor.fetchall()
        return [self._row_to_session(row) for row in rows]

    def delete_session(self, *, user_id: str, session_id: str) -> bool:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE interview_sessions
                    SET deleted_at_ms = (extract(epoch from now()) * 1000)::bigint,
                        status = 'ended', continue_target = 'history',
                        ended_at_ms = COALESCE(ended_at_ms, (extract(epoch from now()) * 1000)::bigint)
                    WHERE owner_user_id = %s AND session_id = %s AND deleted_at_ms IS NULL
                    """,
                    (user_id, session_id),
                )
                deleted = cursor.rowcount > 0
                if deleted:
                    cursor.execute(
                        "DELETE FROM interview_session_context_entries WHERE owner_user_id = %s AND session_id = %s",
                        (user_id, session_id),
                    )
                    cursor.execute(
                        "DELETE FROM interview_session_usage_records WHERE owner_user_id = %s AND session_id = %s",
                        (user_id, session_id),
                    )
                    cursor.execute("SELECT to_regclass('public.approved_realtime_transcripts')")
                    approved_transcript_table = cursor.fetchone()
                    if approved_transcript_table and approved_transcript_table[0]:
                        cursor.execute(
                            "DELETE FROM approved_realtime_transcripts WHERE owner_user_id = %s AND session_id = %s",
                            (user_id, session_id),
                        )
            connection.commit()
        return deleted

    def append_context_entry(self, entry: ConversationContextEntry) -> ConversationContextEntry:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interview_session_context_entries (entry_id, session_id, owner_user_id, ordering, created_at_ms, entry_json)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (entry_id) DO UPDATE SET ordering = EXCLUDED.ordering, created_at_ms = EXCLUDED.created_at_ms, entry_json = EXCLUDED.entry_json
                    """,
                    (entry.entry_id, entry.session_id, entry.owner_user_id, entry.ordering, entry.created_at_ms, Jsonb(asdict(entry))),
                )
            connection.commit()
        return entry

    def list_context_entries(self, *, session_id: str) -> list[ConversationContextEntry]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT entry_json FROM interview_session_context_entries WHERE session_id = %s ORDER BY ordering ASC, created_at_ms ASC, entry_id ASC", (session_id,))
            rows = cursor.fetchall()
        return [self._context_entry_from_json(dict(row["entry_json"])) for row in rows]

    def save_usage_record(self, record: SessionUsageRecord) -> SessionUsageRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interview_session_usage_records (usage_id, session_id, owner_user_id, created_at_ms, usage_json)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (usage_id) DO UPDATE SET created_at_ms = EXCLUDED.created_at_ms, usage_json = EXCLUDED.usage_json
                    """,
                    (record.usage_id, record.session_id, record.owner_user_id, record.created_at_ms, Jsonb(asdict(record))),
                )
            connection.commit()
        return record

    def list_usage_records(self, *, session_id: str) -> list[SessionUsageRecord]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT usage_json FROM interview_session_usage_records WHERE session_id = %s ORDER BY created_at_ms ASC, usage_id ASC", (session_id,))
            rows = cursor.fetchall()
        return [self._usage_record_from_json(dict(row["usage_json"])) for row in rows]

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required")
        return psycopg.connect(self.settings.database_url, connect_timeout=self.settings.database_connect_timeout_seconds, application_name=f"{self.settings.database_application_name}-sessions")

    def _ensure_tables(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interview_sessions (
                      session_id TEXT PRIMARY KEY,
                      owner_user_id TEXT NOT NULL,
                      title TEXT NOT NULL,
                      interview_language TEXT NOT NULL DEFAULT 'zh-CN',
                      status TEXT NOT NULL,
                      continue_target TEXT NOT NULL,
                      material_binding_json JSONB NOT NULL,
                      config_snapshot_json JSONB NOT NULL,
                      usage_totals_json JSONB NOT NULL,
                      integration_references_json JSONB NOT NULL,
                      restart_of_session_id TEXT NULL,
                      started_at_ms BIGINT NULL,
                      ended_at_ms BIGINT NULL,
                      created_at_ms BIGINT NOT NULL,
                      updated_at_ms BIGINT NOT NULL,
                      last_activity_at_ms BIGINT NOT NULL,
                      deleted_at_ms BIGINT NULL
                    )
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_sessions_owner_updated ON interview_sessions (owner_user_id, updated_at_ms DESC)")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interview_session_context_entries (
                      entry_id TEXT PRIMARY KEY,
                      session_id TEXT NOT NULL,
                      owner_user_id TEXT NOT NULL,
                      ordering INTEGER NOT NULL,
                      created_at_ms BIGINT NOT NULL,
                      entry_json JSONB NOT NULL
                    )
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_session_context_entries_session_order ON interview_session_context_entries (session_id, ordering, created_at_ms)")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interview_session_usage_records (
                      usage_id TEXT PRIMARY KEY,
                      session_id TEXT NOT NULL,
                      owner_user_id TEXT NOT NULL,
                      created_at_ms BIGINT NOT NULL,
                      usage_json JSONB NOT NULL
                    )
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_session_usage_records_session_created ON interview_session_usage_records (session_id, created_at_ms)")
                cursor.execute(
                    (REPO_ROOT / "apps/backend/migrations/versions/0016_idle_interview_lifecycle.sql").read_text(encoding="utf8")
                )
                apply_sql_migrations(cursor, [
                    REPO_ROOT / "apps/backend/migrations/versions/0028_restore_unstarted_interviews.sql",
                    REPO_ROOT / "apps/backend/migrations/versions/0033_interview_language.sql",
                ])
            connection.commit()

    def _row_to_session(self, row: dict[str, Any]) -> InterviewSessionRecord:
        material = dict(row["material_binding_json"])
        config = dict(row["config_snapshot_json"])
        totals = dict(row["usage_totals_json"])
        references = [dict(item) for item in list(row["integration_references_json"] or [])]
        return InterviewSessionRecord(
            session_id=row["session_id"],
            owner_user_id=row["owner_user_id"],
            title=row["title"],
            interview_language=row.get("interview_language") or "zh-CN",
            status=row["status"],
            continue_target=row["continue_target"],
            material_binding=self._material_binding_from_json(material),
            config_snapshot=SessionConfigSnapshot(**config),
            usage_totals=SessionUsageTotals(**totals),
            integration_references=[IntegrationReference(**item) for item in references],
            restart_of_session_id=row["restart_of_session_id"],
            started_at_ms=row["started_at_ms"],
            ended_at_ms=row["ended_at_ms"],
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            last_activity_at_ms=int(row["last_activity_at_ms"]),
        )

    def _material_binding_from_json(self, data: dict[str, Any]) -> SessionMaterialBinding:
        documents = [SessionBoundDocument(**dict(item)) for item in data.get("bound_documents", [])]
        return SessionMaterialBinding(
            session_id=data["session_id"],
            owner_user_id=data["owner_user_id"],
            revision=int(data["revision"]),
            resume_document_id=data.get("resume_document_id"),
            job_description_document_id=data.get("job_description_document_id"),
            knowledge_document_ids=list(data.get("knowledge_document_ids") or []),
            bound_documents=documents,
            confirmed_at_ms=data.get("confirmed_at_ms"),
        )

    def _context_entry_from_json(self, data: dict[str, Any]) -> ConversationContextEntry:
        return ConversationContextEntry(**data)

    def _usage_record_from_json(self, data: dict[str, Any]) -> SessionUsageRecord:
        return SessionUsageRecord(**data)
