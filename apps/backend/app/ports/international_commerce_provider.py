from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderCheckout:
    checkout_id: str
    checkout_url: str
    provider_order_id: str | None = None
    provider_subscription_id: str | None = None
    provider_customer_id: str | None = None


@dataclass(frozen=True)
class ProviderProduct:
    product_id: str
    amount_cents: int
    currency: str
    billing_mode: str
    name: str = ""
    billing_period: str | None = None
    status: str = "active"
    mode: str | None = None


class InternationalCommerceProvider(Protocol):
    def create_checkout(self, *, product_id: str, request_id: str, success_url: str, customer_email: str | None = None) -> ProviderCheckout: ...
    def retrieve_checkout(self, checkout_id: str) -> dict[str, object]: ...
    def retrieve_product(self, product_id: str) -> ProviderProduct: ...
    def list_products(self, *, page_size: int = 100, max_pages: int = 5) -> list[ProviderProduct]: ...
    def create_customer_portal(self, customer_id: str) -> str: ...
    def retrieve_order(self, order_id: str) -> dict[str, object]: ...
    def retrieve_subscription(self, subscription_id: str) -> dict[str, object]: ...
    def cancel_subscription(self, subscription_id: str) -> dict[str, object]: ...
    def refund_order(self, order_id: str, *, amount_cents: int | None = None) -> dict[str, object]: ...
