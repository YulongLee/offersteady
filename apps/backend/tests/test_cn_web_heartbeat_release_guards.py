"""Pure overlay and cutover checks; no network or Docker calls."""
import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def release(monkeypatch):
    root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location("heartbeat_release", root / "scripts/release_cn_web_heartbeat.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", ["ports/interview_session.py", "services/interview_session_repository.py",
    "services/postgres_interview_session_repository.py", "services/session_service.py", "services/realtime_speech_service.py"])
def test_overlay_changes_only_approved_nodes(release, path):
    root = Path(__file__).resolve().parents[3]
    local_path = "apps/backend/app/" + path
    before = subprocess.check_output(["git", "show", "HEAD:" + local_path], cwd=root).decode()
    local = (root / local_path).read_text()
    after = release.overlay(path, before, local)
    compile(after, path, "exec")
    assert after != before
    with pytest.raises(AssertionError):
        release.overlay(path, after, local)


def test_overlay_refuses_changed_legacy_heartbeat(release):
    root = Path(__file__).resolve().parents[3]
    path = "services/realtime_speech_service.py"
    local_path = "apps/backend/app/" + path
    before = subprocess.check_output(["git", "show", "HEAD:" + local_path], cwd=root).decode()
    node = release.method(before, "RealtimeSpeechService", "record_web_session_heartbeat")
    old = release.span(before, node)
    changed = before.replace(old, old.replace('page == "live"', 'page == "changed"'), 1)
    with pytest.raises(AssertionError):
        release.overlay(path, changed, (root/local_path).read_text())


def test_configuration_and_environment_are_invariant(release):
    before = {"Config":{"Env":["SYNTHETIC=unchanged"]},"HostConfig":{},"Mounts":[]}
    after = deepcopy(before)
    after["Image"] = "synthetic-candidate"
    release.invariant(before, after, {"newImage":after["Image"]})
    for section, key, value in [("Config","Env",["SYNTHETIC=changed"]), ("HostConfig","PortBindings",{"8000":[]})]:
        changed = deepcopy(after); changed[section][key] = value
        with pytest.raises(AssertionError):
            release.invariant(before, changed, {"newImage":after["Image"]})


def test_cutover_has_two_idle_gates_before_tag_change(release):
    import inspect
    source = inspect.getsource(release.deploy)
    assert source.count("guards.idle_gate()") == 2
    assert source.rfind("guards.idle_gate()") < source.index('guards.run(["docker","tag"')
    assert "guards.verify_non_targets(manifest)" in source
    assert "candidate-verification.json" in source
    assert "atomic_write" not in source
    assert 'target["service"] == "backend"' in source
