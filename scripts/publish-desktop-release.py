#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend"))

from app.core.config import Settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish an OfferSteady desktop artifact to OSS and update the backend release manifest.")
    parser.add_argument("--metadata", default="apps/desktop/release/OfferSteady-Companion-0.1.0-macOS-arm64.json")
    parser.add_argument("--channel", default="test")
    args = parser.parse_args()

    metadata_path = (ROOT / args.metadata).resolve()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    artifact = Path(metadata["zipPath"]).resolve()
    if not artifact.is_file():
        raise SystemExit(f"Desktop artifact is missing: {artifact}")

    settings = Settings()
    if not all((settings.oss_access_key_id, settings.oss_access_key_secret, settings.oss_endpoint, settings.oss_bucket)):
        raise SystemExit("Real OSS credentials are required in .env to publish a desktop release.")

    from oss2 import Auth, Bucket

    endpoint = str(settings.oss_endpoint)
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"https://{endpoint}"
    bucket = Bucket(Auth(settings.oss_access_key_id, settings.oss_access_key_secret), endpoint, settings.oss_bucket)
    version = str(metadata["version"])
    object_key = f"desktop-releases/macos/arm64/{version}/{artifact.name}"
    result = bucket.put_object_from_file(object_key, str(artifact), headers={"Content-Type": "application/zip"})
    if result.status not in {200, 201, 204}:
        raise SystemExit(f"OSS upload failed with status {result.status}")

    published_at_ms = int(time() * 1000)
    manifest = {
        "version": 1,
        "generatedAtMs": published_at_ms,
        "entries": [{
            "id": "mac-arm64-local-dev",
            "platform": "macos",
            "architecture": "arm64",
            "displayName": "macOS Apple Silicon 测试版",
            "version": version,
            "minimumOs": metadata["minimumOs"],
            "fileName": artifact.name,
            "fileSizeBytes": metadata["fileSizeBytes"],
            "sha256": metadata["sha256"],
            "signingStatus": "local-development",
            "notarized": bool(metadata.get("notarized", False)),
            "publishedAtMs": published_at_ms,
            "protocolVersion": metadata["protocolVersion"],
            "developmentOnly": True,
            "objectKey": object_key,
            "capabilities": {
                "microphone": True,
                "systemAudio": True,
                "manualInputFallback": True,
                "screenshotFallback": True,
            },
        }],
    }
    manifest_path = ROOT / "apps" / "backend" / "app" / "desktop_release_manifest.json"
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    bucket.put_object("desktop-releases/macos/arm64/latest.json", manifest_bytes, headers={"Content-Type": "application/json"})
    print(json.dumps({"artifact": str(artifact), "objectKey": object_key, "manifest": str(manifest_path), "channel": args.channel}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
