from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from global_image_retention import plan
from global_release_validation import REQUIRED_CHECKS, SERVICES, SOURCE_ROOTS, ValidationError, digest, source_inventory, validate


@pytest.fixture
def bundle(tmp_path):
    for name in SOURCE_ROOTS:
        path = tmp_path / name
        if "." in path.name:
            path.write_text("synthetic-source\n")
        else:
            path.mkdir(parents=True)
            (path / "source.txt").write_text("synthetic-source\n")
    evidence = tmp_path / "evidence.log"
    evidence.write_text("synthetic verification fixture, not a real release approval\n")
    manifest = {
        "schema_version": 1, "edition": "global", "release": "synthetic-1",
        "deployment_mode": "incremental",
        "baseline_images": {name: "sha256:" + "a" * 64 for name in SERVICES["incremental"]},
        "source_roots": list(SOURCE_ROOTS), "source_files": source_inventory(tmp_path),
        "checks": {name: {"status": "passed", "evidence": "evidence.log", "sha256": digest(evidence)} for name in REQUIRED_CHECKS},
    }
    return tmp_path, manifest


def test_valid_offline_manifest(bundle):
    root, manifest = bundle
    assert validate(root, manifest, "incremental")["release"] == "synthetic-1"


@pytest.mark.parametrize("mutation", ["added", "removed", "changed", "dockerignore", "npmrc"])
def test_reject_source_changes(bundle, mutation):
    root, manifest = bundle
    path = root / "apps/source.txt"
    if mutation == "removed":
        path.unlink()
    elif mutation == "added":
        (root / "apps/other.txt").write_text("new source")
    elif mutation in {"dockerignore", "npmrc"}:
        (root / f".{mutation}").write_text("altered build input")
    else:
        path.write_text("changed source")
    with pytest.raises(ValidationError):
        validate(root, manifest, "incremental")


@pytest.mark.parametrize("mutation", ["cn", "mode", "services", "mutable_image", "roots", "missing_check", "failed_check", "changed_evidence"])
def test_reject_incomplete_or_mixed_manifest(bundle, mutation):
    root, manifest = bundle
    if mutation == "cn":
        manifest["edition"] = "cn"
    elif mutation == "mode":
        manifest["deployment_mode"] = "legacy-compose"
    elif mutation == "services":
        manifest["baseline_images"].pop("web")
    elif mutation == "mutable_image":
        manifest["baseline_images"]["backend"] = "offersteady-global-backend:latest"
    elif mutation == "roots":
        manifest["source_roots"] = ["apps"]
    elif mutation == "missing_check":
        manifest["checks"].pop("web")
    elif mutation == "failed_check":
        manifest["checks"]["web"]["status"] = "failed"
    else:
        (root / "evidence.log").write_text("different evidence")
    with pytest.raises(ValidationError):
        validate(root, manifest, "incremental")


@pytest.mark.parametrize("path", ["../outside.log", "/tmp/outside.log", ".env.production", "private.key", "apps/../evidence.log"])
def test_evidence_cannot_escape_or_expose_secrets(bundle, path):
    root, manifest = bundle
    manifest["checks"]["web"]["evidence"] = path
    with pytest.raises(ValidationError):
        validate(root, manifest, "incremental")


def test_evidence_cannot_use_a_symlink(bundle):
    root, manifest = bundle
    (root / "link.log").symlink_to(root / "evidence.log")
    manifest["checks"]["web"]["evidence"] = "link.log"
    with pytest.raises(ValidationError, match="Symlink"):
        validate(root, manifest, "incremental")


def test_private_files_excluded_but_not_source_symlinks(bundle):
    root, manifest = bundle
    (root / "apps/.env.production").write_text("SYNTHETIC_SECRET=never-print")
    assert validate(root, manifest, "incremental")
    (root / "apps/linked.txt").symlink_to(root / "evidence.log")
    with pytest.raises(ValidationError, match="symlink"):
        validate(root, manifest, "incremental")


def test_legacy_entrypoint_stops_before_mutations_without_manifest(tmp_path):
    script = Path(__file__).with_name("deploy-global-production.sh")
    env_file = tmp_path / ".env.global.production"
    env_file.write_text("SYNTHETIC_SECRET=unchanged\n")
    env_file.chmod(0o644)
    env = {**os.environ, "OFFERSTEADY_GLOBAL_ENV_FILE": str(env_file)}
    env.pop("OFFERSTEADY_GLOBAL_RELEASE_MANIFEST", None)
    result = subprocess.run(["bash", str(script)], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "reviewed Global release manifest is required" in result.stderr
    assert env_file.stat().st_mode & 0o777 == 0o644
    assert "unchanged" not in result.stderr


def image(number, component="backend", **overrides):
    return {"Id": f"sha256:{number:064x}", "Created": f"2026-09-{number:02}T00:00:00Z", "Size": 100, "RepoTags": [f"offersteady-global-{component}:release-{number}"], **overrides}


def test_keep_two_distinct_images_for_each_component():
    images = [image(number, component) for number, component in [(1, "backend"), (2, "backend"), (3, "backend"), (4, "web"), (5, "web"), (6, "web")]]
    result = plan(images, [], set())
    assert {x["id"] for x in result["review_candidates"]} == {images[0]["Id"], images[3]["Id"]}
    assert result["read_only"] is True
    assert "not reclaimable" in result["notice"]


def test_running_or_stopped_container_and_rollback_protected():
    images = [image(i) for i in range(1, 6)]
    result = plan(images, [{"Image": images[0]["Id"], "State": "exited"}], {images[1]["Id"]})
    assert [x["id"] for x in result["review_candidates"]] == [images[2]["Id"]]
    assert any("container-reference" in x["reasons"] for x in result["retained"])
    assert any("explicit-rollback" in x["reasons"] for x in result["retained"])


@pytest.mark.parametrize("overrides,reason", [
    ({"RepoTags": ["offersteady-global-backend:old", "other-project:shared"]}, "foreign-or-unknown-tag"),
    ({"RepoTags": ["offersteady-global-backend:baseline-older"]}, "rollback-tag"),
    ({"RepoTags": None}, "untagged-or-unknown"),
    ({"Created": "unknown"}, "unknown-created-time"),
    ({"Created": "2026-09-01T00:00:00"}, "unknown-created-time"),
])
def test_ambiguous_or_special_images_retained(overrides, reason):
    images = [image(1, **overrides), image(2), image(3)]
    result = plan(images, [], set())
    assert not result["review_candidates"]
    assert reason in next(x["reasons"] for x in result["retained"] if x["id"] == images[0]["Id"])


def test_multiple_tags_do_not_count_as_multiple_versions():
    images = [image(1), image(2), image(3)]
    images[2]["RepoTags"].append("offersteady-global-backend:latest")
    original = copy.deepcopy(images)
    result = plan(images, [], set())
    assert len(result["review_candidates"]) == 1
    assert images == original  # Pure planning, never mutates inventory.


@pytest.mark.parametrize("containers,rollback", [([{"Image": "missing"}], set()), ([], {"missing"})])
def test_incomplete_inventory_rejected(containers, rollback):
    with pytest.raises(ValueError, match="Incomplete"):
        plan([image(1)], containers, rollback)


def test_cannot_request_less_than_two_versions():
    with pytest.raises(ValueError):
        plan([image(1)], [], set(), keep=1)
