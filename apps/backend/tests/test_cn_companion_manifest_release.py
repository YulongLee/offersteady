"""Synthetic publication regressions; real Docker/SSH operations are forbidden."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import threading

import pytest


@pytest.fixture
def release(monkeypatch):
    path = Path(__file__).resolve().parents[3] / "scripts/release_cn_companion_manifest.py"
    spec = importlib.util.spec_from_file_location("cn_companion_manifest_release", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: pytest.fail("unexpected external operation"))
    return module


@pytest.fixture
def payload(release):
    entries = []
    for platform, architecture in sorted(release.TARGETS):
        filename = (f"OfferSteady-Companion-1.3.5-macOS-{architecture}.dmg" if platform == "macos"
                    else "OfferSteady-Companion-Setup-1.3.5-Windows-x64.exe")
        entries.append({
            "id": f"synthetic-{platform}-{architecture}", "platform": platform, "architecture": architecture,
            "version": "1.3.5", "protocolVersion": "2.0", "distributionStatus": "published",
            "developmentOnly": False, "fileSizeBytes": 123456,
            "sha256": hashlib.sha256(filename.encode()).hexdigest(), "publishedAtMs": 1234,
            "fileName": filename, "objectKey": f"desktop-releases/{platform}/{architecture}/1.3.5/{filename}",
            "minimumOs": "macOS 14.2+" if platform == "macos" else "Windows 10 22H2+",
            "signingStatus": "verified" if platform == "macos" else "unsigned",
            "notarized": platform == "macos", "capabilities": {"microphone": True, "systemAudio": True},
        })
    return {"version": 1, "generatedAtMs": 1234, "entries": entries}


@pytest.mark.parametrize("key,value", [
    ("version", "1.3.2"), ("protocolVersion", "1.0"), ("distributionStatus", "internal"),
    ("developmentOnly", True), ("fileSizeBytes", 0), ("fileSizeBytes", True),
    ("sha256", "0" * 64), ("sha256", "short"), ("publishedAtMs", True),
    ("objectKey", "global-desktop-releases/forbidden"), ("fileName", "local-test.zip"),
    ("localPath", "/tmp/private-artifact"), ("platform", {}),
])
def test_invalid_or_partial_publication_is_rejected_before_external_work(release, payload, key, value):
    payload["entries"][0][key] = value
    with pytest.raises(release.GuardError):
        release.validate_manifest(payload)


def test_all_platforms_and_truthful_trust_are_required(release, payload):
    release.validate_manifest(payload)
    duplicate = deepcopy(payload)
    duplicate["entries"][2] = deepcopy(duplicate["entries"][0])
    with pytest.raises(release.GuardError, match="duplicate"):
        release.validate_manifest(duplicate)
    with pytest.raises(release.GuardError, match="all three"):
        release.validate_manifest({**payload, "entries": payload["entries"][:2]})
    for entry in payload["entries"]:
        bad = deepcopy(payload)
        changed = next(item for item in bad["entries"] if item["id"] == entry["id"])
        changed["notarized"] = not changed["notarized"]
        with pytest.raises(release.GuardError):
            release.validate_manifest(bad)
    mac = deepcopy(payload)
    mac["entries"][0]["minimumOs"] = "macOS 13.4+"
    with pytest.raises(release.GuardError, match="baseline changed"):
        release.validate_manifest(mac)


@pytest.fixture
def files(release, payload, tmp_path, monkeypatch):
    target = tmp_path / release.MANIFEST_NAME
    old = b'{"entries":[],"syntheticOnly":true}\n'
    new = (json.dumps(payload) + "\n").encode()
    target.write_bytes(old)
    pending = tmp_path / ".pending"
    pending.write_bytes(new)
    hashes = {}
    for filename in release.BUSINESS_FILES:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic {filename}".encode())
        hashes[filename] = release.digest(path.read_bytes())
    monkeypatch.setattr(release, "OLD_MANIFEST_SHA", release.digest(old))
    return {"path": target, "pending": pending, "expected_old_sha": release.digest(old),
            "expected_new_sha": release.digest(new), "business_hashes": hashes}


def test_atomic_switch_preserves_source_sets_permissions_and_supports_exact_rollback(release, files):
    old, new = files["path"].read_bytes(), files["pending"].read_bytes()
    files["pending"].chmod(0o600)
    release.atomic_switch(**files)
    assert files["path"].read_bytes() == new
    assert files["path"].stat().st_mode & 0o777 == 0o644
    assert not files["pending"].exists()
    files["pending"].write_bytes(old)
    rollback = {**files, "expected_old_sha": files["expected_new_sha"],
                "expected_new_sha": files["expected_old_sha"], "restore_baseline": True}
    release.atomic_switch(**rollback)
    assert files["path"].read_bytes() == old


@pytest.mark.parametrize("drift", ["runtime", "candidate", "business", "symlink", "directory"])
def test_atomic_switch_refuses_drift_without_truncating_public_file(release, files, drift, tmp_path):
    if drift == "runtime":
        files["path"].write_bytes(b"synthetic concurrent release")
    elif drift == "candidate":
        files["pending"].write_bytes(b"synthetic incomplete upload")
    elif drift == "business":
        (tmp_path / release.BUSINESS_FILES[1]).write_bytes(b"synthetic regressed heartbeat")
    elif drift == "symlink":
        data = files["pending"].read_bytes()
        files["pending"].unlink()
        (tmp_path / "other").write_bytes(data)
        files["pending"].symlink_to(tmp_path / "other")
    else:
        directory = tmp_path / "elsewhere"
        directory.mkdir()
        files["pending"] = files["pending"].rename(directory / "pending")
    before = files["path"].read_bytes()
    with pytest.raises(release.GuardError):
        release.atomic_switch(**files)
    assert files["path"].read_bytes() == before


def test_competing_manifest_switches_have_one_cas_winner(release, files, tmp_path):
    second = tmp_path / ".second-pending"
    second.write_bytes(files["pending"].read_bytes())
    barrier = threading.Barrier(2)
    def switch(pending):
        barrier.wait(timeout=3)
        try:
            release.atomic_switch(**{**files, "pending": pending})
            return "published"
        except release.GuardError:
            return "stale"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(switch, [files["pending"], second]))
    assert sorted(results) == ["published", "stale"]
    assert release.digest(files["path"].read_bytes()) == files["expected_new_sha"]


def test_generated_container_guard_executes_the_same_atomic_checks(release, files, monkeypatch):
    args = {key: str(value) if isinstance(value, Path) else value for key, value in files.items()}
    monkeypatch.setattr(release.sys, "argv", ["guard", json.dumps(args)])
    exec(release.portable_atomic_source(), {})
    assert release.digest(files["path"].read_bytes()) == files["expected_new_sha"]


@pytest.fixture
def plan(release, payload, tmp_path, monkeypatch):
    old = b'{"entries":[],"syntheticOnly":true}\n'
    monkeypatch.setattr(release, "OLD_MANIFEST_SHA", release.digest(old))
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    hashes = {filename: hashlib.sha256(filename.encode()).hexdigest() for filename in release.BUSINESS_FILES}
    hashes[release.BUSINESS_FILES[1]] = release.HEARTBEAT_SHA
    hashes[release.MANIFEST_NAME] = release.digest(old)
    summary = {"components": [
        {"name": name, "id": str(index) * 64, "image": release.BASE_IMAGE if index == 1 else f"sha256:{index}" * 8,
         "imageName": "compose-backend" if index == 1 else name, "startedAt": "2026-10-14T16:13:02Z",
         "restartCount": 0, "mounts": []}
        for index, name in enumerate([release.BACKEND_NAME, "compose-web-1", "compose-postgres-1", "compose-redis-1"], 1)
    ], "backendFileHashes": hashes}
    (baseline / "desktop_release_manifest.before.json").write_bytes(old)
    (baseline / "component-summary.before.json").write_text(json.dumps(summary))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload))
    return release.load_plan(manifest, baseline, release.DEFAULT_RELEASE_DIR)


class FakeRemote:
    def __init__(self, release, plan):
        self.release, self.plan = release, plan
        self.calls, self.writes, self.tags = [], {}, {release.FUTURE_TAG: release.BASE_IMAGE}
        self.manifest_sha = release.OLD_MANIFEST_SHA
        self.base = {"Id": release.BASE_IMAGE, "RootFS": {"Layers": ["synthetic-base-layer"]}, "Config": {"Cmd": ["synthetic"]}}
        self.candidate = {"Id": "sha256:synthetic-candidate", "RootFS": {"Layers": ["synthetic-base-layer", "manifest-layer"]}, "Config": deepcopy(self.base["Config"])}
        self.lose_switch_response = False
    def inspect_containers(self, names):
        return [{"Name": "/" + row["name"], "Id": row["id"], "Image": row["image"],
                 "State": {"StartedAt": row["startedAt"], "Running": True, "Health": {"Status": "healthy"}},
                 "RestartCount": row["restartCount"], "Mounts": []} for row in self.plan["summary"]["components"]]
    def image(self, name, *, missing_ok=False):
        image = self.tags.get(name)
        if image is None and missing_ok:
            return None
        return deepcopy(self.base if image == self.release.BASE_IMAGE else self.candidate)
    def hashes(self, name, files, *, candidate=False):
        values = {**self.plan["businessHashes"], self.release.MANIFEST_NAME:
                  self.plan["newManifestSha"] if candidate else self.manifest_sha}
        return {key: values[key] for key in files}
    def put_exclusive(self, path, data):
        assert path not in self.writes
        self.writes[path] = data
    def read_public_file(self, path, *, missing_ok=False):
        if path not in self.writes and not missing_ok:
            raise self.release.GuardError("synthetic staged file missing")
        return self.writes.get(path)
    def replace_public_exact(self, path, before, after):
        assert self.writes[path] == before
        self.calls.append(["replace-public", path])
        self.writes[path] = after
    def manifest_mode(self, image):
        return 0o644
    def run(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[:2] == ["docker", "tag"]:
            self.tags[argv[3]] = argv[2]
        elif argv[:2] == ["docker", "build"]:
            self.tags[self.release.NEW_TAG] = self.candidate["Id"]
        elif argv[:3] == ["docker", "exec", self.release.BACKEND_NAME] and "atomic_switch(**p)" in argv[-2]:
            args = json.loads(argv[-1])
            assert self.manifest_sha == args["expected_old_sha"]
            self.manifest_sha = args["expected_new_sha"]
            if self.lose_switch_response and not args["restore_baseline"]:
                self.lose_switch_response = False
                raise self.release.GuardError("synthetic lost SSH response after rename")


def test_dry_run_is_read_only_even_when_all_guards_pass(release, plan, monkeypatch, capsys):
    remote = FakeRemote(release, plan)
    monkeypatch.setattr(release, "Remote", lambda: remote)
    monkeypatch.setattr(release, "load_plan", lambda *args: plan)
    assert release.main(["--manifest", "synthetic", "--baseline-dir", "synthetic"]) == 0
    assert json.loads(capsys.readouterr().out)["dryRun"] is True
    assert remote.calls == [] and remote.writes == {}


def test_apply_changes_only_metadata_and_future_tag_without_restart(release, plan):
    remote = FakeRemote(release, plan)
    report = release.apply(remote, plan)
    assert remote.manifest_sha == plan["newManifestSha"]
    assert remote.tags[release.FUTURE_TAG] == remote.candidate["Id"]
    assert report["containersRestarted"] is False
    dockerfile = remote.writes[f"{release.DEFAULT_RELEASE_DIR}/Dockerfile"].decode()
    assert dockerfile.splitlines() == [f"FROM {release.ROLLBACK_TAG}",
                                     f"COPY desktop_release_manifest.json {release.APP_ROOT}/desktop_release_manifest.json"]
    assert all(not any(word in call for word in ("restart", "compose", "push", "--force-recreate")) for call in remote.calls)
    assert (plan["baselineDir"].parent / "deployed.json").is_file()


def test_lost_response_after_successful_rename_restores_old_manifest_and_future_image(release, plan):
    remote = FakeRemote(release, plan)
    remote.lose_switch_response = True
    with pytest.raises(release.GuardError, match="lost SSH response"):
        release.apply(remote, plan)
    assert remote.manifest_sha == release.OLD_MANIFEST_SHA
    assert remote.tags[release.FUTURE_TAG] == release.BASE_IMAGE
    assert f"{release.DEFAULT_RELEASE_DIR}/deployed.json" not in remote.writes


@pytest.mark.parametrize("drift", ["layer", "config", "source"])
def test_candidate_cannot_regress_code_or_change_business_configuration(release, plan, drift):
    remote = FakeRemote(release, plan)
    remote.tags[release.ROLLBACK_TAG] = release.BASE_IMAGE
    candidate = deepcopy(remote.candidate)
    if drift == "layer":
        candidate["RootFS"]["Layers"].insert(1, "unapproved-source-layer")
    elif drift == "config":
        candidate["Config"]["Cmd"] = ["unapproved command"]
    else:
        remote.hashes = lambda *a, **k: {**plan["businessHashes"], release.BUSINESS_FILES[1]: "regressed heartbeat"}
    with pytest.raises(release.GuardError):
        release.verify_candidate(remote, plan, candidate)


@pytest.mark.parametrize("value", ["/opt/offersteady/current", "/opt/offersteady/releases/../current",
                                   "/opt/offersteady-global/releases/20261015-cn-companion-135-1",
                                   "/tmp/$(touch forbidden)"])
def test_unreviewed_or_shell_like_release_paths_are_rejected(release, value):
    with pytest.raises(release.GuardError):
        release.validate_release_directory(value)


@pytest.mark.parametrize("field,value", [("Id", "replacement"), ("Image", "old image"), ("RestartCount", 1)])
def test_container_replacement_restart_or_image_drift_blocks_publication(release, plan, field, value):
    remote = FakeRemote(release, plan)
    records = remote.inspect_containers([])
    records[0][field] = value
    with pytest.raises(release.GuardError, match="lifecycle drift"):
        release.verify_components(plan["summary"]["components"], records)


@pytest.mark.parametrize("drift", ["manifest", "heartbeat", "future-image", "rollback-image"])
def test_initial_drift_prevents_even_staging_a_release(release, plan, drift):
    remote = FakeRemote(release, plan)
    if drift == "manifest":
        remote.manifest_sha = "synthetic concurrent release"
    elif drift == "heartbeat":
        remote.hashes = lambda *a, **k: {**plan["businessHashes"], release.BUSINESS_FILES[1]: "old heartbeat",
                                       release.MANIFEST_NAME: release.OLD_MANIFEST_SHA}
    else:
        remote.tags[release.FUTURE_TAG if drift == "future-image" else release.ROLLBACK_TAG] = remote.candidate["Id"]
    with pytest.raises(release.GuardError):
        release.apply(remote, plan)
    assert not remote.writes and not remote.calls


def test_drift_during_build_stops_before_public_switch(release, plan):
    remote = FakeRemote(release, plan)
    original = remote.inspect_containers
    count = 0
    def inspect(names):
        nonlocal count
        count += 1
        if count == 2:
            remote.manifest_sha = "synthetic concurrent update while building"
        return original(names)
    remote.inspect_containers = inspect
    with pytest.raises(release.GuardError, match="runtime manifest"):
        release.apply(remote, plan)
    assert remote.tags[release.FUTURE_TAG] == release.BASE_IMAGE
    assert not any(call[:2] == ["docker", "cp"] for call in remote.calls)


@pytest.mark.parametrize("field", ["old-manifest", "heartbeat-source", "image"])
def test_unreviewed_saved_baseline_is_rejected(release, plan, field):
    baseline = plan["baselineDir"]
    summary_path = baseline / "component-summary.before.json"
    summary = json.loads(summary_path.read_bytes())
    if field == "old-manifest":
        (baseline / "desktop_release_manifest.before.json").write_bytes(b"synthetic other baseline")
    elif field == "heartbeat-source":
        summary["backendFileHashes"][release.BUSINESS_FILES[1]] = "a" * 64
    else:
        summary["components"][0]["image"] = "sha256:old-backend"
    summary_path.write_text(json.dumps(summary))
    with pytest.raises(release.GuardError):
        release.load_plan(baseline.parent / "manifest.json", baseline, release.DEFAULT_RELEASE_DIR)


def seed_staged(release, plan, *, legacy=True, candidate=False):
    remote = FakeRemote(release, plan)
    remote.tags[release.ROLLBACK_TAG] = release.BASE_IMAGE
    remote.writes = {f"{release.DEFAULT_RELEASE_DIR}/{name}": data
                     for name, data in release.staged_contents(plan).items()}
    remote.writes[f"{release.DEFAULT_RELEASE_DIR}/Dockerfile"] = (
        release.original_buildkit_dockerfile() if legacy else release.build_dockerfile())
    if candidate:
        remote.tags[release.NEW_TAG] = remote.candidate["Id"]
    return remote


@pytest.mark.parametrize("filename", ["desktop_release_manifest.before.json", "component-summary.before.json",
                                      "desktop_release_manifest.json", "Dockerfile"])
def test_resume_refuses_mismatched_staged_bytes_before_any_write(release, plan, filename):
    remote = seed_staged(release, plan)
    remote.writes[f"{release.DEFAULT_RELEASE_DIR}/{filename}"] = b"synthetic altered stage"
    before = deepcopy(remote.writes)
    with pytest.raises(release.GuardError, match="staged"):
        release.apply(remote, plan, resume_staged=True)
    assert remote.writes == before and remote.calls == []
    assert remote.manifest_sha == release.OLD_MANIFEST_SHA


def test_resume_preserves_failed_dockerfile_and_builds_single_plain_copy(release, plan):
    remote = seed_staged(release, plan)
    release.apply(remote, plan, resume_staged=True)
    assert remote.writes[f"{release.DEFAULT_RELEASE_DIR}/Dockerfile.buildkit-required.before"] == release.original_buildkit_dockerfile()
    assert remote.writes[f"{release.DEFAULT_RELEASE_DIR}/Dockerfile"] == release.build_dockerfile()
    assert remote.manifest_sha == plan["newManifestSha"]
    assert len([call for call in remote.calls if call[:2] == ["docker", "build"]]) == 1


def test_resume_reuses_only_a_verified_existing_candidate(release, plan):
    remote = seed_staged(release, plan, legacy=False, candidate=True)
    remote.writes[f"{release.DEFAULT_RELEASE_DIR}/Dockerfile.first-attempt"] = release.original_buildkit_dockerfile()
    release.apply(remote, plan, resume_staged=True)
    assert remote.manifest_sha == plan["newManifestSha"]
    assert not any(call[:2] == ["docker", "build"] for call in remote.calls)
    assert not any(call[0] == "replace-public" for call in remote.calls)


@pytest.mark.parametrize("drift", ["config", "mode", "rollback", "backup"])
def test_resume_rejects_unverified_candidate_or_rollback_before_repair(release, plan, drift):
    remote = seed_staged(release, plan, candidate=True)
    if drift == "config":
        remote.candidate["Config"]["Cmd"] = ["unapproved business deployment"]
    elif drift == "mode":
        remote.manifest_mode = lambda image: 0o600
    elif drift == "rollback":
        remote.tags[release.ROLLBACK_TAG] = remote.candidate["Id"]
    else:
        remote.writes[f"{release.DEFAULT_RELEASE_DIR}/Dockerfile.first-attempt"] = b"synthetic different backup"
    before = deepcopy(remote.writes)
    with pytest.raises(release.GuardError):
        release.apply(remote, plan, resume_staged=True)
    assert remote.writes == before and remote.calls == []


def test_resume_flag_without_apply_remains_read_only(release, plan, monkeypatch, capsys):
    remote = seed_staged(release, plan)
    before = deepcopy(remote.writes)
    monkeypatch.setattr(release, "Remote", lambda: remote)
    monkeypatch.setattr(release, "load_plan", lambda *args: plan)
    assert release.main(["--manifest", "synthetic", "--baseline-dir", "synthetic", "--resume-staged"]) == 0
    assert json.loads(capsys.readouterr().out)["resumeStaged"] is True
    assert remote.writes == before and remote.calls == []
