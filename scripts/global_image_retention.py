#!/usr/bin/env python3
"""Read-only Global Docker image retention planner. No delete/apply operation exists."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import subprocess
import sys


COMPONENTS = {"backend", "material-worker", "analytics", "web", "admin"}
PREFIX = "offersteady-global-"


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], capture_output=True, text=True, check=True, timeout=30)
    return result.stdout


def collect(rollback_refs: list[str]) -> tuple[list[dict], list[dict], set[str]]:
    image_ids = sorted(set(docker("image", "ls", "--all", "--quiet", "--no-trunc").split()))
    images = []
    for image_id in image_ids:
        raw = json.loads(docker("image", "inspect", image_id))[0]
        # Do not expose container environment, labels or command lines.
        images.append({key: raw[key] for key in ("Id", "Created", "Size", "RepoTags")})
    container_ids = docker("container", "ls", "--all", "--quiet", "--no-trunc").split()
    containers = []
    for container_id in container_ids:
        raw = json.loads(docker("container", "inspect", container_id))[0]
        containers.append({"Id": raw["Id"], "Image": raw["Image"]})
    # Abort instead of producing a stale plan if Docker changed while collecting it.
    if set(container_ids) != set(docker("container", "ls", "--all", "--quiet", "--no-trunc").split()):
        raise ValueError("Container inventory changed; collect a fresh plan")
    protected = set()
    for ref in rollback_refs:
        protected.add(json.loads(docker("image", "inspect", ref))[0]["Id"])
    return images, containers, protected


def plan(images: list[dict], containers: list[dict], rollback: set[str], keep: int = 2) -> dict:
    if keep < 2:
        raise ValueError("At least two versions per component must be retained")
    by_id = {item["Id"]: item for item in images}
    if len(by_id) != len(images):
        raise ValueError("Duplicate images in inventory")
    used = {item["Image"] for item in containers}
    if not (used | rollback).issubset(by_id):
        raise ValueError("Incomplete image inventory or unresolved rollback image")
    reasons: dict[str, set[str]] = {key: set() for key in by_id}
    groups: dict[str, list[tuple[datetime, str]]] = {name: [] for name in COMPONENTS}
    for image_id, item in by_id.items():
        tags = item.get("RepoTags") or []
        if image_id in used:
            reasons[image_id].add("container-reference")
        if image_id in rollback:
            reasons[image_id].add("explicit-rollback")
        components = set()
        if not tags:
            reasons[image_id].add("untagged-or-unknown")
        for tag in tags:
            repository, separator, version = tag.rpartition(":")
            component = repository.removeprefix(PREFIX)
            if not separator or not version or not repository.startswith(PREFIX) or component not in COMPONENTS:
                reasons[image_id].add("foreign-or-unknown-tag")
            else:
                components.add(component)
                if version.startswith(("baseline-", "rollback-")):
                    reasons[image_id].add("rollback-tag")
        try:
            created = datetime.fromisoformat(item["Created"].replace("Z", "+00:00"))
            if created.tzinfo is None:
                raise ValueError("No timezone")
        except (ValueError, KeyError, TypeError):
            reasons[image_id].add("unknown-created-time")
            continue
        for component in components:
            groups[component].append((created, image_id))
    for component, entries in groups.items():
        for _, image_id in sorted(entries, reverse=True)[:keep]:
            reasons[image_id].add(f"latest-{keep}:{component}")
    retained, candidates = [], []
    for image_id, item in sorted(by_id.items()):
        summary = {"id": image_id, "tags": item.get("RepoTags") or [], "size_bytes": item.get("Size", 0)}
        if reasons[image_id]:
            retained.append({**summary, "reasons": sorted(reasons[image_id])})
        else:
            candidates.append(summary)
    return {
        "read_only": True, "keep_per_component": keep,
        "retained": retained, "review_candidates": candidates,
        "notice": "No files or images were deleted. Candidates require a fresh inventory and manual review. Image sizes share layers and are not reclaimable-byte estimates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollback-image", action="append", required=True, help="Repeat for every known rollback component image; never omit rollback protection")
    args = parser.parse_args()
    try:
        images, containers, rollback = collect(args.rollback_image)
        result = plan(images, containers, rollback)
        result["sampled_at"] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(result, indent=2, sort_keys=True))
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError):
        print("Inventory could not be verified. No cleanup candidates produced; no changes made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
