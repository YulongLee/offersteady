"""Synthetic local-packaging guards; no application, Docker, or production I/O."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("cn_shared_candidate_builder", ROOT / "scripts/build_cn_realtime_shared_candidate.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    baseline, repo = tmp_path / "baseline", tmp_path / "repo"
    existing = [path for path in builder.DELTA if "/cn_" not in path]
    screenshot = "apps/backend/app/modules/screenshot_answer.py"
    names = [*existing, screenshot]
    names.extend(f"synthetic/source-{index}.py" for index in range(233 - len(names)))
    manifest = {}
    for relative in names:
        path = baseline / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        data = b"synthetic baseline runtime\n"
        path.write_bytes(data)
        path.chmod(0o644)
        manifest[relative] = sha256(data).hexdigest()
    for relative in builder.DELTA:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic candidate delta\n")
    # Root contains an unrelated pending feature; it cannot enter this package.
    path = repo / screenshot
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"unreleased synthetic screenshot feature\n")
    path = repo / builder.BASELINE_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(manifest, sort_keys=True).encode()
    path.write_bytes(data)
    monkeypatch.setattr(builder, "BASELINE_MANIFEST_SHA", sha256(data).hexdigest())
    return baseline, repo, manifest


def test_reviewed_production_manifest_is_pinned():
    assert sha256((ROOT / builder.BASELINE_MANIFEST).read_bytes()).hexdigest() == builder.BASELINE_MANIFEST_SHA


def test_candidate_contains_only_allowlisted_runtime_changes(inputs, tmp_path):
    baseline, repo, manifest = inputs
    result = builder.assemble(baseline, tmp_path / "candidate", repo=repo)
    assert result["baselineInputs"] == 233
    assert result["changedOrAdded"] == sorted(builder.DELTA)
    assert result["candidateInputs"] == 233 + len(set(builder.DELTA) - manifest.keys())
    assert result["unchangedBaselineInputs"] == len(set(manifest) - set(builder.DELTA))
    for relative, expected in manifest.items():
        if relative not in builder.DELTA:
            assert sha256((tmp_path / "candidate" / relative).read_bytes()).hexdigest() == expected
    assert result["files"]["apps/backend/app/modules/screenshot_answer.py"] != sha256(
        (repo / "apps/backend/app/modules/screenshot_answer.py").read_bytes()).hexdigest()
    assert result["productionChanges"] == result["gitOperations"] == 0


@pytest.mark.parametrize("kind", ["manifest", "baseline", "delta_missing", "delta_symlink", "incomplete_delta"])
def test_changed_or_unsafe_inputs_refused_before_any_output(inputs, tmp_path, kind):
    baseline, repo, _ = inputs
    if kind == "manifest":
        path = repo / builder.BASELINE_MANIFEST
        path.write_bytes(path.read_bytes() + b" ")
    elif kind == "baseline":
        (baseline / "synthetic/source-0.py").write_bytes(b"synthetic drift")
    else:
        relative = builder.DELTA[0]
        path = repo / relative
        if kind == "incomplete_delta":
            path.write_bytes((baseline / relative).read_bytes())
        else:
            path.unlink()
            if kind == "delta_symlink":
                path.symlink_to(baseline / relative)
    with pytest.raises(ValueError):
        builder.assemble(baseline, tmp_path / "candidate", repo=repo)
    assert not (tmp_path / "candidate").exists()


def test_existing_output_preserved_and_output_symlink_refused(inputs, tmp_path):
    baseline, repo, _ = inputs
    out = tmp_path / "existing"
    out.mkdir()
    marker = out / "keep"
    marker.write_bytes(b"existing work")
    with pytest.raises(ValueError, match="new_unlinked_output_required"):
        builder.assemble(baseline, out, repo=repo)
    assert marker.read_bytes() == b"existing work"
    linked = tmp_path / "linked"
    linked.symlink_to(out)
    with pytest.raises(ValueError, match="new_unlinked_output_required"):
        builder.assemble(baseline, linked, repo=repo)
