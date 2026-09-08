from fastapi.testclient import TestClient

from app.core.config import Settings
from app.deps import global_commerce_service, settings_dependency
from app.main import create_app
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService


def test_catalogue_is_hidden_in_chinese_edition() -> None:
    application = create_app()
    settings = Settings(product_edition="cn")
    application.dependency_overrides[settings_dependency] = lambda: settings
    with TestClient(application) as client:
        assert client.get("/api/v1/global-commerce/catalogue").status_code == 404


def test_global_catalogue_returns_server_owned_prices() -> None:
    application = create_app()
    settings = Settings(product_edition="global")
    service = GlobalCommerceService(settings, InMemoryGlobalCommerceRepository())
    application.dependency_overrides[settings_dependency] = lambda: settings
    application.dependency_overrides[global_commerce_service] = lambda: service
    with TestClient(application) as client:
        response = client.get("/api/v1/global-commerce/catalogue")
    assert response.status_code == 200
    plans = response.json()["data"]["plans"]
    assert [plan["priceCents"] for plan in plans] == [0, 999, 4999, 9999, 19999]
    assert plans[1]["displayName"] == "Interview Day Pass"
    assert plans[1]["durationDays"] == 1
    assert plans[3]["billingMode"] == "recurring"
