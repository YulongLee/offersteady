from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.ports.commercial_hardening import AiUsageRecord
from app.services.commercial_hardening import PostgresCommercialHardeningRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_ai_runtime_latency_metrics_are_persisted_in_postgres() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL, environment="test")
    repository = PostgresCommercialHardeningRepository(settings)
    usage_id = f"ai-metrics-{uuid4().hex}"

    repository.record_ai_usage(AiUsageRecord(
        usage_id=usage_id,
        owner_user_id=f"metrics-user-{uuid4().hex}",
        operation_kind="speech",
        provider="synthetic-provider",
        model="synthetic-model",
        status="succeeded",
        duration_ms=480,
        first_token_ms=120,
        final_latency_ms=480,
        created_at_ms=1_700_000_000_000,
    ))

    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT first_token_ms, final_latency_ms FROM ai_usage_records WHERE usage_id = %s",
            (usage_id,),
        )
        assert cursor.fetchone() == (120, 480)

