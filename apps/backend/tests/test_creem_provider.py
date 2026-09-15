from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest

from app.core.config import Settings
from app.services.creem_provider import CreemConfigurationError, CreemProvider, CreemRequestError


def configured_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "product_edition": "global",
        "creem_test_api_key": "creem_test_secret_value",
        "creem_test_webhook_secret": "webhook_test_secret_value",
        "creem_checkout_success_url": "https://offersteady.com/billing/return",
        "creem_http_retry_attempts": 2,
    }
    values.update(overrides)
    return Settings(**values)


def provider(handler, **settings: object) -> CreemProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return CreemProvider(configured_settings(**settings), client=client, mode="test")


def test_checkout_uses_server_key_product_and_internal_request_id() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "ch_123", "checkout_url": "https://checkout.creem.io/ch_123"})

    result = provider(handler).create_checkout(product_id="prod_server_owned", request_id="order_internal_1", success_url="https://offersteady.com/billing/return")
    assert result.checkout_id == "ch_123"
    assert captured == {
        "url": "https://test-api.creem.io/v1/checkouts",
        "api_key": "creem_test_secret_value",
        "body": {"product_id": "prod_server_owned", "request_id": "order_internal_1", "success_url": "https://offersteady.com/billing/return"},
    }


def test_webhook_signature_uses_exact_raw_body_and_constant_format() -> None:
    raw = b'{"id":"evt_1","eventType":"checkout.completed"}'
    signature = hmac.new(b"webhook_test_secret_value", raw, hashlib.sha256).hexdigest()
    assert provider(lambda _: httpx.Response(500)).verify_webhook(raw, signature)["id"] == "evt_1"
    with pytest.raises(CreemRequestError, match="webhook_signature_invalid"):
        provider(lambda _: httpx.Response(500)).verify_webhook(raw + b" ", signature)


def test_missing_secret_fails_closed() -> None:
    adapter = provider(lambda _: httpx.Response(200), creem_test_webhook_secret=None)
    with pytest.raises(CreemConfigurationError):
        adapter.verify_webhook(b"{}", "invalid")


def test_safe_request_retries_5xx_without_logging_or_returning_secret() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"message": "temporary"})
        return httpx.Response(200, json={"id": "prod_1", "price": {"amount": 999, "currency": "usd"}, "billing_type": "one_time"})

    product = provider(handler).retrieve_product("prod_1")
    assert attempts == 2
    assert (product.amount_cents, product.currency, product.billing_mode) == (999, "USD", "one_time")


def test_product_lookup_accepts_current_creem_shape_and_query_contract() -> None:
    captured_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"id": "prod_1", "price": 1999, "currency": "USD", "billing_type": "recurring"})

    product = provider(handler).retrieve_product("prod_1")
    assert captured_url == "https://test-api.creem.io/v1/products?product_id=prod_1"
    assert (product.product_id, product.amount_cents, product.currency, product.billing_mode) == ("prod_1", 1999, "USD", "recurring")


def test_product_catalogue_uses_search_endpoint_and_safe_metadata() -> None:
    captured_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={
            "items": [{"id": "prod_test_1", "name": "OfferSteady Pro Weekly", "mode": "test", "price": 1999, "currency": "USD", "billing_type": "onetime", "status": "active"}],
            "pagination": {"next_page": None},
        })

    products = provider(handler).list_products()
    assert captured_url == "https://test-api.creem.io/v1/products/search?page_number=1&page_size=100"
    assert len(products) == 1
    assert products[0].name == "OfferSteady Pro Weekly"
    assert products[0].mode == "test"
    assert products[0].status == "active"


def test_live_product_mode_prod_is_normalized() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={
        "items": [{"id": "prod_live_1", "name": "OfferSteady Pro", "mode": "prod", "price": 4999, "currency": "USD", "billing_type": "onetime", "status": "active"}],
        "pagination": {"next_page": None},
    })))
    settings = configured_settings(creem_live_api_key="creem_live_secret_value", creem_live_webhook_secret="webhook_live_secret_value")
    products = CreemProvider(settings, client=client, mode="live").list_products(max_pages=1)
    assert products[0].mode == "live"


def test_product_catalogue_rejects_invalid_response_shape() -> None:
    with pytest.raises(CreemRequestError, match="provider_product_list_shape_invalid"):
        provider(lambda _: httpx.Response(200, json={"items": "not-a-list"})).list_products()


def test_checkout_post_is_not_replayed_after_ambiguous_failure() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={"message": "temporary"})

    with pytest.raises(CreemRequestError):
        provider(handler).create_checkout(product_id="prod_1", request_id="gorder_1", success_url="https://offersteady.com/billing/return")
    assert attempts == 1


def test_checkout_lookup_uses_current_query_contract() -> None:
    captured_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(200, json={"id": "ch_1", "status": "completed"})

    assert provider(handler).retrieve_checkout("ch_1")["status"] == "completed"
    assert captured_url == "https://test-api.creem.io/v1/checkouts?checkout_id=ch_1"


def test_refund_is_not_automatically_retried() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={"message": "temporary"})

    with pytest.raises(CreemRequestError):
        provider(handler).refund_order("ord_1")
    assert attempts == 1
