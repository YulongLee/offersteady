from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.config import Settings
from app.ports.global_commerce import FairUseDecision, GlobalPlan
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService, GlobalCommerceUnavailable, GlobalEntitlementDenied, GlobalFairUseRestricted


def service() -> tuple[GlobalCommerceService, InMemoryGlobalCommerceRepository]:
    repository = InMemoryGlobalCommerceRepository()
    return GlobalCommerceService(Settings(product_edition="global"), repository), repository


def test_chinese_edition_cannot_read_global_commerce() -> None:
    global_service = GlobalCommerceService(Settings(product_edition="cn"), InMemoryGlobalCommerceRepository())
    with pytest.raises(GlobalCommerceUnavailable):
        global_service.catalogue()


def test_catalogue_has_approved_order_prices_and_billing_modes() -> None:
    global_service, _ = service()
    plans = global_service.catalogue()
    assert [(plan.offer_code, plan.price_cents, plan.billing_mode) for plan in plans] == [
        ("global-free", 0, "free"),
        ("global-interview-pass", 999, "one_time"),
        ("global-pro-weekly", 4999, "one_time"),
        ("global-pro-monthly", 9999, "recurring"),
        ("global-job-hunt", 19999, "one_time"),
    ]

    day_pass, weekly, monthly, job_hunt = plans[1:]
    assert (day_pass.duration_days, day_pass.copilot_minutes, day_pass.screen_assist_uses) == (1, 180, None)
    assert day_pass.resume_jd_enabled is True
    assert day_pass.knowledge_tokens == 0
    for plan, days in ((weekly, 7), (monthly, 30), (job_hunt, 90)):
        assert plan.duration_days == days
        assert plan.copilot_minutes is None and plan.screen_assist_uses is None
        assert plan.resume_jd_enabled and plan.knowledge_base_enabled and plan.written_exam_enabled and plan.full_product_enabled
    assert [plan.knowledge_tokens for plan in (weekly, monthly, job_hunt)] == [50_000, 200_000, 1_000_000]


def test_free_is_once_and_usage_reservations_are_idempotent() -> None:
    global_service, _ = service()
    first = global_service.ensure_free_grant("user-1", now_ms=1_000)
    assert global_service.ensure_free_grant("user-1", now_ms=2_000).entitlement_id == first.entitlement_id

    reserved = global_service.reserve(user_id="user-1", kind="screen_assist", amount=1, operation_id="screen-op", now_ms=3_000)
    assert global_service.reserve(user_id="user-1", kind="screen_assist", amount=1, operation_id="screen-op", now_ms=3_001) == reserved
    global_service.settle(operation_id="screen-op")
    assert global_service.state("user-1", now_ms=4_000)["screenAssist"] == {"unlimited": False, "remaining": 2}


def test_free_exhaustion_release_and_paid_unlimited() -> None:
    global_service, _ = service()
    for index in range(3):
        operation_id = f"free-screen-{index}"
        global_service.reserve(user_id="user-2", kind="screen_assist", amount=1, operation_id=operation_id, now_ms=1_000)
        global_service.settle(operation_id=operation_id)
    with pytest.raises(GlobalEntitlementDenied):
        global_service.reserve(user_id="user-2", kind="screen_assist", amount=1, operation_id="exhausted", now_ms=1_000)

    temporary = global_service.reserve(user_id="user-2", kind="copilot_minute", amount=10, operation_id="release-me", now_ms=1_000)
    global_service.release(operation_id=temporary.operation_id)
    assert global_service.state("user-2", now_ms=1_001)["copilot"] == {"unlimited": False, "remaining": 15}

    global_service.grant_purchase(user_id="user-2", offer_code="global-pro-weekly", source_kind="order", source_id="order-paid", starts_at_ms=1_000)
    assert global_service.state("user-2", now_ms=2_000)["screenAssist"] == {"unlimited": True, "remaining": None}
    assert global_service.state("user-2", now_ms=2_000)["features"] == {"resumeJd": True, "knowledgeBase": True, "writtenExam": True}
    paid_reservation = global_service.reserve(user_id="user-2", kind="copilot_minute", amount=1, operation_id="paid-minute", now_ms=2_000)
    assert next(item for item in global_service.active_entitlements("user-2", 2_000) if item.entitlement_id == paid_reservation.entitlement_id).offer_code == "global-pro-weekly"


def test_purchased_entitlement_keeps_immutable_plan_snapshot_after_new_version() -> None:
    global_service, repository = service()
    purchased = global_service.grant_purchase(user_id="user-3", offer_code="global-interview-pass", source_kind="order", source_id="order-v2", starts_at_ms=10_000)
    old = repository.plan("global-interview-pass")
    assert old is not None
    repository.save_draft(replace(old, version=3, status="draft", copilot_minutes=240, created_at_ms=20_000))
    repository.publish("global-interview-pass", 3)

    assert purchased.plan_version == 2
    assert purchased.copilot_minutes_granted == 180
    assert repository.plan("global-interview-pass").version == 3


def test_one_time_passes_stack_without_replacing_existing_usage() -> None:
    global_service, _ = service()
    global_service.grant_purchase(user_id="user-stack", offer_code="global-interview-pass", source_kind="order", source_id="order-a", starts_at_ms=1_000)
    global_service.grant_purchase(user_id="user-stack", offer_code="global-interview-pass", source_kind="order", source_id="order-b", starts_at_ms=2_000)
    assert global_service.state("user-stack", now_ms=3_000)["copilot"] == {"unlimited": False, "remaining": 375}


def test_draft_version_uniqueness_and_publication_rules() -> None:
    _, repository = service()
    active = repository.plan("global-job-hunt")
    assert active is not None
    draft = replace(active, version=3, status="draft", price_cents=20999)
    repository.save_draft(draft)
    with pytest.raises(ValueError):
        repository.save_draft(draft)
    published = repository.publish("global-job-hunt", 3)
    assert published.status == "active"
    assert repository.plan("global-job-hunt", 2).status == "retired"


def test_fair_use_restriction_blocks_only_future_interviews() -> None:
    global_service, repository = service()
    repository.save_fair_use_decision(FairUseDecision("decision-1", "user-review", "restricted", "parallel_automation", {"parallelSessions": 4}, True, 1_000, None))
    global_service.authorize_interview(user_id="user-review", interview_already_active=True, now_ms=2_000)
    with pytest.raises(GlobalFairUseRestricted):
        global_service.authorize_interview(user_id="user-review", interview_already_active=False, now_ms=2_000)
    repository.save_fair_use_decision(replace(repository.active_fair_use_decision("user-review", 2_000), status="cleared", restrict_new_sessions=False))
    global_service.authorize_interview(user_id="user-review", interview_already_active=False, now_ms=2_001)
