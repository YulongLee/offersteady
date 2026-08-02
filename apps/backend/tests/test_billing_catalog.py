from app.services.billing_service import BillingService


def test_fallback_catalog_matches_approved_fixed_benefit_tiers() -> None:
    catalog = BillingService().catalog()
    assert [item.duration_days for item in catalog if item.kind == "time_pass"] == [1, 3, 7, 15, 30]
    assert [item.points for item in catalog if item.kind == "points_pack"] == [1000, 3000, 10000, 30000, 66666]
    assert all(item.catalog_version == 5 for item in catalog)
    assert all(item.price_cents > 0 and item.published for item in catalog)
