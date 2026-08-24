#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from time import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.core.config import Settings  # noqa: E402


def _artifact_content_type(artifact: Path) -> str:
    suffix = artifact.suffix.lower()
    if suffix == ".dmg":
        return "application/x-apple-diskimage"
    if suffix == ".exe":
        return "application/vnd.microsoft.portable-executable"
    return "application/zip"


def _prepare_release(metadata_path: Path, *, is_production: bool, verify_platform: bool = True) -> tuple[dict[str, object], Path]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    artifact_value = metadata.get("artifactPath") or metadata.get("zipPath")
    if not isinstance(artifact_value, str) or not artifact_value:
        raise SystemExit(f"Desktop metadata has no artifact path: {metadata_path}")
    artifact = Path(artifact_value).resolve()
    if not artifact.is_file():
        raise SystemExit(f"Desktop artifact is missing: {artifact}")

    platform = str(metadata.get("platform", ""))
    architecture = str(metadata.get("architecture", ""))
    if platform not in {"macos", "windows"} or architecture not in {"arm64", "x64"}:
        raise SystemExit(f"Unsupported desktop release target: {platform}/{architecture}")

    actual_size = artifact.stat().st_size
    actual_sha256 = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if int(metadata.get("fileSizeBytes", -1)) != actual_size or metadata.get("sha256") != actual_sha256:
        raise SystemExit(f"Desktop artifact size or SHA-256 does not match metadata: {artifact}")

    if is_production and platform == "macos":
        if artifact.suffix.lower() != ".dmg":
            raise SystemExit("macOS production publication requires a verified DMG; ZIP artifacts are not allowed.")
        if metadata.get("signingStatus") != "verified" or metadata.get("notarized") is not True or metadata.get("developmentOnly") is not False:
            raise SystemExit("macOS production publication requires verified, notarized, non-development metadata.")
        if verify_platform:
            if sys.platform != "darwin":
                raise SystemExit("macOS production publication must run on macOS so Gatekeeper and stapler can be revalidated.")
            verification_commands = [
                ["codesign", "--verify", "--strict", "--verbose=2", str(artifact)],
                ["spctl", "--assess", "--type", "open", "--context", "context:primary-signature", "--verbose", str(artifact)],
                ["xcrun", "stapler", "validate", str(artifact)],
            ]
            for command in verification_commands:
                completed = subprocess.run(command, capture_output=True, text=True, check=False)
                if completed.returncode != 0:
                    output = f"{completed.stdout}\n{completed.stderr}".strip()
                    raise SystemExit(f"macOS production verification failed: {' '.join(command)}\n{output}")
    return metadata, artifact


def _build_manifest(existing_payload: dict[str, object], releases: list[tuple[dict[str, object], Path, str]], *, published_at_ms: int, is_production: bool) -> dict[str, object]:
    targets = {(str(metadata["platform"]), str(metadata["architecture"])) for metadata, _, _ in releases}
    existing_entries = [
        entry for entry in existing_payload.get("entries", [])
        if (str(entry.get("platform")), str(entry.get("architecture"))) not in targets
    ]
    new_entries: list[dict[str, object]] = []
    for metadata, artifact, object_key in releases:
        version = str(metadata["version"])
        platform = str(metadata["platform"])
        architecture = str(metadata["architecture"])
        version_suffix = version.replace(".", "")
        display_name = (
            "macOS Apple Silicon" if platform == "macos" and architecture == "arm64"
            else "macOS Intel" if platform == "macos"
            else "Windows 10/11 安装版"
        )
        new_entries.append({
            "id": f"{'mac' if platform == 'macos' else 'win'}-{architecture}-{version_suffix}",
            "platform": platform,
            "architecture": architecture,
            "displayName": display_name if is_production else metadata["displayName"],
            "version": version,
            "minimumOs": metadata["minimumOs"],
            "fileName": artifact.name,
            "fileSizeBytes": metadata["fileSizeBytes"],
            "sha256": metadata["sha256"],
            "signingStatus": metadata.get("signingStatus", "local-development"),
            "distributionStatus": "published" if is_production else "internal",
            "notarized": bool(metadata.get("notarized", False)),
            "publishedAtMs": published_at_ms,
            "protocolVersion": metadata["protocolVersion"],
            "captureRuntime": metadata.get("captureRuntime", "electron-single-owner"),
            "developmentOnly": not is_production,
            "objectKey": object_key,
            "capabilities": metadata["capabilities"],
        })
    return {"version": 1, "generatedAtMs": published_at_ms, "entries": [*existing_entries, *new_entries]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish an OfferSteady desktop artifact to OSS and update the backend release manifest.")
    parser.add_argument("--metadata", action="append", help="Metadata path; repeat to publish multiple targets atomically in one manifest update.")
    parser.add_argument("--channel", default="test")
    args = parser.parse_args()
    is_production = args.channel == "production"

    metadata_arguments = args.metadata or ["apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.json"]
    prepared = [_prepare_release((ROOT / item).resolve(), is_production=is_production) for item in metadata_arguments]
    target_keys = [(str(metadata["platform"]), str(metadata["architecture"])) for metadata, _ in prepared]
    if len(target_keys) != len(set(target_keys)):
        raise SystemExit("Each platform/architecture target may appear only once per publication.")

    settings = Settings()
    if not all((settings.oss_access_key_id, settings.oss_access_key_secret, settings.oss_endpoint, settings.oss_bucket)):
        raise SystemExit("Real OSS credentials are required in .env to publish a desktop release.")

    from oss2 import Auth, Bucket, resumable_upload

    endpoint = str(settings.oss_endpoint)
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"
    bucket = Bucket(Auth(settings.oss_access_key_id, settings.oss_access_key_secret), endpoint, settings.oss_bucket)
    uploaded: list[tuple[dict[str, object], Path, str]] = []
    for metadata, artifact in prepared:
        version = str(metadata["version"])
        platform = str(metadata["platform"])
        architecture = str(metadata["architecture"])
        object_key = f"desktop-releases/{platform}/{architecture}/{version}/{artifact.name}"
        result = resumable_upload(
            bucket,
            object_key,
            str(artifact),
            headers={"Content-Type": _artifact_content_type(artifact)},
            multipart_threshold=8 * 1024 * 1024,
            part_size=4 * 1024 * 1024,
            num_threads=4,
        )
        if result.status not in {200, 201, 204}:
            raise SystemExit(f"OSS upload failed with status {result.status}: {artifact}")
        uploaded.append((metadata, artifact, object_key))

    published_at_ms = int(time() * 1000)
    manifest_path = ROOT / "apps" / "backend" / "app" / "desktop_release_manifest.json"
    existing_payload = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"entries": []}
    manifest = _build_manifest(existing_payload, uploaded, published_at_ms=published_at_ms, is_production=is_production)
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    for metadata, _, _ in uploaded:
        bucket.put_object(
            f"desktop-releases/{metadata['platform']}/{metadata['architecture']}/latest.json",
            manifest_bytes,
            headers={"Content-Type": "application/json"},
        )
    print(json.dumps({
        "artifacts": [{"artifact": str(artifact), "objectKey": object_key} for _, artifact, object_key in uploaded],
        "manifest": str(manifest_path),
        "channel": args.channel,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
