"""Pure restoration-release regression checks; never connect to CN or Docker."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def release(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location("heartbeat_restore", root / "scripts/restore_cn_web_heartbeat.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # All tests must explicitly arrange calls; accidental Docker/network work fails.
    for name in ("run", "inspect", "models", "verify_non_targets", "idle_gate", "wait_healthy"):
        monkeypatch.setattr(module.guards, name, Mock(side_effect=AssertionError("unexpected external operation")))
    monkeypatch.setattr(module, "urlopen", Mock(side_effect=AssertionError("unexpected public request")))
    return module


@pytest.fixture
def local_source():
    root = Path(__file__).resolve().parents[3]
    return (root / "apps/backend/app/services/realtime_speech_service.py").read_text()


LEGACY = '''# The actual baseline is bound separately by SHA-256, not by this fixture.
from typing import Any

class RealtimeSpeechService:
    def untouched_billing(self):
        return "synthetic current written-exam billing"

    def record_web_session_heartbeat(self, *, user_id, session_id, binding_id, page, page_instance_id=None):
        idle = self.reconcile_idle_session(user_id=user_id, session_id=session_id)
        session = self.session_service.get_session(user_id=user_id, session_id=session_id)
        return session

    def untouched_mock_interview(self):
        return "synthetic current mock interview"

class Unrelated:
    constant = "current functionality"
'''


def test_only_heartbeat_method_is_imported_from_local(release, local_source):
    # Local branches may have unrelated functions; none may replace production.
    local = local_source + '\nclass UnapprovedLocalFeature:\n    pass\n'
    after = release.overlay(LEGACY, local)
    assert 'UnapprovedLocalFeature' not in after
    assert 'synthetic current written-exam billing' in after
    assert 'synthetic current mock interview' in after
    assert after.startswith(LEGACY.split('    def record_web_session_heartbeat')[0])
    assert after.endswith(LEGACY.split('    def untouched_mock_interview')[1])
    assert release.node_digest(release.heartbeat_node(ast.parse(after))) == release.REPLACEMENT_NODE_SHA256
    compile(after, "synthetic.py", "exec")


def test_overlay_preserves_non_json_ast_constants_found_in_running_source(release, local_source):
    # The running image contains ellipsis and bytes constants outside heartbeat.
    # Whole-module equality must support every Python Constant, not just JSON.
    baseline = LEGACY + "\nPROTOCOL_DEFAULT = ...\nAUDIO_SENTINEL = b'\\x00\\xff'\nCOMPLEX_SENTINEL = 2j\n"
    after = release.overlay(baseline, local_source)
    assert after.endswith("PROTOCOL_DEFAULT = ...\nAUDIO_SENTINEL = b'\\x00\\xff'\nCOMPLEX_SENTINEL = 2j\n")
    assert release.node_digest(ast.parse(after))
    compile(after, "synthetic.py", "exec")


def test_overlay_rejects_method_drift_and_second_restoration(release, local_source):
    changed = local_source.replace('idle["state"] == "expired"', 'idle["state"] == "changed"', 1)
    with pytest.raises(AssertionError, match="reviewed heartbeat method drift"):
        release.overlay(LEGACY, changed)
    with pytest.raises(AssertionError, match="already restored"):
        release.overlay(release.overlay(LEGACY, local_source), local_source)


@pytest.mark.parametrize("source", ["class RealtimeSpeechService: pass\n", LEGACY + LEGACY])
def test_overlay_rejects_missing_or_duplicate_target(release, local_source, source):
    with pytest.raises(AssertionError, match="missing/duplicated"):
        release.overlay(source, local_source)


def evidence(release):
    target = {"sourceAfterSha256": "synthetic-source-after", "newImage": "sha256:synthetic-candidate"}
    local = {"passed": True, "tests": 30, "baseImage": release.BASE_IMAGE,
             "sourceBeforeSha256": release.SOURCE_BEFORE_SHA256,
             "sourceAfterSha256": target["sourceAfterSha256"], "gitCommit": "a" * 40}
    probe = {"passed": True, "checks": 12, "syntheticOnly": True, "networkRequired": False,
             "candidateImage": target["newImage"], "sourceAfterSha256": target["sourceAfterSha256"]}
    return target, local, probe


def test_local_and_probe_evidence_are_bound_to_same_candidate(release):
    release.verify_evidence(*evidence(release)[1:], evidence(release)[0])


@pytest.mark.parametrize("report,key,value", [
    ("local", "passed", False), ("local", "tests", 0), ("local", "tests", True),
    ("local", "baseImage", "old image"), ("local", "sourceBeforeSha256", "old source"),
    ("local", "sourceAfterSha256", "another candidate"), ("local", "gitCommit", "not pushed evidence"),
    ("probe", "passed", False), ("probe", "checks", 11), ("probe", "checks", True),
    ("probe", "syntheticOnly", False), ("probe", "networkRequired", True),
    ("probe", "candidateImage", "different image"), ("probe", "sourceAfterSha256", "different source"),
])
def test_incomplete_stale_or_unsafe_verification_blocks_cutover(release, report, key, value):
    target, local, probe = evidence(release)
    (local if report == "local" else probe)[key] = value
    with pytest.raises(AssertionError):
        release.verify_evidence(local, probe, target)


def container(release, *, candidate=False):
    return {"Id": "synthetic-before", "Image": "synthetic-candidate" if candidate else release.BASE_IMAGE,
            "Config": {"Env": ["SYNTHETIC=unchanged"]}, "HostConfig": {}, "Mounts": []}


@pytest.mark.parametrize("section,key,value", [
    ("Config", "Env", ["SYNTHETIC=changed"]), ("Config", "Entrypoint", ["changed"]),
    ("HostConfig", "PortBindings", {"8000/tcp": []}), ("HostConfig", "Memory", 100),
])
def test_runtime_configuration_drift_is_rejected(release, section, key, value):
    before, after = container(release), container(release, candidate=True)
    release.invariant(before, after, {"newImage": "synthetic-candidate"})
    after[section][key] = value
    with pytest.raises(AssertionError):
        release.invariant(before, after, {"newImage": "synthetic-candidate"})


def test_candidate_retains_all_running_image_layers_with_one_overlay(release):
    baseline = {"Config": {"Env": ["SYNTHETIC=unchanged"]}, "RootFS": {"Layers": ["base-a", "base-b"]}}
    candidate = deepcopy(baseline)
    candidate["RootFS"]["Layers"].append("heartbeat-only")
    release.verify_candidate_image(candidate, baseline)
    for layers in (["old-base", "heartbeat-only"], ["base-a", "base-b", "extra", "heartbeat-only"], ["base-a", "base-b"]):
        changed = deepcopy(candidate)
        changed["RootFS"]["Layers"] = layers
        with pytest.raises(AssertionError):
            release.verify_candidate_image(changed, baseline)


def test_compose_uses_actual_labels_and_full_runtime_environment(release, monkeypatch):
    current = container(release)
    current["Config"]["Env"] += ["IMAGE_DEFAULT=preserved"]
    base = {"Config": {"Env": ["IMAGE_DEFAULT=preserved"]}}
    monkeypatch.setattr(release.guards, "inspect", Mock(return_value=base))
    target = {"project": "compose", "runtimeTag": "compose-backend", "envFile": "/actual/private.env",
              "composeFiles": ["/actual/compose.yml"]}
    rendered = {"services": {"backend": {"environment": {"SYNTHETIC": "unchanged"}}}}
    release.verify_compose(target, current, rendered)
    assert release.compose_args(target) == ["docker", "compose", "-p", "compose", "--env-file", "/actual/private.env", "-f", "/actual/compose.yml"]
    changed = deepcopy(rendered)
    changed["services"]["backend"]["environment"]["ADDED_SECRET_SETTING"] = "synthetic"
    with pytest.raises(AssertionError, match="environment"):
        release.verify_compose(target, current, changed)
    changed = deepcopy(rendered)
    changed["services"]["backend"]["image"] = "wrong-backend"
    with pytest.raises(AssertionError, match="compose image"):
        release.verify_compose(target, current, changed)


def arrange_deploy(release, monkeypatch, root):
    before = container(release)
    target = {"service": "backend", "container": "compose-backend-1", "newImage": "synthetic-candidate",
              "runtimeTag": "compose-backend", "sourceAfterSha256": release.digest("synthetic candidate"),
              "protectedSourceHashes": {path: release.digest(path) for path in release.SUPPORT_PATHS}}
    manifest = {"models": {"synthetic": "unchanged"}, "nonTargets": {"web": {"id": "same"}}, "targets": [target]}
    monkeypatch.setattr(release, "preflight", Mock(return_value=(manifest, target, before)))
    monkeypatch.setattr(release.guards, "idle_gate", Mock())
    monkeypatch.setattr(release.guards, "run", Mock())
    monkeypatch.setattr(release, "compose", Mock())
    monkeypatch.setattr(release.guards, "wait_healthy", Mock(return_value=container(release, candidate=True)))
    monkeypatch.setattr(release.guards, "models", Mock(return_value=manifest["models"]))
    monkeypatch.setattr(release.guards, "verify_non_targets", Mock())
    monkeypatch.setattr(release, "runtime_source", Mock(side_effect=lambda _name, path: b"synthetic candidate" if path == release.SOURCE_PATH else path.encode()))
    monkeypatch.setattr(release, "verify_public", Mock())
    return target, before


def test_deploy_checks_idle_twice_before_mutation_and_only_recreates_backend(release, monkeypatch, tmp_path):
    arrange_deploy(release, monkeypatch, tmp_path)
    order = []
    release.guards.idle_gate.side_effect = lambda: order.append("idle")
    release.guards.run.side_effect = lambda args: order.append(args)
    release.deploy(tmp_path)
    assert order[:2] == ["idle", "idle"]
    assert order[2] == ["docker", "tag", "synthetic-candidate", "compose-backend"]
    release.compose.assert_called_once()
    assert release.compose.call_args.args[0]["service"] == "backend"
    result = json.loads((tmp_path / "deployed.json").read_text())
    assert result["services"] == ["backend"] and result["rollbackImage"] == release.BASE_IMAGE


@pytest.mark.parametrize("blocked_gate", [1, 2])
def test_protected_user_work_prevents_all_mutations(release, monkeypatch, tmp_path, blocked_gate):
    arrange_deploy(release, monkeypatch, tmp_path)
    release.guards.idle_gate.side_effect = ([None] * (blocked_gate - 1)) + [AssertionError("protected user work")]
    with pytest.raises(AssertionError, match="protected user work"):
        release.deploy(tmp_path)
    release.guards.run.assert_not_called()
    release.compose.assert_not_called()
    assert not (tmp_path / "deployed.json").exists()


def test_preflight_only_never_changes_live_tag_or_container(release, monkeypatch, tmp_path):
    arrange_deploy(release, monkeypatch, tmp_path)
    release.deploy(tmp_path, preflight_only=True)
    release.guards.idle_gate.assert_called_once()
    release.guards.run.assert_not_called()
    release.compose.assert_not_called()


def test_failed_health_restores_current_written_exam_baseline(release, monkeypatch, tmp_path):
    _, before = arrange_deploy(release, monkeypatch, tmp_path)
    release.guards.wait_healthy.side_effect = [AssertionError("candidate failed health"), before]
    with pytest.raises(SystemExit):
        release.deploy(tmp_path)
    assert release.guards.run.call_args_list[-1].args[0] == ["docker", "tag", release.BASE_IMAGE, "compose-backend"]
    assert release.compose.call_count == 2
    assert not (tmp_path / "deployed.json").exists()


def test_idle_gate_includes_ordinary_mock_and_material_guards(release):
    # No gate is executed here. Keep the reviewed ordinary/mock gate inventory
    # and explicit material-work guard; activity cannot be inferred from P95.
    assert len(release.guards.GATES) == 3
    assert any("mock" in str(path) for path in release.guards.GATES)
    assert "material_processing_jobs" in release.guards.MATERIAL_GATE
    assert "material_deletion_jobs" in release.guards.MATERIAL_GATE
    assert "material_reconcile_jobs" in release.guards.MATERIAL_GATE


def test_cli_requires_explicit_action_and_local_source(release, monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["restore_cn_web_heartbeat.py"])
    with pytest.raises(SystemExit):
        release.main()
    monkeypatch.setattr(sys, "argv", ["restore_cn_web_heartbeat.py", "prepare"])
    with pytest.raises(AssertionError, match="requires --local-source"):
        release.main()


@pytest.mark.parametrize("drift", ["image", "source-manifest", "environment", "host-configuration"])
def test_preflight_rejects_baseline_drift_before_any_docker_run(release, monkeypatch, tmp_path, drift):
    before = container(release)
    target = {"service": "backend", "container": "compose-backend-1", "beforeId": before["Id"],
              "baseImage": release.BASE_IMAGE, "sourceBeforeSha256": release.SOURCE_BEFORE_SHA256,
              "methodAfterSha256": release.REPLACEMENT_NODE_SHA256,
              "protectedSourceHashes": {path: "synthetic" for path in release.SUPPORT_PATHS},
              "newTag": release.NEW_TAG, "rollbackTag": release.ROLLBACK_TAG}
    target["protectedSourceHashes"]["services/session_service.py"] = release.SESSION_BEFORE_SHA256
    current = deepcopy(before)
    if drift == "image":
        current["Image"] = "another deployment"
    elif drift == "source-manifest":
        target["sourceBeforeSha256"] = "old release source"
    elif drift == "environment":
        current["Config"]["Env"] = ["SYNTHETIC=changed"]
    else:
        current["HostConfig"]["Memory"] = 100
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend/container-before.json").write_text(json.dumps(before))
    (tmp_path / "prepared.json").write_text(json.dumps({"targets": [target]}))
    monkeypatch.setattr(release.guards, "inspect", Mock(return_value=current))
    with pytest.raises(AssertionError, match="baseline.*drift"):
        release.preflight(tmp_path)
    release.guards.run.assert_not_called()
