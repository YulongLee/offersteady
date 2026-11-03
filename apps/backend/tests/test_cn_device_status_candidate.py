"""The local package must use the sealed live bytes, including its older screenshot route."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("local_device_status_builder", ROOT / "scripts/build_cn_device_status_candidate.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def copied_inputs(tmp_path):
    repo = tmp_path / "repo"
    release = repo / builder.SEAL
    release.mkdir(parents=True)
    for relative in ("manifest.json", "cn/backend-runtime.tar.gz", "cn/backend-runtime-manifest.json"):
        target = release / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / builder.SEAL / relative, target)
    for relative in builder.DELTA:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return repo


def test_local_candidate_preserves_all_non_target_live_bytes(tmp_path):
    repo = copied_inputs(tmp_path)
    result = builder.assemble(tmp_path / "candidate", repo=repo)
    baseline = json.loads((ROOT / builder.SEAL / "cn/backend-runtime-manifest.json").read_text())
    assert result["candidateInputs"] == 233
    assert result["unchangedBaselineInputs"] == 229
    assert result["changedOrAdded"] == sorted(builder.DELTA)
    for relative, digest in baseline.items():
        if relative not in builder.DELTA:
            assert sha256((tmp_path / "candidate" / relative).read_bytes()).hexdigest() == digest
    screenshot = "apps/backend/app/modules/screenshot_answer.py"
    assert result["files"][screenshot] == baseline[screenshot]
    assert result["files"][screenshot] != sha256((ROOT / screenshot).read_bytes()).hexdigest()
    assert result["productionChanges"] == result["gitOperations"] == 0


def test_changed_archive_refused_before_output(tmp_path):
    repo = copied_inputs(tmp_path)
    with (repo / builder.SEAL / "cn/backend-runtime.tar.gz").open("ab") as stream:
        stream.write(b"synthetic drift")
    with pytest.raises(ValueError, match="sealed_input_changed"):
        builder.assemble(tmp_path / "candidate", repo=repo)
    assert not (tmp_path / "candidate").exists()


def test_existing_output_not_adopted_or_cleaned(tmp_path):
    target = tmp_path / "candidate"
    target.mkdir()
    marker = target / "keep"
    marker.write_text("synthetic existing work")
    with pytest.raises(ValueError, match="new_unlinked_output_required"):
        builder.assemble(target)
    assert marker.read_text() == "synthetic existing work"
