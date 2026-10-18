"""Actual frozen source probe acceptance and tamper refusal, without network."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[3]
PROBE = Path(__file__).parent / "probe/candidate-probe.py"
CANDIDATE = ROOT / "artifacts/cn-auth-state-20261016/candidate"
EXPECTATIONS = PROBE.with_name("probe-expectations.json")


@pytest.fixture
def inputs(tmp_path):
    if not CANDIDATE.exists():
        pytest.skip("Local frozen candidate required; production probe is separately exercised in its actual image")
    env = {k: v for k, v in os.environ.items() if not k.startswith("OFFERSTEADY_")}
    env.update(PYTHONPATH=str(CANDIDATE / "apps/backend"), PYTHONDONTWRITEBYTECODE="1",
               OFFERSTEADY_ENVIRONMENT="production", OFFERSTEADY_PRODUCT_EDITION="cn")
    expected = json.loads(EXPECTATIONS.read_text())
    code = ("import hashlib,json;from app.core.config import Settings;s=Settings(_env_file=None);fields="
            + repr(expected["runtimeConfigFields"]) + ";print(hashlib.sha256(json.dumps({k:getattr(s,k) for k in fields},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())")
    config_sha = subprocess.check_output([str(ROOT / ".venv/bin/python"), "-B", "-c", code], env=env, cwd=CANDIDATE, text=True).strip()
    return expected, env, config_sha, tmp_path / "expectations.json"


@pytest.mark.parametrize("tamper,error", [
    (None, None), ("app", "application_inventory_mismatch"), ("prompt", "prompt_inventory_mismatch"),
    ("protected", "protected_node_mismatch"), ("prefetch", "prefetch_source_mismatch"),
    ("sync", "async_state_handler"), ("routes", "routes_mismatch"),
    ("openapi", "openapi_mismatch"), ("config", "runtime_config_mismatch"),
])
def test_candidate_probe_accepts_exact_source_and_refuses_contract_drift(inputs, tamper, error):
    expected, env, config_sha, path = inputs
    if tamper == "app":
        expected["app"]["services/authentication_service.py"] = "0" * 64
    elif tamper == "prompt":
        expected["prompts"]["chat-service/system.md"] = "0" * 64
    elif tamper == "protected":
        expected["protectedNodes"]["services/authentication_service.py"]["AuthenticationService.refresh_session"] = "0" * 64
    elif tamper == "prefetch":
        expected["prefetchSources"]["services/chat_service.py"] = "0" * 64
    elif tamper == "sync":
        expected["syncStateNodes"]["modules/session.py"] = ["missing_synthetic_handler"]
    elif tamper == "routes":
        expected["routes"]["http"]["/api/v1/synthetic-missing"] = ["get"]
    elif tamper == "openapi":
        expected["openapiSha"] = "0" * 64
    elif tamper == "config":
        config_sha = "0" * 64
    path.write_text(json.dumps(expected))
    result = subprocess.run([str(ROOT / ".venv/bin/python"), "-B", str(PROBE), "--app-root",
        str(CANDIDATE / "apps/backend/app"), "--expectations", str(path), "--expected-config-sha", config_sha],
        env=env, cwd=CANDIDATE, text=True, capture_output=True, timeout=15)
    data = json.loads(result.stdout)
    assert data["passed"] is (tamper is None)
    assert result.returncode == (0 if tamper is None else 1)
    if tamper:
        assert data["errorCode"] == error
    else:
        assert data["applicationFiles"] == 148 and data["promptFiles"] == 20
        assert data["syntheticAuthPassed"] is True
        assert data["networkRequests"] == data["databaseOperations"] == data["workerThreadsStarted"] == 0


def test_guard_rejects_io_before_it_executes():
    code = """import importlib.util,sys
spec=importlib.util.spec_from_file_location('readonly_probe',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.install_guards()
import socket,threading,psycopg
for attempt in [lambda:socket.create_connection(('127.0.0.1',1)),lambda:psycopg.connect(''),lambda:threading.Thread(target=lambda:None).start(),lambda:open('/synthetic-probe-write','w')]:
 try:attempt()
 except m.ProbeError:pass
 else:raise AssertionError('IO permitted')
print('passed')
"""
    result = subprocess.run([str(ROOT / ".venv/bin/python"), "-B", "-c", code, str(PROBE)],
        text=True, capture_output=True, timeout=15)
    assert result.returncode == 0 and result.stdout.strip() == "passed"
