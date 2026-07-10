from __future__ import annotations

from dataclasses import replace
from time import time
from uuid import uuid4
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.ports.commercial_hardening import (
    AiUsageRecord,
    CommercialHardeningRepository,
    CommercialJobKind,
    CommercialJobRecord,
    MaterialArtifactRecord,
    RagRetrievalTraceRecord,
)


def now_ms() -> int:
    return int(time() * 1000)


def artifact_id() -> str:
    return f"artifact-{uuid4().hex}"


def job_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def usage_id() -> str:
    return f"usage-{uuid4().hex}"


def trace_id() -> str:
    return f"ragtrace-{uuid4().hex}"


class InMemoryCommercialHardeningRepository(CommercialHardeningRepository):
    def __init__(self) -> None:
        self.artifacts: dict[str, MaterialArtifactRecord] = {}
        self.jobs: dict[str, CommercialJobRecord] = {}
        self.usages: dict[str, AiUsageRecord] = {}
        self.traces: dict[str, RagRetrievalTraceRecord] = {}

    def save_artifact(self, artifact: MaterialArtifactRecord) -> MaterialArtifactRecord:
        key = self._artifact_key(artifact)
        existing = next((item for item in self.artifacts.values() if self._artifact_key(item) == key), None)
        saved = replace(artifact, artifact_id=existing.artifact_id if existing else artifact.artifact_id)
        self.artifacts[saved.artifact_id] = saved
        return saved

    def list_artifacts_for_version(self, *, owner_user_id: str, document_version_id: str) -> list[MaterialArtifactRecord]:
        return [item for item in self.artifacts.values() if item.owner_user_id == owner_user_id and item.document_version_id == document_version_id]

    def enqueue_processing_job(self, job: CommercialJobRecord) -> CommercialJobRecord:
        self.jobs[job.job_id] = job
        return job

    def enqueue_deletion_job(self, job: CommercialJobRecord) -> CommercialJobRecord:
        self.jobs[job.job_id] = job
        return job

    def claim_next_job(self, *, job_kind: CommercialJobKind, now_ms: int) -> CommercialJobRecord | None:
        for job in sorted(self.jobs.values(), key=lambda item: item.created_at_ms):
            if job.job_kind == job_kind and job.status in {"queued", "retrying"} and job.scheduled_after_ms <= now_ms:
                return self.mark_job_running(job_id=job.job_id, now_ms=now_ms)
        return None

    def mark_job_running(self, *, job_id: str, now_ms: int) -> CommercialJobRecord | None:
        return self._update_job(job_id, status="running", started_at_ms=now_ms, updated_at_ms=now_ms)

    def mark_job_succeeded(self, *, job_id: str, now_ms: int, stage: str | None = None) -> CommercialJobRecord | None:
        return self._update_job(job_id, status="succeeded", stage=stage, completed_at_ms=now_ms, updated_at_ms=now_ms, safe_error_code=None)

    def mark_job_failed(self, *, job_id: str, now_ms: int, safe_error_code: str, retryable: bool) -> CommercialJobRecord | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        retrying = retryable and job.retry_count < job.max_retries
        return self._update_job(
            job_id,
            status="retrying" if retrying else "failed",
            retry_count=job.retry_count + 1,
            safe_error_code=safe_error_code,
            scheduled_after_ms=now_ms + 5000 if retrying else job.scheduled_after_ms,
            completed_at_ms=None if retrying else now_ms,
            updated_at_ms=now_ms,
        )

    def complete_processing_job_for_task(self, *, related_task_id: str, now_ms: int, stage: str = "COMPLETED") -> CommercialJobRecord | None:
        job = self._find_job_for_task(related_task_id)
        return self.mark_job_succeeded(job_id=job.job_id, now_ms=now_ms, stage=stage) if job else None

    def fail_processing_job_for_task(self, *, related_task_id: str, now_ms: int, safe_error_code: str, retryable: bool) -> CommercialJobRecord | None:
        job = self._find_job_for_task(related_task_id)
        return self.mark_job_failed(job_id=job.job_id, now_ms=now_ms, safe_error_code=safe_error_code, retryable=retryable) if job else None

    def record_ai_usage(self, usage: AiUsageRecord) -> AiUsageRecord:
        self.usages[usage.usage_id] = usage
        return usage

    def record_rag_trace(self, trace: RagRetrievalTraceRecord) -> RagRetrievalTraceRecord:
        self.traces[trace.trace_id] = trace
        return trace

    def _artifact_key(self, artifact: MaterialArtifactRecord) -> tuple[str, str, str]:
        return (artifact.owner_user_id, artifact.document_version_id, artifact.artifact_kind)

    def _find_job_for_task(self, related_task_id: str) -> CommercialJobRecord | None:
        return next((job for job in self.jobs.values() if job.related_task_id == related_task_id and job.job_kind == "processing"), None)

    def _update_job(self, job_id: str, **changes: object) -> CommercialJobRecord | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        saved = replace(job, **changes)
        self.jobs[job_id] = saved
        return saved


class PostgresCommercialHardeningRepository(CommercialHardeningRepository):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def save_artifact(self, artifact: MaterialArtifactRecord) -> MaterialArtifactRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO material_artifacts (artifact_id, owner_user_id, document_id, document_version_id, document_kind, artifact_kind, object_key, sync_status, required, content_type, size_bytes, sha256, verified_at_ms, created_at_ms, updated_at_ms, safe_error_code)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (owner_user_id, document_version_id, artifact_kind) DO UPDATE SET object_key = EXCLUDED.object_key, sync_status = EXCLUDED.sync_status, required = EXCLUDED.required, content_type = EXCLUDED.content_type, size_bytes = EXCLUDED.size_bytes, sha256 = EXCLUDED.sha256, verified_at_ms = EXCLUDED.verified_at_ms, updated_at_ms = EXCLUDED.updated_at_ms, safe_error_code = EXCLUDED.safe_error_code
                    """,
                    (artifact.artifact_id, artifact.owner_user_id, artifact.document_id, artifact.document_version_id, artifact.document_kind, artifact.artifact_kind, artifact.object_key, artifact.sync_status, artifact.required, artifact.content_type, artifact.size_bytes, artifact.sha256, artifact.verified_at_ms, artifact.created_at_ms, artifact.updated_at_ms, artifact.safe_error_code),
                )
            connection.commit()
        return artifact

    def list_artifacts_for_version(self, *, owner_user_id: str, document_version_id: str) -> list[MaterialArtifactRecord]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM material_artifacts WHERE owner_user_id = %s AND document_version_id = %s ORDER BY created_at_ms ASC", (owner_user_id, document_version_id))
            rows = cursor.fetchall()
        return [self._artifact_from_row(row) for row in rows]

    def enqueue_processing_job(self, job: CommercialJobRecord) -> CommercialJobRecord:
        return self._upsert_job(job)

    def enqueue_deletion_job(self, job: CommercialJobRecord) -> CommercialJobRecord:
        return self._upsert_job(job)

    def claim_next_job(self, *, job_kind: CommercialJobKind, now_ms: int) -> CommercialJobRecord | None:
        table = self._table_for(job_kind)
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                f"SELECT * FROM {table} WHERE status IN ('queued','retrying') AND scheduled_after_ms <= %s ORDER BY created_at_ms ASC LIMIT 1 FOR UPDATE SKIP LOCKED",
                (now_ms,),
            )
            row = cursor.fetchone()
            if row is None:
                connection.commit()
                return None
            cursor.execute(f"UPDATE {table} SET status = 'running', started_at_ms = %s, updated_at_ms = %s WHERE job_id = %s", (now_ms, now_ms, row["job_id"]))
            connection.commit()
            row = {**row, "status": "running", "started_at_ms": now_ms, "updated_at_ms": now_ms}
        return self._job_from_row(row, job_kind)

    def mark_job_running(self, *, job_id: str, now_ms: int) -> CommercialJobRecord | None:
        return self._update_job_by_id(job_id=job_id, status="running", started_at_ms=now_ms, updated_at_ms=now_ms)

    def mark_job_succeeded(self, *, job_id: str, now_ms: int, stage: str | None = None) -> CommercialJobRecord | None:
        return self._update_job_by_id(job_id=job_id, status="succeeded", stage=stage, completed_at_ms=now_ms, updated_at_ms=now_ms, safe_error_code=None)

    def mark_job_failed(self, *, job_id: str, now_ms: int, safe_error_code: str, retryable: bool) -> CommercialJobRecord | None:
        job = self._get_job_by_id(job_id)
        if job is None:
            return None
        retrying = retryable and job.retry_count < job.max_retries
        return self._update_job_by_id(
            job_id=job_id,
            status="retrying" if retrying else "failed",
            retry_count=job.retry_count + 1,
            safe_error_code=safe_error_code,
            scheduled_after_ms=now_ms + 5000 if retrying else job.scheduled_after_ms,
            completed_at_ms=None if retrying else now_ms,
            updated_at_ms=now_ms,
        )

    def complete_processing_job_for_task(self, *, related_task_id: str, now_ms: int, stage: str = "COMPLETED") -> CommercialJobRecord | None:
        job = self._get_job_by_related_task(related_task_id)
        return self.mark_job_succeeded(job_id=job.job_id, now_ms=now_ms, stage=stage) if job else None

    def fail_processing_job_for_task(self, *, related_task_id: str, now_ms: int, safe_error_code: str, retryable: bool) -> CommercialJobRecord | None:
        job = self._get_job_by_related_task(related_task_id)
        return self.mark_job_failed(job_id=job.job_id, now_ms=now_ms, safe_error_code=safe_error_code, retryable=retryable) if job else None

    def record_ai_usage(self, usage: AiUsageRecord) -> AiUsageRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ai_usage_records (usage_id, owner_user_id, operation_kind, provider, model, status, related_job_id, related_task_id, session_id, document_id, document_version_id, trace_id, input_units, output_units, total_units, point_cost, duration_ms, safe_error_code, created_at_ms) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (usage_id) DO NOTHING",
                    (usage.usage_id, usage.owner_user_id, usage.operation_kind, usage.provider, usage.model, usage.status, usage.related_job_id, usage.related_task_id, usage.session_id, usage.document_id, usage.document_version_id, usage.trace_id, usage.input_units, usage.output_units, usage.total_units, usage.point_cost, usage.duration_ms, usage.safe_error_code, usage.created_at_ms),
                )
            connection.commit()
        return usage

    def record_rag_trace(self, trace: RagRetrievalTraceRecord) -> RagRetrievalTraceRecord:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO rag_retrieval_traces (trace_id, owner_user_id, session_id, query_hash, strategy, filter_document_ids, filter_document_version_ids, candidate_count, reranked_count, returned_count, returned_source_ids, safe_error_code, created_at_ms) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (trace_id) DO NOTHING",
                    (trace.trace_id, trace.owner_user_id, trace.session_id, trace.query_hash, trace.strategy, list(trace.filter_document_ids), list(trace.filter_document_version_ids), trace.candidate_count, trace.reranked_count, trace.returned_count, list(trace.returned_source_ids), trace.safe_error_code, trace.created_at_ms),
                )
            connection.commit()
        return trace

    def _upsert_job(self, job: CommercialJobRecord) -> CommercialJobRecord:
        table = self._table_for(job.job_kind)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {table} (job_id, owner_user_id, status, stage, document_id, document_version_id, related_task_id, retry_count, max_retries, safe_error_code, payload_json, created_at_ms, updated_at_ms, scheduled_after_ms, started_at_ms, completed_at_ms)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (job_id) DO UPDATE SET status = EXCLUDED.status, stage = EXCLUDED.stage, related_task_id = EXCLUDED.related_task_id, retry_count = EXCLUDED.retry_count, max_retries = EXCLUDED.max_retries, safe_error_code = EXCLUDED.safe_error_code, payload_json = EXCLUDED.payload_json, updated_at_ms = EXCLUDED.updated_at_ms, scheduled_after_ms = EXCLUDED.scheduled_after_ms, started_at_ms = EXCLUDED.started_at_ms, completed_at_ms = EXCLUDED.completed_at_ms
                    """,
                    (job.job_id, job.owner_user_id, job.status, job.stage, job.document_id, job.document_version_id, job.related_task_id, job.retry_count, job.max_retries, job.safe_error_code, Jsonb(job.payload), job.created_at_ms, job.updated_at_ms, job.scheduled_after_ms, job.started_at_ms, job.completed_at_ms),
                )
            connection.commit()
        return job

    def _get_job_by_related_task(self, related_task_id: str) -> CommercialJobRecord | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM material_processing_jobs WHERE related_task_id = %s ORDER BY created_at_ms DESC LIMIT 1", (related_task_id,))
            row = cursor.fetchone()
        return self._job_from_row(row, "processing") if row else None

    def _get_job_by_id(self, job_id: str) -> CommercialJobRecord | None:
        for kind in ("processing", "deletion", "reconcile"):
            table = self._table_for(kind)  # type: ignore[arg-type]
            with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(f"SELECT * FROM {table} WHERE job_id = %s", (job_id,))
                row = cursor.fetchone()
            if row:
                return self._job_from_row(row, kind)  # type: ignore[arg-type]
        return None

    def _update_job_by_id(self, *, job_id: str, **changes: object) -> CommercialJobRecord | None:
        current = self._get_job_by_id(job_id)
        if current is None:
            return None
        table = self._table_for(current.job_kind)
        allowed = {key: value for key, value in changes.items() if value is not None or key in {"safe_error_code", "completed_at_ms"}}
        assignments = ", ".join(f"{key} = %s" for key in allowed)
        params = list(allowed.values()) + [job_id]
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"UPDATE {table} SET {assignments} WHERE job_id = %s", params)
            connection.commit()
        return replace(current, **allowed)

    def _artifact_from_row(self, row: dict[str, Any]) -> MaterialArtifactRecord:
        return MaterialArtifactRecord(
            artifact_id=row["artifact_id"], owner_user_id=row["owner_user_id"], document_id=row["document_id"], document_version_id=row["document_version_id"], document_kind=row["document_kind"], artifact_kind=row["artifact_kind"], object_key=row["object_key"], sync_status=row["sync_status"], required=bool(row["required"]), content_type=row["content_type"], size_bytes=row["size_bytes"], sha256=row["sha256"], verified_at_ms=row["verified_at_ms"], created_at_ms=int(row["created_at_ms"]), updated_at_ms=int(row["updated_at_ms"]), safe_error_code=row["safe_error_code"]
        )

    def _job_from_row(self, row: dict[str, Any], kind: CommercialJobKind) -> CommercialJobRecord:
        return CommercialJobRecord(
            job_id=row["job_id"], owner_user_id=row["owner_user_id"], job_kind=kind, status=row["status"], stage=row["stage"], document_id=row["document_id"], document_version_id=row["document_version_id"], related_task_id=row["related_task_id"], retry_count=int(row["retry_count"]), max_retries=int(row["max_retries"]), safe_error_code=row["safe_error_code"], payload=dict(row["payload_json"] or {}), created_at_ms=int(row["created_at_ms"]), updated_at_ms=int(row["updated_at_ms"]), scheduled_after_ms=int(row["scheduled_after_ms"]), started_at_ms=row["started_at_ms"], completed_at_ms=row["completed_at_ms"]
        )

    def _table_for(self, job_kind: CommercialJobKind) -> str:
        if job_kind == "processing":
            return "material_processing_jobs"
        if job_kind == "deletion":
            return "material_deletion_jobs"
        return "material_reconcile_jobs"

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required")
        return psycopg.connect(self.settings.database_url, connect_timeout=self.settings.database_connect_timeout_seconds, application_name=f"{self.settings.database_application_name}-commercial")

    def _ensure_tables(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE TABLE IF NOT EXISTS material_artifacts (artifact_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, document_id TEXT NOT NULL, document_version_id TEXT NOT NULL, document_kind TEXT NOT NULL, artifact_kind TEXT NOT NULL, object_key TEXT NOT NULL, sync_status TEXT NOT NULL, required BOOLEAN NOT NULL DEFAULT TRUE, content_type TEXT NULL, size_bytes BIGINT NULL, sha256 TEXT NULL, verified_at_ms BIGINT NULL, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL, safe_error_code TEXT NULL, UNIQUE(owner_user_id, document_version_id, artifact_kind))")
                for table in ("material_processing_jobs", "material_deletion_jobs", "material_reconcile_jobs"):
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} (job_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL, document_id TEXT NULL, document_version_id TEXT NULL, related_task_id TEXT NULL, retry_count INTEGER NOT NULL DEFAULT 0, max_retries INTEGER NOT NULL DEFAULT 3, safe_error_code TEXT NULL, payload_json JSONB NOT NULL DEFAULT '{{}}'::jsonb, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL, scheduled_after_ms BIGINT NOT NULL DEFAULT 0, started_at_ms BIGINT NULL, completed_at_ms BIGINT NULL)")
                cursor.execute("CREATE TABLE IF NOT EXISTS ai_usage_records (usage_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, operation_kind TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL, related_job_id TEXT NULL, related_task_id TEXT NULL, session_id TEXT NULL, document_id TEXT NULL, document_version_id TEXT NULL, trace_id TEXT NULL, input_units INTEGER NULL, output_units INTEGER NULL, total_units INTEGER NULL, point_cost INTEGER NULL, duration_ms INTEGER NULL, safe_error_code TEXT NULL, created_at_ms BIGINT NOT NULL)")
                cursor.execute("CREATE TABLE IF NOT EXISTS rag_retrieval_traces (trace_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, session_id TEXT NULL, query_hash TEXT NOT NULL, strategy TEXT NOT NULL, filter_document_ids TEXT[] NOT NULL DEFAULT '{}', filter_document_version_ids TEXT[] NOT NULL DEFAULT '{}', candidate_count INTEGER NOT NULL, reranked_count INTEGER NOT NULL, returned_count INTEGER NOT NULL, returned_source_ids TEXT[] NOT NULL DEFAULT '{}', safe_error_code TEXT NULL, created_at_ms BIGINT NOT NULL)")
            connection.commit()
