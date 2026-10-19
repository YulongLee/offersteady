"""Verify current sealed CN production sources/static without network or writes."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "releases/cn-20261019.2"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((RELEASE / "manifest.json").read_bytes())
    actual = {
        str(path.relative_to(ROOT)): digest(path.read_bytes())
        for directory in ("apps/backend/app", "apps/backend/migrations", "ai/prompts")
        for path in (ROOT / directory).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        and path.name != ".desktop-release-manifest.lock"
    }
    actual["apps/backend/pyproject.toml"] = digest((ROOT / "apps/backend/pyproject.toml").read_bytes())
    assert actual == manifest["backend"]["files"], "backend_source_inventory_mismatch"
    for name, checksum in manifest["web"]["exactOverlaySourceFiles"].items():
        assert digest((ROOT / name).read_bytes()) == checksum, "published_overlay_source_mismatch"
    bundle = RELEASE / manifest["web"]["bundle"]
    assert digest(bundle.read_bytes()) == manifest["web"]["bundleSha256"], "static_bundle_mismatch"
    with tarfile.open(bundle, "r:gz") as archive:
        members = archive.getmembers()
        assert len(members) == len(manifest["web"]["files"])
        assert {member.name for member in members} == set(manifest["web"]["files"])
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk(), "unsafe_archive_type"
            assert not member.name.startswith("/") and ".." not in Path(member.name).parts, "unsafe_archive_path"
            assert digest(archive.extractfile(member).read()) == manifest["web"]["files"][member.name], "static_byte_mismatch"
    assert not (ROOT / "apps/backend/app/services/cn_resume_optimizer_export.py").exists()
    assert not any((ROOT / "ai/prompts/resume-optimizer" / f"review.zh-CN.v{number}.md").exists() for number in (3, 4, 5, 6))
    assert "resume-optimizer-zh-CN-v2" in (ROOT / "apps/backend/app/services/cn_resume_optimizer_provider.py").read_text()
    print(json.dumps({"passed": True, "version": manifest["version"], "backendFiles": len(actual), "webStaticFiles": len(manifest["web"]["files"]), "exactPublishedOverlaySources": len(manifest["web"]["exactOverlaySourceFiles"]), "productionChanges": 0, "networkCalls": 0}))


if __name__ == "__main__":
    main()
