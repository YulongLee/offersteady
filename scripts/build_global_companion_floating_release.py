"""Assemble a metadata-only publication from the exact released Global inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import time

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "artifacts/global-companion-floating-2-0-0/publication"
PACKAGES = REPO / "apps/desktop/release/global"
OLD_VERSION, VERSION = "1.3.6", "2.0.0"
MANIFEST = "apps/backend/app/global_desktop_release_manifest.json"
TARGETS = (("macos", "arm64"), ("macos", "x64"), ("windows", "x64"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(relative, data):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def main():
    frozen = REPO / "releases/20261106.1/global"
    static = REPO / "releases/20261102.1/global"
    with tarfile.open(frozen / "backend-runtime.tar.gz") as source:
        baseline_manifest = source.extractfile(MANIFEST).read()
    previous = json.loads(baseline_manifest)
    assert len(previous["entries"]) == 3 and all(entry["version"] == OLD_VERSION for entry in previous["entries"])
    now = int(time.time() * 1000)
    entries = []
    for (platform, arch), old in zip(TARGETS, previous["entries"], strict=True):
        assert (old["platform"], old["architecture"]) == (platform, arch)
        filename = old["fileName"].replace(OLD_VERSION, VERSION)
        metadata = json.loads((PACKAGES / (PurePosixPath(filename).stem + ".json")).read_bytes())
        artifact = PACKAGES / filename
        assert metadata["fileName"] == filename and metadata["version"] == VERSION and metadata["protocolVersion"] == "2.0"
        assert metadata["fileSizeBytes"] == artifact.stat().st_size and metadata["sha256"] == digest(artifact.read_bytes())
        assert (metadata["signingStatus"], metadata["notarized"]) == (("verified", True) if platform == "macos" else ("unsigned", False))
        entry = dict(old)
        entry.update({key: metadata[key] for key in ("id", "fileName", "fileSizeBytes", "sha256", "version")})
        entry.update(objectKey=f"global-desktop-releases/{platform}/{arch}/{VERSION}/{filename}", publishedAtMs=now)
        entries.append(entry)
        write(f"objects/{filename}.json", json_bytes(entry))
    manifest = json_bytes({**previous, "generatedAtMs": now, "entries": entries + previous["entries"]})
    write("backend/before.json", baseline_manifest)
    write("backend/after.json", manifest)

    backend_inventory = json.loads((frozen / "backend-runtime-manifest.json").read_bytes())
    assert backend_inventory[MANIFEST] == digest(baseline_manifest)
    static_inventory = json.loads((static / "web-static-manifest.json").read_bytes())
    assert len(static_inventory) == 251
    old_modules = tuple(json.loads((static / "web-delta.json").read_bytes())["moduleMapping"].values())
    mapping = {name: name[:-3] + "-" + digest((digest(manifest) + name).encode())[:10] + ".js" for name in old_modules}
    static_delta = {}
    with tarfile.open(static / "web-static.tar.gz") as source:
        for member in source:
            name = member.name
            if not member.isfile() or (name not in old_modules and not name.endswith(".html")):
                continue
            old = source.extractfile(member).read()
            assert static_inventory[name] == digest(old)
            target = mapping.get(name, name)
            new = old
            for origin, updated in mapping.items():
                new = new.replace(PurePosixPath(origin).name.encode(), PurePosixPath(updated).name.encode())
            if name in ("assets/main-08d5d48b-1eebe5e2.js", "index.html"):
                assert old.count(OLD_VERSION.encode()) == (6 if name.startswith("assets/") else 3)
                new = new.replace(OLD_VERSION.encode(), VERSION.encode())
                assert all(entry["fileName"].encode() in new for entry in entries)
            if name == "assets/DownloadCenter-4f4b7a2d-c73921a6.js":
                component = b"function l({manifest:e}){"
                assert new.count(component) == 1
                # Keep immutable historical URLs available without adding a
                # second download card for each platform and architecture.
                new = new.replace(component, component + (
                    b"e={...e,entries:e.entries.filter((e,t,n)=>"
                    b"n.findIndex(t=>t.platform===e.platform&&t.architecture===e.architecture)===t)};"
                ), 1)
            if new == old and name not in mapping:
                continue
            if name in mapping:
                assert target not in static_inventory
            else:
                write(f"web-before/{name}", old)
            static_delta[target] = digest(new)
            write(f"web/{target}", new)

    assert set(mapping.values()) <= set(static_delta)
    assert "download/index.html" in static_delta and "index.html" in static_delta
    write("plan.json", json_bytes({
        "backendInventory": backend_inventory,
        "backendBefore": digest(baseline_manifest),
        "backendAfter": digest(manifest),
        "webInventory": static_inventory,
        "webDelta": static_delta,
        "entries": entries,
    }))
    print(json.dumps({"publication": str(OUT), "packages": len(entries), "newWebModules": len(mapping),
                      "updatedHtml": len(static_delta) - len(mapping), "oldDownloadEntries": len(previous["entries"])}))


if __name__ == "__main__":
    main()
