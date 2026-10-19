"""Synthetic release-controller checks; no Docker, SSH, sockets or databases."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


SOURCE = Path(__file__).resolve().parents[3] / "scripts/release_global_question_prefetch.py"


def load_release():
    spec = importlib.util.spec_from_file_location("synthetic_prefetch_cutover", SOURCE)
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
    release.save("compose-before.private.json", rendered)
    release.save("compose.prefetch.json", {"services": {"backend": {"image": new_image}}})
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
        "runtimeConfigSha": "synthetic-effective-config", "newImage": new_image,
        "rollbackImage": release.BASE_IMAGE,
        "overlaySha": release.digest((tmp_path / "compose.prefetch.json").read_bytes()),
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

    def idle_gates(_plan):
        gates.append(True)
        if (len(gates) == 1 and faults["gate_first"]) or (len(gates) == 2 and faults["gate_second"]):
            raise release.ReleaseError("protected_user_work_cutover_deferred")
        if len(gates) == 2 and faults["late_drift"]:
            target = {"env": envfile, "compose": composefile,
                      "overlay": tmp_path / "compose.prefetch.json"}[faults["late_drift"]]
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
    monkeypatch.setattr(release, "config_digest", lambda: manifest["runtimeConfigSha"])
    monkeypatch.setattr(release, "inventory", lambda _name: (
        before_inventory if current[release.CONTAINER]["Image"] == release.BASE_IMAGE else before_inventory | plan["files"]))
    monkeypatch.setattr(release, "wait_healthy", lambda expected: inspect(release.CONTAINER))
    monkeypatch.setattr(release, "refresh_proxy_if_needed", lambda *_args: [])
    monkeypatch.setattr(release, "verify_live", verify_live)
    monkeypatch.setattr(release, "idle_gates", idle_gates)
    return SimpleNamespace(release=release, root=tmp_path, plan=plan, manifest=manifest, base=base,
                           current=current, faults=faults, actions=actions, commands=commands, gates=gates)


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
    monkeypatch.setattr(sys, "argv", ["release_global_question_prefetch.py", "rollback"])
    with pytest.raises(harness.release.ReleaseError):
        harness.release.main()
    assert harness.actions == []


def test_manual_rollback_rejects_a_same_image_with_unowned_configuration_drift(harness, monkeypatch):
    harness.current[harness.release.CONTAINER]["Image"] = harness.manifest["newImage"]
    harness.current[harness.release.CONTAINER]["Config"]["Env"] = ["SAFE_SYNTHETIC_SETTING=synthetic-other-change"]
    monkeypatch.setattr(sys, "argv", ["release_global_question_prefetch.py", "rollback"])
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
        "files": files, "verified": {"candidateTests": 221, "answerTests": 16}, "supportFiles": {}, "gates": []})
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

    def gate(plan):
        if len(harness.gates) == 2:
            raise harness.release.ReleaseError("protected_user_work_cutover_deferred")
        original(plan)

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
    args = h.release.compose_args(manifest, "compose.prefetch.json")
    assert args[args.index("-p") + 1] == h.release.PROJECT
    assert args[args.index("--project-directory") + 1] == str(h.workdir)
    assert [args[index+1] for index, item in enumerate(args) if item == "--env-file"] == manifest["frozenEnvFiles"]
    assert [args[index+1] for index, item in enumerate(args) if item == "-f"] == (
        manifest["frozenComposeFiles"] + [str(h.root / "compose.prefetch.json")])
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
