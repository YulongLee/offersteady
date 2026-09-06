from __future__ import annotations

import argparse
import time

from app.core.config import get_settings
from app.deps import commercial_hardening_repository, document_processing_service, logger, storage_port
from app.services.commercial_worker import CommercialWorkerService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OfferSteady commercial material worker.")
    parser.add_argument("--once", action="store_true", help="process one batch then exit")
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    args = parser.parse_args()
    settings = get_settings()
    worker = CommercialWorkerService(
        repository=commercial_hardening_repository(),
        storage=storage_port(),
        logger=logger(),
        processing_service=document_processing_service(),
        lease_seconds=settings.document_processing_job_lease_seconds,
    )
    while True:
        result = worker.run_once()
        if result.processed or result.failed:
            logger().info("commercial_worker.tick", extra={"processed": result.processed, "succeeded": result.succeeded, "failed": result.failed})
        if args.once:
            return
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
