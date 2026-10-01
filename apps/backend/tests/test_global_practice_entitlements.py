from dataclasses import replace

import pytest

from app.core.config import Settings
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_usage_billing_adapter import GlobalUsageBillingAdapter

NOW = 1_800_000_000_000


@pytest.fixture
def commerce():
    return GlobalCommerceService(Settings(_env_file=None, environment="test", product_edition="global"), InMemoryGlobalCommerceRepository())


@pytest.mark.parametrize("offer,allowed", [("global-interview-pass", False), ("global-pro-weekly", True), ("global-pro-monthly", True), ("global-job-hunt", True)])
def test_purchased_duration_not_time_remaining(commerce, offer, allowed):
    commerce.grant_purchase(user_id="synthetic", offer_code=offer, source_kind="test", source_id="purchase", starts_at_ms=NOW-1000, ends_at_ms=NOW+1)
    assert commerce.practice_access("synthetic", NOW) is allowed
    assert commerce.state("synthetic", NOW)["features"]["webAnswer"] is allowed
    assert commerce.state("synthetic", NOW)["features"]["mockInterview"] is allowed
    assert commerce.practice_access("synthetic", NOW+1) is False


def test_free_future_and_revoked_never_qualify(commerce):
    assert not commerce.practice_access("synthetic", NOW)
    entitlement = commerce.grant_purchase(user_id="synthetic", offer_code="global-pro-weekly", source_kind="test", source_id="future", starts_at_ms=NOW+1)
    assert not commerce.practice_access("synthetic", NOW)
    commerce.repository.update_entitlement(replace(entitlement, starts_at_ms=NOW-1000, status="revoked"))
    assert not commerce.practice_access("synthetic", NOW)


def test_existing_purchase_uses_immutable_plan_version(commerce):
    entitlement = commerce.grant_purchase(user_id="synthetic", offer_code="global-pro-weekly", source_kind="test", source_id="purchase", starts_at_ms=NOW-1000)
    plan = commerce.repository.plan(entitlement.offer_code, entitlement.plan_version)
    commerce.repository.save_draft(replace(plan, version=plan.version+1, duration_days=1, status="draft"))
    commerce.repository.publish(plan.offer_code, plan.version+1)
    assert commerce.practice_access("synthetic", NOW)


def test_web_usage_never_becomes_an_ordinary_free_answer(commerce, monkeypatch):
    monkeypatch.setattr("app.services.global_usage_billing_adapter.time", lambda: NOW/1000)
    adapter = GlobalUsageBillingAdapter(commerce)
    assert adapter.reserve_usage(user_id="synthetic", usage_id="ordinary", usage_kind="answer").status == "reserved"
    assert adapter.reserve_usage(user_id="synthetic", usage_id="web", usage_kind="web_answer").status == "insufficient_balance"
    commerce.grant_purchase(user_id="synthetic", offer_code="global-pro-weekly", source_kind="test", source_id="purchase", starts_at_ms=NOW-1)
    record = adapter.reserve_usage(user_id="synthetic", usage_id="web-eligible", usage_kind="web_answer")
    assert record.status == "reserved" and record.points_reserved == 0
    assert adapter.settle_usage(usage_id="web-eligible").status == "settled"
    with pytest.raises(ValueError):
        adapter.reserve_usage(user_id="different-owner", usage_id="web-eligible", usage_kind="web_answer")
    with pytest.raises(ValueError):
        adapter.reserve_usage(user_id="synthetic", usage_id="web-eligible", usage_kind="answer")


def test_global_mock_cannot_instantiate_on_cn():
    from app.services.global_mock_interview_repository import GlobalMockInterviewRepository
    with pytest.raises(RuntimeError, match="Global edition"):
        GlobalMockInterviewRepository(Settings(_env_file=None, product_edition="cn"))
