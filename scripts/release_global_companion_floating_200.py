"""Publish the exact Global 2.0.0 companion metadata to the existing containers."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request

BACKEND = "offersteady-global-backend-1"
WEB = "offersteady-global-web-1"
IDS = {
    BACKEND: ("bf9eab2626100d1b090de78e3cab6f6fa00a727d6181c54c61ccb3e4f70eb197",
              "sha256:687fe1b4b421eb11024bbe6fd36f8ff81a973cf37a74f43e653e7e9321752bea"),
    WEB: ("a164dbd6999dbfbb47969baee68b482fdc6c100a9c3b0d8f6fcadc9a3c2523ba",
          "sha256:73c351fbc0502f50989b729174620173c80988292fe6d0d2b4fcf660f29caa44"),
}
PRIOR = Path("/opt/offersteady-global/releases/20261106-global-cleanup-control-1")
ROOT = Path("/opt/offersteady-global/releases/20261110-global-companion-floating-200")
MANIFEST = "apps/backend/app/global_desktop_release_manifest.json"
STATIC = "/usr/share/nginx/html"
OLD_MANIFEST = "136f43b076a5064db83b1d747c45f3acb9b6d15c9299eeaadeb6a64c02f4d1dc"
PREVIOUS_CONTROLLER = "40c566cd79ffcf28e5250ff6d0eb9d0f9dd10244742d9ac662e02923ea50d63f"
VERSIONS = {("macos", "arm64"), ("macos", "x64"), ("windows", "x64")}
ORIGIN = "https://offersteady.com"
HISTORY = "apps/backend/app/global_desktop_release_history.json"
PUBLIC_STATE_FIELDS = {
    "account", "activeAnswerTask", "billing", "captureState", "contextSelections",
    "interviews", "knowledgeCollections", "knowledgeDocuments", "librarySources",
    "preparation", "questions", "releaseManifest", "review", "speaker",
}


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*args, data=None, timeout=45):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    require(result.returncode == 0, f"command_failed:{args[0]}:{args[1]}")
    return result.stdout


def record(filename, value):
    target = ROOT / filename
    temporary = target.with_suffix(".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def checked_path(name):
    require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9._/-]+", name)
            and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts,
            "invalid_inventory_path")
    return name


def load_plan():
    plan = json.loads((ROOT / "plan.json").read_bytes())
    require(len(plan["backendInventory"]) == 308 and len(plan["webInventory"]) == 251,
            "incomplete_baseline_inventory")
    require(plan["backendBefore"] == OLD_MANIFEST == plan["backendInventory"][MANIFEST],
            "baseline_manifest_mismatch")
    before, after = ((ROOT / "backend" / (which + ".json")).read_bytes() for which in ("before", "after"))
    require(sha(before) == OLD_MANIFEST and sha(after) == plan["backendAfter"], "manifest_bytes_mismatch")
    old, new = json.loads(before), json.loads(after)
    entries = plan["entries"]
    require(len(entries) == 3 and {(x["platform"], x["architecture"]) for x in entries} == VERSIONS,
            "three_global_platforms_required")
    require(new["entries"] == entries + old["entries"], "historical_download_entries_changed")
    for entry in entries:
        target = (entry["platform"], entry["architecture"])
        name = checked_path(entry["fileName"])
        expected = ("OfferSteady-Companion-Global-Setup-2.0.0-Windows-x64.exe" if target[0] == "windows"
                    else f"OfferSteady-Companion-Global-2.0.0-macOS-{target[1]}.dmg")
        require(name == expected and entry["version"] == "2.0.0" and entry["protocolVersion"] == "2.0"
                and entry["objectKey"] == f"global-desktop-releases/{target[0]}/{target[1]}/2.0.0/{name}"
                and entry["distributionStatus"] == "published" and entry["developmentOnly"] is False,
                "invalid_global_release_entry")
        proof = json.loads((ROOT / "proofs" / f"{name}.json").read_bytes())
        require(proof["objectReadbackVerified"] is True and
                all(proof[key] == entry[key] for key in ("fileName", "sha256", "fileSizeBytes", "objectKey", "version")),
                "immutable_object_readback_mismatch")
    delta = plan["webDelta"]
    require(len(delta) == 32, "unexpected_web_delta_count")
    for name, digest in delta.items():
        checked_path(name)
        require(sha((ROOT / "web" / name).read_bytes()) == digest, "web_delta_bytes_changed")
        if name in plan["webInventory"]:
            require(name.endswith(".html") and sha((ROOT / "web-before" / name).read_bytes()) == plan["webInventory"][name],
                    "web_original_bytes_changed")
        else:
            require(name.startswith("assets/") and name.endswith(".js"), "unexpected_new_web_path")
    return plan


def owner():
    names = run("docker", "ps", "-a", "--format", "{{.Names}}").decode().splitlines()
    inspected = json.loads(run("docker", "inspect", *sorted(names)))
    summary = {}
    for item in inspected:
        name = item["Name"][1:]
        state = item["State"]
        summary[name] = [item["Id"], item["Image"], state["StartedAt"], item["RestartCount"], state["Running"]]
        if name in IDS:
            require(tuple(summary[name][:2]) == IDS[name] and state["Running"], "global_component_drift")
    require(set(IDS) <= set(summary), "global_component_missing")
    return summary


def file_inventory(container, root, inventory):
    checks = "".join(f"{digest}  {checked_path(name)}\n" for name, digest in inventory.items()).encode()
    run("docker", "exec", "-i", container, "sh", "-c", 'cd "$1" && sha256sum -c -', "verify", root, data=checks)


def idle_gates():
    previous = PRIOR / "controller.py"
    require(sha(previous.read_bytes()) == PREVIOUS_CONTROLLER, "previous_gate_controller_drift")
    spec = importlib.util.spec_from_file_location("global_release_baseline", previous)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.save = lambda name, value: None
    module.bind_primitives()
    previous_plan = module.check_plan()
    prepared = module.read_json(PRIOR / "prepared.json")
    module.check_files(prepared, previous_plan)
    module.idle_gates(prepared)
    module.tcp_gate(prepared, module.progress_state())


def build_recreate_image(container, tag, directory, content, destination):
    base = IDS[container][1]
    base_tag = tag + "-base"
    run("docker", "image", "tag", base, base_tag)
    context = ROOT / directory
    context.mkdir(exist_ok=True)
    (context / "Dockerfile").write_text(f"FROM {base_tag}\nCOPY {content} {destination}\n")
    result = subprocess.run(["docker", "build", "--pull=false", "--network=none", "--rm", "-t", tag, "-f",
                             str(context / "Dockerfile"), str(context)], env={**os.environ, "DOCKER_BUILDKIT": "0"},
                            capture_output=True, timeout=180)
    require(result.returncode == 0, f"immutable_recreate_image_build_failed:{container}")
    old, new = json.loads(run("docker", "image", "inspect", base, tag))
    require(new["Config"] == old["Config"] and new["RootFS"]["Layers"][:-1] == old["RootFS"]["Layers"],
            "candidate_image_config_or_layers_changed")
    return new["Id"]


def backend_swap(source, expected, candidate):
    script = """
from pathlib import Path
import fcntl, hashlib, os, sys, tempfile
p=Path('/app/apps/backend/app/global_desktop_release_manifest.json')
def digest(b): return hashlib.sha256(b).hexdigest()
new=sys.stdin.buffer.read()
with p.with_name('.global-companion-200.lock').open('a+b') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 assert not p.is_symlink() and digest(p.read_bytes()) == sys.argv[1]
 assert digest(new) == sys.argv[2]
 old=p.stat()
 fd,tmp=tempfile.mkstemp(prefix='.global-release-',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as handle:
   handle.write(new)
   os.fchown(handle.fileno(),old.st_uid,old.st_gid)
   os.fchmod(handle.fileno(),old.st_mode & 0o777)
   handle.flush()
   os.fsync(handle.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp): os.unlink(tmp)
"""
    run("docker", "exec", "-i", BACKEND, "python", "-B", "-c", script, expected, candidate, data=source.read_bytes())


def stage_web(source, inventory):
    archive = ROOT / "web-stage.tar"
    with tarfile.open(archive, "w") as bundle:
        for name in inventory:
            bundle.add(ROOT / source / name, arcname=name)
    stage = run("docker", "exec", WEB, "mktemp", "-d", STATIC + "/.global-companion-200.XXXXXX").decode().strip()
    run("docker", "exec", "-i", WEB, "tar", "-xf", "-", "-C", stage, data=archive.read_bytes())
    file_inventory(WEB, stage, inventory)
    return stage


def publish_web(stage, delta, baseline, *, include_originals):
    paths = [name for name in delta if (name in baseline) == include_originals]
    code = """
set -eu
root=$1
stage=$2
while IFS=' ' read -r name old new; do
 target="$root/$name"
 source="$stage/$name"
 if [ "$old" = absent ]; then
   test ! -e "$target" && test ! -L "$target"
 else
   test ! -L "$target"
   printf '%s  %s\n' "$old" "$target" | sha256sum -c -
 fi
 printf '%s  %s\n' "$new" "$source" | sha256sum -c -
 chmod 644 "$source"
 mv "$source" "$target"
done
"""
    lines = "".join(f"{name} {baseline.get(name, 'absent')} {delta[name]}\n" for name in paths)
    run("docker", "exec", "-i", WEB, "sh", "-c", code, "publish", STATIC, stage, data=lines.encode())


def preflight(plan):
    identity = owner()
    require(shutil.disk_usage(ROOT).free >= 2 * 1024**3, "global_release_disk_space_too_low")
    file_inventory(BACKEND, "/app", plan["backendInventory"])
    file_inventory(WEB, STATIC, plan["webInventory"])
    idle_gates()
    require(owner() == identity, "global_container_ownership_changed")
    return identity


def current_hashes(container, root, paths):
    code = """
set -eu
cd "$1"
while IFS= read -r path; do
 test -f "$path" && test ! -L "$path"
 sha256sum "$path"
done
"""
    names = "".join(checked_path(name) + "\n" for name in paths)
    lines = run("docker", "exec", "-i", container, "sh", "-c", code, "hash", root, data=names.encode())
    return {name: digest for digest, name in (line.split(None, 1) for line in lines.decode().splitlines())}


def rollback(plan, previous):
    require(owner() == previous, "rollback_container_ownership_changed")
    before, after = plan["backendBefore"], plan["backendAfter"]
    backend = current_hashes(BACKEND, "/app", [MANIFEST])[MANIFEST]
    require(backend in {before, after}, "rollback_manifest_unrecognized")
    old_html = {name: plan["webInventory"][name] for name in plan["webDelta"] if name in plan["webInventory"]}
    current = current_hashes(WEB, STATIC, old_html)
    require(all(current[name] in {digest, plan["webDelta"][name]} for name, digest in old_html.items()),
            "rollback_web_bytes_unrecognized")
    changed = {name: digest for name, digest in old_html.items() if current[name] != digest}
    if changed:
        stage = stage_web("web-before", changed)
        publish_web(stage, changed, current, include_originals=True)
    if backend == after:
        backend_swap(ROOT / "backend/before.json", after, before)
    file_inventory(BACKEND, "/app", plan["backendInventory"])
    file_inventory(WEB, STATIC, plan["webInventory"])
    require(owner() == previous, "rollback_container_ownership_changed")
    record("rolled-back.json", {"version": "1.3.6", "containerIdentities": previous})


def get(path, *, headers=None, limit=2 * 1024 * 1024):
    request = urllib.request.Request(ORIGIN + path, headers={"Accept-Encoding": "identity", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            content = response.read(limit + 1)
            require(len(content) <= limit, "public_response_exceeded_limit")
            return response.status, response.headers, content
    except Exception:
        raise RuntimeError(f"public_request_failed:{path}") from None


def verify_public(plan):
    status, _, health = get("/healthz")
    require(status == 200 and json.loads(health)["data"]["status"] == "ok", "public_health_failed")
    status, _, payload = get("/api/v1/web/state", headers={"Cache-Control": "no-cache"})
    state = json.loads(payload)["data"]
    require(status == 200 and set(state) == PUBLIC_STATE_FIELDS, "public_state_fields_changed")
    releases = state["releaseManifest"]["entries"]
    expected = json.loads((ROOT / "backend/after.json").read_bytes())["entries"]
    require(len(releases) == len(expected), "public_manifest_entry_count_changed")
    for actual, entry in zip(releases, expected):
        require(all(actual[key] == entry[key] for key in ("version", "sha256", "fileSizeBytes", "platform", "architecture")),
                "public_manifest_platform_mismatch")
    history = json.loads(run("docker", "exec", BACKEND, "cat", f"/app/{HISTORY}"))["entries"]
    require(len(history) == 3 and all(entry["version"] == "1.3.5" for entry in history), "public_history_contract_changed")
    downloads = []
    for entry in expected + history:
        filename = checked_path(entry["fileName"])
        status, headers, body = get("/api/v1/web/downloads/desktop/" + filename, headers={"Range": "bytes=0-3"}, limit=4)
        mime = "application/x-apple-diskimage" if entry["platform"] == "macos" else "application/vnd.microsoft.portable-executable"
        require(status == 206 and headers.get("Content-Range") == f'bytes 0-3/{entry["fileSizeBytes"]}'
                and headers.get_content_type() == mime and len(body) == 4, f"public_download_range_mismatch:{filename}")
        downloads.append(filename)
    for path, name in (("/", "index.html"), ("/download", "download/index.html")):
        status, _, body = get(path, headers={"Cache-Control": "no-cache"})
        require(status == 200 and sha(body) == plan["webDelta"][name], f"public_page_bytes_mismatch:{path}")
    for name, digest in plan["webDelta"].items():
        if name.endswith(".js"):
            status, _, body = get("/" + name)
            require(status == 200 and sha(body) == digest, f"public_asset_bytes_mismatch:{name}")
    return downloads


def apply(plan):
    require(not (ROOT / "cutover-intent.json").exists(), "previous_cutover_requires_reconciliation")
    previous = preflight(plan)
    # Freeze recovery and future recreation inputs before the runtime metadata changes.
    back_context = ROOT / "backend-image"
    back_context.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "backend/after.json", back_context / "manifest.json")
    for name in plan["webDelta"]:
        target = ROOT / "web-image/public" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "web" / name, target)
    images = {
        "backend": build_recreate_image(BACKEND, "offersteady-global-backend:companion-200", "backend-image", "manifest.json", f"/app/{MANIFEST}"),
        "web": build_recreate_image(WEB, "offersteady-global-web:companion-200", "web-image", "public/", STATIC + "/"),
    }
    record("recreate-images.json", images)
    record("recreate.compose.json", {"services": {service: {"image": image} for service, image in images.items()}})
    stage = stage_web("web", plan["webDelta"])
    idle_gates()
    require(owner() == previous, "global_container_ownership_changed")
    record("cutover-intent.json", {"images": images, "containerIdentities": previous})
    publish_web(stage, plan["webDelta"], plan["webInventory"], include_originals=False)
    try:
        backend_swap(ROOT / "backend/after.json", plan["backendBefore"], plan["backendAfter"])
        publish_web(stage, plan["webDelta"], plan["webInventory"], include_originals=True)
        file_inventory(BACKEND, "/app", {**plan["backendInventory"], MANIFEST: plan["backendAfter"]})
        file_inventory(WEB, STATIC, {**plan["webInventory"], **plan["webDelta"]})
        require(owner() == previous, "global_container_ownership_changed")
        downloads = verify_public(plan)
    except Exception:
        rollback(plan, previous)
        raise
    record("published.json", {"images": images, "containerIdentities": previous,
                              "publicDownloadsVerified": downloads, "version": "2.0.0"})
    print(json.dumps({"published": True, "restartCount": 0, "version": "2.0.0"}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preflight", "apply", "verify", "rollback"))
    args = parser.parse_args()
    with (ROOT / ".release.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = load_plan()
        if args.action == "preflight":
            preflight(plan)
            print('{"preflight":true,"productionChanged":false}')
        elif args.action == "apply":
            apply(plan)
        else:
            intent = json.loads((ROOT / "cutover-intent.json").read_text())
            previous = intent["containerIdentities"]
            require(owner() == previous, "global_container_ownership_changed")
            if args.action == "verify":
                file_inventory(BACKEND, "/app", {**plan["backendInventory"], MANIFEST: plan["backendAfter"]})
                file_inventory(WEB, STATIC, {**plan["webInventory"], **plan["webDelta"]})
                downloads = verify_public(plan)
                print(json.dumps({"verified": True, "version": "2.0.0", "downloads": len(downloads)}))
            else:
                rollback(plan, previous)
                print('{"rolledBack":true,"version":"1.3.6"}')


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Global companion cutover stopped: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from None
