"""Synthetic release-controller checks; no Docker, SSH, sockets or databases."""
from __future__ import annotations

import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[3] / "scripts/release_global_auth_state.py"


def load_release():
    spec = importlib.util.spec_from_file_location("synthetic_global_auth_state_cutover", SOURCE)
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    return release


@pytest.fixture
def harness(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    workdir = tmp_path / "old-release/infra/compose"
    workdir.mkdir(parents=True)
    envfile = workdir.parents[1] / ".env.production"
    envfile.write_text("SAFE_SYNTHETIC_SETTING=private-not-for-output\n")
    composefile = workdir / "compose.json"
    new_image = "sha256:" + "a" * 64
    base = {
        "Id": release.BASE_ID, "Image": release.BASE_IMAGE, "RestartCount": 0,
        "Config": {"Image": "compose-backend", "Env": ["SAFE_SYNTHETIC_SETTING=private-not-for-output"],
            "Labels": {"com.docker.compose.project": release.PROJECT, "com.docker.compose.service": "backend",
                "com.docker.compose.project.working_dir": str(workdir),
                "com.docker.compose.project.config_files": str(composefile)},
            "Cmd": ["synthetic-server"], "Entrypoint": None, "WorkingDir": "/app/apps/backend", "User": "",
            "ExposedPorts": {"8000/tcp": {}}, "Healthcheck": {"Test": ["CMD", "synthetic"]},
            "Volumes": None, "StopSignal": None},
        "HostConfig": {"Memory": 1024, "NetworkMode": "offersteady-global_default", "Binds": None,
                       "PidsLimit": 128, "CapAdd": [], "Dns": [], "Ulimits": []},
        "Mounts": [{"Type": "volume", "Name": "synthetic-volume", "Destination": "/synthetic"}],
        "NetworkSettings": {"Networks": {"offersteady-global_default": {"IPAddress": "172.30.0.2"}}},
        "State": {"Running": True, "StartedAt": "synthetic-before", "Health": {"Status": "healthy"}},
    }
    rendered = {"name": release.PROJECT, "services": {
        "backend": {"image": "compose-backend", "environment": {"SAFE_SYNTHETIC_SETTING": "private-not-for-output"},
                    "pids_limit": 128},
        "web": {"image": "synthetic-web-unchanged"},
    }}
    composefile.write_text(json.dumps(rendered))
    release.save("container-before.private.json", base)
    (tmp_path / "runtime.env.private").write_text("SAFE_SYNTHETIC_SETTING=private-not-for-output\n")
    release.save("compose-before.private.json", rendered)
    release.save("compose.auth-state.json", {"services": {"backend": {"image": new_image}}})
    release.save("compose.rollback.json", {"services": {"backend": {"image": release.BASE_IMAGE}}})
    before_inventory = {"apps/backend/app/services/chat_service.py": "synthetic-before-chat",
                        "apps/backend/app/services/realtime_speech_service.py": "synthetic-before-realtime",
                        "ai/prompts/chat-service/quick.md": "synthetic-unchanged-prompt"}
    plan = {"beforeInventory": before_inventory, "files": {path: "synthetic-after" for path in release.FILES},
            "gates": ["gates/synthetic-reviewed.py"], "supportFiles": {}}
    release.save("input.json", plan)
    current = {release.CONTAINER: deepcopy(base), "offersteady-global-web-1": {
        "Id": "synthetic-web", "Image": "sha256:" + "b" * 64,
        "State": {"StartedAt": "synthetic-web-before"}}}
    after_render = deepcopy(rendered)
    after_render["services"]["backend"]["image"] = new_image
    manifest = {
        "baselineImage": release.BASE_IMAGE, "beforeId": release.BASE_ID, "oldRuntimeImage": "compose-backend",
        "project": release.PROJECT,
        "composeFiles": [str(composefile)], "workDir": str(workdir), "envFiles": [str(envfile)],
        "frozenComposeFiles": [str(composefile)], "frozenEnvFiles": [str(envfile)],
        "contextHashes": {str(composefile): release.digest(composefile.read_bytes()), str(envfile): release.digest(envfile.read_bytes())},
        "nonTargets": {"offersteady-global-web-1": {"id": "synthetic-web", "image": current["offersteady-global-web-1"]["Image"],
                                        "startedAt": "synthetic-web-before"}},
        "inputSha": release.digest((tmp_path / "input.json").read_bytes()),
        "renderedBeforeSha": release.digest(release.canonical(rendered)),
        "renderedAfterSha": release.digest(release.canonical(after_render)),
        "runtimeConfigSha": "synthetic-effective-config", "newImage": new_image, "sharedTags": {},
        "runtimeEnvSha": release.digest((tmp_path / "runtime.env.private").read_bytes()),
        "beforeContainerSha": release.digest((tmp_path / "container-before.private.json").read_bytes()),
        "rollbackImage": release.BASE_IMAGE,
        "overlaySha": release.digest((tmp_path / "compose.auth-state.json").read_bytes()),
        "rollbackOverlaySha": release.digest((tmp_path / "compose.rollback.json").read_bytes()),
    }
    context = tmp_path / "context"
    context.mkdir()
    for originals, key in ((manifest["composeFiles"], "frozenComposeFiles"), (manifest["envFiles"], "frozenEnvFiles")):
        frozen = []
        for source in originals:
            saved = context / Path(source).name
            saved.write_bytes(Path(source).read_bytes())
            frozen.append(str(saved))
            manifest["contextHashes"][str(saved)] = release.digest(saved.read_bytes())
        manifest[key] = frozen
    release.save("prepared.json", manifest)
    image_ids = {release.NEW_TAG: new_image, release.ROLLBACK_TAG: release.BASE_IMAGE,
                 "compose-backend": release.BASE_IMAGE}
    actions, commands, gates = [], [], []
    faults = {"gate_first": False, "gate_second": False, "late_drift": None,
              "verify": False, "verify_drift": None, "verify_foreign": False}

    def inspect(name):
        return deepcopy(current[name]) if name in current else {"Id": image_ids[name]}

    def configuration(args):
        paths = [args[index + 1] for index, value in enumerate(args) if value == "-f"]
        result = deepcopy(json.loads(Path(paths[0]).read_text()))
        for path in paths[1:]:
            overlay = json.loads(Path(path).read_text())
            for service, values in overlay.get("services", {}).items():
                result["services"].setdefault(service, {}).update(values)
        return result

    def run(args, **_kwargs):
        commands.append(list(args))
        if args[:2] == ["docker", "compose"]:
            config = configuration(args)
            if "config" in args:
                return json.dumps(config).encode()
            assert "up" in args and args[-1] == "backend"
            image = config["services"]["backend"]["image"]
            actions.append(("up", "backend", image))
            current[release.CONTAINER] = deepcopy(base)
            current[release.CONTAINER]["Id"] = "synthetic-new-container-" + str(len(actions))
            current[release.CONTAINER]["Image"] = image
            current[release.CONTAINER]["Config"]["Image"] = image
            return b""
        raise AssertionError(f"unexpected synthetic command: {args[:2]}")

    def idle_gates(_plan, *, recovery_manifest=None):
        gates.append(True)
        if (len(gates) == 1 and faults["gate_first"]) or (len(gates) == 2 and faults["gate_second"]):
            raise release.ReleaseError("protected_user_work_cutover_deferred")
        if len(gates) == 2 and faults["late_drift"]:
            target = {"env": envfile, "compose": composefile,
                      "overlay": tmp_path / "compose.auth-state.json"}[faults["late_drift"]]
            if faults["late_drift"] == "compose":
                changed = deepcopy(rendered)
                changed["services"]["backend"]["pids_limit"] = 999
                target.write_text(json.dumps(changed))
            elif faults["late_drift"] == "overlay":
                target.write_text(json.dumps({"services": {"backend": {"image": new_image},
                                                          "web": {"image": "synthetic-wrong-web"}}}))
            else:
                target.write_text("SAFE_SYNTHETIC_SETTING=synthetic-late-drift\n")

    def verify_live(_manifest, _plan):
        if faults["verify_foreign"]:
            target = current[release.CONTAINER]
            target["Id"] = "synthetic-foreign-container"
            target["Image"] = "sha256:" + "c" * 64
            raise release.ReleaseError("synthetic_other_release_took_ownership")
        if faults["verify_drift"]:
            target = current[release.CONTAINER]
            if faults["verify_drift"] == "environment":
                target["Config"]["Env"] = ["SAFE_SYNTHETIC_SETTING=synthetic-own-bad-env"]
            else:
                target["HostConfig"]["PidsLimit"] = 999
            raise release.ReleaseError("synthetic_own_configuration_validation_failed")
        if faults["verify"]:
            raise release.ReleaseError("synthetic_post_switch_verification_failed")
        return {"deployed": True, "image": new_image}

    monkeypatch.setattr(release, "inspect", inspect)
    monkeypatch.setattr(release, "run", run)
    monkeypatch.setattr(release, "check_inputs", lambda: plan)
    monkeypatch.setattr(release, "shared_tags", lambda: {})
    monkeypatch.setattr(release, "config_digest", lambda: manifest["runtimeConfigSha"])
    monkeypatch.setattr(release, "inventory", lambda _name: (
        before_inventory if current[release.CONTAINER]["Image"] == release.BASE_IMAGE else before_inventory | plan["files"]))
    monkeypatch.setattr(release, "wait_healthy", lambda expected: inspect(release.CONTAINER))
    monkeypatch.setattr(release, "refresh_proxy_if_needed", lambda *_args: [])
    real_verify_live = release.verify_live
    real_verify_live_routes = release.verify_live_routes
    monkeypatch.setattr(release, "verify_live_routes", lambda: {"http": {}, "schemaSha": "synthetic-schema"})
    monkeypatch.setattr(release, "verify_live", verify_live)
    monkeypatch.setattr(release, "idle_gates", idle_gates)
    return SimpleNamespace(release=release, root=tmp_path, plan=plan, manifest=manifest, base=base,
                           current=current, faults=faults, actions=actions, commands=commands, gates=gates,
                           real_verify_live=real_verify_live, real_verify_live_routes=real_verify_live_routes)


def test_protected_first_gate_never_switches(harness):
    harness.faults["gate_first"] = True
    with pytest.raises(harness.release.ReleaseError):
        harness.release.deploy()
    assert harness.actions == []


def test_second_gate_new_activity_never_switches_or_rolls_back(harness):
    harness.faults["gate_second"] = True
    with pytest.raises(harness.release.ReleaseError):
        harness.release.deploy()
    assert len(harness.gates) == 2
    assert harness.actions == []


def test_preflight_does_not_mutate_any_service(harness):
    harness.release.deploy(preflight=True)
    assert len(harness.gates) == 1
    assert harness.actions == []
    assert not (harness.root / "deployed.json").exists()


def test_post_switch_verification_failure_rolls_back_only_backend(harness):
    harness.faults["verify"] = True
    with pytest.raises(harness.release.ReleaseError, match="rollback_succeeded"):
        harness.release.deploy()
    assert harness.actions == [("up", "backend", harness.manifest["newImage"]),
                               ("up", "backend", harness.release.BASE_IMAGE)]
    assert harness.current[harness.release.CONTAINER]["Image"] == harness.release.BASE_IMAGE
    assert json.loads((harness.root / "rollback-result.json").read_text())["restored"] is True


@pytest.mark.parametrize("kind", ["environment", "host"])
def test_own_failed_candidate_configuration_can_still_be_automatically_restored(harness, kind):
    harness.faults["verify_drift"] = kind
    with pytest.raises(harness.release.ReleaseError, match="rollback_succeeded"):
        harness.release.deploy()
    assert harness.actions == [("up", "backend", harness.manifest["newImage"]),
                               ("up", "backend", harness.release.BASE_IMAGE)]
    restored = harness.current[harness.release.CONTAINER]
    assert restored["Config"]["Env"] == harness.base["Config"]["Env"]
    assert restored["HostConfig"] == harness.base["HostConfig"]


def test_automatic_rollback_never_replaces_a_foreign_container(harness):
    harness.faults["verify_foreign"] = True
    with pytest.raises(harness.release.ReleaseError, match="rollback_needs_attention"):
        harness.release.deploy()
    assert harness.actions == [("up", "backend", harness.manifest["newImage"])]
    assert harness.current[harness.release.CONTAINER]["Id"] == "synthetic-foreign-container"
    assert json.loads((harness.root / "failed-cutover.json").read_text())["rollbackSucceeded"] is False


def test_automatic_rollback_rejects_foreign_id_even_when_image_matches(harness):
    harness.current[harness.release.CONTAINER]["Id"] = "synthetic-foreign-same-image"
    harness.current[harness.release.CONTAINER]["Image"] = harness.manifest["newImage"]
    with pytest.raises(harness.release.ReleaseError, match="owner_drift"):
        harness.release.rollback(harness.manifest, harness.plan, owned_container_id="synthetic-owned-container")
    assert harness.actions == []


def test_success_uses_private_image_overlay_and_only_backend(harness):
    harness.release.deploy()
    assert harness.actions == [("up", "backend", harness.manifest["newImage"])]
    up = next(args for args in harness.commands if "up" in args)
    assert up[-1] == "backend"
    assert all(flag in up for flag in ("--no-build", "--no-deps", "--pull", "never", "--project-directory"))
    assert not any(args[:2] == ["docker", "tag"] for args in harness.commands)


@pytest.mark.parametrize("kind", ["env", "compose", "overlay"])
def test_file_drift_during_final_gate_is_rejected_before_switch(harness, kind):
    harness.faults["late_drift"] = kind
    with pytest.raises(harness.release.ReleaseError):
        harness.release.deploy()
    assert harness.actions == []


@pytest.mark.parametrize("section,field,value", [
    ("Config", "Env", ["SAFE_SYNTHETIC_SETTING=synthetic-drift"]),
    ("HostConfig", "Memory", 2048),
    ("HostConfig", "PidsLimit", 999),
    ("HostConfig", "CapAdd", ["SYS_ADMIN"]),
    ("HostConfig", "Dns", ["203.0.113.1"]),
    ("HostConfig", "Ulimits", [{"Name": "nofile", "Hard": 4, "Soft": 4}]),
])
def test_runtime_invariant_rejects_environment_and_all_host_drift(harness, section, field, value):
    after = deepcopy(harness.base)
    after[section][field] = value
    with pytest.raises(harness.release.ReleaseError):
        harness.release.runtime_invariant(harness.base, after, harness.release.BASE_IMAGE)


def test_runtime_invariant_rejects_mount_drift(harness):
    after = deepcopy(harness.base)
    after["Mounts"][0]["Destination"] = "/synthetic-wrong"
    with pytest.raises(harness.release.ReleaseError):
        harness.release.runtime_invariant(harness.base, after, harness.release.BASE_IMAGE)


@pytest.mark.parametrize("kind", ["environment", "host", "mount"])
def test_preflight_rejects_current_configuration_drift(harness, kind):
    current = harness.current[harness.release.CONTAINER]
    if kind == "environment":
        current["Config"]["Env"] = ["SAFE_SYNTHETIC_SETTING=synthetic-drift"]
    elif kind == "host":
        current["HostConfig"]["PidsLimit"] = 999
    else:
        current["Mounts"][0]["Destination"] = "/synthetic-wrong"
    with pytest.raises(harness.release.ReleaseError):
        harness.release.deploy(preflight=True)
    assert harness.actions == []


def test_manual_rollback_refuses_to_overwrite_a_later_release(harness, monkeypatch):
    harness.current[harness.release.CONTAINER]["Image"] = "sha256:" + "c" * 64
    monkeypatch.setattr(sys, "argv", ["release_global_auth_state.py", "rollback"])
    with pytest.raises(harness.release.ReleaseError):
        harness.release.main()
    assert harness.actions == []


def test_manual_rollback_rejects_a_same_image_with_unowned_configuration_drift(harness, monkeypatch):
    harness.current[harness.release.CONTAINER]["Image"] = harness.manifest["newImage"]
    harness.current[harness.release.CONTAINER]["Config"]["Env"] = ["SAFE_SYNTHETIC_SETTING=synthetic-other-change"]
    monkeypatch.setattr(sys, "argv", ["release_global_auth_state.py", "rollback"])
    with pytest.raises(harness.release.ReleaseError):
        harness.release.main()
    assert harness.actions == []


def test_empty_gate_list_is_rejected_by_actual_input_validation(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    files = {}
    for path in release.FILES:
        output = tmp_path / "input" / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("# synthetic candidate payload\n")
        files[path] = release.digest(output.read_bytes())
    release.save("input.json", {"baselineImage": release.BASE_IMAGE, "baselineContainer": release.BASE_ID,
        "files": files, "verified": {"candidateTests": 37, "additionalSubtests": 3, "skipped": 2, "syntheticOnly": True}, "supportFiles": {}, "gates": []})
    with pytest.raises(release.ReleaseError):
        release.check_inputs()


def test_isolated_candidate_probe_uses_correct_python_arguments_and_network_sandbox(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    commands = []

    def run(args, **_kwargs):
        commands.append(args)
        return json.dumps({"passed": True}).encode()

    monkeypatch.setattr(release, "run", run)
    image = "sha256:" + "d" * 64
    release.probe({"newImage": image, "runtimeConfigSha": "synthetic-config"})
    command = commands[0]
    assert command[:3] == ["docker", "run", "--rm"]
    assert command[command.index("--network") + 1] == "none"
    assert "--read-only" in command and "--cap-drop" in command and "--security-opt" in command
    assert command[command.index("--entrypoint") + 1] == "python"
    assert command[command.index(image) + 1:] == [
        "-B", "/verify/candidate-probe.py", "--expectations", "/verify/probe-expectations.json",
        "--expected-config-sha", "synthetic-config",
    ]
    assert any("dst=/verify,readonly" in arg for arg in command)
    assert not any("private-not-for-output" in arg for arg in command)


def test_live_probe_copies_only_public_probe_files_and_preserves_argument_positions(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    commands = []

    def run(args, **_kwargs):
        commands.append(args)
        return json.dumps({"passed": True}).encode()

    monkeypatch.setattr(release, "run", run)
    release.probe({"runtimeConfigSha": "synthetic-config"}, live=True)
    copies = [args for args in commands if args[:2] == ["docker", "cp"]]
    assert len(copies) == 2
    assert {Path(args[2]).name for args in copies} == {"candidate-probe.py", "probe-expectations.json"}
    command = commands[-1]
    assert command[:2] == ["docker", "exec"]
    python_index = command.index("python")
    assert command[python_index + 1] == "-B"
    assert command[python_index + 2].endswith("/candidate-probe.py")
    assert command[python_index + 3] == "--expectations"
    assert command[python_index + 4].endswith("/probe-expectations.json")
    assert command[-2:] == ["--expected-config-sha", "synthetic-config"]


def test_gate_output_drops_legacy_private_extras():
    release = load_release()
    counts = {field: 0 for field in ("atMs", "liveInterviews", "recentPreparing", "livePageLeases", "recentAudioTracks", "unfinishedTasks", "runningMaterialJobs")}
    result = release.safe_gate_counts("legacy-gates/check-idle.py", counts | {"private": "synthetic-secret"})
    assert result == counts
    assert "synthetic" not in json.dumps(result)


@pytest.mark.parametrize("bad", ["synthetic-secret", -1, True, None, []])
def test_gate_required_counts_fail_closed_instead_of_echoing_private_values(bad):
    release = load_release()
    with pytest.raises(release.ReleaseError) as error:
        release.safe_gate_counts("legacy-gates/check-mock-idle.py", {"activeOrRecentMockInterviews": bad})
    assert "synthetic-secret" not in str(error.value)


def test_gate_rejects_missing_legacy_protection_counts():
    release = load_release()
    with pytest.raises(release.ReleaseError):
        release.safe_gate_counts("legacy-gates/check-idle.py", {"liveInterviews": 0})


def test_extra_gate_rejects_unknown_summary_field_without_echo(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    (tmp_path / "active_work_gate.py").write_text('PROTECTED=("active", "metadataReadFailures")\n')
    with pytest.raises(release.ReleaseError) as error:
        release.safe_gate_counts("active_work_gate.py", {"active": 0, "synthetic-private-key": "synthetic-secret"})
    assert str(error.value) == "unknown_gate_summary_field"


def test_automatic_recovery_defers_when_new_protected_work_arrives(harness, monkeypatch):
    harness.faults["verify"] = True
    original = harness.release.idle_gates

    def gate(plan, *, recovery_manifest=None):
        if len(harness.gates) == 2:
            raise harness.release.ReleaseError("protected_user_work_cutover_deferred")
        original(plan, recovery_manifest=recovery_manifest)

    monkeypatch.setattr(harness.release, "idle_gates", gate)
    with pytest.raises(harness.release.ReleaseError, match="rollback_needs_attention"):
        harness.release.deploy()
    assert harness.actions == [("up", "backend", harness.manifest["newImage"])]
    assert harness.current[harness.release.CONTAINER]["Image"] == harness.manifest["newImage"]


@pytest.fixture
def multi_context(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "RELEASES_ROOT", tmp_path)
    root = tmp_path / "new-release"
    root.mkdir()
    monkeypatch.setattr(release, "ROOT", root)
    old = tmp_path / "actual-release"
    old.mkdir()
    workdir = old / "infra/compose"
    workdir.mkdir(parents=True)
    values = [
        {"name": release.PROJECT, "services": {
            "backend": {"image": "synthetic-old-tag", "environment": {
                "SAFE": "synthetic-private-not-printed", "OFFERSTEADY_APP_VERSION": "historical"}},
            "web": {"image": "synthetic-web-unchanged"}}},
        {"services": {"backend": {"pids_limit": 128}}},
        {"services": {"backend": {"environment": {"OFFERSTEADY_APP_VERSION": "actual-version"}}}},
        {"services": {"backend": {"image": release.BASE_IMAGE}}},
    ]
    files = []
    for index, value in enumerate(values):
        path = old / f"compose-{index}.json"
        path.write_text(json.dumps(value))
        files.append(path)
    envs = []
    for index in range(2):
        path = old / f"environment-{index}.private"
        path.write_text(f"SYNTHETIC_SETTING_{index}=not-for-output\n")
        envs.append(path)
    before = {"Config": {"Image": release.BASE_IMAGE, "Env": [
        "SAFE=synthetic-private-not-printed", "OFFERSTEADY_APP_VERSION=actual-version"], "Labels": {
        "com.docker.compose.project": release.PROJECT,
        "com.docker.compose.service": "backend",
        "com.docker.compose.project.working_dir": str(workdir),
        "com.docker.compose.project.config_files": ",".join(map(str, files)),
        "com.docker.compose.project.environment_file": ",".join(map(str, envs)),
    }}}
    commands = []

    def merge(left, right):
        for key, value in right.items():
            if isinstance(value, dict) and isinstance(left.get(key), dict):
                merge(left[key], value)
            else:
                left[key] = deepcopy(value)

    def run(args, **kwargs):
        assert args[:2] == ["docker", "compose"] and args[-3:] == ["config", "--format", "json"]
        assert kwargs["cwd"] == str(workdir)
        commands.append(args)
        rendered = {}
        for index, argument in enumerate(args):
            if argument == "-f":
                merge(rendered, json.loads(Path(args[index+1]).read_text()))
        return json.dumps(rendered).encode()

    monkeypatch.setattr(release, "run", run)
    return SimpleNamespace(release=release, before=before, root=root, files=files, envs=envs,
                           commands=commands, workdir=workdir)


def test_actual_four_compose_two_environment_files_are_frozen_in_order(multi_context, capsys):
    h = multi_context
    manifest, source = h.release.freeze_context(h.before)
    assert manifest["project"] == h.release.PROJECT
    assert len(manifest["frozenComposeFiles"]) == 4
    assert len(manifest["frozenEnvFiles"]) == 2
    for original, saved in zip(h.files + h.envs,
            map(Path, manifest["frozenComposeFiles"] + manifest["frozenEnvFiles"])):
        assert original != saved
        assert original.read_bytes() == saved.read_bytes()
    assert source["services"]["backend"]["environment"]["OFFERSTEADY_APP_VERSION"] == "actual-version"
    h.release.verify_context(manifest)
    args = h.release.compose_args(manifest, "compose.auth-state.json")
    assert args[args.index("-p") + 1] == h.release.PROJECT
    assert args[args.index("--project-directory") + 1] == str(h.workdir)
    assert [args[index+1] for index, item in enumerate(args) if item == "--env-file"] == manifest["frozenEnvFiles"]
    assert [args[index+1] for index, item in enumerate(args) if item == "-f"] == (
        manifest["frozenComposeFiles"] + [str(h.root / "compose.auth-state.json")])
    assert not capsys.readouterr().out


@pytest.mark.parametrize("group,index", [("composeFiles", 0), ("composeFiles", 2), ("envFiles", 1),
    ("frozenComposeFiles", 3), ("frozenEnvFiles", 0)])
def test_original_and_frozen_context_drift_is_rejected(multi_context, group, index):
    h = multi_context
    manifest, _ = h.release.freeze_context(h.before)
    path = Path(manifest[group][index])
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(h.release.ReleaseError, match="context_file_drift"):
        h.release.verify_context(manifest)


@pytest.mark.parametrize("field,value", [("com.docker.compose.project", "compose"),
    ("com.docker.compose.service", "web"), ("com.docker.compose.project.environment_file", ""),
    ("com.docker.compose.project.config_files", "/tmp/unreviewed-compose"),
    ("com.docker.compose.project.working_dir", "/tmp/unrelated")])
def test_wrong_actual_compose_context_is_rejected(multi_context, field, value):
    h = multi_context
    h.before["Config"]["Labels"][field] = value
    with pytest.raises(h.release.ReleaseError):
        h.release.freeze_context(h.before)


def test_actual_environment_mismatch_is_not_silently_repaired(multi_context):
    h = multi_context
    h.before["Config"]["Env"] = ["SAFE=other", "OFFERSTEADY_APP_VERSION=actual-version"]
    with pytest.raises(h.release.ReleaseError, match="rendered_runtime_environment_drift"):
        h.release.freeze_context(h.before)


def test_missing_global_lease_count_fails_closed():
    release = load_release()
    with pytest.raises(release.ReleaseError, match="missing_gate_summary_field"):
        release.safe_gate_counts("global_mock_companion_idle_gate.py", {"mockControlOrGenerationLeases": 0})


def test_missing_active_protection_count_fails_closed(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    (tmp_path / "active_work_gate.py").write_text('PROTECTED=("active", "metadataReadFailures")\n')
    with pytest.raises(release.ReleaseError, match="missing_gate_summary_field"):
        release.safe_gate_counts("active_work_gate.py", {"active": 0, "ignoredLegacyFailedQueuedTasks": 0})


def test_positive_protected_count_rejects_even_if_gate_exits_zero(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    path = "legacy-gates/check-mock-idle.py"
    output = tmp_path / path
    output.parent.mkdir()
    output.write_text("# reviewed synthetic gate\n")
    plan = {"gates": [path], "supportFiles": {path: release.digest(output.read_bytes())}}
    monkeypatch.setattr(release.subprocess, "run", lambda *_args, **_kwargs:
        SimpleNamespace(returncode=0, stdout=b'{"activeOrRecentMockInterviews":1}'))
    with pytest.raises(release.ReleaseError, match="protected_user_work_cutover_deferred"):
        release.idle_gates(plan)


@pytest.mark.parametrize("change", ["stopped", "unhealthy", "starting", "missing-health", "restarted"])
def test_direct_verify_rejects_current_health_and_restart_drift(harness, monkeypatch, change):
    current = harness.current[harness.release.CONTAINER]
    current["Image"] = harness.manifest["newImage"]
    if change == "stopped":
        current["State"]["Running"] = False
    elif change == "missing-health":
        current["State"].pop("Health")
    elif change == "restarted":
        current["RestartCount"] = 1
    else:
        current["State"]["Health"]["Status"] = change
    # The shared harness replaces successful production verification. Invoke
    # the real entry point from a fresh module against its synthetic inspect.
    original = load_release()
    monkeypatch.setattr(original, "ROOT", harness.root)
    monkeypatch.setattr(original, "inspect", harness.release.inspect)
    with pytest.raises(original.ReleaseError, match="released_backend_unhealthy"):
        original.verify_live(harness.manifest, harness.plan)
    assert harness.actions == []


@pytest.fixture
def valid_inputs(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    files = {}
    for index, path in enumerate(sorted(release.FILES)):
        target = tmp_path / "input" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# synthetic approved payload {index}\n")
        files[path] = release.digest(target.read_bytes())
    report = {"passed": True, "sourceFrozenAfterTests": True, "candidateHashes": files,
              "records": [{"name": f"synthetic-group-{index}", "returncode": 0} for index in range(4)],
              "candidateTests": 37, "additionalSubtests": 3, "skipped": 2, "syntheticOnly": True}
    release.save("candidate-verification.json", report)
    support_paths = release.GATES | {SOURCE.name, "candidate-verification.json",
                                    "probe/candidate-probe.py", "probe/probe-expectations.json"}
    support = {}
    for path in support_paths:
        target = tmp_path / path
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# synthetic support only\n")
        support[path] = release.digest(target.read_bytes())
    before = {path: "f" * 64 for path in files}
    before.update({f"apps/backend/app/synthetic-protected-{index}.py": "b" * 64
                   for index in range(236-len(before))})
    plan = {"baselineImage": release.BASE_IMAGE, "baselineContainer": release.BASE_ID,
            "files": files, "beforeInventory": before, "gates": sorted(release.GATES),
            "supportFiles": support,
            "verified": {"candidateTests": 37, "additionalSubtests": 3, "skipped": 2, "syntheticOnly": True}}
    release.save("input.json", plan)
    return SimpleNamespace(release=release, root=tmp_path, plan=plan, report=report)


def save_input(fixture):
    fixture.release.save("input.json", fixture.plan)


def save_report(fixture):
    fixture.release.save("candidate-verification.json", fixture.report)
    fixture.plan["supportFiles"]["candidate-verification.json"] = fixture.release.digest(
        (fixture.root / "candidate-verification.json").read_bytes())
    save_input(fixture)


def test_all_frozen_candidate_inputs_are_accepted(valid_inputs):
    assert valid_inputs.release.check_inputs() == valid_inputs.plan


@pytest.mark.parametrize("key,value", [("candidateTests", 0), ("additionalSubtests", -1),
                                       ("skipped", -1)])
def test_verification_counts_are_bound_to_auth_state_candidate(valid_inputs, key, value):
    valid_inputs.plan["verified"][key] = value
    save_input(valid_inputs)
    with pytest.raises(valid_inputs.release.ReleaseError, match="local_verification_missing"):
        valid_inputs.release.check_inputs()


@pytest.mark.parametrize("kind", ["scope", "source", "support", "gate", "inventory", "unbound-probe"])
def test_scope_source_support_gates_and_full_baseline_are_bound(valid_inputs, kind):
    fixture = valid_inputs
    path = next(iter(fixture.plan["files"]))
    if kind == "scope":
        del fixture.plan["files"][path]
    elif kind == "source":
        (fixture.root / "input" / path).write_text("# changed after local tests\n")
    elif kind == "support":
        (fixture.root / "probe/candidate-probe.py").write_text("# changed support\n")
    elif kind == "gate":
        fixture.plan["gates"].pop()
    elif kind == "unbound-probe":
        del fixture.plan["supportFiles"]["probe/candidate-probe.py"]
    else:
        del fixture.plan["beforeInventory"][path]
    save_input(fixture)
    with pytest.raises(fixture.release.ReleaseError):
        fixture.release.check_inputs()


@pytest.mark.parametrize("kind", ["passed", "frozen", "hash", "failed-group", "empty-groups"])
def test_candidate_test_results_must_be_exact_frozen_source_and_successful_groups(valid_inputs, kind):
    fixture = valid_inputs
    if kind == "passed":
        fixture.report["passed"] = False
    elif kind == "frozen":
        fixture.report["sourceFrozenAfterTests"] = "true"
    elif kind == "hash":
        fixture.report["candidateHashes"] = {"synthetic-wrong-path": "c" * 64}
    elif kind == "failed-group":
        fixture.report["records"][0]["returncode"] = 1
    elif kind == "empty-groups":
        fixture.report["records"] = []
    else:
        fixture.report["records"].pop()
    save_report(fixture)
    with pytest.raises(fixture.release.ReleaseError):
        fixture.release.check_inputs()


def test_shared_compose_tag_is_recorded_without_tagging_or_creating_it(monkeypatch):
    release = load_release()
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=json.dumps([{"Id": release.BASE_IMAGE}]).encode(), stderr=b"")
    monkeypatch.setattr(release.subprocess, "run", run)
    assert release.shared_tags() == {"offersteady-global-backend": release.BASE_IMAGE}
    assert calls == [["docker", "image", "inspect", "offersteady-global-backend"]]


def test_absent_optional_shared_tag_is_explicitly_recorded(monkeypatch):
    release = load_release()
    monkeypatch.setattr(release.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout=b"", stderr=b"Error response from daemon: No such image: offersteady-global-backend:latest"))
    assert release.shared_tags() == {}


def test_docker_failure_is_not_treated_as_absent_optional_shared_tag(monkeypatch):
    release = load_release()
    monkeypatch.setattr(release.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout=b"", stderr=b"Cannot connect to the Docker daemon"))
    with pytest.raises(release.ReleaseError, match="shared_runtime_tag_inspection_failed"):
        release.shared_tags()


def test_shared_compose_tag_drift_is_rejected_before_restart(harness, monkeypatch):
    monkeypatch.setattr(harness.release, "shared_tags", lambda: {"offersteady-global-backend": "sha256:" + "c" * 64})
    with pytest.raises(harness.release.ReleaseError, match="shared_runtime_tag_changed"):
        harness.release.deploy()
    assert harness.actions == []


@pytest.mark.parametrize("kind", ["stopped", "restart", "unhealthy", "health-missing"])
def test_prepare_revalidation_rejects_unhealthy_baseline_before_restart(harness, kind):
    current = harness.current[harness.release.CONTAINER]
    if kind == "stopped":
        current["State"]["Running"] = False
    elif kind == "restart":
        current["RestartCount"] = 1
    elif kind == "unhealthy":
        current["State"]["Health"]["Status"] = "unhealthy"
    else:
        current["State"].pop("Health")
    with pytest.raises(harness.release.ReleaseError, match="baseline_unhealthy"):
        harness.release.deploy()
    assert harness.actions == []


def setup_live(harness, monkeypatch, routes=None):
    release = harness.release
    current = harness.current[release.CONTAINER]
    current["Image"] = harness.manifest["newImage"]
    current["Config"]["Image"] = harness.manifest["newImage"]
    expected = {"/api/v1/synthetic": ["get"]}
    probe = harness.root / "probe/probe-expectations.json"
    probe.parent.mkdir(exist_ok=True)
    probe.write_text(json.dumps({"routes": {"http": expected}, "liveHttp": expected,
                                 "liveOpenapiSha": "synthetic-schema"}))
    monkeypatch.setattr(release, "verify_live_routes", harness.real_verify_live_routes)
    monkeypatch.setattr(release, "probe", lambda *args, **kwargs: {
        "passed": True, "applicationFiles": 162, "promptFiles": 74})
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"data":{"status":"ok"}}'
    monkeypatch.setattr(release, "urlopen", lambda *args, **kwargs: Response())
    original_run = release.run
    harness.live_payload = {"http": expected if routes is None else routes, "schemaSha": "synthetic-schema"}
    def run(args, **kwargs):
        if args[:2] == ["docker", "compose"]:
            return original_run(args, **kwargs)
        return json.dumps(harness.live_payload).encode()
    monkeypatch.setattr(release, "run", run)
    return current


@pytest.mark.parametrize("kind", ["stopped", "restart", "unhealthy", "health-missing"])
def test_verify_live_checks_running_health_and_restart_state(harness, monkeypatch, kind):
    current = setup_live(harness, monkeypatch)
    if kind == "stopped":
        current["State"]["Running"] = False
    elif kind == "restart":
        current["RestartCount"] = 1
    elif kind == "unhealthy":
        current["State"]["Health"]["Status"] = "unhealthy"
    else:
        current["State"].pop("Health")
    with pytest.raises(harness.release.ReleaseError, match="released_backend_unhealthy"):
        harness.real_verify_live(harness.manifest, harness.plan)


@pytest.mark.parametrize("routes", [{}, {"/api/v1/synthetic": ["post"]},
                                    {"/api/v1/synthetic": ["get"], "/api/v1/unapproved": ["get"]}])
def test_verify_live_requires_full_openapi_route_dictionary_equality(harness, monkeypatch, routes):
    setup_live(harness, monkeypatch, routes)
    with pytest.raises(harness.release.ReleaseError, match="live_api_routes_mismatch"):
        harness.real_verify_live(harness.manifest, harness.plan)


def test_verify_live_accepts_full_routes_and_healthy_frozen_runtime(harness, monkeypatch):
    setup_live(harness, monkeypatch)
    result = harness.real_verify_live(harness.manifest, harness.plan)
    assert result["deployed"] and result["healthy"] and result["sharedRuntimeTagUnchanged"]
    assert result["applicationFiles"] == 162 and result["promptFiles"] == 74
    assert result["httpPathsVerified"] == 1


def test_manual_rollback_rechecks_activity_inside_controller(harness):
    harness.faults["gate_first"] = True
    with pytest.raises(harness.release.ReleaseError, match="protected_user_work_cutover_deferred"):
        harness.release.rollback(harness.manifest, harness.plan)
    assert len(harness.gates) == 1
    assert harness.actions == []


def test_automatic_failed_cutover_recovery_rechecks_activity_without_requiring_candidate_health_or_env(harness):
    harness.current[harness.release.CONTAINER]["Id"] = "synthetic-owned-failed"
    harness.current[harness.release.CONTAINER]["Image"] = harness.manifest["newImage"]
    harness.current[harness.release.CONTAINER]["State"]["Running"] = False
    harness.current[harness.release.CONTAINER]["Config"]["Env"] = ["synthetic-broken-owned-config"]
    harness.release.rollback(harness.manifest, harness.plan, owned_container_id="synthetic-owned-failed")
    assert len(harness.gates) == 1
    assert harness.actions == [("up", "backend", harness.release.BASE_IMAGE)]


def test_automatic_rollback_defers_if_protected_work_has_arrived(harness):
    harness.current[harness.release.CONTAINER]["Id"] = "synthetic-owned-failed"
    harness.current[harness.release.CONTAINER]["Image"] = harness.manifest["newImage"]
    harness.faults["gate_first"] = True
    with pytest.raises(harness.release.ReleaseError, match="protected_user_work_cutover_deferred"):
        harness.release.rollback(harness.manifest, harness.plan, owned_container_id="synthetic-owned-failed")
    assert len(harness.gates) == 1
    assert harness.actions == []


@pytest.fixture
def gates_fixture(tmp_path, monkeypatch):
    release = load_release()
    monkeypatch.setattr(release, "ROOT", tmp_path)
    old_support = SOURCE.parent / "release_support/global_question_prefetch_20261016"
    hashes = {}
    for path in release.GATES:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((old_support / path).read_bytes())
        hashes[path] = release.digest(target.read_bytes())
    return SimpleNamespace(release=release, root=tmp_path, hashes=hashes)


def zero_gate_counts(fixture, path):
    if path == "legacy-gates/check-idle.py":
        return {"atMs": 123456, "liveInterviews": 0, "recentPreparing": 0, "livePageLeases": 0,
                "recentAudioTracks": 0, "unfinishedTasks": 0, "runningMaterialJobs": 0}
    if path == "legacy-gates/check-mock-idle.py":
        return {"activeOrRecentMockInterviews": 0}
    if path == "global_mock_companion_idle_gate.py":
        return dict.fromkeys(("mockControlOrGenerationLeases", "material_processing_jobs", "material_deletion_jobs",
                              "material_reconcile_jobs", "protectedMaterialTasks", "activeEntityOrLegacyPageLeases"), 0)
    fields = set()
    for node in ast.parse((fixture.root / path).read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in
                {"PROTECTED", "MOCK_FIELDS"} for target in node.targets):
            fields.update(ast.literal_eval(node.value))
    if path == "active_work_gate.py":
        fields.add("ignoredLegacyFailedQueuedTasks")
    return dict.fromkeys(fields, 0)

@pytest.mark.parametrize("path", ["legacy-gates/check-idle.py", "legacy-gates/check-mock-idle.py",
                                 "global_mock_companion_idle_gate.py", "extra_idle_gate.py", "active_work_gate.py"])
def test_each_reviewed_gate_accepts_only_complete_idle_summary(gates_fixture, path):
    counts = gates_fixture.release.safe_gate_counts(path, zero_gate_counts(gates_fixture, path))
    assert gates_fixture.release.gate_is_idle(path, counts)


@pytest.mark.parametrize("path,field", [
    ("legacy-gates/check-idle.py", "recentAudioTracks"),
    ("legacy-gates/check-mock-idle.py", "activeOrRecentMockInterviews"),
    ("extra_idle_gate.py", "unfinishedChatTasks"),
    ("active_work_gate.py", "connectedDesktopPublishers"),
])
def test_gate_exit_zero_does_not_override_protected_activity(gates_fixture, monkeypatch, path, field):
    fixture = gates_fixture
    counts = zero_gate_counts(fixture, path)
    counts[field] = 1
    plan = {"gates": [path], "supportFiles": fixture.hashes}
    monkeypatch.setattr(fixture.release.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=json.dumps(counts).encode(), stderr=b""))
    with pytest.raises(fixture.release.ReleaseError, match="protected_user_work_cutover_deferred"):
        fixture.release.idle_gates(plan)


@pytest.mark.parametrize("kind", ["protected-legacy", "missing", "bool", "unknown-field", "nonzero-exit"])
def test_malformed_stale_or_failed_gate_cannot_pass(gates_fixture, monkeypatch, kind):
    fixture = gates_fixture
    path = "legacy-gates/check-idle.py" if kind == "protected-legacy" else "active_work_gate.py"
    counts = zero_gate_counts(fixture, path)
    if kind == "protected-legacy":
        counts["recentAudioTracks"] = 1
    elif kind == "missing":
        del counts["connectedDesktopPublishers"]
    elif kind == "bool":
        counts["connectedDesktopPublishers"] = False
    elif kind == "unknown-field":
        counts["unapproved-private-field"] = 0
    monkeypatch.setattr(fixture.release.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=75 if kind == "nonzero-exit" else 0, stdout=json.dumps(counts).encode(), stderr=b""))
    with pytest.raises(fixture.release.ReleaseError):
        fixture.release.idle_gates({"gates": [path], "supportFiles": fixture.hashes})


@pytest.fixture
def recovery_gates(gates_fixture):
    fixture = gates_fixture
    env = fixture.root / "runtime.env.private"
    env.write_text("SYNTHETIC_DATABASE_URL=private-synthetic-before\n")
    fixture.release.save("container-before.private.json", {
        "HostConfig": {"NetworkMode": "synthetic_frozen_default"},
        "Config": {"Env": ["SYNTHETIC_DATABASE_URL=private-synthetic-before"]}})
    fixture.manifest = {"runtimeEnvSha": fixture.release.digest(env.read_bytes()),
        "beforeContainerSha": fixture.release.digest((fixture.root / "container-before.private.json").read_bytes())}
    return fixture


def test_recovery_executes_same_gates_on_baseline_in_frozen_network_and_environment(recovery_gates, monkeypatch):
    fixture = recovery_gates
    commands, inputs = [], []
    path = "active_work_gate.py"
    def run(args, **kwargs):
        commands.append(args)
        inputs.append(kwargs["input"])
        return SimpleNamespace(returncode=0, stdout=json.dumps(zero_gate_counts(fixture, path)).encode(), stderr=b"")
    monkeypatch.setattr(fixture.release.subprocess, "run", run)
    fixture.release.idle_gates({"gates": [path], "supportFiles": fixture.hashes},
                               recovery_manifest=fixture.manifest)
    assert len(commands) == 1 and inputs == [(fixture.root / path).read_bytes()]
    command = commands[0]
    assert command[:4] == ["docker", "run", "--rm", "-i"]
    assert command[command.index("--network")+1] == "synthetic_frozen_default"
    assert command[command.index("--env-file")+1] == str(fixture.root / "runtime.env.private")
    assert command[command.index("--entrypoint")+1:] == ["python", fixture.release.BASE_IMAGE, "-B", "-"]
    for flag in ("--read-only", "--cap-drop", "--security-opt", "--pids-limit", "--memory"):
        assert flag in command
    assert not any(flag in command for flag in ("--mount", "-v", "--volume", "-p", "--publish", "--privileged"))
    assert not any("private-synthetic-before" in argument for argument in command)
    assert fixture.release.CONTAINER not in command


@pytest.mark.parametrize("kind", ["environment", "network-snapshot"])
def test_recovery_frozen_private_context_drift_blocks_before_starting_gate_container(recovery_gates, monkeypatch, kind):
    fixture = recovery_gates
    if kind == "environment":
        (fixture.root / "runtime.env.private").write_text("SYNTHETIC_DATABASE_URL=wrong-after-freeze\n")
    else:
        fixture.release.save("container-before.private.json", {"HostConfig": {"NetworkMode": "unowned-network"}})
    calls = []
    monkeypatch.setattr(fixture.release.subprocess, "run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(fixture.release.ReleaseError):
        fixture.release.idle_gates({"gates": ["active_work_gate.py"], "supportFiles": fixture.hashes},
                                   recovery_manifest=fixture.manifest)
    assert calls == []


def test_recovery_baseline_gate_still_defers_new_protected_work(recovery_gates, monkeypatch):
    fixture = recovery_gates
    path = "active_work_gate.py"
    counts = zero_gate_counts(fixture, path)
    counts["connectedDesktopPublishers"] = 1
    monkeypatch.setattr(fixture.release.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=json.dumps(counts).encode(), stderr=b""))
    with pytest.raises(fixture.release.ReleaseError, match="protected_user_work_cutover_deferred"):
        fixture.release.idle_gates({"gates": [path], "supportFiles": fixture.hashes},
                                   recovery_manifest=fixture.manifest)



def test_live_full_schema_accepts_64_admin_public_health_routes_beyond_offline_shell(harness, monkeypatch):
    setup_live(harness, monkeypatch)
    offline = {f"/api/v1/synthetic-{index}": ["get"] for index in range(151)}
    full = offline | {f"/synthetic-admin-public-health-{index}": ["get"] for index in range(64)}
    (harness.root / "probe/probe-expectations.json").write_text(json.dumps({
        "routes": {"http": offline}, "liveHttp": full, "liveOpenapiSha": "synthetic-full-schema"}))
    harness.live_payload = {"http": full, "schemaSha": "synthetic-full-schema"}
    result = harness.real_verify_live(harness.manifest, harness.plan)
    assert result["httpPathsVerified"] == 215
    assert result["liveOpenapiSha"] == "synthetic-full-schema"


@pytest.mark.parametrize("kind", ["missing-admin", "unexpected-public", "schema-drift"])
def test_full_live_schema_rejects_extra_router_loss_unexpected_route_or_schema_drift(harness, monkeypatch, kind):
    setup_live(harness, monkeypatch)
    offline = {f"/api/v1/synthetic-{index}": ["get"] for index in range(151)}
    full = offline | {f"/synthetic-admin-public-health-{index}": ["get"] for index in range(64)}
    actual = dict(full)
    schema_sha = "synthetic-full-schema"
    if kind == "missing-admin":
        del actual["/synthetic-admin-public-health-1"]
    elif kind == "unexpected-public":
        actual["/unexpected-synthetic-public"] = ["get"]
    else:
        schema_sha = "synthetic-schema-changed-with-same-routes"
    (harness.root / "probe/probe-expectations.json").write_text(json.dumps({
        "routes": {"http": offline}, "liveHttp": full, "liveOpenapiSha": "synthetic-full-schema"}))
    harness.live_payload = {"http": actual, "schemaSha": schema_sha}
    with pytest.raises(harness.release.ReleaseError, match=(
            "live_api_schema_mismatch" if kind == "schema-drift" else "live_api_routes_mismatch")):
        harness.real_verify_live(harness.manifest, harness.plan)


def test_pre_cutover_full_live_route_verification_failure_never_restarts(harness, monkeypatch):
    def reject():
        raise harness.release.ReleaseError("live_api_schema_mismatch")
    monkeypatch.setattr(harness.release, "verify_live_routes", reject)
    with pytest.raises(harness.release.ReleaseError, match="live_api_schema_mismatch"):
        harness.release.deploy()
    assert harness.actions == []


@pytest.mark.parametrize("key", ["candidateTests", "additionalSubtests", "skipped", "syntheticOnly"])
def test_dynamic_counts_must_match_frozen_report(valid_inputs, key):
    fixture = valid_inputs
    value = fixture.report[key]
    fixture.report[key] = False if key == "syntheticOnly" else value+1
    save_report(fixture)
    with pytest.raises(fixture.release.ReleaseError, match="candidate_test_count_mismatch"):
        fixture.release.check_inputs()


def test_zero_skips_and_subtests_are_accepted_when_actual_report_matches(valid_inputs):
    fixture = valid_inputs
    for key in ("additionalSubtests", "skipped"):
        fixture.plan["verified"][key] = fixture.report[key] = 0
    save_report(fixture)
    assert fixture.release.check_inputs() == fixture.plan


def test_report_counters_cannot_use_boolean_instead_of_integer(valid_inputs):
    fixture = valid_inputs
    fixture.plan["verified"]["additionalSubtests"] = 0
    fixture.report["additionalSubtests"] = False
    save_report(fixture)
    with pytest.raises(fixture.release.ReleaseError, match="candidate_test_count_mismatch"):
        fixture.release.check_inputs()


def test_global_release_constants_and_domains_do_not_take_cn_context():
    release = load_release()
    assert str(release.ROOT) == "/opt/offersteady-global/releases/20261017-global-auth-state-1"
    assert release.PROJECT == "offersteady-global"
    assert release.CONTAINER == "offersteady-global-backend-1"
    assert release.BASE_ID == "c2b7caa35c86c85c13c4f9baeebb1da30465562d4ad50126c56db3d141d5bd4e"
    assert release.BASE_IMAGE == "sha256:b31a810a49f718e360f8ddbcbae0e7aa3d0184012b8993cd0e2f5f973bc7657a"
    assert len(release.FILES) == 8 and len(release.GATES) == 5
    assert release.GATES == {"legacy-gates/check-idle.py", "legacy-gates/check-mock-idle.py",
                             "global_mock_companion_idle_gate.py", "extra_idle_gate.py", "active_work_gate.py"}
    assert "mianshiwen.cn" not in SOURCE.read_text()
    assert "https://offersteady.com/healthz" in SOURCE.read_text()


@pytest.mark.parametrize("path", ["legacy-gates/check-idle.py", "legacy-gates/check-mock-idle.py",
                                 "global_mock_companion_idle_gate.py", "extra_idle_gate.py", "active_work_gate.py"])
def test_all_five_global_gate_sources_are_identical_to_reviewed_global_baseline(path):
    support = Path(__file__).parent
    old_support = support.parent / "global_question_prefetch_20261016"
    assert (support/path).read_bytes() == (old_support/path).read_bytes()


@pytest.mark.parametrize("name", ["freeze_context", "verify_context", "compose_args", "config_digest",
                                 "safe_gate_counts", "gate_is_idle", "refresh_proxy_if_needed", "runtime_invariant"])
def test_global_deployment_context_and_gate_rules_are_byte_preserved(name):
    old = SOURCE.with_name("release_global_question_prefetch.py").read_text()
    new = SOURCE.read_text()
    def function(text):
        lines = text.splitlines(keepends=True)
        node = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == name)
        return "".join(lines[node.lineno-1:node.end_lineno])
    assert function(old) == function(new)



def test_actual_five_compose_one_environment_context_is_frozen_in_order(multi_context):
    h = multi_context
    fifth = h.files[0].parent / "compose-fifth-private-overlay.json"
    fifth.write_text(json.dumps({"services": {"backend": {"image": h.release.BASE_IMAGE}}}))
    h.before["Config"]["Labels"]["com.docker.compose.project.config_files"] += "," + str(fifth)
    h.before["Config"]["Labels"]["com.docker.compose.project.environment_file"] = str(h.envs[0])
    manifest, source = h.release.freeze_context(h.before)
    assert manifest["composeFiles"] == list(map(str, h.files)) + [str(fifth)]
    assert manifest["envFiles"] == [str(h.envs[0])]
    assert len(manifest["frozenComposeFiles"]) == 5 and len(manifest["frozenEnvFiles"]) == 1
    assert source["services"]["backend"]["image"] == h.release.BASE_IMAGE
    h.release.verify_context(manifest)


def test_all_six_non_target_containers_are_frozen_and_drift_prevents_switch(harness):
    for index in range(5):
        name = f"synthetic-global-non-target-{index}"
        harness.current[name] = {"Id": f"synthetic-id-{index}", "Image": f"synthetic-image-{index}",
                                 "State": {"StartedAt": "synthetic-original-start"}}
        harness.manifest["nonTargets"][name] = {"id": f"synthetic-id-{index}", "image": f"synthetic-image-{index}",
                                               "startedAt": "synthetic-original-start"}
    assert len(harness.manifest["nonTargets"]) == 6
    harness.release.save("prepared.json", harness.manifest)
    harness.current["synthetic-global-non-target-4"]["Id"] = "synthetic-unowned-replacement"
    with pytest.raises(harness.release.ReleaseError, match="unrelated_container_drift"):
        harness.release.deploy()
    assert harness.actions == []
