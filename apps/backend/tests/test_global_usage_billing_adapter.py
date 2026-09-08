from time import time

from app.core.config import Settings
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_usage_billing_adapter import GlobalUsageBillingAdapter


def adapter_for(user_id: str, offer_code: str | None = None):
    repository = InMemoryGlobalCommerceRepository()
    commerce = GlobalCommerceService(Settings(product_edition="global"), repository)
    if offer_code:
        commerce.grant_purchase(user_id=user_id, offer_code=offer_code, source_kind="order", source_id=f"order:{user_id}", starts_at_ms=int(time() * 1000))
    return GlobalUsageBillingAdapter(commerce), commerce


def test_realtime_minutes_and_screenshot_calls_use_global_quotas() -> None:
    adapter, commerce = adapter_for("free-user")
    minute = adapter.reserve_usage(user_id="free-user", usage_id="minute-1", usage_kind="realtime_minute")
    assert minute.status == "reserved"
    adapter.settle_usage(usage_id="minute-1")
    screenshot = adapter.reserve_usage(user_id="free-user", usage_id="screen-1", usage_kind="screenshot_answer")
    adapter.release_usage(usage_id="screen-1")
    assert commerce.state("free-user")["copilot"] == {"unlimited": False, "remaining": 14}
    assert commerce.state("free-user")["screenAssist"] == {"unlimited": False, "remaining": 3}


def test_interview_pass_enables_written_exam_but_not_knowledge_base() -> None:
    adapter, commerce = adapter_for("pass-user", "global-interview-pass")
    assert adapter.reserve_usage(user_id="pass-user", usage_id="written-1", usage_kind="written_exam_entry").status == "reserved"
    assert commerce.state("pass-user")["features"]["knowledgeBase"] is False


def test_free_account_cannot_enter_written_exam() -> None:
    adapter, _ = adapter_for("free-user")
    assert adapter.reserve_usage(user_id="free-user", usage_id="written-1", usage_kind="written_exam_entry").status == "insufficient_balance"


def test_pro_knowledge_index_is_authorized_without_domestic_points() -> None:
    adapter, _ = adapter_for("pro-user", "global-pro-weekly")
    quote = adapter.quote_knowledge_index(user_id="pro-user", document_version_id="doc-v1", token_estimate=9_000, idempotency_key="doc-v1")
    assert quote.points_required == 0
    reservation = adapter.reserve_knowledge_index_for_quote(user_id="pro-user", quote_id=quote.quote_id, document_version_id="doc-v1")
    assert reservation.status == "reserved"
    assert reservation.billing_source == "global_entitlement"
    assert adapter.settle_knowledge_index_for_document(user_id="pro-user", document_version_id="doc-v1").status == "settled"
