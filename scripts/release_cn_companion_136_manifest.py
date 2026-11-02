"""Publish the reviewed CN 1.3.6 manifest without restarting business containers.

Default execution is read-only. --apply stages public metadata, adds exactly one
manifest layer to the actual immutable running image, and atomically changes one runtime
JSON file. OSS upload and artifact verification happen separately, before apply.
No environment, credentials, user content, or backend source is transferred.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys


VERSION = "1.3.6"
BASE_IMAGE = "sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a"
OLD_MANIFEST_SHA = "76ba8b6009071d4c4c0b824b6bbbf1c05c7d848f95c1ab08649c9e9e05c4a76a"
HEARTBEAT_SHA = "26b2e46196b47ff8c4d0a64ec3f90885a3a90f3045509a2715d0d19459510516"
APP_ROOT = "/app/apps/backend/app"
MANIFEST_NAME = "desktop_release_manifest.json"
BACKEND_NAME = "compose-backend-1"
PRESERVED_TAG = "compose-backend:latest"
PRESERVED_TAG_IMAGE = "sha256:eb242b56fded1473659c2f4517f07b42eeaff138b59029e5819fbaa972b12488"
BASE_INPUTS_SHA = "f2e6c5911519a01bc3bd687748a78939d9a149eb748cfa86dd9b121bc34f8641"
MANIFEST_INPUT = "apps/backend/app/desktop_release_manifest.json"
COMPOSE_DIR = "/opt/offersteady/releases/20261101-cn-mock-1/backend"
EXPECTED_COMPOSE_FILES = {*(f"{COMPOSE_DIR}/compose-{index}.before" for index in range(14)),
                          f"{COMPOSE_DIR}/new.compose.json"}
EXPECTED_NAMES = {"compose-backend-1", "compose-web-1", "compose-material-worker-1", "compose-admin-1", "compose-postgres-1", "compose-redis-1", "compose-promotion-analytics-1", "compose-analytics-1"}
NEW_TAG = "offersteady-cn-backend:companion-136-manifest-20261102"
ROLLBACK_TAG = "offersteady-cn-backend:companion-136-manifest-rollback-20261102"
DEFAULT_RELEASE_DIR = "/opt/offersteady/releases/20261102-cn-companion-136-1"
TARGETS = {("macos", "arm64"), ("macos", "x64"), ("windows", "x64")}
BUSINESS_FILES = (
    "modules/web.py", "services/realtime_speech_service.py",
    "services/session_service.py", "services/mock_interview_runtime.py",
)


class GuardError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise GuardError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def positive_int(value):
    return type(value) is int and value > 0


def validate_manifest(payload):
    require(isinstance(payload, dict) and type(payload.get("version")) is int
            and payload["version"] == 1, "unsupported manifest version")
    require(positive_int(payload.get("generatedAtMs")), "missing publication timestamp")
    entries = payload.get("entries")
    require(isinstance(entries, list) and len(entries) == 3, "all three official targets are required")
    targets, ids = set(), set()
    for entry in entries:
        require(isinstance(entry, dict), "invalid release entry")
        target = (entry.get("platform"), entry.get("architecture"))
        require(all(isinstance(value, str) for value in target), "invalid platform type")
        require(target in TARGETS and target not in targets, "unexpected or duplicate platform")
        targets.add(target)
        release_id = entry.get("id")
        require(isinstance(release_id, str) and release_id and release_id not in ids, "invalid release id")
        ids.add(release_id)
        require(entry.get("version") == VERSION and entry.get("protocolVersion") == "2.0",
                "unaligned version or protocol")
        require(entry.get("distributionStatus") == "published" and entry.get("developmentOnly") is False,
                "release is not production-published")
        require(positive_int(entry.get("fileSizeBytes")) and entry["fileSizeBytes"] < 2_000_000_000,
                "invalid artifact size")
        checksum = entry.get("sha256")
        require(isinstance(checksum, str) and re.fullmatch(r"[0-9a-f]{64}", checksum)
                and checksum != "0" * 64, "invalid artifact checksum")
        require(positive_int(entry.get("publishedAtMs")) and entry["publishedAtMs"] == payload["generatedAtMs"],
                "publication timestamps disagree")
        platform, architecture = target
        filename = (f"OfferSteady-Companion-{VERSION}-macOS-{architecture}.dmg" if platform == "macos"
                    else f"OfferSteady-Companion-Setup-{VERSION}-Windows-x64.exe")
        require(entry.get("fileName") == filename, "unexpected artifact filename or edition")
        require(entry.get("objectKey") == f"desktop-releases/{platform}/{architecture}/{VERSION}/{filename}",
                "artifact object does not target the CN immutable release")
        capabilities = entry.get("capabilities")
        require(isinstance(capabilities, dict) and capabilities.get("microphone") is True
                and capabilities.get("systemAudio") is True, "audio capabilities missing")
        if platform == "macos":
            require(entry.get("minimumOs") == "macOS 14.2+", "Mac OS baseline changed")
            require(entry.get("signingStatus") == "verified" and entry.get("notarized") is True,
                    "Mac artifact lacks verified signing or notarization")
        else:
            require(entry.get("minimumOs") == "Windows 10 22H2+", "Windows OS baseline changed")
            require(entry.get("signingStatus") in {"unsigned", "local-development"}
                    and entry.get("notarized") is False, "Windows trust metadata is not truthful")
        require(not any(key in entry for key in ("localPath", "artifactPath", "zipPath")),
                "private local artifact metadata cannot be published")
    require(targets == TARGETS, "missing platform")


def atomic_switch(path, pending, expected_old_sha, expected_new_sha, source_hashes,
                  *, restore_baseline=False):
    """CAS under a file lock, then rename; used identically locally and in Docker."""
    import fcntl

    path, pending = Path(path), Path(pending)
    require(path.parent == pending.parent and path != pending, "pending manifest must share its directory")
    require(not path.is_symlink() and not pending.is_symlink(), "manifest symlink refused")
    with path.with_name(".desktop-release-manifest.lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        candidate = pending.read_bytes()
        require(digest(candidate) == expected_new_sha, "staged manifest checksum drift")
        if restore_baseline:
            require(expected_new_sha == OLD_MANIFEST_SHA, "rollback is not the reviewed baseline")
            json.loads(candidate)
        else:
            validate_manifest(json.loads(candidate))
        require(digest(path.read_bytes()) == expected_old_sha, "runtime manifest changed before switch")
        for relative, checksum in source_hashes.items():
            require(isinstance(relative, str) and not PurePosixPath(relative).is_absolute()
                    and ".." not in PurePosixPath(relative).parts, "invalid source path")
            require(digest((path.parents[3] / relative).read_bytes()) == checksum, "runtime source drift before switch")
        os.chmod(pending, 0o644)
        with pending.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(pending, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def portable_atomic_source():
    functions = (require, digest, positive_int, validate_manifest, atomic_switch)
    constants = {"VERSION": VERSION, "TARGETS": TARGETS, "BUSINESS_FILES": BUSINESS_FILES,
                 "OLD_MANIFEST_SHA": OLD_MANIFEST_SHA}
    return ("import hashlib,json,os,re,sys\nfrom pathlib import Path,PurePosixPath\n"
            + "class GuardError(RuntimeError): pass\n"
            + "\n".join(f"{key} = {value!r}" for key, value in constants.items()) + "\n"
            + "\n".join(inspect.getsource(function) for function in functions)
            + "\np=json.loads(sys.argv[1]); atomic_switch(**p)\n")


def validate_release_directory(value):
    require(value == DEFAULT_RELEASE_DIR, "only the reviewed CN release directory is allowed")
    require(str(PurePosixPath(value)) == value, "noncanonical release directory")
    return value


def load_plan(manifest_path, baseline_dir, release_directory):
    release_directory = validate_release_directory(release_directory)
    manifest = Path(manifest_path).read_bytes()
    validate_manifest(json.loads(manifest))
    baseline_dir = Path(baseline_dir).resolve()
    old_manifest = (baseline_dir / "desktop_release_manifest.before.json").read_bytes()
    summary = json.loads((baseline_dir / "component-summary.before.json").read_bytes())
    inputs_data = (baseline_dir / "backend-runtime-manifest.before.json").read_bytes()
    require(digest(old_manifest) == OLD_MANIFEST_SHA, "old public manifest is not the reviewed baseline")
    require(digest(inputs_data) == BASE_INPUTS_SHA, "complete runtime input baseline drift")
    inputs = json.loads(inputs_data)
    require(isinstance(inputs, dict) and len(inputs) == 232, "complete runtime inputs missing")
    require(inputs.get(MANIFEST_INPUT) == OLD_MANIFEST_SHA, "runtime input manifest drift")
    require(all(isinstance(path, str) and not PurePosixPath(path).is_absolute()
                and str(PurePosixPath(path)) == path and ".." not in PurePosixPath(path).parts
                and isinstance(checksum, str) and re.fullmatch(r"[0-9a-f]{64}", checksum)
                for path, checksum in inputs.items()), "invalid complete runtime input")
    compose_files = summary.get("backendComposeFiles", {})
    require(isinstance(compose_files, dict) and set(compose_files) == EXPECTED_COMPOSE_FILES
            and all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                    for value in compose_files.values()), "backend frozen compose baseline missing or invalid")
    components = summary.get("components")
    require(isinstance(components, list) and len(components) == 8, "eight-component baseline required")
    names = [component.get("name") for component in components]
    require(len(names) == len(set(names)) and set(names) == EXPECTED_NAMES, "component baseline is ambiguous")
    backend = next(component for component in components if component["name"] == BACKEND_NAME)
    require(backend["image"] == BASE_IMAGE and backend["imageName"] == BASE_IMAGE,
            "baseline is not the actual immutable running image")
    require(not backend.get("mounts"), "unexpected backend mounts")
    files = summary.get("backendFileHashes", {})
    require(set(files) == {*BUSINESS_FILES, MANIFEST_NAME}, "incomplete runtime source baseline")
    require(files[MANIFEST_NAME] == OLD_MANIFEST_SHA
            and files["services/realtime_speech_service.py"] == HEARTBEAT_SHA,
            "lightweight heartbeat baseline changed")
    require(all(inputs.get("apps/backend/app/" + path) == checksum for path, checksum in files.items()),
            "partial source hashes disagree with complete input baseline")
    for component in components:
        require(isinstance(component.get("id"), str) and re.fullmatch(r"[0-9a-f]{64}", component["id"]),
                "invalid component identity")
        require(isinstance(component.get("startedAt"), str) and component["startedAt"].endswith("Z"),
                "component startup baseline missing")
        require(isinstance(component.get("runtimeConfigSha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", component["runtimeConfigSha256"]),
                "component runtime configuration baseline missing")
    return {"manifest": manifest, "oldManifest": old_manifest, "summary": summary,
            "baselineDir": baseline_dir, "releaseDirectory": release_directory,
            "newManifestSha": digest(manifest), "inputs": inputs, "inputsData": inputs_data,
            "businessHashes": {key: files[key] for key in BUSINESS_FILES}}


class Remote:
    def __init__(self):
        self.ssh = ["ssh", "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-i",
                    str(Path.home() / ".ssh/id_ed25519_oneshowtools_server"), "-o", "ConnectTimeout=10",
                    "-o", "StrictHostKeyChecking=yes", "root@101.133.147.212"]

    def run(self, argv, *, data=None, timeout=60, allow_failure=False):
        result = subprocess.run([*self.ssh, shlex.join(argv)], input=data, capture_output=True, timeout=timeout)
        if result.returncode and not allow_failure:
            raise GuardError(f"remote {argv[0]} operation failed (exit {result.returncode}); output withheld")
        return result

    def inspect_containers(self, names):
        return json.loads(self.run(["docker", "inspect", *names]).stdout)

    def image(self, name, *, missing_ok=False):
        result = self.run(["docker", "image", "inspect", name], allow_failure=missing_ok)
        return None if result.returncode else json.loads(result.stdout)[0]

    def hashes(self, image_or_container, files, *, candidate=False):
        # Full inventory paths are rooted at /app, not at the Python package.
        source = ("from pathlib import Path;import hashlib,json;"
                  f"p=Path('/app');files={tuple(files)!r};"
                  "print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files}))")
        argv = (["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                 "--security-opt", "no-new-privileges", "--entrypoint", "python", image_or_container]
                if candidate else ["docker", "exec", image_or_container, "python"])
        return json.loads(self.run([*argv, "-B", "-c", source]).stdout)

    def host_hashes(self, paths):
        code = ("import sys,json,hashlib;from pathlib import Path;"
                "paths=json.loads(sys.argv[1]);"
                "print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}))")
        return json.loads(self.run(["python3", "-c", code, json.dumps(list(paths))]).stdout)

    def put_exclusive(self, path, data):
        code = ("import os,sys;from pathlib import Path;p=Path(sys.argv[1]);"
                "f=p.open('xb');f.write(sys.stdin.buffer.read());f.flush();os.fsync(f.fileno());f.close();os.chmod(p,0o644)")
        self.run(["python3", "-c", code, path], data=data)

    def read_public_file(self, path, *, missing_ok=False):
        code = "import sys;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())"
        result = self.run(["python3", "-c", code, path], allow_failure=missing_ok)
        return None if result.returncode else result.stdout

    def manifest_mode(self, image):
        code = f"from pathlib import Path;print(Path({(APP_ROOT + '/' + MANIFEST_NAME)!r}).stat().st_mode & 0o777)"
        args = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--entrypoint", "python", image, "-B", "-c", code]
        return int(self.run(args).stdout)


def runtime_config_sha(record):
    # A digest only: Config can contain private Env values, never persist it.
    return digest(json.dumps({key: record.get(key) for key in ("Config", "HostConfig", "Mounts")},
                             sort_keys=True, separators=(",", ":")).encode())


def runtime_config_matches(record, expected_sha):
    """Preserve the published raw digest; allow only Docker's two-mount order.

    The frozen CN scope has at most two mounts per component. Compare the
    original whole Config/HostConfig/Mounts digest first. If Docker emits those
    two complete mount objects in reverse order, reproduce the original digest
    by swapping only those objects. No field, mount, duplicate or value is
    dropped, normalized or ignored, and no baseline evidence is rewritten.
    """
    if runtime_config_sha(record) == expected_sha:
        return True
    mounts = record.get("Mounts")
    if not isinstance(mounts, list) or len(mounts) != 2:
        return False
    return runtime_config_sha({**record, "Mounts": [mounts[1], mounts[0]]}) == expected_sha


def verify_components(baseline, actual):
    actual = {record["Name"].lstrip("/"): record for record in actual}
    require(set(actual) == {record["name"] for record in baseline}, "component count or names changed")
    for expected in baseline:
        now = actual[expected["name"]]
        require((now["Id"], now["Image"], now["Config"]["Image"], now["State"]["StartedAt"], now["RestartCount"]) ==
                (expected["id"], expected["image"], expected["imageName"], expected["startedAt"], expected["restartCount"]),
                "production component lifecycle drift")
        require(runtime_config_matches(now, expected["runtimeConfigSha256"]), "component runtime configuration drift")
        require(now["State"]["Running"], "production component is not running")
        if expected["name"] == BACKEND_NAME:
            require(now["State"].get("Health", {}).get("Status") == "healthy", "backend is not healthy")
            require(not now.get("Mounts"), "backend mount drift")


def expected_inputs(plan, manifest_sha):
    return {**plan["inputs"], MANIFEST_INPUT: manifest_sha}


def verify_live(remote, plan, *, published=False):
    components = plan["summary"]["components"]
    actual = remote.inspect_containers([component["name"] for component in components])
    verify_components(components, actual)
    backend = next(record for record in actual if record["Name"].lstrip("/") == BACKEND_NAME)
    files = plan["summary"]["backendComposeFiles"]
    require(set(backend["Config"].get("Labels", {}).get("com.docker.compose.project.config_files", "").split(","))
            == set(files), "backend frozen compose ownership drift")
    require(remote.host_hashes(files) == files, "backend frozen compose file drift")
    expected = expected_inputs(plan, plan["newManifestSha"] if published else OLD_MANIFEST_SHA)
    require(remote.hashes(BACKEND_NAME, expected) == expected, "complete runtime inputs or manifest drift")
    require(remote.image(PRESERVED_TAG)["Id"] == PRESERVED_TAG_IMAGE, "untargeted legacy Compose tag drift")


def build_dockerfile():
    # The CN host has no Buildx; legacy COPY preserves the source's 0644 mode,
    # which put_exclusive establishes and verify_candidate checks in the image.
    return (f"FROM {ROLLBACK_TAG}\n"
            f"COPY {MANIFEST_NAME} {APP_ROOT}/{MANIFEST_NAME}\n").encode()


def staged_contents(plan):
    return {"desktop_release_manifest.before.json": plan["oldManifest"],
            "component-summary.before.json": (json.dumps(plan["summary"], indent=2) + "\n").encode(),
            "backend-runtime-manifest.before.json": plan["inputsData"],
            MANIFEST_NAME: plan["manifest"]}


def verify_staged(remote, plan):
    directory = plan["releaseDirectory"]
    for filename, expected in staged_contents(plan).items():
        require(remote.read_public_file(f"{directory}/{filename}") == expected,
                f"staged {filename} does not match the reviewed plan")
    require(remote.read_public_file(f"{directory}/Dockerfile") == build_dockerfile(),
            "staged Dockerfile is not the reviewed manifest-only build")
    require(remote.image(ROLLBACK_TAG)["Id"] == BASE_IMAGE, "staged rollback image drift")
    candidate = remote.image(NEW_TAG, missing_ok=True)
    if candidate is not None:
        verify_candidate(remote, plan, candidate)
    return candidate


def preserve_or_verify(remote, path, data):
    existing = remote.read_public_file(path, missing_ok=True)
    if existing is None:
        remote.put_exclusive(path, data)
    else:
        require(existing == data, "existing release evidence differs from this candidate")


def verify_candidate(remote, plan, candidate):
    base = remote.image(ROLLBACK_TAG)
    require(base["Id"] == BASE_IMAGE, "rollback tag no longer matches actual baseline")
    layers, old_layers = candidate["RootFS"]["Layers"], base["RootFS"]["Layers"]
    require(len(layers) == len(old_layers) + 1 and layers[:-1] == old_layers,
            "candidate is not exactly one manifest layer above baseline")
    require(candidate["Config"] == base["Config"], "candidate image configuration changed")
    expected = expected_inputs(plan, plan["newManifestSha"])
    require(remote.hashes(candidate["Id"], expected, candidate=True) == expected,
            "candidate did not preserve complete runtime inputs")
    require(remote.manifest_mode(candidate["Id"]) == 0o644, "candidate manifest permission is not 0644")


def switch_arguments(plan, *, rollback=False):
    return {"path": f"{APP_ROOT}/{MANIFEST_NAME}",
            "pending": f"{APP_ROOT}/.desktop-manifest-136-{'rollback' if rollback else plan['newManifestSha'][:12]}.pending",
            "expected_old_sha": plan["newManifestSha"] if rollback else OLD_MANIFEST_SHA,
            "expected_new_sha": OLD_MANIFEST_SHA if rollback else plan["newManifestSha"],
            "source_hashes": {key: value for key, value in plan["inputs"].items() if key != MANIFEST_INPUT},
            "restore_baseline": rollback}


def copy_and_switch(remote, plan, *, rollback=False):
    args = switch_arguments(plan, rollback=rollback)
    code = ("from pathlib import Path;import sys;p=Path(sys.argv[1]);"
            "sys.exit('staged manifest already exists') if p.exists() or p.is_symlink() else None")
    remote.run(["docker", "exec", BACKEND_NAME, "python", "-B", "-c", code, args["pending"]])
    filename = "desktop_release_manifest.before.json" if rollback else MANIFEST_NAME
    remote.run(["docker", "cp", f"{plan['releaseDirectory']}/{filename}", f"{BACKEND_NAME}:{args['pending']}"])
    remote.run(["docker", "exec", BACKEND_NAME, "python", "-B", "-c", portable_atomic_source(), json.dumps(args)])


def report_for(plan, candidate):
    return {"version": VERSION, "newManifestSha256": plan["newManifestSha"],
            "runningImage": BASE_IMAGE, "durableRecreateImage": candidate["Id"],
            "durableImageTag": NEW_TAG, "rollbackTag": ROLLBACK_TAG,
            "preservedLegacyTag": PRESERVED_TAG, "preservedLegacyImage": PRESERVED_TAG_IMAGE,
            "releaseDirectory": plan["releaseDirectory"], "containersRestarted": False,
            "runtimeInputCount": len(plan["inputs"]), "publicManifestOnly": True}


def overlay_for(candidate):
    # Explicit opt-in for the next controlled recreation, not a modified historical compose file.
    return (json.dumps({"services": {"backend": {"image": candidate["Id"]}}}, indent=2) + "\n").encode()


def verify_published(remote, plan):
    verify_live(remote, plan, published=True)
    candidate = verify_staged(remote, plan)
    require(candidate is not None, "published candidate image missing")
    report = report_for(plan, candidate)
    require(remote.read_public_file(f"{plan['releaseDirectory']}/candidate-image.json") ==
            (json.dumps(report, indent=2) + "\n").encode(), "durable candidate record drift")
    require(remote.read_public_file(f"{plan['releaseDirectory']}/backend-image.compose.json") == overlay_for(candidate),
            "durable recreation overlay drift")
    # deployed.json may be absent if SSH acknowledgement was lost after a successful switch.
    saved = remote.read_public_file(f"{plan['releaseDirectory']}/deployed.json", missing_ok=True)
    require(saved is None or saved == (json.dumps(report, indent=2) + "\n").encode(), "published record drift")
    return {**report, "verifiedPublished": True, "deployedRecordPresent": saved is not None}


def rollback(remote, plan):
    current = remote.hashes(BACKEND_NAME, [MANIFEST_INPUT])[MANIFEST_INPUT]
    if current == OLD_MANIFEST_SHA:
        verify_live(remote, plan)
        candidate = verify_staged(remote, plan)
        require(candidate is not None, "rollback candidate image missing")
        expected = {"version": VERSION, "rolledBack": True, "restoredManifestSha256": OLD_MANIFEST_SHA,
                    "containersRestarted": False, "durableRecreateImage": BASE_IMAGE}
        require(remote.read_public_file(f"{plan['releaseDirectory']}/rolled-back.json") ==
                (json.dumps(expected, indent=2) + "\n").encode(), "exact prior rollback record missing")
        require(remote.read_public_file(f"{plan['releaseDirectory']}/rollback-image.compose.json") ==
                overlay_for({"Id": BASE_IMAGE}), "rollback recreation overlay drift")
        return {**expected, "verifiedRolledBack": True}
    verify_published(remote, plan)
    try:
        copy_and_switch(remote, plan, rollback=True)
    except Exception:
        # Retry is never blind: an interrupted SSH call may already have restored the file.
        verify_live(remote, plan)
    verify_live(remote, plan)
    evidence = {"version": VERSION, "rolledBack": True, "restoredManifestSha256": OLD_MANIFEST_SHA,
                "containersRestarted": False, "durableRecreateImage": BASE_IMAGE}
    preserve_or_verify(remote, f"{plan['releaseDirectory']}/rollback-image.compose.json",
                       overlay_for({"Id": BASE_IMAGE}))
    preserve_or_verify(remote, f"{plan['releaseDirectory']}/rolled-back.json",
                       (json.dumps(evidence, indent=2) + "\n").encode())
    return evidence


def apply(remote, plan, *, resume_staged=False):
    current = remote.hashes(BACKEND_NAME, [MANIFEST_INPUT])[MANIFEST_INPUT]
    if current == plan["newManifestSha"]:
        # Idempotent rerun does not rebuild, switch, or touch any metadata.
        return verify_published(remote, plan)
    verify_live(remote, plan)
    release_dir = plan["releaseDirectory"]
    candidate = None
    if resume_staged:
        candidate = verify_staged(remote, plan)
    else:
        require(remote.image(NEW_TAG, missing_ok=True) is None, "candidate tag already exists; inspect prior attempt")
        previous = remote.image(ROLLBACK_TAG, missing_ok=True)
        require(previous is None or previous["Id"] == BASE_IMAGE, "rollback tag belongs to another image")
        remote.run(["python3", "-c", "import os,sys;os.mkdir(sys.argv[1],0o700)", release_dir])
        for filename, data in staged_contents(plan).items():
            remote.put_exclusive(f"{release_dir}/{filename}", data)
        remote.put_exclusive(f"{release_dir}/Dockerfile", build_dockerfile())
        remote.run(["docker", "tag", BASE_IMAGE, ROLLBACK_TAG])
    require(remote.image(ROLLBACK_TAG)["Id"] == BASE_IMAGE, "rollback tag failed verification")
    if candidate is None:
        remote.run(["docker", "build", "--pull=false", "--network=none", "-t", NEW_TAG,
                    "-f", f"{release_dir}/Dockerfile", release_dir], timeout=180)
        candidate = remote.image(NEW_TAG)
    verify_candidate(remote, plan, candidate)
    report = report_for(plan, candidate)
    report_data = (json.dumps(report, indent=2) + "\n").encode()
    preserve_or_verify(remote, f"{release_dir}/candidate-image.json", report_data)
    preserve_or_verify(remote, f"{release_dir}/backend-image.compose.json", overlay_for(candidate))
    verify_live(remote, plan)
    try:
        copy_and_switch(remote, plan)
        verify_live(remote, plan, published=True)
    except Exception:
        # Keep protection strict on source/config/container drift and inspect real file state.
        current = remote.hashes(BACKEND_NAME, [MANIFEST_INPUT])[MANIFEST_INPUT]
        require(current in {OLD_MANIFEST_SHA, plan["newManifestSha"]},
                "unknown runtime manifest during recovery; manual inspection required")
        verify_live(remote, plan, published=current == plan["newManifestSha"])
        if current == plan["newManifestSha"]:
            try:
                copy_and_switch(remote, plan, rollback=True)
            except Exception:
                verify_live(remote, plan)
        verify_live(remote, plan)
        raise
    preserve_or_verify(remote, f"{release_dir}/deployed.json", report_data)
    (plan["baselineDir"].parent / "deployed.json").write_bytes(report_data)
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--release-directory", default=DEFAULT_RELEASE_DIR)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="Stage and publish only reviewed release metadata.")
    action.add_argument("--verify-published", action="store_true", help="Read-only exact published-state verification.")
    action.add_argument("--rollback", action="store_true", help="Restore the exact pre-release manifest without a restart.")
    parser.add_argument("--resume-staged", action="store_true",
                        help="Verify and resume exactly the previously staged public metadata; still requires --apply to write.")
    args = parser.parse_args(argv)
    plan = load_plan(args.manifest, args.baseline_dir, args.release_directory)
    remote = Remote()
    if args.resume_staged and not args.apply:
        parser.error("--resume-staged requires --apply")
    if args.verify_published:
        report = verify_published(remote, plan)
    elif args.rollback:
        report = rollback(remote, plan)
    elif args.apply:
        report = apply(remote, plan, resume_staged=args.resume_staged)
    else:
        verify_live(remote, plan)
        if args.resume_staged:
            verify_staged(remote, plan)
        report = {"dryRun": True, "version": VERSION, "baseImage": BASE_IMAGE,
                  "newManifestSha256": plan["newManifestSha"], "releaseDirectory": plan["releaseDirectory"],
                  "targets": 3, "businessContainersWillRestart": False, "resumeStaged": args.resume_staged}
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GuardError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"CN manifest publication stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
