"""Reviewed, idle-gated CN cutover for the prepared 2026-10-08 model overlay.

Execute only on the CN host after prepare/provider verification. Never prints
environment contents, credentials, or user records. No database writes or pruning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

ROOT = Path("/opt/offersteady/releases/20261008-cn-shared-text-v4-1-1")
MODEL = "deepseek-v4.1-flash"
KEY = "OFFERSTEADY_CHAT_QWEN_MODEL"
GATES = (
    Path("/opt/offersteady/releases/20260925-cn-answer-errors-1/idle_gate.py"),
    Path("/opt/offersteady/releases/20260923-cn-quick-stage-1/deploy/check-idle.py"),
    Path("/opt/offersteady/releases/20260926-cn-mock-report-3/deploy/readiness-idle.py"),
)
MODEL_FIELDS = (
    "chat_qwen_model", "chat_quick_model", "chat_detail_model",
    "mock_interview_tts_model", "screenshot_vision_model", "realtime_asr_model",
    "embedding_model", "rerank_model",
)
MATERIAL_GATE = '''
import sys,json,time
sys.path.insert(0,"/app/apps/backend")
from app.core.config import Settings
import psycopg
s=Settings()
with psycopg.connect(s.database_url,connect_timeout=3,options="-c default_transaction_read_only=on -c statement_timeout=3000") as conn:
 with conn.cursor() as c:
  jobs={}
  for table in ("material_processing_jobs","material_deletion_jobs","material_reconcile_jobs"):
   c.execute("SELECT count(*) FROM "+table+" WHERE status IN ('queued','retrying','running')")
   jobs[table]=c.fetchone()[0]
  # Historical stale QUEUED tasks whose durable job already failed are not
  # executing work. Keep all records untouched; block any other nonterminal task.
  c.execute("""SELECT count(*) FROM material_processing_tasks t
   WHERE current_stage NOT IN ('COMPLETED','FAILED') AND NOT (
    current_stage='QUEUED' AND updated_at_ms < %s AND EXISTS (
     SELECT 1 FROM material_processing_jobs j WHERE j.related_task_id=t.task_id AND j.status='failed')
   )""",(int(time.time()*1000)-86400000,))
  tasks=c.fetchone()[0]
  print(json.dumps({"pendingMaterialJobs":jobs,"protectedMaterialTasks":tasks}))
  if any(jobs.values()) or tasks: raise SystemExit(75)
'''


def inspect(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name], timeout=15))[0]


def run(args, *, cwd=None, timeout=60):
    # Capture potentially sensitive diagnostics; only safe status is reported.
    return subprocess.run(args, cwd=cwd, capture_output=True, check=True, timeout=timeout)


def environment(container):
    return dict(item.split("=", 1) for item in container["Config"]["Env"] if "=" in item)


def models(name):
    code = ("import sys,json;sys.path.insert(0,'/app/apps/backend');"
            "from app.core.config import Settings;s=Settings();"
            f"print(json.dumps({{k:getattr(s,k,None) for k in {MODEL_FIELDS!r}}}))")
    return json.loads(run(["docker", "exec", name, "python", "-B", "-c", code]).stdout)


def replacement(data: bytes) -> bytes:
    lines = data.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line.startswith((KEY + "=").encode())]
    assert len(matches) == 1, "model key missing/duplicated"
    index = matches[0]
    assert lines[index].strip() == (KEY + "=deepseek-v4-flash").encode(), "unexpected model baseline"
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = (KEY + "=" + MODEL).encode() + newline
    return b"".join(lines)


def atomic_write(path: Path, data: bytes):
    stat = path.stat()
    temp = path.with_name(path.name + ".model-cutover.tmp")
    # Refuse unexpected leftovers rather than overwriting an unrelated file.
    with temp.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temp, stat.st_mode & 0o777)
    os.chown(temp, stat.st_uid, stat.st_gid)
    os.replace(temp, path)


def idle_gate():
    for script in GATES:
        result = subprocess.run(
            ["docker", "exec", "-i", "-w", "/app/apps/backend", "compose-backend-1", "python", "-B", "-"],
            input=script.read_bytes(), capture_output=True, timeout=20,
        )
        # Existing reviewed gate outputs contain counts only.
        print(json.dumps({"gate": script.name, "exitCode": result.returncode,
                          "counts": result.stdout.decode().strip()}), flush=True)
        assert result.returncode == 0, "protected user work; cutover deferred"
    result = subprocess.run(
        ["docker", "exec", "-i", "-w", "/app/apps/backend", "compose-backend-1", "python", "-B", "-"],
        input=MATERIAL_GATE.encode(), capture_output=True, timeout=20,
    )
    print(json.dumps({"gate": "material-work", "exitCode": result.returncode,
                      "counts": result.stdout.decode().strip()}), flush=True)
    assert result.returncode == 0, "protected material work; cutover deferred"


def compose(target):
    run(["docker", "compose", "-p", "compose", "--env-file", target["envFile"],
         "-f", target["composeFile"], "up", "-d", "--no-build", "--no-deps",
         "--force-recreate", target["service"]], cwd=target["release"], timeout=90)


def wait_healthy(target):
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        d = inspect(target["container"])
        if d["State"]["Running"] and d["RestartCount"] == 0:
            health = d["State"].get("Health", {}).get("Status")
            if health == "healthy" or (health is None and time.monotonic() > deadline - 40):
                return d
        time.sleep(1)
    raise AssertionError("service health gate failed")


def invariant(before, after, target):
    expected = environment(before)
    expected[KEY] = MODEL
    assert environment(after) == expected, "unexpected runtime environment change"
    assert after["Image"] == target["newImage"], "unexpected effective image"
    for key in ("Cmd", "Entrypoint", "WorkingDir", "User", "ExposedPorts", "Healthcheck"):
        assert before["Config"].get(key) == after["Config"].get(key), "container configuration drift"
    for key in ("RestartPolicy", "PortBindings", "NetworkMode", "Memory", "NanoCpus", "ShmSize",
                "SecurityOpt", "ReadonlyRootfs", "Privileged", "LogConfig", "Binds"):
        assert before["HostConfig"].get(key) == after["HostConfig"].get(key), "container host configuration drift"
    assert before["Mounts"] == after["Mounts"], "mount drift"


def verify_non_targets(manifest):
    for name, old in manifest["nonTargets"].items():
        now = inspect(name)
        assert (now["Id"], now["Image"], now["State"]["StartedAt"]) == (
            old["id"], old["image"], old["started"]
        ), "unrelated service changed"


def main(*, preflight_only=False):
    os.umask(0o077)
    assert not (ROOT / "deployed.json").exists(), "deployment already recorded; inspect first"
    manifest = json.loads((ROOT / "prepared.json").read_text())
    assert manifest["model"] == MODEL
    before_models = {}
    before_containers = {}
    replacements = {}
    for target in manifest["targets"]:
        name, service = target["container"], target["service"]
        assert service in ("backend", "material-worker")
        assert target["runtimeTag"] == "compose-" + service
        saved = json.loads((ROOT / service / "container-before.json").read_text())
        current = inspect(name)
        assert current["Id"] == target["beforeId"] == saved["Id"], "container baseline drift"
        assert current["Image"] == target["baseImage"] and current["Config"] == saved["Config"], "runtime baseline drift"
        old_env = (ROOT / service / "env.before").read_bytes()
        assert Path(target["envFile"]).read_bytes() == old_env, "environment baseline drift"
        assert hashlib.sha256(old_env).hexdigest() == target["envSha256"]
        replacements[service] = replacement(old_env)
        candidate = inspect(target["newTag"])
        assert candidate["Id"] == target["newImage"]
        assert candidate["Config"] == inspect(target["baseImage"])["Config"]
        report = json.loads((ROOT / service / "provider-probe.json").read_text())
        assert report["passed"], "provider verification failed"
        before_containers[service] = saved
        before_models[service] = models(name)
        assert before_models[service]["chat_qwen_model"] == "deepseek-v4-flash"
        # Re-render immediately before deployment; reject any unrelated env drift.
        rendered = json.loads(run(["docker", "compose", "-p", "compose", "--env-file", target["envFile"],
                                   "-f", target["composeFile"], "config", "--format", "json"]).stdout)
        assert all(str(v) == environment(current).get(k)
                   for k, v in rendered["services"][service]["environment"].items()), "compose environment drift"
    verify_non_targets(manifest)
    idle_gate()
    if preflight_only:
        print(json.dumps({"preflightPassed": True, "productionChanged": False}), flush=True)
        return
    # Complete preflight before any production environment file/tag is touched.
    touched = []
    try:
        idle_gate()
        for target in manifest["targets"]:
            touched.append(target)
            atomic_write(Path(target["envFile"]), replacements[target["service"]])
            run(["docker", "tag", target["newTag"], target["runtimeTag"]])
            compose(target)
            wait_healthy(target)
            print(json.dumps({"switched": target["service"], "model": MODEL}), flush=True)
        after_models = {}
        for target in manifest["targets"]:
            after = wait_healthy(target)
            invariant(before_containers[target["service"]], after, target)
            actual = models(target["container"])
            expected = dict(before_models[target["service"]], chat_qwen_model=MODEL)
            assert actual == expected, "effective model configuration drift"
            assert actual["chat_quick_model"] == actual["chat_detail_model"] == MODEL
            source = run(["docker", "exec", target["container"], "python", "-B", "-c",
                          "from pathlib import Path;import hashlib;print(hashlib.sha256(Path('/app/apps/backend/app/services/document_processing.py').read_bytes()).hexdigest())"]).stdout.decode().strip()
            assert source == target["newSourceSha256"], "summary source drift"
            after_models[target["service"]] = actual
        verify_non_targets(manifest)
        with urlopen("https://mianshiwen.cn/healthz", timeout=10) as response:
            assert response.status == 200
            assert json.loads(response.read())["data"]["status"] == "ok"
        result = {"deployed": True, "atMs": int(time.time() * 1000), "models": after_models,
                  "services": [t["service"] for t in manifest["targets"]], "nonTargetsUnchanged": True}
        (ROOT / "deployed.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except Exception as exc:
        # Restore only the two explicitly authorized services, never data volumes.
        rollback_ok = True
        for target in reversed(touched):
            try:
                atomic_write(Path(target["envFile"]), (ROOT / target["service"] / "env.before").read_bytes())
                run(["docker", "tag", target["baseImage"], target["runtimeTag"]])
                compose(target)
                wait_healthy(target)
                assert inspect(target["container"])["Image"] == target["baseImage"]
            except Exception:
                rollback_ok = False
        print(json.dumps({"deployed": False, "errorType": type(exc).__name__, "rollbackHealthy": rollback_ok}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    try:
        main(preflight_only=args.preflight_only)
    except Exception as exc:
        print(json.dumps({"deployed": False, "preflightErrorType": type(exc).__name__,
                          "reason": str(exc) if isinstance(exc, AssertionError) else "preflight failed"}), flush=True)
        raise SystemExit(1) from None
