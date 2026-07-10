from __future__ import annotations

import logging
from dataclasses import dataclass

from app.ports.commercial_hardening import CommercialHardeningRepository, CommercialJobRecord
from app.ports.storage import FileStoragePort
from app.services.commercial_hardening import now_ms


@dataclass
class CommercialWorkerResult:
    processed: int
    succeeded: int
    failed: int


class CommercialWorkerService:
    def __init__(self, *, repository: CommercialHardeningRepository, storage: FileStoragePort, logger: logging.Logger) -> None:
        self.repository = repository
        self.storage = storage
        self.logger = logger

    def run_once(self) -> CommercialWorkerResult:
        processed = succeeded = failed = 0
        for kind in ("deletion", "reconcile"):
            job = self.repository.claim_next_job(job_kind=kind, now_ms=now_ms())  # type: ignore[arg-type]
            if job is None:
                continue
            processed += 1
            try:
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
