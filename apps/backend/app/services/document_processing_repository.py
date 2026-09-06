from __future__ import annotations

from dataclasses import replace
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings
from app.ports.document_processing import ProcessingTaskEvent, ProcessingTaskRecord, ProcessingTaskRepository


class InMemoryProcessingTaskRepository(ProcessingTaskRepository):
    def __init__(self) -> None:
        self.tasks: dict[str, ProcessingTaskRecord] = {}
        self.events: dict[str, list[ProcessingTaskEvent]] = {}

    def save_task(self, task: ProcessingTaskRecord) -> ProcessingTaskRecord:
        stored = replace(task)
        self.tasks[stored.task_id] = stored
        return replace(stored)

    def get_task(self, task_id: str) -> ProcessingTaskRecord | None:
        record = self.tasks.get(task_id)
        return replace(record) if record else None

    def list_tasks_for_user(self, *, user_id: str | None = None, document_id: str | None = None) -> list[ProcessingTaskRecord]:
        records = list(self.tasks.values())
        if user_id is not None:
            records = [record for record in records if record.owner_user_id == user_id]
        if document_id is not None:
            records = [record for record in records if record.document_id == document_id]
        return [replace(record) for record in sorted(records, key=lambda item: item.updated_at_ms, reverse=True)]

    def save_event(self, event: ProcessingTaskEvent) -> ProcessingTaskEvent:
        stored = replace(event)
        self.events.setdefault(stored.task_id, []).append(stored)
        return replace(stored)

    def list_events_for_task(self, task_id: str) -> list[ProcessingTaskEvent]:
        return [replace(event) for event in self.events.get(task_id, [])]


class PostgresProcessingTaskRepository(ProcessingTaskRepository):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_tables()

    def save_task(self, task: ProcessingTaskRecord) -> ProcessingTaskRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO material_processing_tasks (
                      task_id, document_id, owner_user_id, document_kind, current_stage,
                      retry_count, max_retries, parser_provider, embedding_provider,
                      chunk_count, error_code, error_message, created_at_ms, updated_at_ms,
                      queued_at_ms, started_at_ms, completed_at_ms, last_retry_at_ms,
                      billing_quote_id
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (task_id) DO UPDATE SET
                      current_stage = EXCLUDED.current_stage,
                      retry_count = EXCLUDED.retry_count,
                      max_retries = EXCLUDED.max_retries,
                      parser_provider = EXCLUDED.parser_provider,
                      embedding_provider = EXCLUDED.embedding_provider,
                      chunk_count = EXCLUDED.chunk_count,
                      error_code = EXCLUDED.error_code,
                      error_message = EXCLUDED.error_message,
                      updated_at_ms = EXCLUDED.updated_at_ms,
                      queued_at_ms = EXCLUDED.queued_at_ms,
                      started_at_ms = EXCLUDED.started_at_ms,
                      completed_at_ms = EXCLUDED.completed_at_ms,
                      last_retry_at_ms = EXCLUDED.last_retry_at_ms,
                      billing_quote_id = EXCLUDED.billing_quote_id
                    """,
                    (
                        task.task_id,
                        task.document_id,
                        task.owner_user_id,
                        task.document_kind,
                        task.current_stage,
                        task.retry_count,
                        task.max_retries,
                        task.parser_provider,
                        task.embedding_provider,
                        task.chunk_count,
                        task.error_code,
                        task.error_message,
                        task.created_at_ms,
                        task.updated_at_ms,
                        task.queued_at_ms,
                        task.started_at_ms,
                        task.completed_at_ms,
                        task.last_retry_at_ms,
                        task.billing_quote_id,
                    ),
                )
            connection.commit()
        return task

    def get_task(self, task_id: str) -> ProcessingTaskRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM material_processing_tasks WHERE task_id = %s", (task_id,))
            row = cursor.fetchone()
        return self._task_from_row(row) if row else None

    def list_tasks_for_user(self, *, user_id: str | None = None, document_id: str | None = None) -> list[ProcessingTaskRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if user_id is not None:
            clauses.append("owner_user_id = %s")
            params.append(user_id)
        if document_id is not None:
            clauses.append("document_id = %s")
            params.append(document_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(f"SELECT * FROM material_processing_tasks {where} ORDER BY updated_at_ms DESC", params)
            rows = cursor.fetchall()
        return [self._task_from_row(row) for row in rows]

    def save_event(self, event: ProcessingTaskEvent) -> ProcessingTaskEvent:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO material_processing_task_events (
                      event_id, task_id, stage, retry_count, event_name,
                      duration_ms, error_code, created_at_ms
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        event.event_id,
                        event.task_id,
                        event.stage,
                        event.retry_count,
                        event.event_name,
                        event.duration_ms,
                        event.error_code,
                        event.created_at_ms,
                    ),
                )
            connection.commit()
        return event

    def list_events_for_task(self, task_id: str) -> list[ProcessingTaskEvent]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM material_processing_task_events WHERE task_id = %s ORDER BY created_at_ms ASC",
                (task_id,),
            )
            rows = cursor.fetchall()
        return [self._event_from_row(row) for row in rows]

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required")
        return psycopg.connect(
            self.settings.database_url,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name=f"{self.settings.database_application_name}-processing-tasks",
        )

    def _ensure_tables(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS material_processing_tasks (
                      task_id TEXT PRIMARY KEY,
                      document_id TEXT NOT NULL,
                      owner_user_id TEXT NOT NULL,
                      document_kind TEXT NOT NULL,
                      current_stage TEXT NOT NULL,
                      retry_count INTEGER NOT NULL DEFAULT 0,
                      max_retries INTEGER NOT NULL DEFAULT 0,
                      parser_provider TEXT NOT NULL,
                      embedding_provider TEXT NOT NULL,
                      chunk_count INTEGER NOT NULL DEFAULT 0,
                      error_code TEXT NULL,
                      error_message TEXT NULL,
                      created_at_ms BIGINT NOT NULL,
                      updated_at_ms BIGINT NOT NULL,
                      queued_at_ms BIGINT NULL,
                      started_at_ms BIGINT NULL,
                      completed_at_ms BIGINT NULL,
                      last_retry_at_ms BIGINT NULL,
                      billing_quote_id TEXT NULL
                    )
                    """
                )
                cursor.execute("ALTER TABLE material_processing_tasks ADD COLUMN IF NOT EXISTS billing_quote_id TEXT NULL")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_material_processing_tasks_owner_document ON material_processing_tasks(owner_user_id, document_id, updated_at_ms DESC)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_material_processing_tasks_stage_updated ON material_processing_tasks(current_stage, updated_at_ms DESC)"
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS material_processing_task_events (
                      event_id TEXT PRIMARY KEY,
                      task_id TEXT NOT NULL REFERENCES material_processing_tasks(task_id) ON DELETE CASCADE,
                      stage TEXT NOT NULL,
                      retry_count INTEGER NOT NULL DEFAULT 0,
                      event_name TEXT NOT NULL,
                      duration_ms BIGINT NULL,
                      error_code TEXT NULL,
                      created_at_ms BIGINT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_material_processing_task_events_task_created ON material_processing_task_events(task_id, created_at_ms DESC)"
                )
            connection.commit()

    @staticmethod
    def _task_from_row(row: dict[str, Any]) -> ProcessingTaskRecord:
        return ProcessingTaskRecord(
            task_id=row["task_id"],
            document_id=row["document_id"],
            owner_user_id=row["owner_user_id"],
            document_kind=row["document_kind"],
            current_stage=row["current_stage"],
            retry_count=int(row["retry_count"]),
            max_retries=int(row["max_retries"]),
            parser_provider=row["parser_provider"],
            embedding_provider=row["embedding_provider"],
            chunk_count=int(row["chunk_count"]),
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at_ms=int(row["created_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            queued_at_ms=row["queued_at_ms"],
            started_at_ms=row["started_at_ms"],
            completed_at_ms=row["completed_at_ms"],
            last_retry_at_ms=row["last_retry_at_ms"],
            billing_quote_id=row.get("billing_quote_id"),
        )

    @staticmethod
    def _event_from_row(row: dict[str, Any]) -> ProcessingTaskEvent:
        return ProcessingTaskEvent(
            event_id=row["event_id"],
            task_id=row["task_id"],
            stage=row["stage"],
            retry_count=int(row["retry_count"]),
            event_name=row["event_name"],
            duration_ms=row["duration_ms"],
            error_code=row["error_code"],
            created_at_ms=int(row["created_at_ms"]),
        )
