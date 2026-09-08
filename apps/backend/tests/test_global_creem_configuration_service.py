from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_creem_configuration_service import GlobalCreemConfigurationService


def service(repository: InMemoryGlobalCommerceRepository | None = None) -> tuple[GlobalCreemConfigurationService, InMemoryGlobalCommerceRepository]:
    repo = repository or InMemoryGlobalCommerceRepository()
    settings = Settings(
        product_edition="global",
        admin_encryption_key="synthetic-admin-encryption-key",
        creem_test_api_key="creem_test_environment_fallback",
        creem_test_webhook_secret="environment-webhook-secret",
    )
    return GlobalCreemConfigurationService(settings, repo), repo


def test_saved_credentials_are_encrypted_masked_and_disable_only_test() -> None:
    configuration, repository = service()
    repository.set_provider_enabled(mode="test", enabled=True, validation_status="ready", validation_errors=[], updated_by_user_id="admin", updated_at_ms=1)
    repository.set_provider_enabled(mode="live", enabled=True, validation_status="ready", validation_errors=[], updated_by_user_id="admin", updated_at_ms=1)

    configuration.save(
        mode="test",
        api_key="creem_test_synthetic_saved_key",
        webhook_secret="synthetic-saved-webhook-secret",
        user_id="admin",
    )

    test_row = repository.provider_config("test")
    assert test_row["enabled"] is False
    assert repository.provider_config("live")["enabled"] is True
    ciphertext = str(test_row["credential_ciphertext"])
    assert "creem_test_synthetic_saved_key" not in ciphertext
    assert "synthetic-saved-webhook-secret" not in ciphertext
    masked = configuration.masked("test")
    assert masked["apiKey"]["configured"] is True  # type: ignore[index]
    assert masked["webhookSecret"]["configured"] is True  # type: ignore[index]
    assert "saved_key" not in str(masked)


def test_partial_replacement_preserves_existing_secret_and_live_is_isolated() -> None:
    configuration, _ = service()
    configuration.save(mode="test", api_key="creem_test_first_key", webhook_secret="first-webhook-secret", user_id="admin")
    configuration.save(mode="test", api_key="creem_test_second_key", webhook_secret=None, user_id="admin")

    test_credentials = configuration.effective_credentials("test")
    live_credentials = configuration.effective_credentials("live")
    assert test_credentials.api_key == "creem_test_second_key"
    assert test_credentials.webhook_secret == "first-webhook-secret"
    assert live_credentials.api_key is None
    assert live_credentials.webhook_secret is None


def test_test_mode_rejects_live_key_without_persisting_it() -> None:
    configuration, repository = service()
    with pytest.raises(ValueError, match="Test 环境"):
        configuration.save(mode="test", api_key="creem_live_wrong_key", webhook_secret="synthetic-webhook-secret", user_id="admin")
    assert repository.provider_config("test")["credential_ciphertext"] is None

