"""Run the image-probe synthetic contracts and permanent guards in subprocesses."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PROBE = Path(__file__).with_name("candidate_probe.py")
CANDIDATE = ROOT / "artifacts/cn-cleanup-control-local-20261104/candidate/apps/backend"
ANCILLARY = "packages/protocol/src/material-upload-formats.json"


def run(code, *arguments):
    env = {key: value for key, value in os.environ.items() if not key.startswith("OFFERSTEADY_")}
    env.update(PYTHONPATH=str(CANDIDATE), PYTHONDONTWRITEBYTECODE="1",
        OFFERSTEADY_ENV="production", OFFERSTEADY_PRODUCT_EDITION="cn",
        OFFERSTEADY_DATABASE_URL="", OFFERSTEADY_REDIS_URL="")
    prefix = """import importlib.util,json,sys
spec=importlib.util.spec_from_file_location('synthetic_probe',sys.argv[1])
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
"""
    return subprocess.run([sys.executable, "-B", "-c", prefix + code, str(PROBE), *map(str, arguments)],
        cwd=CANDIDATE.parents[1], env=env, text=True, capture_output=True, timeout=20)


def test_marker_is_unique_and_template_compiles():
    source = PROBE.read_text()
    assert source.count("EXPECTED = None  # RELEASE_EXPECTATIONS") == 1
    compile(source, str(PROBE), "exec")


def test_real_candidate_routes_services_executor_and_timing_under_guards():
    result = run("""m.install_guards()
from app.core.config import Settings
import asyncio
settings=Settings(_env_file=None,environment='production',product_edition='cn')
result=asyncio.run(m.scenarios(settings))
for worker in m.WORKERS:worker.join(timeout=3)
assert m.WORKERS and not any(worker.is_alive() for worker in m.WORKERS)
result['workerThreadsStarted']=len(m.WORKERS)
result['allSyntheticWorkersReleased']=True
print(json.dumps(result))
""")
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ownerScopedReadDispatchPassed"] is True
    assert payload["lightweightAckStages"] == 4
    assert payload["detachedOldCloseCannotTouchReplacement"] is True
    assert payload["preparationIndependentFromBothLifecycleWorkers"] is True
    assert payload["preparationCancelledResourceCompensatedOnce"] is True
    assert payload["ambiguousCloseSubmitExactlyOnce"] is True
    assert payload["pinnedSyntheticScaleCases"] == 3
    assert payload["pinnedPairingTransportCalls"] == [3, 3, 3]
    assert payload["pinnedActualLuaExecutedInImageProbe"] is False
    assert payload["pinnedIdentityRetirementPrecisionPassed"] is True
    assert payload["syntheticStatusCases"] == 11
    assert payload["nonblockingExecutorCases"] == 2
    assert payload["controlReadsPerValidManualStatus"] == 2
    assert payload["fullSessionReadsPerValidManualStatus"] == payload["materialReadsPerValidManualStatus"] == 0
    assert payload["eventsPerValidManualStatus"] == 1
    assert payload["timingPrivacyPassed"] is payload["globalOriginalPathPassed"] is True
    assert payload["voiceNonblockingCases"] == 2
    assert payload["voiceDefaultCapacityPassed"] is payload["slowCloseLeavesIngressAndControlAvailable"] is True
    assert payload["globalVoiceDispatchUnchanged"] is True
    assert payload["cancelledResourcesCreated"] == payload["cancelledResourcesCleaned"] == 3
    for key in ("shutdownRejectsNewBusiness", "shutdownCleanupCapacityPassed", "metadataBatchAndFallbackPassed",
        "ordinaryWrittenMockGuardsPassed", "loopMonitorBoundedNumericPassed"):
        assert payload[key] is True
    assert payload["allSyntheticWorkersReleased"] is True and payload["workerThreadsStarted"] >= 8
    assert "synthetic-private" not in result.stdout


@pytest.mark.parametrize("attempt", [
    "socket.create_connection(('127.0.0.1',1))",
    "socket.getaddrinfo('synthetic.invalid',443)",
    "socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b'synthetic',('127.0.0.1',1))",
    "psycopg.connect('')",
    "psycopg.Connection.connect('')",
    "psycopg.AsyncConnection.connect('')",
    "threading.Thread(target=lambda:None,name='unapproved').start()",
    "open(sys.argv[2],'w')",
    "os.mkdir(sys.argv[2])",
    "subprocess.run(['true'])",
])
def test_guard_denies_io_before_it_executes(tmp_path, attempt):
    target = tmp_path / "must-not-exist"
    result = run("""m.install_guards()
import socket,threading,psycopg,os,subprocess
try:
 """ + attempt + """
except m.ProbeError as error:
 assert str(error) in {'external_io_forbidden','unapproved_worker_thread'}
else:
 raise AssertionError('guard_permitted_io')
assert m.WORKERS==[]
print(json.dumps({'guardPassed':True}))
""", target)
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout) == {"guardPassed": True}
    assert not target.exists()


def test_expected_exact_inventory_and_compilation_count_are_verified():
    # This is only a local source inventory check. Python/deps/private Settings
    # checks remain mandatory in main() and must execute in the actual image.
    base = CANDIDATE.parents[1]
    inventory = {path.relative_to(base).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in ("apps/backend/app", "ai/prompts", "apps/backend/migrations")
        for path in (base / directory).rglob("*") if path.is_file()
        and "__pycache__" not in path.parts and path.suffix != ".pyc"}
    inventory["apps/backend/pyproject.toml"] = hashlib.sha256((CANDIDATE / "pyproject.toml").read_bytes()).hexdigest()
    assert len(inventory) == 238
    assert len([path for path in (CANDIDATE / "app").rglob("*.py") if not path.name.startswith("._")]) == 162
    manifest = json.loads((base.parent / "candidate-manifest.json").read_text())
    assert inventory == manifest["files"]
    tree = ast.parse(PROBE.read_text())
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    verifier = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "verify_source")
    source = ast.get_source_segment(PROBE.read_text(), main) + ast.get_source_segment(PROBE.read_text(), verifier)
    for code in ["application_inventory_mismatch", "compiled_python_count_changed", "python_version_changed",
        "unapproved_dependency_change", "existing_settings_changed", "existing_pool_setting_changed",
        "openapi_changed", "api_routes_changed", "pool_activated_unexpectedly"]:
        assert code in source
    assert '"3.13.15"' in source and 'len(deps) == 44' in source
    assert 'len(values) == 344' in source and 'verify_source(root, EXPECTED)' in source


@pytest.mark.parametrize("failure", [None, "inventory", "ancillary_hash", "ancillary_missing", "expectation_missing"])
def test_exact_frozen_source_and_baseline_ancillary_are_read_only_verified(tmp_path, failure):
    # Owned fixture only: links preserve the frozen bytes; the separate helper is
    # never added to or substituted inside the frozen candidate directory.
    base = CANDIDATE.parents[1]
    for name in ("apps", "ai"):
        (tmp_path / name).symlink_to(base / name, target_is_directory=True)
    helper = tmp_path / ANCILLARY
    helper.parent.mkdir(parents=True)
    value = (ROOT / ANCILLARY).read_bytes()
    if failure != "ancillary_missing":
        helper.write_bytes(value)
    expected = {"inventory": json.loads((base.parent / "candidate-manifest.json").read_text())["files"],
        "ancillary": {ANCILLARY: hashlib.sha256(value).hexdigest()}}
    if failure == "inventory": expected["inventory"]["apps/backend/app/main.py"] = "0" * 64
    if failure == "ancillary_hash": expected["ancillary"][ANCILLARY] = "0" * 64
    if failure == "expectation_missing": expected.pop("ancillary")
    expectations = tmp_path / "expectations.json"
    expectations.write_text(json.dumps(expected))
    error = {"inventory": "application_inventory_mismatch", "ancillary_hash": "baseline_ancillary_mismatch",
        "ancillary_missing": "baseline_ancillary_mismatch", "expectation_missing": "baseline_ancillary_expectation_missing"}.get(failure)
    result = run("""from pathlib import Path
expected=json.loads(Path(sys.argv[3]).read_text())
m.install_guards()
try:
 inventory,compiled=m.verify_source(Path(sys.argv[2]),expected)
except m.ProbeError as error:
 assert str(error)==json.loads(sys.argv[4])
else:
 assert json.loads(sys.argv[4]) is None
 assert len(inventory)==238 and compiled==162
print(json.dumps({'sourceGuardPassed':True}))
""", tmp_path, expectations, json.dumps(error))
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout) == {"sourceGuardPassed": True}


def test_lifespan_and_startup_are_denied_without_running_handlers():
    result = run("""m.install_guards()
from fastapi import FastAPI
import asyncio
app=FastAPI()
calls=[]
app.router.on_startup.append(lambda:calls.append('unexpected'))
m.forbid_lifespan(app)
async def attempts():
 for operation in [lambda:app.router.lifespan_context(app),lambda:app.router.startup()]:
  try:operation()
  except m.ProbeError:pass
  else:raise AssertionError('lifespan_permitted')
asyncio.run(attempts())
assert calls==[]
print(json.dumps({'lifespanGuardPassed':True}))
""")
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout) == {"lifespanGuardPassed": True}
