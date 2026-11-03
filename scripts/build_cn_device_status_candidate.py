"""Assemble a local-only CN Backend delta from the sealed live runtime bytes.

Does not invoke Docker, SSH, application startup, Git, or any network service.
The pending root screenshot route is deliberately not an input.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
from pathlib import Path
import tarfile


REPO_ROOT = Path(__file__).resolve().parents[1]
SEAL = Path("releases/20261102.1")
BASELINE_IMAGE = "sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a"
DELTA = (
    "apps/backend/app/modules/realtime_speech.py",
    "apps/backend/app/services/realtime_speech_service.py",
    "apps/backend/app/services/postgres_interview_session_repository.py",
    "apps/backend/app/platform/cn_device_status_timing.py",
)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def assemble(output: Path, *, repo: Path = REPO_ROOT) -> dict:
    output = output.absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError("new_unlinked_output_required")
    seal = json.loads((repo / SEAL / "manifest.json").read_text())
    component = seal["components"]["cn-backend"]
    archive_path, inventory_path = component["archive"], component["inventory"]
    if (archive_path != str(SEAL / "cn/backend-runtime.tar.gz")
            or inventory_path != str(SEAL / "cn/backend-runtime-manifest.json")
            or component["image"] != BASELINE_IMAGE or component["count"] != 232):
        raise ValueError("cn_component_provenance_changed")
    archive, inventory = (repo / archive_path).read_bytes(), (repo / inventory_path).read_bytes()
    if any(digest(data) != seal["files"][path] for path, data in ((archive_path, archive), (inventory_path, inventory))):
        raise ValueError("sealed_input_changed")
    expected = json.loads(inventory)
    entries, modes = {}, {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as stream:
        for member in stream.getmembers():
            if member.isdir():
                continue
            path = Path(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts or member.name in entries:
                raise ValueError("invalid_archive_entry")
            data = stream.extractfile(member).read()
            entries[member.name] = data
            modes[member.name] = member.mode & 0o777
    if len(expected) != 232 or {key: digest(data) for key, data in entries.items()} != expected:
        raise ValueError("actual_runtime_inventory_changed")
    original = dict(entries)
    for relative in DELTA:
        path = repo / relative
        if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
            raise ValueError("delta_input_invalid")
        entries[relative] = path.read_bytes()
        modes.setdefault(relative, 0o644)
    changed = sorted(key for key, value in entries.items() if original.get(key) != value)
    if changed != sorted(DELTA):
        raise ValueError("delta_set_incomplete")
    unchanged = {key: value for key, value in original.items() if key not in DELTA}
    if any(entries[key] != value for key, value in unchanged.items()):
        raise ValueError("non_target_changed")
    result = {
        "localOnly": True, "baselineImage": BASELINE_IMAGE,
        "sealedBaselineInputs": len(original), "candidateInputs": len(entries),
        "unchangedBaselineInputs": len(unchanged), "changedOrAdded": changed,
        "files": {key: digest(value) for key, value in sorted(entries.items())},
        "productionChanges": 0, "gitOperations": 0,
    }
    # Recheck immediately before any writes; never adopt or clean an existing directory.
    if output.exists() or output.is_symlink():
        raise ValueError("new_unlinked_output_required")
    output.mkdir(parents=True)
    for relative, data in sorted(entries.items()):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
        path.chmod(modes[relative])
    if any(digest((output / key).read_bytes()) != value for key, value in result["files"].items()):
        raise ValueError("local_output_verification_failed")
    (output / "local-candidate-manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assemble(args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
