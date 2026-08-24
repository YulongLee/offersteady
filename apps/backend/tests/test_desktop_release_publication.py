from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "publish_desktop_release",
    ROOT / "scripts" / "publish-desktop-release.py",
)
assert SPEC is not None and SPEC.loader is not None
publish_desktop_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publish_desktop_release)


def _metadata(tmp_path: Path, *, suffix: str = ".dmg", signing_status: str = "verified", notarized: bool = True) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    artifact = tmp_path / f"OfferSteady-Companion-0.1.16-macOS-arm64{suffix}"
    artifact.write_bytes(b"synthetic release artifact")
    payload = {
        "platform": "macos",
        "architecture": "arm64",
        "displayName": "macOS Apple Silicon",
        "version": "0.1.16",
        "minimumOs": "macOS 14.2+",
        "artifactPath": str(artifact),
        "fileSizeBytes": artifact.stat().st_size,
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "signingStatus": signing_status,
        "notarized": notarized,
        "developmentOnly": signing_status != "verified",
        "protocolVersion": "2.0",
        "capabilities": {"microphone": True, "systemAudio": True, "screenCapture": True},
    }
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_macos_production_rejects_development_zip_before_upload(tmp_path: Path) -> None:
    metadata_path = _metadata(tmp_path, suffix=".zip", signing_status="local-development", notarized=False)

    with pytest.raises(SystemExit, match="requires a verified DMG"):
        publish_desktop_release._prepare_release(metadata_path, is_production=True, verify_platform=False)


def test_macos_production_accepts_verified_notarized_dmg_metadata(tmp_path: Path) -> None:
    metadata_path = _metadata(tmp_path)

    metadata, artifact = publish_desktop_release._prepare_release(
        metadata_path,
        is_production=True,
        verify_platform=False,
    )

    assert artifact.suffix == ".dmg"
    assert metadata["signingStatus"] == "verified"
    assert publish_desktop_release._artifact_content_type(artifact) == "application/x-apple-diskimage"


def test_manifest_replaces_both_mac_entries_and_preserves_windows(tmp_path: Path) -> None:
    arm_metadata_path = _metadata(tmp_path / "arm64")
    x64_dir = tmp_path / "x64"
    x64_dir.mkdir(parents=True, exist_ok=True)
    x64_metadata_path = _metadata(x64_dir)
    x64_payload = json.loads(x64_metadata_path.read_text(encoding="utf-8"))
    x64_payload["architecture"] = "x64"
    x64_payload["displayName"] = "macOS Intel"
    x64_artifact = x64_dir / "OfferSteady-Companion-0.1.16-macOS-x64.dmg"
    Path(x64_payload["artifactPath"]).rename(x64_artifact)
    x64_payload["artifactPath"] = str(x64_artifact)
    x64_payload["fileSizeBytes"] = x64_artifact.stat().st_size
    x64_payload["sha256"] = hashlib.sha256(x64_artifact.read_bytes()).hexdigest()
    x64_metadata_path.write_text(json.dumps(x64_payload), encoding="utf-8")

    arm = publish_desktop_release._prepare_release(arm_metadata_path, is_production=True, verify_platform=False)
    x64 = publish_desktop_release._prepare_release(x64_metadata_path, is_production=True, verify_platform=False)
    windows = {"platform": "windows", "architecture": "x64", "fileName": "existing.exe"}
    manifest = publish_desktop_release._build_manifest(
        {"entries": [
            {"platform": "macos", "architecture": "arm64", "fileName": "old-arm.zip"},
            {"platform": "macos", "architecture": "x64", "fileName": "old-intel.zip"},
            windows,
        ]},
        [
            (arm[0], arm[1], "desktop-releases/macos/arm64/0.1.16/arm.dmg"),
            (x64[0], x64[1], "desktop-releases/macos/x64/0.1.16/x64.dmg"),
        ],
        published_at_ms=123,
        is_production=True,
    )

    entries = manifest["entries"]
    assert windows in entries
    mac_entries = [entry for entry in entries if entry["platform"] == "macos"]
    assert {entry["architecture"] for entry in mac_entries} == {"arm64", "x64"}
    assert all(entry["fileName"].endswith(".dmg") for entry in mac_entries)
    assert all(entry["signingStatus"] == "verified" and entry["notarized"] for entry in mac_entries)
