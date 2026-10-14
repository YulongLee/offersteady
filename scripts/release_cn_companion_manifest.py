"""Publish the reviewed CN 1.3.5 manifest without restarting business containers.

Default execution is read-only. --apply stages public metadata, adds exactly one
manifest layer to the actual heartbeat image, and atomically changes one runtime
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


VERSION = "1.3.5"
BASE_IMAGE = "sha256:ec510532ca598878e147c4277e6da9776924fbf056ed942ab4cc2bf110f398bb"
OLD_MANIFEST_SHA = "10a217b8dd766bd46b6ebfacc6d020bdcd356f5b2fa997ac6cd6f72f281db1d4"
HEARTBEAT_SHA = "fdef7f2f7cfb47302415dac9ba255e4be9cd4bdb928b04f1c92283ff487c0fc2"
APP_ROOT = "/app/apps/backend/app"
MANIFEST_NAME = "desktop_release_manifest.json"
BACKEND_NAME = "compose-backend-1"
FUTURE_TAG = "compose-backend:latest"
NEW_TAG = "offersteady-cn-backend:companion-135-manifest-20261015"
ROLLBACK_TAG = "offersteady-cn-backend:companion-135-manifest-rollback-20261015"
DEFAULT_RELEASE_DIR = "/opt/offersteady/releases/20261015-cn-companion-135-1"
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


def atomic_switch(path, pending, expected_old_sha, expected_new_sha, business_hashes,
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
        for relative, checksum in business_hashes.items():
            require(relative in BUSINESS_FILES, "unexpected business file")
            require(digest((path.parent / relative).read_bytes()) == checksum, "business source drift before switch")
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
    return ("import hashlib,json,os,re,sys\nfrom pathlib import Path\n"
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
    require(digest(old_manifest) == OLD_MANIFEST_SHA, "old public manifest is not the reviewed baseline")
    components = summary.get("components")
    require(isinstance(components, list) and len(components) >= 4, "component baseline missing")
    names = [component.get("name") for component in components]
    require(len(names) == len(set(names)) and BACKEND_NAME in names, "component baseline is ambiguous")
    backend = next(component for component in components if component["name"] == BACKEND_NAME)
    require(backend["image"] == BASE_IMAGE and backend["imageName"] == "compose-backend",
            "baseline is not the actual heartbeat image")
    require(not backend.get("mounts"), "unexpected backend mounts")
    files = summary.get("backendFileHashes", {})
    require(set(files) == {*BUSINESS_FILES, MANIFEST_NAME}, "incomplete runtime source baseline")
    require(files[MANIFEST_NAME] == OLD_MANIFEST_SHA
            and files["services/realtime_speech_service.py"] == HEARTBEAT_SHA,
            "lightweight heartbeat baseline changed")
    require(all(isinstance(checksum, str) and re.fullmatch(r"[0-9a-f]{64}", checksum)
                for checksum in files.values()), "invalid business source checksum")
    for component in components:
        require(isinstance(component.get("id"), str) and re.fullmatch(r"[0-9a-f]{64}", component["id"]),
                "invalid component identity")
        require(isinstance(component.get("startedAt"), str) and component["startedAt"].endswith("Z"),
                "component startup baseline missing")
    return {"manifest": manifest, "oldManifest": old_manifest, "summary": summary,
            "baselineDir": baseline_dir, "releaseDirectory": release_directory,
            "newManifestSha": digest(manifest), "businessHashes": {key: files[key] for key in BUSINESS_FILES}}


class Remote:
    def __init__(self):
        self.ssh = ["ssh", "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-i",
                    str(Path.home() / ".ssh/id_ed25519_oneshowtools_server"), "root@101.133.147.212"]

    def run(self, argv, *, data=None, timeout=60, allow_failure=False):
        # Each remote argument is quoted independently; JSON is never shell escaping.
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
        source = ("from pathlib import Path;import hashlib,json;"
                  f"p=Path({APP_ROOT!r});files={tuple(files)!r};"
                  "print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files}))")
        argv = (["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                 "--security-opt", "no-new-privileges", "--entrypoint", "python", image_or_container]
                if candidate else ["docker", "exec", image_or_container, "python"])
        return json.loads(self.run([*argv, "-B", "-c", source]).stdout)

    def put_exclusive(self, path, data):
        code = ("import os,sys;from pathlib import Path;p=Path(sys.argv[1]);"
                "f=p.open('xb');f.write(sys.stdin.buffer.read());f.flush();os.fsync(f.fileno());f.close();os.chmod(p,0o644)")
        self.run(["python3", "-c", code, path], data=data)

    def read_public_file(self, path, *, missing_ok=False):
        code = "import sys;from pathlib import Path;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())"
        result = self.run(["python3", "-c", code, path], allow_failure=missing_ok)
        return None if result.returncode else result.stdout

    def replace_public_exact(self, path, before, after):
        code = '''import hashlib,os,sys
from pathlib import Path
p=Path(sys.argv[1]); data=sys.stdin.buffer.read()
if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sys.argv[2]:
 raise SystemExit("staged Dockerfile changed during recovery")
if hashlib.sha256(data).hexdigest()!=sys.argv[3]:
 raise SystemExit("replacement Dockerfile checksum mismatch")
pending=p.with_name(p.name+".resume.pending")
with pending.open("xb") as f:
 f.write(data); f.flush(); os.fsync(f.fileno())
os.chmod(pending,0o644); os.replace(pending,p)
directory=os.open(p.parent,os.O_RDONLY)
try: os.fsync(directory)
finally: os.close(directory)
'''
        self.run(["python3", "-c", code, path, digest(before), digest(after)], data=after)

    def manifest_mode(self, image):
        code = f"from pathlib import Path;print(Path({(APP_ROOT + '/' + MANIFEST_NAME)!r}).stat().st_mode & 0o777)"
        args = ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--entrypoint", "python", image, "-B", "-c", code]
        return int(self.run(args).stdout)


def verify_components(baseline, actual):
    actual = {record["Name"].lstrip("/"): record for record in actual}
    for expected in baseline:
        now = actual.get(expected["name"])
        require(now is not None, "production component disappeared")
        require((now["Id"], now["Image"], now["State"]["StartedAt"], now["RestartCount"]) ==
                (expected["id"], expected["image"], expected["startedAt"], expected["restartCount"]),
                "production component lifecycle drift")
        require(now["State"]["Running"], "production component is not running")
        if expected["name"] == BACKEND_NAME:
            require(now["State"].get("Health", {}).get("Status") == "healthy", "backend is not healthy")
            require(not now.get("Mounts"), "backend mount drift")


def verify_live(remote, plan, *, expected_manifest_sha=None, expected_future_image=None):
    expected_manifest_sha = expected_manifest_sha or OLD_MANIFEST_SHA
    expected_future_image = expected_future_image or BASE_IMAGE
    components = plan["summary"]["components"]
    verify_components(components, remote.inspect_containers([component["name"] for component in components]))
    expected = {**plan["businessHashes"], MANIFEST_NAME: expected_manifest_sha}
    require(remote.hashes(BACKEND_NAME, expected) == expected, "runtime manifest or business source drift")
    require(remote.image(FUTURE_TAG)["Id"] == expected_future_image, "future Compose image tag drift")


def build_dockerfile():
    # The CN host has no Buildx; legacy COPY preserves the source's 0644 mode,
    # which put_exclusive establishes and verify_candidate checks in the image.
    return (f"FROM {ROLLBACK_TAG}\n"
            f"COPY {MANIFEST_NAME} {APP_ROOT}/{MANIFEST_NAME}\n").encode()


def original_buildkit_dockerfile():
    return (f"FROM {ROLLBACK_TAG}\n"
            f"COPY --chmod=0644 {MANIFEST_NAME} {APP_ROOT}/{MANIFEST_NAME}\n").encode()


def staged_contents(plan):
    return {"desktop_release_manifest.before.json": plan["oldManifest"],
            "component-summary.before.json": (json.dumps(plan["summary"], indent=2) + "\n").encode(),
            MANIFEST_NAME: plan["manifest"]}


def verify_staged(remote, plan):
    directory = plan["releaseDirectory"]
    for filename, expected in staged_contents(plan).items():
        require(remote.read_public_file(f"{directory}/{filename}") == expected,
                f"staged {filename} does not match the reviewed plan")
    dockerfile = remote.read_public_file(f"{directory}/Dockerfile")
    require(dockerfile in {build_dockerfile(), original_buildkit_dockerfile()},
            "staged Dockerfile is not a reviewed manifest-only build")
    require(remote.image(ROLLBACK_TAG)["Id"] == BASE_IMAGE, "staged rollback image drift")
    candidate = remote.image(NEW_TAG, missing_ok=True)
    if candidate is not None:
        verify_candidate(remote, plan, candidate)
    for filename in ("Dockerfile.buildkit-required.before", "Dockerfile.first-attempt"):
        backup = remote.read_public_file(f"{directory}/{filename}", missing_ok=True)
        require(backup is None or backup == original_buildkit_dockerfile(), "failed Dockerfile backup drift")
    return dockerfile, candidate


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
    expected = {**plan["businessHashes"], MANIFEST_NAME: plan["newManifestSha"]}
    require(remote.hashes(candidate["Id"], expected, candidate=True) == expected,
            "candidate did not preserve heartbeat and business source")
    require(remote.manifest_mode(candidate["Id"]) == 0o644, "candidate manifest permission is not 0644")


def switch_arguments(plan, *, rollback=False):
    return {"path": f"{APP_ROOT}/{MANIFEST_NAME}",
            "pending": f"{APP_ROOT}/.desktop-manifest-135-{'rollback' if rollback else plan['newManifestSha'][:12]}.pending",
            "expected_old_sha": plan["newManifestSha"] if rollback else OLD_MANIFEST_SHA,
            "expected_new_sha": OLD_MANIFEST_SHA if rollback else plan["newManifestSha"],
            "business_hashes": plan["businessHashes"], "restore_baseline": rollback}


def copy_and_switch(remote, plan, *, rollback=False):
    args = switch_arguments(plan, rollback=rollback)
    code = ("from pathlib import Path;import sys;p=Path(sys.argv[1]);"
            "sys.exit('staged manifest already exists') if p.exists() or p.is_symlink() else None")
    remote.run(["docker", "exec", BACKEND_NAME, "python", "-B", "-c", code, args["pending"]])
    filename = "desktop_release_manifest.before.json" if rollback else MANIFEST_NAME
    remote.run(["docker", "cp", f"{plan['releaseDirectory']}/{filename}", f"{BACKEND_NAME}:{args['pending']}"])
    remote.run(["docker", "exec", BACKEND_NAME, "python", "-B", "-c", portable_atomic_source(), json.dumps(args)])


def apply(remote, plan, *, resume_staged=False):
    verify_live(remote, plan)
    release_dir = plan["releaseDirectory"]
    candidate = None
    if resume_staged:
        dockerfile, candidate = verify_staged(remote, plan)
        if dockerfile != build_dockerfile():
            preserve_or_verify(remote, f"{release_dir}/Dockerfile.buildkit-required.before", dockerfile)
            remote.replace_public_exact(f"{release_dir}/Dockerfile", dockerfile, build_dockerfile())
    else:
        require(remote.image(NEW_TAG, missing_ok=True) is None, "candidate tag already exists; inspect prior attempt")
        rollback = remote.image(ROLLBACK_TAG, missing_ok=True)
        require(rollback is None or rollback["Id"] == BASE_IMAGE, "rollback tag belongs to another image")
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
    report = {"version": VERSION, "newManifestSha256": plan["newManifestSha"],
              "runningImage": BASE_IMAGE, "futureRecreateImage": candidate["Id"],
              "futureTag": FUTURE_TAG, "rollbackTag": ROLLBACK_TAG,
              "releaseDirectory": release_dir, "containersRestarted": False}
    # Both durable backups and the validated candidate exist before public change.
    preserve_or_verify(remote, f"{release_dir}/candidate-image.json", (json.dumps(report, indent=2) + "\n").encode())
    verify_live(remote, plan)
    try:
        remote.run(["docker", "tag", candidate["Id"], FUTURE_TAG])
        verify_live(remote, plan, expected_future_image=candidate["Id"])
        copy_and_switch(remote, plan)
        verify_live(remote, plan, expected_manifest_sha=plan["newManifestSha"], expected_future_image=candidate["Id"])
    except Exception:
        # A lost SSH response can follow a successful rename. Inspect the file,
        # rather than relying on whether the remote command returned success.
        verify_components(plan["summary"]["components"], remote.inspect_containers(
            [component["name"] for component in plan["summary"]["components"]]))
        current = remote.hashes(BACKEND_NAME, [MANIFEST_NAME])[MANIFEST_NAME]
        require(current in {OLD_MANIFEST_SHA, plan["newManifestSha"]},
                "unknown runtime manifest during recovery; manual inspection required")
        require(remote.image(FUTURE_TAG)["Id"] in {BASE_IMAGE, candidate["Id"]},
                "unknown future image during recovery; manual inspection required")
        if current == plan["newManifestSha"]:
            copy_and_switch(remote, plan, rollback=True)
        remote.run(["docker", "tag", BASE_IMAGE, FUTURE_TAG])
        raise
    report_data = (json.dumps(report, indent=2) + "\n").encode()
    remote.put_exclusive(f"{release_dir}/deployed.json", report_data)
    (plan["baselineDir"].parent / "deployed.json").write_bytes(report_data)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--release-directory", default=DEFAULT_RELEASE_DIR)
    parser.add_argument("--apply", action="store_true", help="Explicitly authorize staging and atomic publication; otherwise read-only.")
    parser.add_argument("--resume-staged", action="store_true",
                        help="Verify and resume exactly the previously staged public metadata; still requires --apply to write.")
    args = parser.parse_args(argv)
    plan = load_plan(args.manifest, args.baseline_dir, args.release_directory)
    remote = Remote()
    if args.apply:
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
