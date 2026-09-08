from __future__ import annotations

import pytest
from pydantic import ValidationError
from types import SimpleNamespace

from app.core.config import Settings
from app.modules import web


def test_product_edition_defaults_to_chinese() -> None:
    settings = Settings(_env_file=None, environment="test")
    assert settings.product_edition == "cn"


def test_global_product_edition_requires_explicit_configuration() -> None:
    settings = Settings(_env_file=None, environment="test", product_edition="global")
    assert settings.product_edition == "global"


def test_unknown_product_edition_fails_closed() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="test", product_edition="international")


def test_global_product_edition_uses_isolated_desktop_release_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web, "get_settings", lambda: SimpleNamespace(product_edition="global"))

    assert web._published_desktop_manifest_path().name == "global_desktop_release_manifest.json"
