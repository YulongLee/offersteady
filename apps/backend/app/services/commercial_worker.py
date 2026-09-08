from __future__ import annotations

import logging
from dataclasses import dataclass

from app.ports.commercial_hardening import CommercialHardeningRepository, CommercialJobRecord
from app.ports.storage import FileStoragePort
from app.services.commercial_hardening import now_ms
from app.services.document_processing import DocumentProcessingService


@dataclass
class CommercialWorkerResult:
    processed: int
    succeeded: int
    failed: int


class CommercialWorkerService:
    def __init__(
        self,
        *,
        repository: CommercialHardeningRepository,
        storage: FileStoragePort,
        logger: logging.Logger,
        processing_service: DocumentProcessingService | None = None,
        lease_seconds: int = 900,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.logger = logger
        self.processing_service = processing_service
        self.lease_seconds = max(60, lease_seconds)
        self._last_maintenance_ms = 0
        self._last_recovery_ms = 0

    def run_once(self) -> CommercialWorkerResult:
        processed = succeeded = failed = 0
        tick_ms = now_ms()
        kinds: list[str] = ["processing"] if self.processing_service is not None else []
        if tick_ms - self._last_maintenance_ms >= 30_000:
            kinds.extend(("deletion", "reconcile"))
            self._last_maintenance_ms = tick_ms
        recovery_due = tick_ms - self._last_recovery_ms >= 60_000
        for kind in kinds:
            if recovery_due:
                recovered = self.repository.recover_stale_jobs(
                    job_kind=kind,  # type: ignore[arg-type]
                    now_ms=tick_ms,
                    stale_before_ms=tick_ms - self.lease_seconds * 1000,
                )
                if recovered:
                    self.logger.warning(
                        "commercial_worker.stale_jobs_recovered",
                        extra={"job_kind": kind, "recovered": recovered},
                    )
            job = self.repository.claim_next_job(job_kind=kind, now_ms=now_ms())  # type: ignore[arg-type]
            if job is None:
                continue
            processed += 1
            try:
                if kind == "processing":
                    if self.processing_service is None or not job.related_task_id:
                        raise RuntimeError("processing_task_reference_missing")
                    task = self.processing_service.recover_task_for_job(job)
                    if task is not None and task.current_stage not in {"COMPLETED", "FAILED"}:
                        task = self.processing_service.process_task(job.related_task_id)
                    if task is None:
                        raise RuntimeError("processing_task_missing")
                    if task.current_stage == "COMPLETED":
                        succeeded += 1
                    else:
                        self.repository.mark_job_failed(
                            job_id=job.job_id,
                            now_ms=now_ms(),
                            safe_error_code=task.error_code or "processing_task_failed",
                            retryable=False,
                        )
                        failed += 1
                    continue
                if kind == "deletion":
                    self._run_deletion(job)
                else:
                    self._run_reconcile(job)
                self.repository.mark_job_succeeded(job_id=job.job_id, now_ms=now_ms())
                succeeded += 1
            except Exception as exc:  # pragma: no cover - provider/OSS dependent boundary.
                self.logger.warning("commercial_worker.job_failed", extra={"job_id": job.job_id, "job_kind": job.job_kind, "safe_error_code": exc.__class__.__name__})
                self.repository.mark_job_failed(job_id=job.job_id, now_ms=now_ms(), safe_error_code=exc.__class__.__name__, retryable=True)
                failed += 1
        if recovery_due:
            self._last_recovery_ms = tick_ms
        return CommercialWorkerResult(processed=processed, succeeded=succeeded, failed=failed)

    def _run_deletion(self, job: CommercialJobRecord) -> None:
        keys = job.payload.get("objectKeys", [])
        if not isinstance(keys, list):
            return
        for object_key in keys:
            if isinstance(object_key, str) and object_key and not object_key.startswith("inline://"):
                self.storage.delete_object(object_key=object_key)

    def _run_reconcile(self, job: CommercialJobRecord) -> None:
        # First commercial pass keeps reconciliation durable and retryable; artifact verification
        # is still derived by the API state path until a scheduled reconciler is enabled.
        self.logger.info("commercial_worker.reconcile_noop", extra={"job_id": job.job_id})
