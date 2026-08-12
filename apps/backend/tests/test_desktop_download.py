from fastapi.testclient import TestClient

from app.deps import storage_port
from app.main import app
from app.modules import web as web_module


class SignedReleaseStorage:
    def create_signed_download_url(self, *, object_key: str, expires_seconds: int) -> str:
        assert object_key.startswith("desktop-releases/")
        assert expires_seconds == 600
        return "https://example.invalid/signed-desktop-release"


def test_web_state_exposes_operator_published_desktop_download_actions() -> None:
    with TestClient(app) as client:
        state = client.get("/api/v1/web/state").json()["data"]
    entries = state["releaseManifest"]["entries"]
    assert {(entry["platform"], entry["architecture"]) for entry in entries} == {
        ("macos", "arm64"),
        ("macos", "x64"),
        ("windows", "x64"),
    }
    assert all(entry["distributionStatus"] == "published" for entry in entries)
    assert all(entry["downloadUrl"].startswith("/api/v1/web/downloads/desktop/") for entry in entries)
    assert all("objectKey" not in entry for entry in entries)


def test_desktop_download_redirects_to_short_lived_signed_oss_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(web_module, "_desktop_release_dir", lambda: tmp_path)
    monkeypatch.setattr(web_module, "_published_desktop_manifest", lambda: {
        "version": 1,
        "generatedAtMs": 1,
        "entries": [{
            "id": "mac-arm64-verified",
            "platform": "macos",
            "architecture": "arm64",
            "fileName": "OfferSteady-Companion-1.0.0-macOS-arm64.dmg",
            "sha256": "a" * 64,
            "signingStatus": "verified",
            "notarized": True,
            "objectKey": "desktop-releases/macos/arm64/1.0.0/OfferSteady-Companion-1.0.0-macOS-arm64.dmg",
        }],
    })
    app.dependency_overrides[storage_port] = lambda: SignedReleaseStorage()
    try:
        with TestClient(app) as client:
            state = client.get("/api/v1/web/state").json()["data"]
            arm_entry = next(
                entry for entry in state["releaseManifest"]["entries"]
                if entry["platform"] == "macos" and entry["architecture"] == "arm64"
            )
            response = client.get(
                arm_entry["downloadUrl"],
                follow_redirects=False,
            )
    finally:
        app.dependency_overrides.pop(storage_port, None)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.invalid/signed-desktop-release"


def test_direct_unverified_desktop_download_is_not_accessible(monkeypatch, tmp_path) -> None:
    filename = "OfferSteady-Companion-0.1.5-macOS-arm64.zip"
    (tmp_path / filename).write_bytes(b"synthetic-unverified-artifact")
    monkeypatch.setattr(web_module, "_desktop_release_dir", lambda: tmp_path)
    monkeypatch.setattr(web_module, "_published_desktop_manifest", lambda: {
        "version": 1,
        "generatedAtMs": 1,
        "entries": [{
            "id": "mac-arm64-internal",
            "platform": "macos",
            "architecture": "arm64",
            "fileName": filename,
            "sha256": "a" * 64,
            "signingStatus": "local-development",
            "distributionStatus": "internal",
            "notarized": False,
        }],
    })
    with TestClient(app) as client:
        response = client.get(f"/api/v1/web/downloads/desktop/{filename}")
    assert response.status_code == 404


def test_operator_published_desktop_download_is_accessible_without_claiming_verified_signing(monkeypatch, tmp_path) -> None:
    filename = "OfferSteady-Companion-0.1.5-Windows-x64.exe"
    monkeypatch.setattr(web_module, "_desktop_release_dir", lambda: tmp_path)
    monkeypatch.setattr(web_module, "_published_desktop_manifest", lambda: {
        "version": 1,
        "generatedAtMs": 1,
        "entries": [{
            "id": "windows-x64-operator-published",
            "platform": "windows",
            "architecture": "x64",
            "fileName": filename,
            "sha256": "b" * 64,
            "signingStatus": "local-development",
            "distributionStatus": "published",
            "notarized": False,
            "objectKey": f"desktop-releases/windows/x64/0.1.5/{filename}",
        }],
    })
    app.dependency_overrides[storage_port] = lambda: SignedReleaseStorage()
    try:
        with TestClient(app) as client:
            state = client.get("/api/v1/web/state").json()["data"]
            entry = state["releaseManifest"]["entries"][0]
            response = client.get(entry["downloadUrl"], follow_redirects=False)
    finally:
        app.dependency_overrides.pop(storage_port, None)
    assert entry["signingStatus"] == "local-development"
    assert entry["distributionStatus"] == "published"
    assert response.status_code == 307
