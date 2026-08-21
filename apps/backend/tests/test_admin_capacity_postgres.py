from __future__ import annotations

import os
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.admin_repository import AdminRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_capacity_peak_migration_accepts_five_minute_samples_and_keeps_maximum() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL, environment="test")
    repository = AdminRepository(settings)
    unique_offset = int(uuid4().hex[:8], 16) % (365 * 24 * 12)
    at_ms = 4_102_444_800_000 + unique_offset * 300_000

    try:
        repository.record_capacity_peak(at_ms=at_ms, active_interviews=2)
        repository.record_capacity_peak(at_ms=at_ms + 1_000, active_interviews=7)
        repository.record_capacity_peak(at_ms=at_ms + 2_000, active_interviews=4)

        five_minute_bucket = at_ms - at_ms % 300_000
        with repository.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT metric_value, sample_count
                FROM admin_metric_snapshots
                WHERE bucket_start_ms = %s
                  AND granularity = 'capacity_5m'
                  AND metric_key = 'peak_concurrent_interviews'
                """,
                (five_minute_bucket,),
            )
            row = cursor.fetchone()
        assert row == {"metric_value": 7.0, "sample_count": 3}
    finally:
        with repository.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM admin_metric_snapshots WHERE bucket_start_ms >= %s AND bucket_start_ms < %s",
                (at_ms - 86_400_000, at_ms + 86_400_000),
            )
            connection.commit()
