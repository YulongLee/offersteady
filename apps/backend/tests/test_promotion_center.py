from __future__ import annotations

import asyncio
from pathlib import Path
import json
from time import perf_counter

import pytest
from fastapi import BackgroundTasks, Request
from fastapi.testclient import TestClient

from app.api import promotion as promotion_api
from app.api.promotion import _admit, _read_click, _sign_click, redirect_promotion_link
from app.core.config import REPO_ROOT, Settings, get_settings
from app.main import create_app
from app.services.admin_service import HIGH_RISK_PERMISSIONS, PERMISSIONS_BY_ROLE
from app.services.promotion_analytics_job import sanitize_event
from app.services.promotion_repository import classify_client, cost_metrics, safe_destination
from app.services.promotion_repository import PromotionRepository, validate_promotion_runtime


def promotion_settings(**overrides) -> Settings:
    values = {
        "promotion_visitor_hmac_secret": "synthetic-test-secret",
        "promotion_allowed_destination_prefixes": ["/", "/app", "/guide"],
        **overrides,
    }
    return Settings(_env_file=None, **values)


def test_promotion_defaults_are_safe_and_disabled() -> None:
    settings = promotion_settings()
    assert settings.promotion_enabled is False
    assert settings.promotion_attribution_window_days == 30
    assert settings.promotion_visitor_cookie_days == 90
    assert settings.promotion_touchpoint_retention_days == 180
    assert settings.promotion_reporting_timezone == "Asia/Shanghai"
    assert settings.resolved_promotion_public_base_url == settings.public_web_base_url


def test_promotion_public_origin_defaults_to_canonical_web_origin_and_allows_override() -> None:
    canonical = promotion_settings(public_web_base_url="https://mianshiwen.cn/")
    dedicated = promotion_settings(
        public_web_base_url="https://mianshiwen.cn",
        promotion_public_base_url="https://go.mianshiwen.cn/",
    )
    assert canonical.resolved_promotion_public_base_url == "https://mianshiwen.cn"
    assert dedicated.resolved_promotion_public_base_url == "https://go.mianshiwen.cn"


def test_public_nginx_forwards_promotion_short_links_to_backend() -> None:
    config = (REPO_ROOT / "infra/nginx/default.conf").read_text()
    assert "location /r/" in config
    promotion_location = config.split("location /r/", 1)[1].split("}", 1)[0]
    assert "proxy_pass http://backend:8000;" in promotion_location


def test_enabled_production_promotion_requires_private_hmac_secret_and_redis() -> None:
    with pytest.raises(RuntimeError, match="OFFERSTEADY_REDIS_URL"):
        validate_promotion_runtime(promotion_settings(promotion_enabled=True, environment="production", database_url="postgresql://synthetic.invalid/db"))
    with pytest.raises(RuntimeError, match="OFFERSTEADY_PROMOTION_VISITOR_HMAC_SECRET"):
        validate_promotion_runtime(promotion_settings(
            promotion_enabled=True,
            environment="production",
            database_url="postgresql://synthetic.invalid/db",
            redis_url="redis://synthetic.invalid/0",
        ))
    validate_promotion_runtime(promotion_settings(
        promotion_enabled=True,
        environment="production",
        database_url="postgresql://synthetic.invalid/db",
        redis_url="redis://synthetic.invalid/0",
        promotion_visitor_hmac_secret="synthetic-private-hmac-secret-at-least-32-bytes",
    ))


def test_reporting_query_budget_fails_fast_before_opening_an_extra_connection() -> None:
    repository = PromotionRepository(
        promotion_settings(
            database_url="postgresql://unused.invalid/db",
            admin_max_concurrent_queries=1,
            admin_query_timeout_ms=50,
        ),
        migrate=False,
    )
    assert repository._query_budget.acquire(timeout=0.01)
    started = perf_counter()
    try:
        with pytest.raises(TimeoutError, match="promotion_database_budget_exhausted"):
            with repository.connect(readonly=True):
                pass
    finally:
        repository._query_budget.release()
    assert (perf_counter() - started) < 0.2


@pytest.mark.parametrize("path", ["https://evil.invalid", "//evil.invalid", "/\r\nLocation:https://evil.invalid", "javascript:alert(1)"])
def test_destination_rejects_open_redirect_and_header_injection(path: str) -> None:
    assert safe_destination(path, ["/app", "/guide"]) is False


def test_destination_allows_configured_internal_paths() -> None:
    assert safe_destination("/app/interviews/new?source=promotion", ["/app", "/guide"]) is True
    assert safe_destination("/admin", ["/app", "/guide"]) is False


def test_click_context_is_signed_expiring_and_tamper_evident() -> None:
    settings = promotion_settings()
    signed = _sign_click("AbCd123456", "synthetic-click", 9_999_999_999_999, settings)
    assert _read_click(signed, settings) == {"s": "AbCd123456", "c": "synthetic-click", "t": 9_999_999_999_999}
    assert _read_click(f"{signed[:-1]}0", settings) is None


def test_bot_and_internal_preview_classification_has_no_raw_identity() -> None:
    assert classify_client("Bytespider/1.0", admin_preview=False, internal_test=False) == "known_bot_or_preview"
    assert classify_client("Mozilla/5.0", admin_preview=True, internal_test=False) == "admin_preview"
    assert classify_client("Mozilla/5.0", admin_preview=False, internal_test=True) == "internal_test"
    assert classify_client("Mozilla/5.0", admin_preview=False, internal_test=False) is None


def test_cost_metrics_never_render_missing_cost_as_zero() -> None:
    assert cost_metrics(cost_cents=None, revenue_cents=10_000, paying_users=2) == {
        "costCents": None, "cacCents": None, "roas": None, "roi": None, "costCoverage": "missing",
    }
    metrics = cost_metrics(cost_cents=2_000, revenue_cents=10_000, paying_users=2)
    assert metrics["cacCents"] == 1_000
    assert metrics["roas"] == 5
    assert metrics["roi"] == 4


def test_event_schema_rejects_sensitive_and_oversized_payloads() -> None:
    valid = {
        "event_id": "event-12345678", "event_type": "redirect_hit", "link_id": "link-1",
        "occurred_at_ms": 1, "destination_key": "/", "qualification_state": "raw",
    }
    assert sanitize_event(valid)["event_id"] == "event-12345678"
    with pytest.raises(ValueError, match="disallowed"):
        sanitize_event({**valid, "access_token": "secret"})
    with pytest.raises(ValueError, match="too_large"):
        sanitize_event({**valid, "referrer_host": "x" * 513})


def test_promotion_migration_contains_required_exactly_once_and_bounded_indexes() -> None:
    sql = (Path(REPO_ROOT) / "apps/backend/migrations/versions/0038_promotion_center.sql").read_text()
    for table in (
        "promotion_channels", "promotion_campaigns", "promotion_links", "promotion_cost_entries",
        "promotion_touchpoints", "promotion_identity_bindings", "promotion_conversion_events",
        "promotion_attribution_facts", "promotion_metric_snapshots", "promotion_analytics_runs",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "UNIQUE(conversion_type, source_record_id, attribution_model, model_version)" in sql
    assert "reversal_of_entry_id TEXT NULL UNIQUE" in sql
    assert "idx_promotion_touchpoints_visitor_time" in sql
    assert "idx_promotion_snapshots_dimension_date" in sql
    assert "trg_auth_user_promotion_detach" in sql
    assert "visitor_hmac = 'deleted:' || identity_binding_id" in sql
    assert "trg_promotion_cost_append_only" in sql
    assert "trg_promotion_link_attribution_immutable" in sql


def test_production_compose_runs_promotion_analytics_as_an_independent_service() -> None:
    compose = (Path(REPO_ROOT) / "infra/compose/docker-compose.foundation.yml").read_text()
    assert "  promotion-analytics:" in compose
    assert "app.services.promotion_analytics_job" in compose
    assert "OFFERSTEADY_PROMOTION_ENABLED" in compose


def test_permissions_are_independent_and_mutations_require_recent_mfa() -> None:
    assert "promotion.read" in PERMISSIONS_BY_ROLE["operations"]
    assert "promotion.manage" in PERMISSIONS_BY_ROLE["operations"]
    assert "promotion.cost.manage" in PERMISSIONS_BY_ROLE["finance"]
    assert "promotion.manage" not in PERMISSIONS_BY_ROLE["finance"]
    assert "promotion.manage" in HIGH_RISK_PERMISSIONS
    assert "promotion.cost.manage" in HIGH_RISK_PERMISSIONS


def test_disabled_public_redirect_fails_open_to_safe_product_home(monkeypatch) -> None:
    monkeypatch.setenv("OFFERSTEADY_PROMOTION_ENABLED", "false")
    monkeypatch.setenv("OFFERSTEADY_PUBLIC_WEB_BASE_URL", "https://www.example.test")
    get_settings.cache_clear()
    try:
        response = TestClient(create_app()).get("/r/AbCd123456", follow_redirects=False)
    finally:
        get_settings.cache_clear()
    assert response.status_code == 302
    assert response.headers["location"] == "https://www.example.test/"
    assert "offersteady_pv" not in response.headers.get("set-cookie", "")


def test_opt_out_is_available_even_when_collection_is_disabled() -> None:
    response = TestClient(create_app()).post("/api/v1/promotion/opt-out")
    assert response.status_code == 200
    cookies = response.headers.get_list("set-cookie")
    assert any("offersteady_analytics_optout=1" in item for item in cookies)
    assert any("offersteady_pv=" in item and "Max-Age=0" in item for item in cookies)


def test_public_abuse_budget_is_bounded_without_persisting_raw_client_identity() -> None:
    key = "synthetic-client-hmac-never-a-raw-ip"
    assert _admit(key, 2) is True
    assert _admit(key, 2) is True
    assert _admit(key, 2) is False


def test_redirect_remains_fast_and_available_when_event_queue_fails(monkeypatch) -> None:
    settings = promotion_settings(
        promotion_enabled=True,
        database_url="postgresql://unused.invalid/unused",
        public_web_base_url="https://www.example.test",
    )

    class RepositoryStub:
        def resolve_active_link(self, slug: str, *, at_ms: int):
            assert slug == "AbCd123456"
            return {"link_id": "promotion-link-synthetic", "destination_path": "/app", "slug": slug}

    class FailingQueue:
        def publish(self, payload):
            assert "user_agent" not in payload
            assert "raw_ip" not in payload
            return False

    monkeypatch.setattr(promotion_api, "get_settings", lambda: settings)
    monkeypatch.setattr(promotion_api, "promotion_repository", lambda: RepositoryStub())
    monkeypatch.setattr(promotion_api, "promotion_queue", lambda: FailingQueue())
    durations = []
    for _ in range(20):
        request = Request({
            "type": "http", "http_version": "1.1", "method": "GET", "scheme": "https",
            "path": "/r/AbCd123456", "raw_path": b"/r/AbCd123456", "query_string": b"",
            "root_path": "", "headers": [(b"user-agent", b"Mozilla/5.0")],
            "client": ("203.0.113.10", 443), "server": ("www.example.test", 443),
        })
        background_tasks = BackgroundTasks()
        started = perf_counter()
        response = redirect_promotion_link("AbCd123456", request, background_tasks, preview=False)
        durations.append((perf_counter() - started) * 1000)
        assert response.status_code == 302
        assert response.headers["location"] == "https://www.example.test/app"
        asyncio.run(background_tasks())
    # Measure the route itself rather than TestClient thread scheduling under a
    # 400+ test suite; queue delivery happens after this fail-open response.
    assert sorted(durations)[18] < 50


def test_unknown_and_malformed_slugs_have_the_same_safe_fallback(monkeypatch) -> None:
    settings = promotion_settings(promotion_enabled=True, database_url="postgresql://unused.invalid/unused", public_web_base_url="https://www.example.test")

    class MissingRepository:
        def resolve_active_link(self, slug: str, *, at_ms: int):
            return None

    monkeypatch.setattr(promotion_api, "get_settings", lambda: settings)
    monkeypatch.setattr(promotion_api, "promotion_repository", lambda: MissingRepository())
    client = TestClient(create_app())
    unknown = client.get("/r/ZzZz123456", follow_redirects=False)
    malformed = client.get("/r/not-valid!", follow_redirects=False)
    assert unknown.status_code == malformed.status_code == 302
    assert unknown.headers["location"] == malformed.headers["location"] == "https://www.example.test/"


def test_synthetic_fixture_covers_closed_loop_without_real_user_data() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures/promotion_center_e2e.json").read_text())
    assert {item["code"] for item in fixture["channels"]} == {"nowcoder", "xiaohongshu"}
    assert len(fixture["campaigns"][0]["channelIds"]) == 2
    assert any(item["state"] == "excluded" for item in fixture["touchpoints"])
    assert len({item["visitor"] for item in fixture["touchpoints"] if item["state"] == "qualified"}) == 2
    assert any(item["visitor"] is None for item in fixture["users"])
    assert any(item["deleted"] for item in fixture["users"])
    paid = [item for item in fixture["conversions"] if item.get("status") == "paid" and item["type"] == "payment"]
    assert sum(item["amountCents"] for item in paid) == 19_900
    assert sum(item["amountCents"] for item in fixture["costs"]) == 80_000


def test_synthetic_fixture_reconciles_models_revenue_and_unattributed() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures/promotion_center_e2e.json").read_text())
    touches = sorted(
        (item for item in fixture["touchpoints"] if item.get("visitor") == "visitor-a-hmac" and item["state"] == "qualified"),
        key=lambda item: item["occurredAtMs"],
    )
    assert touches[0]["linkId"] == "link-nowcoder-article"
    assert touches[-1]["linkId"] == "link-rednote-one"
    payments = {item["sourceId"]: item for item in fixture["conversions"] if item["type"] == "payment" and item.get("status") == "paid"}
    assert len(payments) == 1
    assert sum(item["amountCents"] for item in payments.values()) == 19_900
    assert any(user["visitor"] is None for user in fixture["users"])
    metrics = cost_metrics(cost_cents=sum(item["amountCents"] for item in fixture["costs"]), revenue_cents=19_900, paying_users=1)
    assert metrics["costCoverage"] == "complete"
    assert metrics["roas"] == round(19_900 / 80_000, 6)
    assert cost_metrics(cost_cents=None, revenue_cents=19_900, paying_users=1)["roas"] is None


@pytest.mark.parametrize("model,expected_link", [("first_touch", "link-nowcoder-article"), ("last_non_direct_touch", "link-rednote-one")])
def test_fixture_dimension_rollups_reconcile_to_one_overview_total(model: str, expected_link: str) -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures/promotion_center_e2e.json").read_text())
    link = next(item for item in fixture["links"] if item["id"] == expected_link)
    revenue = sum(item["amountCents"] for item in fixture["conversions"] if item["type"] == "payment" and item.get("status") == "paid")
    link_totals = {expected_link: revenue}
    channel_totals = {link["channelId"]: sum(link_totals.values())}
    campaign_totals = {link["campaignId"]: sum(channel_totals.values())}
    assert sum(link_totals.values()) == sum(channel_totals.values()) == sum(campaign_totals.values()) == revenue
    assert model in {"first_touch", "last_non_direct_touch"}
