from __future__ import annotations

import psycopg
import pytest

from app import deps
from app.core.config import Settings


def failing_repository(_settings: Settings):
    raise psycopg.OperationalError("synthetic database outage")


def test_authentication_does_not_fallback_to_memory_when_database_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(environment="development", database_url="postgresql://synthetic")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    monkeypatch.setattr(deps, "PostgresAuthenticationRepository", failing_repository)
    deps.authentication_repository.cache_clear()
    try:
        with pytest.raises(psycopg.OperationalError, match="synthetic database outage"):
            deps.authentication_repository()
    finally:
        deps.authentication_repository.cache_clear()


def test_billing_does_not_fallback_to_memory_when_database_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(environment="development", database_url="postgresql://synthetic")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(deps, "get_settings", lambda: settings)
    monkeypatch.setattr(deps, "PostgresBillingRepository", failing_repository)
    deps.billing_service.cache_clear()
    try:
        with pytest.raises(psycopg.OperationalError, match="synthetic database outage"):
            deps.billing_service()
    finally:
        deps.billing_service.cache_clear()
