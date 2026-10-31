"""Prepare the five-file CN mock overlay; never SSH or deploy.

The caller builds this context on the target host from the freshly inspected
image. The generated manifest/probe verify the complete resulting image, not
just the five source files. Private environment values stay with that caller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[2]
RELEASE = "cn-mock-20261101.1"
BASE_ALIAS = "offersteady-cn-backend-baseline:mock-20261101"
DIAGNOSTICS = "apps/backend/app/services/mock_interview_diagnostics.py"
CHANGED = frozenset({
    "apps/backend/app/modules/mock_interview.py",
    "apps/backend/app/services/mock_interview_runtime.py",
    "apps/backend/app/services/mock_interview_generation.py",
    "apps/backend/app/services/mock_interview_jobs.py",
    DIAGNOSTICS,
})
MARKER = "EXPECTED = None  # RELEASE_EXPECTATIONS"


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def inventory(value):
    require(isinstance(value, dict) and len(value) >= 150, "incomplete_runtime_inventory")
    for name, digest in value.items():
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", name), "invalid_inventory_path")
        require(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts, "unsafe_inventory_path")
        require(name.startswith(("apps/backend/app/", "apps/backend/migrations/", "ai/prompts/"))
                or name == "apps/backend/pyproject.toml", "unexpected_runtime_input")
        require(valid_hash(digest), "invalid_inventory_hash")
    require("apps/backend/pyproject.toml" in value, "project_manifest_missing")
    return dict(value)


def baseline_contract(value):
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", value.get("image", "")), "baseline_image_must_be_fixed")
    result = {key: value[key] for key in ("image", "python", "dependencies", "settingsSha256", "openapiSha256", "httpPaths")}
    result["inventory"] = inventory(value.get("inventory"))
    require(re.fullmatch(r"3\.13\.\d+", result["python"]), "unexpected_python_runtime")
    require(isinstance(result["dependencies"], dict) and len(result["dependencies"]) >= 20
            and all(isinstance(k, str) and isinstance(v, str) for k, v in result["dependencies"].items()), "dependencies_missing")
    require(valid_hash(result["settingsSha256"]) and valid_hash(result["openapiSha256"]), "baseline_contract_hash_missing")
    require(result["httpPaths"] == 203, "baseline_api_path_count_changed")
    require(DIAGNOSTICS not in result["inventory"] and CHANGED - {DIAGNOSTICS} <= result["inventory"].keys(), "unexpected_mock_baseline")
    return result


def source_bytes(root, name):
    root = Path(root).resolve()
    path = root / name
    require(path.is_file(), "missing_source_file")
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root.parent), "symlink_source_rejected")
    require(path.resolve().is_relative_to(root), "source_outside_root")
    return path.read_bytes()


def prepare(baseline, baseline_source, handoff, source_root, output, *, release=RELEASE):
    baseline = baseline_contract(baseline)
    frozen = handoff.get("backend")
    require(isinstance(frozen, dict) and set(frozen) == CHANGED, "handoff_scope_changed")
    require(all(valid_hash(v) for v in frozen.values()), "invalid_handoff_hash")
    require(re.fullmatch(r"cn-mock-\d{8}\.\d+", release), "invalid_release_name")
    sources, changes = {}, {}
    for name in sorted(CHANGED):
        data = source_bytes(source_root, name)
        require(sha(data) == frozen[name], "frozen_source_drift")
        compile(data, name, "exec")
        old = baseline["inventory"].get(name)
        if old is not None:
            require(sha(source_bytes(baseline_source, name)) == old, "baseline_source_drift")
            require(old != frozen[name], "expected_patch_has_no_change")
        else:
            require(not (Path(baseline_source) / name).exists(), "unexpected_new_file_in_baseline")
        sources[name] = data
        changes[name] = {"before": old, "after": frozen[name]}
    candidate_inventory = baseline["inventory"] | frozen
    require(set(candidate_inventory) == set(baseline["inventory"]) | {DIAGNOSTICS}, "unexpected_candidate_inputs")
    template = (ROOT / "scripts/release_support/cn_mock_20261101/candidate_probe.py").read_text()
    require(template.count(MARKER) == 1, "probe_template_marker_invalid")
    expectations = baseline | {"inventory": candidate_inventory, "release": release}
    probe = template.replace(MARKER, "EXPECTED = " + repr(expectations))
    compile(probe, "candidate-probe.py", "exec")
    output = Path(output)
    require(not output.is_symlink() and (not output.exists() or (output.is_dir() and not any(output.iterdir()))), "output_not_empty")
    output.mkdir(parents=True, exist_ok=True)
    for name, data in sources.items():
        path = output / "backend" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    # BuildKit treats bare sha256:... as a repository name. The server caller
    # pins this local alias to baseImage before/after build, disallows pulling,
    # and verifies candidate Config and RootFS ancestry against that digest.
    dockerfile = "FROM " + BASE_ALIAS + "\n" + "".join("COPY " + name + " /app/" + name + "\n" for name in sorted(sources))
    (output / "backend/Dockerfile").write_text(dockerfile)
    (output / "candidate-probe.py").write_text(probe)
    manifest = {"schemaVersion": 1, "releaseId": release, "baseImage": baseline["image"], "baseAlias": BASE_ALIAS,
        "inventory": candidate_inventory, "baselineInventory": baseline["inventory"], "changes": changes,
        "python": baseline["python"], "dependencies": baseline["dependencies"],
        "settingsSha256": baseline["settingsSha256"], "openapiSha256": baseline["openapiSha256"],
        "httpPaths": 203, "probeSha256": sha(probe.encode()), "dockerfileSha256": sha(dockerfile.encode()),
        "newRuntimeFiles": [DIAGNOSTICS], "dependenciesChanged": False, "configurationChanged": False,
        "compiledChangedPython": len(sources), "productionWrites": 0, "deploymentIncluded": False}
    (output / "backend-manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release", default=RELEASE)
    args = parser.parse_args()
    result = prepare(json.loads(args.baseline.read_text()), args.baseline_source,
        json.loads(args.handoff.read_text()), args.source_root, args.output, release=args.release)
    print(json.dumps({"release": result["releaseId"], "baseImage": result["baseImage"],
        "runtimeFiles": len(result["inventory"]), "changedPython": result["compiledChangedPython"],
        "newFiles": result["newRuntimeFiles"], "dependenciesChanged": False, "productionWrites": 0}))


if __name__ == "__main__":
    main()
