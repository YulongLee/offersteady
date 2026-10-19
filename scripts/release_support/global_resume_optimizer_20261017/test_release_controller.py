"""Synthetic Global resume release safety tests; no Docker, SSH or real data."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "release_global_resume_optimizer.py"


def load_release():
    spec = importlib.util.spec_from_file_location("synthetic_global_resume_release", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def release(tmp_path, monkeypatch):
    module = load_release()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    return module


def container(release, service="backend"):
    ident, image = release.BASES[service]
    return {
        "Id": ident, "Image": image, "RestartCount": 0,
        "Config": {"Image": "synthetic-compose-" + service, "Env": ["SAFE_SYNTHETIC=private-value"],
            "Hostname": ident[:12], "Labels": {"com.docker.compose.project": release.PROJECT,
            "com.docker.compose.service": service, "com.docker.compose.project.working_dir": "/opt/offersteady-global/releases/old/infra",
            "com.docker.compose.project.config_files": "/opt/offersteady-global/releases/old/compose.json",
            "com.docker.compose.project.environment_file": "/opt/offersteady-global/releases/old/env.private",
            "com.docker.compose.container-number": "1", "com.docker.compose.oneoff": "False",
            "safe-label": "retained"}, "Cmd": ["synthetic-server"], "Entrypoint": None,
            "WorkingDir": "/app/apps/backend", "User": "", "ExposedPorts": {"8000/tcp": {}}},
        "HostConfig": {"NetworkMode": "offersteady-global_default", "Memory": 1024, "PidsLimit": 128},
        "Mounts": [{"Type": "volume", "Name": "synthetic", "Destination": "/synthetic"}],
        "NetworkSettings": {"Networks": {"offersteady-global_default": {"IPAddress": "172.31.0.2"}}},
        "State": {"Running": True, "StartedAt": "synthetic-before", "Health": {"Status": "healthy"}},
    }


def target(release, service="backend"):
    return {"service": service, "container": release.PROJECT + "-" + service + "-1",
        "newImage": "sha256:" + ("a" if service == "backend" else "b") * 64,
        "rollbackImage": release.BASES[service][1], "frozenComposeFiles": ["/synthetic/frozen-compose"],
        "frozenEnvFiles": ["/synthetic/frozen-env"], "composeDirectory": "/opt/offersteady-global/releases/old/infra",
        "newOverlay": "/synthetic/new-image", "rollbackOverlay": "/synthetic/rollback-image"}


def save_before(release, value, service="backend"):
    directory = release.ROOT / service
    directory.mkdir(exist_ok=True)
    release.write_json(directory / "container-before.json", value)


def new_container(release, before, t, kind="new"):
    value = deepcopy(before)
    value["Id"] = "synthetic-" + t["service"] + "-" + kind
    value["Image"] = t[kind + "Image"]
    value["Config"]["Image"] = t[kind + "Image"]
    value["Config"]["Hostname"] = value["Id"][:12]
    value["Config"]["Labels"]["com.docker.compose.project.config_files"] = ",".join(t["frozenComposeFiles"] + [t[kind + "Overlay"]])
    value["Config"]["Labels"]["com.docker.compose.project.working_dir"] = t["composeDirectory"]
    value["Config"]["Labels"]["com.docker.compose.project.environment_file"] = ",".join(t["frozenEnvFiles"])
    if kind == "new" and t["service"] == "backend":
        value["Config"]["Env"].append(release.FLAG + "=true")
    return value


def test_new_overlay_changes_only_fixed_image_and_backend_flag(release):
    before = {"services": {"backend": {"image": "old", "environment": {"UNCHANGED": "yes"}, "mem_limit": 5},
                             "web": {"image": "old-web", "environment": {"KEEP": "yes"}}}, "networks": {"x": {}}}
    for service in ("backend", "web"):
        t = target(release, service)
        after = release.expected_config(before, t, "new")
        expected = deepcopy(before)
        expected["services"][service]["image"] = t["newImage"]
        if service == "backend":
            expected["services"][service]["environment"][release.FLAG] = "true"
        assert after == expected
        assert before["services"]["backend"]["environment"] == {"UNCHANGED": "yes"}
        rolled = release.expected_config(before, t, "rollback")
        expected = deepcopy(before)
        expected["services"][service]["image"] = t["rollbackImage"]
        assert rolled == expected


@pytest.mark.parametrize("service", ["backend", "web"])
def test_runtime_invariant_accepts_only_declared_new_environment(release, service):
    before, t = container(release, service), target(release, service)
    release.runtime_invariant(before, new_container(release, before, t), t, "new")


@pytest.mark.parametrize("section,field,value", [
    ("HostConfig", "Memory", 9999), ("HostConfig", "PidsLimit", 7), ("HostConfig", "NetworkMode", "host"),
    ("Config", "Cmd", ["foreign"]), ("Config", "User", "foreign"), ("Config", "WorkingDir", "/foreign"),
    ("Config", "Entrypoint", ["foreign"]), ("Config", "ExposedPorts", {}),
    ("Config", "Hostname", "foreign-host"), ("Config", "Env", ["SAFE_SYNTHETIC=changed"]),
])
def test_runtime_invariant_refuses_unrelated_host_or_config_drift(release, section, field, value):
    before, t = container(release), target(release)
    after = new_container(release, before, t)
    after[section][field] = value
    with pytest.raises(release.GuardError):
        release.runtime_invariant(before, after, t, "new")


@pytest.mark.parametrize("kind", ["mount", "label", "image"])
def test_runtime_invariant_refuses_mount_label_and_image_drift(release, kind):
    before, t = container(release), target(release)
    after = new_container(release, before, t)
    if kind == "mount": after["Mounts"] = []
    elif kind == "label": after["Config"]["Labels"]["safe-label"] = "foreign"
    else: after["Image"] = release.BASE_IMAGE
    with pytest.raises(release.GuardError): release.runtime_invariant(before, after, t, "new")


def test_runtime_version_legacy_override_does_not_fix_other_drift(release):
    before = container(release)
    before["Config"]["Env"].append("OFFERSTEADY_APP_VERSION=actual")
    source = {"services": {"backend": {"environment": {"SAFE_SYNTHETIC": "private-value", "OFFERSTEADY_APP_VERSION": "historical"}}}}
    actual, used = release.runtime_baseline(source, before, "backend")
    assert used and actual["services"]["backend"]["environment"]["OFFERSTEADY_APP_VERSION"] == "actual"
    assert source["services"]["backend"]["environment"]["OFFERSTEADY_APP_VERSION"] == "historical"
    source["services"]["backend"]["environment"]["SAFE_SYNTHETIC"] = "foreign"
    with pytest.raises(release.GuardError): release.runtime_baseline(source, before, "backend")


def test_web_environment_mismatch_is_not_treated_as_legacy_backend_version(release):
    before = container(release, "web")
    before["Config"]["Env"].append("OFFERSTEADY_APP_VERSION=actual")
    with pytest.raises(release.GuardError):
        release.runtime_baseline({"services": {"web": {"environment": {"OFFERSTEADY_APP_VERSION": "historical"}}}}, before, "web")


@pytest.mark.parametrize("mutation", ["foreign-id", "same-id-foreign-image", "same-image-foreign-labels", "wrong-project", "wrong-service"])
def test_recovery_never_claims_a_foreign_container(release, monkeypatch, mutation):
    before, t = container(release), target(release)
    save_before(release, before)
    current = new_container(release, before, t)
    progress = {"backend": {"id": current["Id"], "image": current["Image"], "kind": "new"}}
    if mutation == "foreign-id": current["Id"] = "foreign-later-release"
    elif mutation == "same-id-foreign-image": current["Image"] = "sha256:" + "c" * 64
    elif mutation == "same-image-foreign-labels": current["Config"]["Labels"]["com.docker.compose.project.config_files"] = "/foreign/context"
    elif mutation == "wrong-project": current["Config"]["Labels"]["com.docker.compose.project"] = "foreign"
    else: current["Config"]["Labels"]["com.docker.compose.service"] = "foreign"
    monkeypatch.setattr(release, "inspect", lambda _: current)
    with pytest.raises(release.GuardError): release.assert_owned({}, t, progress)


@pytest.mark.parametrize("mutation", ["id", "image", "config"])
def test_unmodified_baseline_requires_original_id_image_and_config(release, monkeypatch, mutation):
    before, t = container(release), target(release)
    save_before(release, before)
    current = deepcopy(before)
    if mutation == "config": current["Config"]["Cmd"] = ["foreign"]
    elif mutation == "id": current["Id"] = "foreign"
    else: current["Image"] = "foreign"
    monkeypatch.setattr(release, "inspect", lambda _: current)
    with pytest.raises(release.GuardError): release.assert_owned({}, t, {})


def test_independent_gates_use_fixed_old_image_frozen_environment_and_network(release):
    save_before(release, container(release))
    command = release.baseline_command({})
    assert command[-3:] == [release.BASE_IMAGE, "-B", "-"]
    assert "--read-only" in command and "--cap-drop" in command and "ALL" in command
    assert command[command.index("--network") + 1] == "offersteady-global_default"
    assert command[command.index("--env-file") + 1] == str(release.ROOT / "runtime.env.private")
    assert command[command.index("--entrypoint") + 1] == "python"
    assert "--security-opt" in command and "no-new-privileges" in command
    assert "app.main" not in " ".join(command)


@pytest.mark.parametrize("network", ["host", "none", "bad network", "x; touch /bad", "", "x\nsecret"])
def test_independent_gate_refuses_unsafe_frozen_network(release, network):
    before = container(release)
    before["HostConfig"]["NetworkMode"] = network
    save_before(release, before)
    with pytest.raises(release.GuardError): release.baseline_command({})


@pytest.fixture
def gates(release, monkeypatch):
    save_before(release, container(release))
    plan = {"gates": sorted(release.GATES), "supportFiles": {}, "gateFields": {}, "gateInformationalFields": {}}
    for path in plan["gates"]:
        p = release.ROOT / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# synthetic read-only gate " + path)
        plan["supportFiles"][path] = release.digest(p.read_bytes())
        plan["gateFields"][path] = ["protected", "unknown", "readFailures"]
        plan["gateInformationalFields"][path] = ["terminal"]
    calls = []
    reply = {"counts": {"protected": 0, "unknown": 0, "readFailures": 0, "terminal": 99}, "exit": 0, "exception": None}
    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if reply["exception"]: raise reply["exception"]
        value = reply["counts"]
        return SimpleNamespace(returncode=reply["exit"], stdout=json.dumps(value).encode())
    monkeypatch.setattr(release.subprocess, "run", fake_run)
    return SimpleNamespace(release=release, plan=plan, calls=calls, reply=reply)


def test_all_six_independent_gates_execute_and_only_summary_is_saved(gates):
    result = gates.release.idle_gates({}, gates.plan)
    assert len(result) == len(gates.calls) == 6
    assert any(r["gate"] == "resume_optimizer_idle_gate.py" for r in result)
    assert all(c[0][-3:] == [gates.release.BASE_IMAGE, "-B", "-"] for c in gates.calls)
    assert all(c[1]["timeout"] == 25 for c in gates.calls)
    assert json.loads((gates.release.ROOT / "last-idle-gates.json").read_text()) == result


@pytest.mark.parametrize("key,value", [("protected", 1), ("unknown", 1), ("readFailures", 1), ("protected", 999)])
def test_protected_counts_cannot_be_overridden_by_exit_zero(gates, key, value):
    gates.reply["counts"][key] = value
    with pytest.raises(gates.release.GuardError, match="protected_user_work_cutover_deferred"):
        gates.release.idle_gates({}, gates.plan)
    assert len(gates.calls) == 1


@pytest.mark.parametrize("kind", ["missing", "extra", "bool", "negative", "string", "list", "null", "exception", "exit-failed"])
def test_unknown_malformed_or_failed_gate_never_passes(gates, kind):
    if kind == "missing": del gates.reply["counts"]["unknown"]
    elif kind == "extra": gates.reply["counts"]["private-body"] = 0
    elif kind == "bool": gates.reply["counts"]["protected"] = False
    elif kind == "negative": gates.reply["counts"]["protected"] = -1
    elif kind == "string": gates.reply["counts"]["protected"] = "0"
    elif kind == "list": gates.reply["counts"] = []
    elif kind == "null": gates.reply["counts"] = None
    elif kind == "exception": gates.reply["exception"] = TimeoutError("private connection detail")
    else: gates.reply["exit"] = 3
    with pytest.raises(gates.release.GuardError) as caught:
        gates.release.idle_gates({}, gates.plan)
    assert "private" not in str(caught.value) and len(gates.calls) == 1


def test_changed_gate_source_stops_before_launch(gates):
    (gates.release.ROOT / gates.plan["gates"][0]).write_text("# drift")
    with pytest.raises(gates.release.GuardError, match="protected_gate_source_drift"):
        gates.release.idle_gates({}, gates.plan)
    assert gates.calls == []


def test_entire_api_schema_equality_includes_nonoptimizer_routes(release):
    expected = {"paths": {"/admin": {"get": {}}, "/api/v1/chat": {"post": {}}}, "components": {"schemas": {"Protected": {"type": "string"}}}}
    release.assert_schema(deepcopy(expected), expected)
    for actual in ({"paths": {}}, expected | {"info": {"foreign": True}}, expected | {"components": {}}):
        with pytest.raises(release.GuardError): release.assert_schema(actual, expected)


@pytest.mark.parametrize("kind", ["id", "image", "started", "shared-tag"])
def test_nontarget_and_shared_tag_drift_are_rejected(release, monkeypatch, kind):
    current = {"other": {"Id": "old", "Image": "old-image", "State": {"StartedAt": "old-start"}}, "shared": {"Id": "fixed-shared"}}
    manifest = {"nonTargets": {"other": {"id": "old", "image": "old-image", "startedAt": "old-start"}}, "sharedTags": {"shared": "fixed-shared"}}
    if kind == "started": current["other"]["State"]["StartedAt"] = "new"
    elif kind == "shared-tag": current["shared"]["Id"] = "foreign"
    else: current["other"]["Id" if kind == "id" else "Image"] = "foreign"
    monkeypatch.setattr(release, "inspect", lambda name: current[name])
    with pytest.raises(release.GuardError): release.verify_non_targets(manifest)


@pytest.fixture
def cutover(release, monkeypatch):
    targets = [target(release, s) for s in ("backend", "web")]
    manifest = {"targets": targets}
    release.write_json(release.ROOT / "prepared.json", manifest)
    events, faults = [], {"gate": None, "switch": None, "foreign": False}
    monkeypatch.setattr(release, "check_inputs", lambda: {})
    monkeypatch.setattr(release, "verify_files", lambda *_: None)
    def verify(_manifest, _plan, progress, final=False):
        events.append(("verify", final, dict(progress)))
        if final and any(progress.get(s, {}).get("kind") != "new" for s in ("backend", "web")):
            raise release.GuardError("release_incomplete")
    monkeypatch.setattr(release, "verify_current", verify)
    gate_calls = []
    def idle(*_):
        gate_calls.append(True)
        events.append(("gate", len(gate_calls)))
        if faults["gate"] == len(gate_calls):
            raise release.GuardError("protected_user_work_cutover_deferred")
    monkeypatch.setattr(release, "idle_gates", idle)
    monkeypatch.setattr(release, "migrate", lambda _: events.append(("migrate",)))
    def switch(_manifest, t, kind, progress):
        events.append(("switch", t["service"], kind))
        if faults["switch"] == (t["service"], kind): raise release.GuardError("target_health_failed")
        progress[t["service"]] = {"id": "synthetic-" + t["service"] + kind, "image": t[kind + "Image"], "kind": kind}
        release.write_json(release.ROOT / "progress.json", progress)
    monkeypatch.setattr(release, "switch", switch)
    def owned(*_):
        if faults["foreign"]: raise release.GuardError("release_container_owner_changed")
    monkeypatch.setattr(release, "assert_owned", owned)
    monkeypatch.setattr(release, "public_checks", lambda: [{"path": "/login", "status": 200}])
    return SimpleNamespace(release=release, manifest=manifest, targets=targets, events=events, gates=gate_calls, faults=faults)


def mutations(cutover):
    return [e for e in cutover.events if e[0] in ("switch", "migrate")]


def test_preflight_never_migrates_or_switches(cutover):
    cutover.release.deploy(preflight=True)
    assert mutations(cutover) == [] and len(cutover.gates) == 1


@pytest.mark.parametrize("gate", [1, 2, 3])
def test_activity_before_backend_cutover_never_mutates_service(cutover, gate):
    cutover.faults["gate"] = gate
    with pytest.raises(cutover.release.GuardError): cutover.release.deploy()
    assert not [e for e in cutover.events if e[0] == "switch"]
    assert not (cutover.release.ROOT / "deployed.json").exists()
    if gate < 3: assert mutations(cutover) == []


def test_new_activity_after_backend_preserves_partial_release_for_resume(cutover):
    cutover.faults["gate"] = 4
    with pytest.raises(cutover.release.GuardError): cutover.release.deploy()
    assert [e for e in cutover.events if e[0] == "switch"] == [("switch", "backend", "new")]
    cutover.faults["gate"] = None
    cutover.release.deploy()
    assert [e for e in cutover.events if e[0] == "switch"] == [("switch", "backend", "new"), ("switch", "web", "new")]


def test_success_changes_only_backend_then_web(cutover):
    cutover.release.deploy()
    assert [e for e in cutover.events if e[0] == "switch"] == [("switch", "backend", "new"), ("switch", "web", "new")]
    assert len(cutover.gates) == 4
    assert json.loads((cutover.release.ROOT / "deployed.json").read_text())["deployed"] is True


def test_completed_deploy_is_verified_without_restart_or_migration(cutover):
    cutover.release.deploy()
    cutover.events.clear()
    cutover.release.deploy()
    assert mutations(cutover) == []


def test_failed_web_switch_restores_owned_backend_only(cutover):
    cutover.faults["switch"] = ("web", "new")
    with pytest.raises(cutover.release.GuardError): cutover.release.deploy()
    assert [e for e in cutover.events if e[0] == "switch"] == [("switch", "backend", "new"), ("switch", "web", "new"), ("switch", "backend", "rollback")]
    assert json.loads((cutover.release.ROOT / "rollback-result.json").read_text())["restored"] is True


def test_recovery_refuses_a_foreign_owner(cutover):
    cutover.release.write_json(cutover.release.ROOT / "progress.json", {"backend": {"kind": "new"}})
    cutover.faults["foreign"] = True
    with pytest.raises(cutover.release.GuardError): cutover.release.rollback()
    assert mutations(cutover) == []


def test_recovery_defers_when_a_user_starts_work(cutover):
    cutover.release.write_json(cutover.release.ROOT / "progress.json", {"backend": {"kind": "new"}})
    cutover.faults["gate"] = 1
    with pytest.raises(cutover.release.GuardError): cutover.release.rollback()
    assert mutations(cutover) == []


def test_recovery_restores_web_before_backend_and_retains_additive_tables(cutover):
    cutover.release.deploy()
    cutover.events.clear()
    cutover.release.rollback()
    assert [e for e in cutover.events if e[0] == "switch"] == [("switch", "web", "rollback"), ("switch", "backend", "rollback")]
    assert len([e for e in cutover.events if e[0] == "gate"]) == 2
    assert json.loads((cutover.release.ROOT / "rollback-result.json").read_text())["additiveTablesRetained"] is True


def test_actual_candidate_probe_is_networkless_readonly_and_not_main(release, monkeypatch):
    t = target(release)
    calls = []
    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout=b'{"passed":true}')
    monkeypatch.setattr(release, "run", fake_run)
    assert release.probe({"targets": [t]}) == {"passed": True}
    command = calls[0][0]
    assert "--network=none" in command and "--read-only" in command
    assert "--cap-drop" in command and "ALL" in command and "no-new-privileges" in command
    assert command[-3:] == [t["newImage"], "-B", "/verify/candidate-probe.py"]
    assert command[command.index("--entrypoint") + 1] == "python"
    assert "app.main" not in " ".join(command)


def test_release_lock_refuses_second_action_and_releases_after_exception(release):
    with release.release_lock():
        with pytest.raises(release.GuardError, match="another_release_action_is_running"):
            with release.release_lock():
                pytest.fail("concurrent controller action acquired an exclusive release lock")
    with pytest.raises(ValueError):
        with release.release_lock():
            raise ValueError("synthetic")
    with release.release_lock():
        pass


@pytest.fixture
def inputs(release):
    files = {"apps/backend/app/services/synthetic_resume.py": b"# synthetic source\n"}
    web = {"index.html": b"synthetic new root", "assets/new-synthetic.js": b"synthetic bundle"}
    wheels = {"reportlab-4.4.9-py3-none-any.whl": b"synthetic wheel not executed"}
    for dirname, records in (("input", files), ("web-input", web), ("wheels", wheels)):
        for name, body in records.items():
            p = release.ROOT / dirname / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
    verified = {"passed": True, "syntheticOnly": True, "backendTests": 65, "webTests": 10,
                "browserScenarios": 26, "exportsRendered": True}
    plan = {"baselines": {s: {"id": v[0], "image": v[1]} for s, v in release.BASES.items()},
            "gates": sorted(release.GATES), "verified": verified,
            "files": {p: release.digest(b) for p, b in files.items()},
            "approvedFiles": list(files), "webFiles": {p: release.digest(b) for p, b in web.items()},
            "webBefore": {"assets/old-synthetic.js": "old-hash"},
            "wheels": {p: release.digest(b) for p, b in wheels.items()}, "supportFiles": {}}
    report = {"passed": True, "sourceFrozenAfterTests": True, "files": plan["files"],
              "webFiles": plan["webFiles"], "verified": deepcopy(verified),
              "records": [{"returncode": 0, "group": "synthetic"}]}
    release.write_json(release.ROOT / "candidate-verification.json", report)
    required = {SOURCE.name, *release.GATES, "probe/candidate-probe.py", "probe/expectations.json", "candidate-verification.json"}
    for path in required:
        p = release.ROOT / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if path in release.GATES:
            actual_gate = Path(__file__).parent / path
            if not actual_gate.exists():
                actual_gate = Path(__file__).parent.parent / "global_auth_state_20261017" / path
            p.write_bytes(actual_gate.read_bytes())
        elif path != "candidate-verification.json":
            p.write_text("synthetic support " + path)
        plan["supportFiles"][path] = release.digest(p.read_bytes())
    plan["gateFields"], plan["gateInformationalFields"] = {}, {}
    for gate in release.GATES:
        protected, informational = release.gate_contract(gate)
        plan["gateFields"][gate] = sorted(protected)
        plan["gateInformationalFields"][gate] = sorted(informational)
    release.write_json(release.ROOT / "input.json", plan)
    return SimpleNamespace(release=release, plan=plan, report=report)


def persist_inputs(inputs, *, report=False):
    if report:
        inputs.release.write_json(inputs.release.ROOT / "candidate-verification.json", inputs.report)
        inputs.plan["supportFiles"]["candidate-verification.json"] = inputs.release.digest((inputs.release.ROOT / "candidate-verification.json").read_bytes())
    inputs.release.write_json(inputs.release.ROOT / "input.json", inputs.plan)


def test_frozen_verified_payload_is_accepted(inputs):
    assert inputs.release.check_inputs() == inputs.plan


@pytest.mark.parametrize("key", ["backendTests", "webTests", "browserScenarios", "exportsRendered"])
def test_plan_cannot_claim_verification_counts_different_from_report(inputs, key):
    inputs.plan["verified"][key] = False if key == "exportsRendered" else inputs.plan["verified"][key] + 1
    persist_inputs(inputs)
    with pytest.raises(inputs.release.GuardError): inputs.release.check_inputs()


@pytest.mark.parametrize("kind", ["empty", "failed-group", "source-not-frozen", "wrong-source", "wrong-web", "not-passed"])
def test_verification_requires_frozen_source_and_every_group_passed(inputs, kind):
    if kind == "empty": inputs.report["records"] = []
    elif kind == "failed-group": inputs.report["records"][0]["returncode"] = 1
    elif kind == "source-not-frozen": inputs.report["sourceFrozenAfterTests"] = False
    elif kind == "wrong-source": inputs.report["files"] = {}
    elif kind == "wrong-web": inputs.report["webFiles"] = {}
    else: inputs.report["passed"] = False
    persist_inputs(inputs, report=True)
    with pytest.raises(inputs.release.GuardError): inputs.release.check_inputs()


@pytest.mark.parametrize("kind", ["missing-gate", "unapproved-source", "changed-source", "support-drift", "old-asset-overwrite", "dependency-drift", "foreign-baseline"])
def test_scope_or_payload_drift_stops_prepare(inputs, kind):
    if kind == "missing-gate": inputs.plan["gates"].pop()
    elif kind == "unapproved-source": inputs.plan["approvedFiles"] = []
    elif kind == "changed-source": (inputs.release.ROOT / "input" / next(iter(inputs.plan["files"]))).write_bytes(b"drift")
    elif kind == "support-drift": (inputs.release.ROOT / SOURCE.name).write_bytes(b"drift")
    elif kind == "old-asset-overwrite": inputs.plan["webBefore"]["assets/new-synthetic.js"] = "different-immutable-before"
    elif kind == "dependency-drift": (inputs.release.ROOT / "wheels/reportlab-4.4.9-py3-none-any.whl").write_bytes(b"drift")
    else: inputs.plan["baselines"]["backend"]["id"] = "foreign"
    persist_inputs(inputs)
    with pytest.raises(inputs.release.GuardError): inputs.release.check_inputs()


@pytest.mark.parametrize("dirname", ["input", "web-input", "wheels"])
def test_unbound_payload_file_is_rejected_before_image_build(inputs, dirname):
    (inputs.release.ROOT / dirname / "unbound-extra-file").write_bytes(b"unapproved source")
    with pytest.raises(inputs.release.GuardError): inputs.release.check_inputs()


@pytest.mark.parametrize("dirname,key", [("input", "files"), ("web-input", "webFiles"), ("wheels", "wheels")])
def test_manifested_payload_symlink_is_rejected(inputs, dirname, key):
    path = inputs.release.ROOT / dirname / next(iter(inputs.plan[key]))
    content = path.read_bytes()
    path.unlink()
    referent = inputs.release.ROOT / "unapproved-referent"
    referent.write_bytes(content)
    path.symlink_to(referent)
    with pytest.raises(inputs.release.GuardError): inputs.release.check_inputs()


def load_resume_gate():
    path = Path(__file__).parent / "resume_optimizer_idle_gate.py"
    spec = importlib.util.spec_from_file_location("synthetic_resume_idle_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GateDatabase:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.queries = []
        self.connection_options = None
    def connect(self, _url, **kwargs):
        self.connection_options = kwargs
        assert kwargs["connect_timeout"] == 3
        assert "default_transaction_read_only=on" in kwargs["options"]
        assert "statement_timeout=3000" in kwargs["options"]
        return self
    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def execute(self, sql):
        self.queries.append(sql)
        assert sql.lstrip().startswith("SELECT")
        return self
    def fetchone(self): return next(self.rows)


def test_new_job_gate_accepts_absent_pre_migration_schema_only():
    gate = load_resume_gate()
    database = GateDatabase([(None,), (0,)])
    counts = gate.collect_counts(SimpleNamespace(database_url="synthetic-only"), database.connect)
    assert not any(counts.values()) and len(database.queries) == 2
    assert "0053_global_resume_optimizer.sql" in database.queries[1]


@pytest.mark.parametrize("rows", [[(None,), (1,)], [(None,), None], [None], [("jobs",), None],
                                  [("jobs",), (-1, 0)], [("jobs",), (False, 0)], [("jobs",), (0,)],
                                  [("jobs",), (0, 0, 0)], [("jobs",), ("0", 0)]])
def test_new_job_gate_schema_loss_or_malformed_aggregate_fails_closed(rows):
    gate = load_resume_gate()
    counts = gate.collect_counts(SimpleNamespace(database_url="synthetic-only"), GateDatabase(rows).connect)
    assert counts["resumeOptimizerReadFailures"] == 1
    assert set(counts) == {"resumeOptimizerQueuedOrRunning", "unknownResumeOptimizerStates", "resumeOptimizerReadFailures"}


@pytest.mark.parametrize("row", [(0, 0), (1, 0), (0, 1), (5, 2)])
def test_new_job_gate_reports_all_active_and_unknown_counts(row):
    gate = load_resume_gate()
    database = GateDatabase([("jobs",), row])
    counts = gate.collect_counts(SimpleNamespace(database_url="synthetic-only"), database.connect)
    assert counts == {"resumeOptimizerQueuedOrRunning": row[0], "unknownResumeOptimizerStates": row[1], "resumeOptimizerReadFailures": 0}
    assert "deleted_at_ms IS NULL" in database.queries[-1]
    assert "queued','running" in database.queries[-1]


def test_new_job_gate_does_not_echo_private_read_errors():
    gate = load_resume_gate()
    def refused(*_args, **_kwargs): raise RuntimeError("postgres://private-credential-and-user-data")
    counts = gate.collect_counts(SimpleNamespace(database_url="synthetic-only"), refused)
    assert counts == {"resumeOptimizerQueuedOrRunning": 0, "unknownResumeOptimizerStates": 0, "resumeOptimizerReadFailures": 1}
    assert "private" not in json.dumps(counts)


@pytest.mark.parametrize("attempt,kind", [
    ("psycopg.connect('invalid-dsn')", "database"),
    ("psycopg.Connection.connect('invalid-dsn')", "database"),
    ("psycopg.AsyncConnection.connect('invalid-dsn')", "database"),
    ("redis.Redis().execute_command('GET', 'synthetic')", "database"),
    ("threading.Thread(target=lambda:None).start()", "threadStarts"),
    ("socket.create_connection(('127.0.0.1', 1))", "network"),
    ("socket.getaddrinfo('example.invalid', 443)", "network"),
    ("open('/synthetic-never-created-probe-file', 'w')", "fileWrites"),
    ("subprocess.Popen(['synthetic-never-executed'])", "subprocesses"),
    ("sys.audit('os.chmod', '/synthetic', 384, -1)", "fileWrites"),
    ("sys.audit('os.chown', '/synthetic', 0, 0, -1)", "fileWrites"),
    ("sys.audit('os.truncate', '/synthetic', 0)", "fileWrites"),
    ("sys.audit('os.link', '/synthetic', '/synthetic-2', -1, -1)", "fileWrites"),
    ("sys.audit('os.symlink', '/synthetic', '/synthetic-2', -1)", "fileWrites"),
    ("sys.audit('os.utime', '/synthetic', None, None, -1)", "fileWrites"),
    ("sys.audit('os.fork')", "fileWrites"),
    ("sys.audit('os.posix_spawn', '/synthetic', [], {})", "fileWrites"),
])
def test_probe_rejects_each_io_attempt_before_application_import(attempt, kind):
    """Execute the actual probe's guard prefix in a disposable Python child.

    Unsafe OS operations use audit-event simulation, never real chmod/fork.
    Direct libpq entry points receive an invalid DSN, so a missing guard still
    cannot contact a real database or inherit production configuration.
    """
    import subprocess
    import sys
    probe_path = Path(__file__).parent / "probe/candidate-probe.py"
    source = probe_path.read_text()
    prefix = source.split("    root = Path('/app')", 1)[0]
    assert prefix != source
    prefix = prefix.replace("expected = json.loads(Path('/verify/expectations.json').read_text())", "expected = {}")
    script = prefix + '''
    try:
        eval(sys.argv[1])
    except BaseException as exc:
        print(json.dumps({'counters':counters,'blocked':str(exc)=='offline_probe_side_effect_rejected'}))
    else:
        print(json.dumps({'counters':counters,'blocked':False}))
main()
'''
    result = subprocess.run([sys.executable, "-B", "-c", script, attempt], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr[-1000:]
    report = json.loads(result.stdout)
    assert report["blocked"] is True and report["counters"][kind] >= 1


@pytest.mark.parametrize("gate", sorted(load_release().GATES))
@pytest.mark.parametrize("kind", ["empty-protected", "protected-as-informational", "missing-field", "extra-field"])
def test_protected_gate_contract_cannot_be_weakened_by_input_manifest(inputs, gate, kind):
    if kind == "empty-protected": inputs.plan["gateFields"][gate] = []
    elif kind == "protected-as-informational":
        field = inputs.plan["gateFields"][gate].pop()
        inputs.plan["gateInformationalFields"][gate].append(field)
    elif kind == "missing-field": inputs.plan["gateFields"][gate].pop()
    else: inputs.plan["gateFields"][gate].append("unreviewedField")
    persist_inputs(inputs)
    with pytest.raises(inputs.release.GuardError, match="protected_gate_contract_changed"):
        inputs.release.check_inputs()


@pytest.mark.parametrize("kind", ["image-config", "root-layer", "base-prefix-loss"])
def test_candidate_image_must_retain_real_base_layers_and_configuration(release, kind):
    base = {"Config": {"Cmd": ["server"], "Env": ["UNCHANGED=value"]}, "RootFS": {"Layers": ["old-a", "old-b"]}}
    candidate = deepcopy(base)
    candidate["RootFS"]["Layers"].append("new-resume-layer")
    release.verify_image_base(candidate, base)
    if kind == "image-config": candidate["Config"]["Env"] = ["FOREIGN=value"]
    elif kind == "root-layer": candidate["RootFS"]["Layers"][0] = "foreign"
    else: candidate["RootFS"]["Layers"] = ["old-a"]
    with pytest.raises(release.GuardError): release.verify_image_base(candidate, base)


@pytest.mark.parametrize("field,value", [
    ("com.docker.compose.project", "offersteady-cn"),
    ("com.docker.compose.service", "admin"),
    ("com.docker.compose.project.config_files", "relative-compose.json"),
    ("com.docker.compose.project.config_files", "/opt/offersteady-cn/releases/compose.json"),
    ("com.docker.compose.project.environment_file", ""),
])
def test_freeze_rejects_wrong_regional_identity_or_context(release, field, value):
    before = container(release)
    before["Config"]["Labels"][field] = value
    with pytest.raises(release.GuardError): release.context(before, "backend")


def test_context_preserves_every_compose_and_env_in_original_order(release):
    before = container(release)
    labels = before["Config"]["Labels"]
    composes = [f"/opt/offersteady-global/releases/old/compose-{n}.json" for n in range(5)]
    envs = ["/opt/offersteady-global/releases/old/env-0.private", "/opt/offersteady-global/releases/old/env-1.private"]
    labels["com.docker.compose.project.config_files"] = ",".join(composes)
    labels["com.docker.compose.project.environment_file"] = ",".join(envs)
    value = release.context(before, "backend")
    assert value["composeFiles"] == composes and value["envFiles"] == envs
    args = release.compose_args(value)
    assert [args[i+1] for i, v in enumerate(args) if v == "-f"] == composes
    assert [args[i+1] for i, v in enumerate(args) if v == "--env-file"] == envs
    assert args[args.index("--project-directory") + 1] == labels["com.docker.compose.project.working_dir"]


@pytest.mark.parametrize("outcome", ["created-own", "foreign-image", "foreign-context", "container-missing"])
def test_failed_compose_records_only_identifiable_owned_result_and_never_guesses(release, monkeypatch, outcome):
    import subprocess
    before, t = container(release), target(release)
    save_before(release, before)
    current, progress, calls = {"value": deepcopy(before)}, {}, []
    monkeypatch.setattr(release, "check_inputs", lambda: {})
    monkeypatch.setattr(release, "verify_files", lambda *_: None)
    def inspect(_name):
        if current["value"] is None: raise RuntimeError("synthetic missing container")
        return current["value"]
    monkeypatch.setattr(release, "inspect", inspect)
    monkeypatch.setattr(release, "compose_args", lambda *_args, **_kwargs: ["synthetic-compose"])
    def run(args, **_kwargs):
        calls.append(args)
        current["value"] = new_container(release, before, t)
        if outcome == "foreign-image": current["value"]["Image"] = "sha256:" + "f" * 64
        elif outcome == "foreign-context": current["value"]["Config"]["Labels"]["com.docker.compose.project.config_files"] = "/foreign"
        elif outcome == "container-missing": current["value"] = None
        raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(release, "run", run)
    with pytest.raises((subprocess.CalledProcessError, RuntimeError)):
        release.switch({"targets": [t]}, t, "new", progress)
    assert len(calls) == 1 and calls[0][-1] == "backend"
    assert (release.ROOT / "switch-intent.json").exists()
    if outcome == "created-own":
        assert progress["backend"] == {"id": current["value"]["Id"], "image": t["newImage"], "kind": "new"}
        assert json.loads((release.ROOT / "progress.json").read_text()) == progress
    else:
        assert progress == {} and not (release.ROOT / "progress.json").exists()


@pytest.fixture
def pending_intent(release, monkeypatch):
    before, t = container(release), target(release)
    save_before(release, before)
    current = new_container(release, before, t)
    manifest, progress = {"targets": [t]}, {}
    release.write_json(release.ROOT / "switch-intent.json", {"service": "backend", "kind": "new", "previousProgress": {}})
    events = []
    monkeypatch.setattr(release, "check_inputs", lambda: {})
    monkeypatch.setattr(release, "verify_files", lambda *_: events.append("frozen-verified"))
    def inspect(_name):
        events.append("inspected")
        return current
    monkeypatch.setattr(release, "inspect", inspect)
    return SimpleNamespace(release=release, before=before, target=t, current=current, manifest=manifest, progress=progress, events=events)


@pytest.mark.parametrize("kind", ["new", "rollback"])
def test_lost_progress_is_reconciled_only_for_exact_owned_cutover(pending_intent, kind):
    f = pending_intent
    if kind == "rollback":
        f.current.clear()
        f.current.update(new_container(f.release, f.before, f.target, "rollback"))
        f.release.write_json(f.release.ROOT / "switch-intent.json", {"service": "backend", "kind": "rollback", "previousProgress": {}})
    f.release.reconcile_intent(f.manifest, f.progress)
    assert f.events == ["frozen-verified", "inspected"]
    assert f.progress == {"backend": {"id": f.current["Id"], "image": f.target[kind + "Image"], "kind": kind}}
    assert json.loads((f.release.ROOT / "progress.json").read_text()) == f.progress


@pytest.mark.parametrize("kind", ["image", "project", "service", "compose-files", "workdir", "env-files", "env", "host", "mount", "application", "safe-label"])
def test_lost_progress_never_claims_later_changed_configuration(pending_intent, kind):
    f = pending_intent
    labels = f.current["Config"]["Labels"]
    if kind == "image": f.current["Image"] = "sha256:" + "d" * 64
    elif kind == "project": labels["com.docker.compose.project"] = "foreign"
    elif kind == "service": labels["com.docker.compose.service"] = "foreign"
    elif kind == "compose-files": labels["com.docker.compose.project.config_files"] = "/foreign"
    elif kind == "workdir": labels["com.docker.compose.project.working_dir"] = "/foreign"
    elif kind == "env-files": labels["com.docker.compose.project.environment_file"] = "/foreign"
    elif kind == "env": f.current["Config"]["Env"].append("OTHER_RELEASE=changed")
    elif kind == "host": f.current["HostConfig"]["PidsLimit"] = 999
    elif kind == "mount": f.current["Mounts"] = []
    elif kind == "safe-label": labels["safe-label"] = "foreign"
    else: f.current["Config"]["Cmd"] = ["foreign"]
    try:
        f.release.reconcile_intent(f.manifest, f.progress)
    except f.release.GuardError:
        pass
    assert f.progress == {} and not (f.release.ROOT / "progress.json").exists()


def test_lost_progress_cannot_skip_frozen_file_verification(pending_intent, monkeypatch):
    f = pending_intent
    def drift(*_): raise f.release.GuardError("frozen_context_drift")
    monkeypatch.setattr(f.release, "verify_files", drift)
    with pytest.raises(f.release.GuardError): f.release.reconcile_intent(f.manifest, f.progress)
    assert f.progress == {} and f.events == []


def test_previous_intent_never_rewrites_more_recent_progress(pending_intent):
    f = pending_intent
    f.progress["backend"] = {"id": "later", "image": "later", "kind": "new"}
    before = deepcopy(f.progress)
    f.release.reconcile_intent(f.manifest, f.progress)
    assert f.progress == before and f.events == []


@pytest.mark.parametrize("reason", [
    "runtime_source_mismatch", "runtime_static_mismatch", "runtime_settings_mismatch", "runtime_nginx_changed",
    "complete_runtime_api_schema_drift", "shared_runtime_tag_changed", "non_target_identity_changed",
    "release_container_owner_changed", "released_compose_owner_changed", "pending_switch_context_drift",
    "runtime_environment_changed", "host_mount_or_label_changed", "private_original_context_drift",
])
def test_any_source_configuration_schema_or_ownership_drift_stops_without_automatic_restore(cutover, monkeypatch, reason):
    f = cutover
    f.release.write_json(f.release.ROOT / "progress.json", {"backend": {"id": "ours-before-drift", "image": "synthetic", "kind": "new"}})
    def drift(*_args, **_kwargs): raise f.release.GuardError(reason)
    monkeypatch.setattr(f.release, "verify_current", drift)
    with pytest.raises(f.release.GuardError, match=reason): f.release.deploy()
    assert not [event for event in f.events if event[0] == "switch"]
    assert not (f.release.ROOT / "rollback-result.json").exists()


def test_explicit_completed_rollback_blocks_redeployment_of_same_revision(cutover):
    f = cutover
    f.release.write_json(f.release.ROOT / "rollback-result.json", {"restored": True})
    with pytest.raises(f.release.GuardError, match="release_was_rolled_back_prepare_a_new_revision"):
        f.release.deploy()
    assert mutations(f) == []


@pytest.fixture
def interrupted_prepare(release, monkeypatch):
    """Frozen contexts left by a prior failed probe, with disposable build dirs."""
    states = {release.PROJECT + '-' + s + '-1': container(release, s) for s in ('backend', 'web')}
    states[release.PROJECT + '-admin-1'] = {'Id': 'other-id', 'Image': 'other-image', 'State': {'StartedAt': 'before'}}
    image_config = {'Cmd': ['synthetic-server'], 'Env': ['SAFE_SYNTHETIC=private-value']}
    images = {release.BASES[s][1]: {'Id': release.BASES[s][1], 'Config': deepcopy(image_config),
              'RootFS': {'Layers': ['base-' + s]}} for s in ('backend', 'web')}
    images['synthetic-shared-backend'] = deepcopy(images[release.BASES['backend'][1]])
    images['synthetic-shared-web'] = deepcopy(images[release.BASES['web'][1]])
    before_render = {'name': release.PROJECT, 'services': {
        s: {'image': 'synthetic-compose-' + s, 'environment': {'SAFE_SYNTHETIC': 'private-value'}}
        for s in ('backend', 'web')}}
    frozen_targets = []
    for service in ('backend', 'web'):
        before = states[release.PROJECT + '-' + service + '-1']
        directory = release.ROOT / service
        directory.mkdir()
        original = release.ROOT / 'original-contexts' / service
        original.mkdir(parents=True)
        t = target(release, service)
        t.update(beforeId=before['Id'], baseImage=before['Image'], beforeTag=before['Config']['Image'],
                 composeDirectory=str(original), composeFiles=[], envFiles=[], frozenComposeFiles=[], frozenEnvFiles=[], sourceHashes={})
        for index in range(3 if service == 'backend' else 2):
            source, frozen = original / f'compose-{index}.json', directory / f'compose-{index}.before'
            body = json.dumps(before_render).encode()
            source.write_bytes(body)
            frozen.write_bytes(body)
            t['composeFiles'].append(str(source)); t['frozenComposeFiles'].append(str(frozen))
            t['sourceHashes'][str(source)] = release.digest(body)
        env_source, env_frozen = original / 'env.private', directory / 'env-0.before'
        env_source.write_text('SAFE_SYNTHETIC=private-value\n'); env_frozen.write_bytes(env_source.read_bytes())
        t['envFiles'] = [str(env_source)]; t['frozenEnvFiles'] = [str(env_frozen)]
        t['sourceHashes'][str(env_source)] = release.digest(env_source.read_bytes())
        t['sourceRenderedSha'] = t['renderedSha'] = release.digest(release.canonical(before_render))
        release.write_json(directory / 'container-before.json', before)
        release.write_json(directory / 'rendered-before.json', before_render)
        release.write_json(directory / 'rendered-source-before.json', before_render)
        release.write_json(directory / 'frozen-target.json', t)
        frozen_targets.append(t)
        stale = release.ROOT / 'build' / service
        stale.mkdir(parents=True)
        (stale / 'stale-previous-attempt').write_text('must not reach a rebuilt image')
    for directory in ('input', 'wheels', 'web-input'):
        (release.ROOT / directory).mkdir()
    (release.ROOT / 'input/synthetic-source.py').write_text('# synthetic payload\n')
    (release.ROOT / 'wheels/reportlab-4.4.9-py3-none-any.whl').write_bytes(b'synthetic, never installed')
    (release.ROOT / 'web-input/index.html').write_text('synthetic new web')
    nginx = b'synthetic nginx baseline'
    plan = {'beforeInventory': {'protected': 'before'}, 'webBefore': {'assets/old.js': 'old'},
            'webFiles': {'index.html': 'new'}, 'openapiBefore': {'paths': {'/protected': {}}},
            'configBeforeSha': 'synthetic-config', 'nginxSha': release.digest(nginx),
            'sharedTags': ['synthetic-shared-backend', 'synthetic-shared-web'],
            'nonTargets': {release.PROJECT + '-admin-1': {'id': 'other-id', 'image': 'other-image', 'startedAt': 'before'}}}
    release.write_json(release.ROOT / 'input.json', plan)
    events, faults = [], {'probe': True, 'render': False}
    monkeypatch.setattr(release, 'check_inputs', lambda: plan)
    monkeypatch.setattr(release, 'backend_inventory', lambda _: plan['beforeInventory'])
    monkeypatch.setattr(release, 'web_inventory', lambda _name, image=False: plan['webBefore'] | (plan['webFiles'] if image else {}))
    monkeypatch.setattr(release, 'current_schema', lambda: plan['openapiBefore'])
    monkeypatch.setattr(release, 'settings_digest', lambda _: {'sha': plan['configBeforeSha'], 'enabled': False})
    monkeypatch.setattr(release, 'freeze', lambda *_: pytest.fail('must reuse original frozen context after a failed probe'))
    monkeypatch.setattr(release, 'inspect', lambda name: deepcopy(states[name] if name in states else images[name]))
    def render(t, *, frozen=False, overlay=None):
        result = deepcopy(before_render)
        if faults['render']: result['services']['backend']['environment']['FOREIGN'] = 'drift'
        if overlay:
            for service, fields in release.read_json(Path(overlay))['services'].items():
                result['services'][service]['image'] = fields['image']
                result['services'][service]['environment'].update(fields.get('environment', {}))
        return result
    monkeypatch.setattr(release, 'rendered', render)
    build_counts = {'backend': 0, 'web': 0}
    def run(args, **_kwargs):
        events.append(args)
        if args[:2] == ['docker', 'ps']:
            return SimpleNamespace(stdout=('\n'.join(states) + '\n').encode())
        if args[:2] == ['docker', 'tag']:
            images[args[3]] = deepcopy(images[args[2]])
            return SimpleNamespace(stdout=b'')
        if args[:2] == ['docker', 'build']:
            service = Path(args[-1]).name
            build_counts[service] += 1
            tag = args[args.index('-t') + 1]
            new = deepcopy(images[release.BASES[service][1]])
            new['Id'] = 'sha256:' + release.digest((service + str(build_counts[service])).encode())
            new['RootFS']['Layers'].append('new-' + str(build_counts[service]))
            images[tag] = new; images[new['Id']] = new
            assert not (Path(args[-1]) / 'stale-previous-attempt').exists()
            assert '--network=none' in args and '--pull=false' in args
            return SimpleNamespace(stdout=b'')
        if args[:2] == ['docker', 'run'] and args[-1] == '/etc/nginx/conf.d/default.conf':
            return SimpleNamespace(stdout=nginx)
        raise AssertionError('unexpected synthetic prepare command')
    monkeypatch.setattr(release, 'run', run)
    def probe(_manifest):
        if faults['probe']: raise release.GuardError('actual_candidate_probe_failed')
        return {'passed': True}
    monkeypatch.setattr(release, 'probe', probe)
    return SimpleNamespace(release=release, plan=plan, states=states, targets=frozen_targets,
                           events=events, faults=faults, build_counts=build_counts)


def test_prepare_reuses_original_frozen_context_after_failed_probe_and_rebuilds_only_owned_dirs(interrupted_prepare):
    f = interrupted_prepare
    frozen_before = {p: Path(p).read_bytes() for t in f.targets for p in t['frozenComposeFiles'] + t['frozenEnvFiles']}
    with pytest.raises(f.release.GuardError, match='actual_candidate_probe_failed'):
        f.release.prepare()
    assert not (f.release.ROOT / 'prepared.json').exists()
    assert f.build_counts == {'backend': 1, 'web': 1}
    for t in f.targets:
        (f.release.ROOT / 'build' / t['service'] / 'stale-previous-attempt').write_text('second stale build')
    f.faults['probe'] = False
    f.release.prepare()
    assert f.build_counts == {'backend': 2, 'web': 2}
    manifest = f.release.read_json(f.release.ROOT / 'prepared.json')
    assert all(t['beforeId'] == f.release.BASES[t['service']][0] for t in manifest['targets'])
    assert all(Path(path).read_bytes() == body for path, body in frozen_before.items())
    assert not [args for args in f.events if args[:2] == ['docker', 'compose'] and 'up' in args]
    assert {t['service']: t['composeDirectory'] for t in manifest['targets']} == {t['service']: t['composeDirectory'] for t in f.targets}


@pytest.mark.parametrize('kind', ['original-env', 'original-compose', 'frozen-env', 'frozen-compose', 'runtime-config', 'runtime-host', 'runtime-mount', 'frozen-owner', 'render'])
def test_retried_prepare_refuses_any_frozen_context_or_runtime_drift_before_build(interrupted_prepare, kind):
    f = interrupted_prepare
    t = f.targets[0]
    if kind == 'original-env': Path(t['envFiles'][0]).write_text('drift')
    elif kind == 'original-compose': Path(t['composeFiles'][0]).write_text('drift')
    elif kind == 'frozen-env': Path(t['frozenEnvFiles'][0]).write_text('drift')
    elif kind == 'frozen-compose': Path(t['frozenComposeFiles'][0]).write_text('drift')
    elif kind == 'runtime-config': f.states[f.release.CONTAINER]['Config']['Cmd'] = ['foreign']
    elif kind == 'runtime-host': f.states[f.release.CONTAINER]['HostConfig']['Memory'] = 999
    elif kind == 'runtime-mount': f.states[f.release.CONTAINER]['Mounts'] = []
    elif kind == 'render': f.faults['render'] = True
    else:
        value = f.release.read_json(f.release.ROOT / 'backend/frozen-target.json')
        value['beforeId'] = 'foreign-owner'
        f.release.write_json(f.release.ROOT / 'backend/frozen-target.json', value)
    with pytest.raises(f.release.GuardError): f.release.prepare()
    assert f.build_counts == {'backend': 0, 'web': 0}
    assert not (f.release.ROOT / 'prepared.json').exists()
