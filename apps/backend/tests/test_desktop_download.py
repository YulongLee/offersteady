from fastapi.testclient import TestClient

from app.deps import storage_port
from app.main import app
from app.modules import web as web_module


class SignedReleaseStorage:
    def create_signed_download_url(self, *, object_key: str, expires_seconds: int) -> str:
        assert object_key.startswith("desktop-releases/macos/arm64/")
        assert expires_seconds == 600
        return "https://example.invalid/signed-desktop-release"


def test_web_state_exposes_same_origin_mac_arm_download() -> None:
    with TestClient(app) as client:
        state = client.get("/api/v1/web/state").json()["data"]
    entries = state["releaseManifest"]["entries"]
    assert len(entries) == 1
    assert entries[0]["architecture"] == "arm64"
    assert entries[0]["downloadUrl"].startswith("/api/v1/web/downloads/desktop/")
    assert "objectKey" not in entries[0]


def test_desktop_download_redirects_to_short_lived_signed_oss_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(web_module, "_desktop_release_dir", lambda: tmp_path)
    app.dependency_overrides[storage_port] = lambda: SignedReleaseStorage()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/web/downloads/desktop/OfferSteady-Companion-0.1.0-macOS-arm64.zip",
                follow_redirects=False,
            )
    finally:
        app.dependency_overrides.pop(storage_port, None)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.invalid/signed-desktop-release"
