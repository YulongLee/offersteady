#!/usr/bin/env python3
"""Offline, fail-closed source-bundle checks. This does not approve a deployment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


SOURCE_ROOTS = (
    "apps", "packages", "ai", "infra",
    "scripts", "package.json", "package-lock.json", "tsconfig.base.json",
)
OPTIONAL_ROOT_FILES = (".dockerignore", ".npmrc", "npm-shrinkwrap.json")
IGNORED_DIRS = {"node_modules", "dist", "build", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv"}
SERVICES = {
    "incremental": {"backend", "material-worker", "web", "admin"},
    "legacy-compose": {"backend", "analytics", "web", "admin"},
}
REQUIRED_CHECKS = {"backend", "web", "admin", "web-build", "admin-build"}
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def private_path(path: PurePosixPath) -> bool:
    return any(
        (part.startswith(".env") and not part.endswith((".example", ".sample")))
        or part in {"id_rsa", "id_ed25519"}
        or part.endswith((".pem", ".key", ".p12"))
        for part in path.parts
    )


def safe_file(root: Path, name: str) -> Path:
    require(isinstance(name, str) and bool(name), "Empty or invalid file path")
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in name, "File path escapes bundle")
    require(str(relative) == name, "File path is not canonical")
    require(not private_path(relative), "Private configuration cannot be release evidence")
    path = root
    for part in relative.parts:
        path /= part
        require(not path.is_symlink(), "Symlink is not permitted in release evidence")
    require(path.is_file() and path.resolve().is_relative_to(root.resolve()), "Missing or invalid evidence file")
    return path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def source_inventory(root: Path) -> dict[str, str]:
    """Complete source inventory; only known caches/build outputs and private files excluded."""
    result: dict[str, str] = {}

    def visit(path: Path) -> None:
        name = path.relative_to(root).as_posix()
        if path.name in IGNORED_DIRS or private_path(PurePosixPath(name)):
            return
        require(not path.is_symlink(), "Source bundle contains a symlink outside excluded dependency directories")
        if path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            result[name] = digest(safe_file(root, name))

    for name in SOURCE_ROOTS:
        path = root / name
        require(path.exists(), f"Required source root missing: {name}")
        visit(path)
    for name in OPTIONAL_ROOT_FILES:
        if (root / name).exists() or (root / name).is_symlink():
            visit(root / name)
    return result


def validate(root: Path, manifest: dict, mode: str) -> dict:
    require(isinstance(manifest, dict), "Manifest must be an object")
    require(manifest.get("schema_version") == 1 and manifest.get("edition") == "global", "Expected a Global v1 manifest")
    release = manifest.get("release")
    require(isinstance(release, str) and bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}", release)), "Invalid release identifier")
    require(mode in SERVICES and manifest.get("deployment_mode") == mode, "Wrong deployment mode; do not mix incremental and legacy releases")
    baseline = manifest.get("baseline_images")
    require(isinstance(baseline, dict) and set(baseline) == SERVICES[mode], "Wrong or incomplete baseline service set")
    require(all(isinstance(value, str) and IMAGE_ID.fullmatch(value) for value in baseline.values()), "Baseline images require full immutable image IDs")
    require(manifest.get("source_roots") == list(SOURCE_ROOTS), "Source roots must cover the complete Global build inputs")
    inventory = manifest.get("source_files")
    require(isinstance(inventory, dict) and bool(inventory), "Missing source inventory")
    for name, value in inventory.items():
        safe_file(root, name)
        require(isinstance(value, str) and bool(DIGEST.fullmatch(value)), "Invalid source hash")
    require(inventory == source_inventory(root), "Source inventory changed: added, removed or modified files; re-test and re-review")
    checks = manifest.get("checks")
    require(isinstance(checks, dict) and REQUIRED_CHECKS.issubset(checks), "Required regression evidence is missing")
    for check in checks.values():
        require(isinstance(check, dict) and check.get("status") == "passed", "A regression check has not passed")
        evidence = safe_file(root, check.get("evidence", ""))
        require(evidence.stat().st_size > 0, "Empty regression evidence")
        require(check.get("sha256") == digest(evidence), "Regression evidence hash changed")
    return {"edition": "global", "release": release, "mode": mode, "source_file_count": len(inventory), "check_count": len(checks)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=SERVICES, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        print(json.dumps(validate(args.root.resolve(), manifest, args.mode), sort_keys=True))
    except (OSError, ValueError, TypeError) as exc:
        # OSError and JSONDecodeError can contain data or paths; do not print private input.
        print(str(exc) if isinstance(exc, ValidationError) else "Cannot read a valid release manifest", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
