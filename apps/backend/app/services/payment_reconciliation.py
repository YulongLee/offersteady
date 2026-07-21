from __future__ import annotations

from json import dumps

from app.core.config import get_settings
from app.services.billing_service import BillingService
from app.services.postgres_billing_repository import PostgresBillingRepository


def main() -> None:
    settings = get_settings()
    repository = PostgresBillingRepository(settings)
    report = BillingService(settings, billing_repository=repository).reconciliation_summary()
    print(dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

