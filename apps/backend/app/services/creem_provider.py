from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Literal

import httpx

from app.core.config import Settings
from app.ports.international_commerce_provider import ProviderCheckout, ProviderProduct


class CreemConfigurationError(RuntimeError):
    pass


class CreemRequestError(RuntimeError):
    def __init__(self, safe_code: str, status_code: int | None = None) -> None:
        super().__init__(safe_code)
        self.safe_code = safe_code
        self.status_code = status_code


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: float | None = None


class CreemProvider:
    """Server-only Creem adapter. Secrets and provider payloads never cross the API boundary."""

    def __init__(self, settings: Settings, *, client: httpx.Client | None = None, mode: Literal["test", "live"] | None = None) -> None:
        self.settings = settings
        self.mode = mode or settings.global_commerce_provider_mode
        self.base_url = (settings.creem_test_base_url if self.mode == "test" else settings.creem_live_base_url).rstrip("/")
        self.api_key = settings.creem_test_api_key if self.mode == "test" else settings.creem_live_api_key
        self.webhook_secret = settings.creem_test_webhook_secret if self.mode == "test" else settings.creem_live_webhook_secret
        self._client = client or httpx.Client(timeout=httpx.Timeout(settings.creem_http_timeout_seconds), follow_redirects=False)
        self._circuit = _CircuitState()
        self._logger = logging.getLogger("offersteady.creem")

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.webhook_secret and self.settings.public_web_base_url)

    def create_checkout(self, *, product_id: str, request_id: str, success_url: str, customer_email: str | None = None) -> ProviderCheckout:
        payload: dict[str, object] = {"product_id": product_id, "request_id": request_id, "success_url": success_url}
        if customer_email:
            payload["customer"] = {"email": customer_email}
        # Creem documents request_id as a tracking reference, not as a provider-side
        # idempotency guarantee. Do not replay a checkout POST after an ambiguous
        # transport failure; the local order remains available for reconciliation.
        data = self._request("POST", "/v1/checkouts", json_body=payload, retry_safe=False)
        checkout_id = self._required_text(data, "id")
        checkout_url = self._required_text(data, "checkout_url")
        return ProviderCheckout(
            checkout_id=checkout_id,
            checkout_url=checkout_url,
            provider_order_id=self._nested_id(data.get("order")),
            provider_subscription_id=self._nested_id(data.get("subscription")),
            provider_customer_id=self._nested_id(data.get("customer")),
        )

    def retrieve_product(self, product_id: str) -> ProviderProduct:
        data = self._request("GET", "/v1/products", query={"product_id": product_id}, retry_safe=True)
        return self._product(data)

    def list_products(self, *, page_size: int = 100, max_pages: int = 5) -> list[ProviderProduct]:
        page_size = max(1, min(page_size, 100))
        max_pages = max(1, min(max_pages, 10))
        products: list[ProviderProduct] = []
        seen: set[str] = set()
        for page_number in range(1, max_pages + 1):
            data = self._request(
                "GET",
                "/v1/products/search",
                query={"page_number": str(page_number), "page_size": str(page_size)},
                retry_safe=True,
            )
            items = data.get("items")
            if not isinstance(items, list):
                raise CreemRequestError("provider_product_list_shape_invalid")
            for item in items:
                if not isinstance(item, dict):
                    raise CreemRequestError("provider_product_list_shape_invalid")
                product = self._product(item)
                if product.product_id not in seen:
                    products.append(product)
                    seen.add(product.product_id)
            pagination = data.get("pagination")
            next_page = pagination.get("next_page") if isinstance(pagination, dict) else None
            if not next_page or not items:
                break
        return products

    def _product(self, data: dict[str, Any]) -> ProviderProduct:
        raw_price = data.get("price")
        if isinstance(raw_price, dict):
            # Keep compatibility with the earlier test API response shape.
            amount = raw_price.get("amount")
            currency = raw_price.get("currency") or data.get("currency")
        else:
            amount = raw_price
            currency = data.get("currency")
        billing_type = data.get("billing_type") or data.get("type")
        product_id = data.get("id")
        if not isinstance(amount, int) or not isinstance(currency, str) or not isinstance(billing_type, str):
            raise CreemRequestError("provider_product_shape_invalid")
        if not isinstance(product_id, str) or not product_id:
            raise CreemRequestError("provider_product_shape_invalid")
        normalized_billing_type = billing_type.lower().replace("-", "_")
        if normalized_billing_type in {"recurring", "subscription"}:
            mode = "recurring"
        elif normalized_billing_type in {"onetime", "one_time"}:
            mode = "one_time"
        else:
            raise CreemRequestError("provider_product_shape_invalid")
        provider_mode = data.get("mode")
        if provider_mode is not None and provider_mode not in {"test", "live"}:
            raise CreemRequestError("provider_product_shape_invalid")
        name = data.get("name")
        status = data.get("status")
        billing_period = data.get("billing_period")
        return ProviderProduct(
            product_id,
            amount,
            currency.upper(),
            mode,
            name if isinstance(name, str) else product_id,
            billing_period if isinstance(billing_period, str) else None,
            status.lower() if isinstance(status, str) else "active",
            provider_mode or self.mode,
        )

    def retrieve_checkout(self, checkout_id: str) -> dict[str, object]:
        return self._request("GET", "/v1/checkouts", query={"checkout_id": checkout_id}, retry_safe=True)

    def create_customer_portal(self, customer_id: str) -> str:
        data = self._request("POST", "/v1/customers/billing", json_body={"customer_id": customer_id}, retry_safe=True)
        return self._required_text(data, "customer_portal_link")

    def retrieve_order(self, order_id: str) -> dict[str, object]:
        return self._request("GET", "/v1/orders", query={"order_id": order_id}, retry_safe=True)

    def retrieve_subscription(self, subscription_id: str) -> dict[str, object]:
        return self._request("GET", "/v1/subscriptions", query={"subscription_id": subscription_id}, retry_safe=True)

    def cancel_subscription(self, subscription_id: str) -> dict[str, object]:
        return self._request("POST", f"/v1/subscriptions/{subscription_id}/cancel", json_body={}, retry_safe=True)

    def refund_order(self, order_id: str, *, amount_cents: int | None = None) -> dict[str, object]:
        body: dict[str, object] = {"order_id": order_id}
        if amount_cents is not None:
            body["amount"] = amount_cents
        return self._request("POST", "/v1/refunds", json_body=body, retry_safe=False)

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> dict[str, Any]:
        if not self.webhook_secret:
            raise CreemConfigurationError("Creem webhook secret is not configured")
        if not signature:
            raise CreemRequestError("webhook_signature_missing")
        expected = hmac.new(self.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        normalized = signature.removeprefix("sha256=").strip()
        if not hmac.compare_digest(expected, normalized):
            raise CreemRequestError("webhook_signature_invalid")
        try:
            payload = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CreemRequestError("webhook_payload_invalid") from exc
        if not isinstance(payload, dict):
            raise CreemRequestError("webhook_payload_invalid")
        return payload

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, object] | None = None,
        query: dict[str, str] | None = None,
        retry_safe: bool,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise CreemConfigurationError(f"Creem {self.mode} API key is not configured")
        if self._circuit.opened_at is not None and monotonic() - self._circuit.opened_at < 15:
            raise CreemRequestError("provider_circuit_open")
        attempts = max(1, self.settings.creem_http_retry_attempts if retry_safe else 1)
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = self._client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
                    params=query,
                    json=json_body,
                )
                if response.status_code >= 500 and attempt + 1 < attempts:
                    continue
                if response.status_code >= 400:
                    raise CreemRequestError("provider_request_rejected", response.status_code)
                data = response.json()
                if not isinstance(data, dict):
                    raise CreemRequestError("provider_response_invalid", response.status_code)
                self._circuit = _CircuitState()
                return data
            except (httpx.TimeoutException, httpx.TransportError, ValueError, CreemRequestError) as exc:
                last_error = exc
                if isinstance(exc, CreemRequestError) and exc.status_code is not None and exc.status_code < 500:
                    raise
        self._circuit.failures += 1
        if self._circuit.failures >= 3:
            self._circuit.opened_at = monotonic()
        self._logger.warning("creem_request_failed", extra={"mode": self.mode, "path": path, "attempts": attempts, "error_type": type(last_error).__name__})
        raise CreemRequestError("provider_temporarily_unavailable") from last_error

    @staticmethod
    def _required_text(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise CreemRequestError("provider_response_invalid")
        return value

    @staticmethod
    def _nested_id(value: object) -> str | None:
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            return value["id"]
        return value if isinstance(value, str) else None
