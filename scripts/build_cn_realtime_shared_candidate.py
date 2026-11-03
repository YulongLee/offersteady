"""Build a local CN-only overlay from a verified 233-input running baseline.

No Docker, SSH, Git, environment loading, application startup or network calls.
The baseline directory must already contain the exact captured production bytes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_IMAGE = "sha256:5efba4abea9b12e1af2b9d2c6e8f6edb2c205afed93f4f9fc9ba862e96499229"
BASELINE_MANIFEST = Path("docs/releases/cn-device-status-20261103.1/backend-runtime-manifest.json")
BASELINE_MANIFEST_SHA = "18d50582a66b4bb338301ea405ee650347c41a8998391732eab2b99ea6ba224b"
DELTA = (
    "apps/backend/app/main.py",
    "apps/backend/app/modules/realtime_speech.py",
    "apps/backend/app/modules/session.py",
    "apps/backend/app/services/realtime_speech_service.py",
    "apps/backend/app/services/redis_realtime_speech_repository.py",
    "apps/backend/app/services/cn_realtime_entity_state.py",
    "apps/backend/app/services/cn_realtime_io_executor.py",
    "apps/backend/app/services/session_service.py",
    "apps/backend/app/services/knowledge_retrieval.py",
    "apps/backend/app/services/postgres_material_persistence.py",
    "apps/backend/app/platform/cn_realtime_lifespan.py",
    "apps/backend/app/platform/cn_realtime_loop_monitor.py",
)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def unlinked_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents)


def assemble(baseline: Path, output: Path, *, repo: Path = ROOT) -> dict:
    baseline, output = baseline.absolute(), output.absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError("new_unlinked_output_required")
    manifest_path = repo / BASELINE_MANIFEST
    if not unlinked_file(manifest_path):
        raise ValueError("baseline_manifest_invalid")
    manifest_bytes = manifest_path.read_bytes()
    if digest(manifest_bytes) != BASELINE_MANIFEST_SHA:
        raise ValueError("baseline_manifest_changed")
    manifest = json.loads(manifest_bytes)
    if len(manifest) != 233 or not isinstance(manifest, dict):
        raise ValueError("baseline_manifest_invalid")
    # Every captured runtime byte is verified before any output is written.
    entries, modes = {}, {}
    for relative, expected in manifest.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or not unlinked_file(baseline / path):
            raise ValueError("baseline_input_invalid")
        data = (baseline / path).read_bytes()
        if digest(data) != expected:
            raise ValueError("baseline_input_changed")
        entries[relative] = data
        modes[relative] = (baseline / path).stat().st_mode & 0o777
    original = dict(entries)
    for relative in DELTA:
        source = repo / relative
        if not unlinked_file(source):
            raise ValueError("delta_input_invalid")
        entries[relative] = source.read_bytes()
        modes.setdefault(relative, 0o644)
    changed = sorted(key for key, value in entries.items() if original.get(key) != value)
    if changed != sorted(DELTA):
        raise ValueError("delta_set_incomplete")
    unchanged = {key: value for key, value in original.items() if key not in DELTA}
    if any(entries[key] != value for key, value in unchanged.items()):
        raise ValueError("non_target_changed")
    result = {
        "localOnly": True, "baselineImage": BASELINE_IMAGE,
        "baselineManifestSha256": digest(manifest_path.read_bytes()),
        "baselineInputs": len(original), "candidateInputs": len(entries),
        "unchangedBaselineInputs": len(unchanged), "changedOrAdded": changed,
        "files": {key: digest(data) for key, data in sorted(entries.items())},
        "productionChanges": 0, "gitOperations": 0,
    }
    if output.exists() or output.is_symlink():
        raise ValueError("new_unlinked_output_required")
    output.mkdir(parents=True)
    for relative, data in sorted(entries.items()):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        target.chmod(modes[relative])
    if any(digest((output / key).read_bytes()) != value for key, value in result["files"].items()):
        raise ValueError("local_output_verification_failed")
    (output / "local-candidate-manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.baseline, args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}))


if __name__ == "__main__":
    main()
