from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from statistics import quantiles
from time import perf_counter
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.services.promotion_repository import PromotionRepository, now_ms


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


@pytest.fixture(scope="module")
def repository() -> PromotionRepository:
    if not DATABASE_URL:
        pytest.skip("OFFERSTEADY_TEST_DATABASE_URL is not configured")
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=DATABASE_URL,
        redis_url="redis://synthetic.invalid/0",
        promotion_enabled=True,
        promotion_visitor_hmac_secret="synthetic-private-hmac-secret-at-least-32-bytes",
        admin_query_timeout_ms=1500,
        admin_max_concurrent_queries=2,
    )
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Promotion is additive to these already-authoritative production tables.
        # Keep the fixture minimal so historical repository-specific migrations
        # are not incorrectly replayed in filename order.
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS auth_users (
                 user_id TEXT PRIMARY KEY, login_id TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                 display_name TEXT NOT NULL, avatar_url TEXT NULL, last_login_provider TEXT NOT NULL,
                 last_login_at_ms BIGINT NOT NULL, created_at_ms BIGINT NOT NULL, updated_at_ms BIGINT NOT NULL,
                 membership_anchor_ref TEXT NULL
               );
               CREATE TABLE IF NOT EXISTS interview_sessions (
                 session_id TEXT PRIMARY KEY, owner_user_id TEXT NOT NULL, started_at_ms BIGINT NULL
               );
               CREATE TABLE IF NOT EXISTS billing_checkout_orders (
                 order_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, amount_cents INTEGER NOT NULL,
                 currency TEXT NOT NULL, status TEXT NOT NULL, created_at_ms BIGINT NOT NULL, paid_at_ms BIGINT NULL
               );"""
        )
        connection.commit()
    first = PromotionRepository(settings)
    # Applying the same additive migration twice must remain compatible.
    PromotionRepository(settings)
    return first


def _insert_user(repository: PromotionRepository, user_id: str, created_at_ms: int) -> None:
    with repository.connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO auth_users
               (user_id,login_id,password_hash,display_name,last_login_provider,last_login_at_ms,created_at_ms,updated_at_ms)
               VALUES (%s,%s,'synthetic-hash','Synthetic Promotion User','test',%s,%s,%s)""",
            (user_id, f"test:{user_id}", created_at_ms, created_at_ms, created_at_ms),
        )
        connection.commit()


def _cleanup(repository: PromotionRepository, prefix: str, user_id: str) -> None:
    # This suite requires a disposable test database. Promotion costs are
    # intentionally protected from UPDATE/DELETE even for test actors, so the
    # enclosing ephemeral PostgreSQL container owns cleanup instead of weakening
    # the append-only invariant here.
    del repository, prefix, user_id


def test_repository_idempotency_immutability_cost_reversal_and_concurrent_claims(repository: PromotionRepository) -> None:
    prefix = f"promotion_it_{uuid4().hex[:10]}"
    user_id = f"{prefix}_user"
    current = now_ms()
    try:
        _insert_user(repository, user_id, current)
        first_channel = repository.create_channel(code=f"{prefix}_one", name="Synthetic One", sort_order=1, actor_user_id=user_id)
        second_channel = repository.create_channel(code=f"{prefix}_two", name="Synthetic Two", sort_order=2, actor_user_id=user_id)
        campaign = repository.create_campaign(
            {"name": f"{prefix}_campaign", "objective": "synthetic", "status": "active", "starts_at_ms": None, "ends_at_ms": None, "budget_cents": None, "notes": ""},
            actor_user_id=user_id,
        )
        link = repository.create_link(
            {"content_name": f"{prefix}_content", "channel_id": first_channel["channel_id"], "campaign_id": campaign["campaign_id"], "destination_path": "/", "starts_at_ms": None, "ends_at_ms": None},
            actor_user_id=user_id,
        )
        assert any(item["link_id"] == link["link_id"] for item in repository.list_links(limit=100, offset=0))
        assert any(item["link_id"] == link["link_id"] for item in repository.list_links(limit=100, offset=0, status="active"))
        event = {
            "event_id": f"{prefix}_touch", "event_type": "qualified_visit", "link_id": link["link_id"],
            "visitor_hmac": f"{prefix}_visitor", "click_hmac": f"{prefix}_click", "occurred_at_ms": current - 1_000,
            "destination_key": "/", "referrer_host": "example.test", "device_class": "desktop",
            "qualification_state": "qualified", "exclusion_reason": None,
        }
        assert repository.record_touchpoint(event) is True
        assert repository.record_touchpoint(event) is False

        with pytest.raises(ValueError, match="clone_required"):
            repository.update_link(link["link_id"], {
                "content_name": link["content_name"], "channel_id": second_channel["channel_id"],
                "campaign_id": campaign["campaign_id"], "destination_path": "/", "status": "active",
                "starts_at_ms": None, "ends_at_ms": None,
            })

        cost = repository.add_cost(
            {"scope_type": "link", "scope_id": link["link_id"], "cost_date": "2026-09-02", "amount_cents": 1_000, "reason": f"{prefix}_cost"},
            actor_user_id=user_id,
        )
        reversal = repository.reverse_cost(cost["cost_entry_id"], reason=f"{prefix}_reversal", actor_user_id=user_id)
        assert int(reversal["amount_cents"]) == -1_000
        with pytest.raises(ValueError, match="already_reversed"):
            repository.reverse_cost(cost["cost_entry_id"], reason=f"{prefix}_duplicate_reversal", actor_user_id=user_id)

        def claim(claim_key: str):
            return repository.claim_identity(claim_key=claim_key, visitor_hmac=event["visitor_hmac"], user_id=user_id)

        with ThreadPoolExecutor(max_workers=2) as executor:
            claims = list(executor.map(claim, (f"{prefix}_claim_a", f"{prefix}_claim_b")))
        assert len({item["identity_binding_id"] for item in claims}) == 1

        assert repository.record_conversion(
            event_id=f"{prefix}_payment_event", conversion_type="payment", source_record_id=f"{prefix}_order",
            visitor_hmac=event["visitor_hmac"], user_id=user_id, occurred_at_ms=current, amount_cents=19_900, currency="CNY",
        ) is True
        assert repository.record_conversion(
            event_id=f"{prefix}_payment_event_retry", conversion_type="payment", source_record_id=f"{prefix}_order",
            visitor_hmac=event["visitor_hmac"], user_id=user_id, occurred_at_ms=current, amount_cents=19_900, currency="CNY",
        ) is False
    finally:
        _cleanup(repository, prefix, user_id)


def test_reporting_queries_are_indexable_and_do_not_starve_a_hot_path(repository: PromotionRepository) -> None:
    with repository.connect(readonly=True) as connection, connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan=off")
        cursor.execute(
            "EXPLAIN (FORMAT TEXT) SELECT * FROM promotion_touchpoints WHERE visitor_hmac=%s ORDER BY occurred_at_ms DESC LIMIT 10",
            ("synthetic-visitor",),
        )
        plan = "\n".join(str(row["QUERY PLAN"]) for row in cursor.fetchall())
    assert "idx_promotion_touchpoints_visitor_time" in plan

    start_ms = now_ms() - 7 * 86_400_000
    end_ms = now_ms() + 1

    def report_load() -> None:
        for _ in range(8):
            repository.overview(start_ms=start_ms, end_ms=end_ms, model="last_non_direct_touch")
            repository.dimension_report(start_ms=start_ms, end_ms=end_ms, model="last_non_direct_touch", dimension="channel")

    hot_path_ms: list[float] = []

    def hot_path() -> None:
        for _ in range(40):
            started = perf_counter()
            with psycopg.connect(DATABASE_URL, connect_timeout=1) as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                assert cursor.fetchone()[0] == 1
            hot_path_ms.append((perf_counter() - started) * 1_000)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(report_load), executor.submit(report_load), executor.submit(hot_path)]
        for future in futures:
            future.result()

    p95 = quantiles(hot_path_ms, n=20)[18]
    assert p95 < 500
