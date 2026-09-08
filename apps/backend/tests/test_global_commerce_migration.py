from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_global_commerce_migration_is_isolated_and_idempotent() -> None:
    sql = (REPO_ROOT / "apps/backend/migrations/versions/0040_global_creem_commerce.sql").read_text()
    assert sql.count("CREATE TABLE IF NOT EXISTS global_commerce_") == 10
    assert "ON CONFLICT (offer_code, plan_version) DO NOTHING" in sql
    assert "PRIMARY KEY (user_id, grant_kind)" in sql
    assert "PRIMARY KEY (mode, provider_event_id)" in sql
    assert "billing_catalog_products" not in sql
    assert "billing_wallets" not in sql
    assert "payment_provider_configs" not in sql


def test_global_creem_admin_configuration_migration_is_additive_and_secret_safe() -> None:
    sql = (REPO_ROOT / "apps/backend/migrations/versions/0043_global_creem_admin_configuration.sql").read_text()
    assert "ADD COLUMN IF NOT EXISTS credential_ciphertext" in sql
    assert "ADD COLUMN IF NOT EXISTS connection_checked_at_ms" in sql
    assert "api_key TEXT" not in sql
    assert "webhook_secret TEXT" not in sql


def test_global_catalogue_v2_preserves_history_and_invalidates_provider_readiness() -> None:
    sql = (REPO_ROOT / "apps/backend/migrations/versions/0045_global_commerce_catalog_v2.sql").read_text()
    assert "'Interview Day Pass'" in sql
    assert "'one_time', 1, 180" in sql
    assert "'USD', 4999" in sql
    assert "'USD', 9999" in sql
    assert "'USD', 19999" in sql
    assert "plan_version = 2" in sql
    assert "SET status = 'retired'" in sql
    assert "SET enabled = FALSE" in sql
    assert "validation_status = 'draft'" in sql
    assert "DELETE FROM global_commerce" not in sql

    repository = (REPO_ROOT / "apps/backend/app/services/postgres_global_commerce_repository.py").read_text()
    assert 'migrations/versions/0045_global_commerce_catalog_v2.sql' in repository
    admin_repository = (REPO_ROOT / "apps/backend/app/services/admin_repository.py").read_text()
    assert 'if self.settings.product_edition == "global"' in admin_repository
    assert 'migrations/versions/0045_global_commerce_catalog_v2.sql' in admin_repository
