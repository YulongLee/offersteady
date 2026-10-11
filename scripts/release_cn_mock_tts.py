"""Fixed-scope CN backend TTS overlay. Server-only secrets never leave backups.

Uses reviewed cutover helpers from the preceding CN release. No helper main runs
on import. Preparation changes no running service; cutover is separately invoked.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import urlopen

import cutover_cn_shared_text_model as guards

ROOT = Path("/opt/offersteady/releases/20261009-cn-mock-tts-qwen-audio-plus-1")
SOURCE = "/app/apps/backend/app/services/mock_interview_tts.py"
BASE_SOURCE_SHA = "bd34817b18e0e84317750e49e0e298110a893bacac5ef2deecf9573d1e8ee08a"
BASE_IMAGE = "sha256:711cd937b57acce5c9f248ae064498ca1b751a5da608837ff225765cb18e4d00"
CHANGES = {
    "OFFERSTEADY_MOCK_INTERVIEW_TTS_MODEL": ("qwen3-tts-instruct-flash-realtime", "qwen-audio-3.0-tts-plus"),
    "OFFERSTEADY_MOCK_INTERVIEW_TTS_VOICE": ("Cherry", "longanhuan_v3.6"),
    "OFFERSTEADY_MOCK_INTERVIEW_TTS_WS_URL": ("wss://dashscope.aliyuncs.com/api-ws/v1/realtime", "wss://dashscope.aliyuncs.com/api-ws/v1/inference"),
}


def replacement(data):
    lines = data.splitlines(keepends=True)
    for key, (old, new) in CHANGES.items():
        matches = [i for i, line in enumerate(lines) if line.startswith((key + "=").encode())]
        assert len(matches) <= 1, "TTS environment key duplicated"
        if not matches:
            # The verified live image currently uses Settings defaults. Make the
            # three settings explicit without altering any existing env line.
            if lines and not lines[-1].endswith(b"\n"):
                lines[-1] += b"\n"
            lines.append((key + "=" + new).encode() + b"\n")
            continue
        index = matches[0]
        assert lines[index].strip() == (key + "=" + old).encode(), "TTS baseline changed"
        newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
        lines[index] = (key + "=" + new).encode() + newline
    return b"".join(lines)


def cn_source(source):
    """Strip only the three known Global-only branches absent from the CN baseline."""
    branches = [
        ('        prompt = "ai/prompts/mock-interview/en/tts.txt" if settings.product_edition == "global" else "ai/prompts/mock-interview/tts.txt"\n        self._instructions = (REPO_ROOT / prompt).read_text(encoding="utf-8").strip()',
         '        self._instructions = (REPO_ROOT / "ai/prompts/mock-interview/tts.txt").read_text(encoding="utf-8").strip()'),
        ('        endpoint = urlsplit(self.settings.global_mock_interview_tts_ws_url\n            if self.settings.product_edition == "global" else self.settings.mock_interview_tts_ws_url)',
         '        endpoint = urlsplit(self.settings.mock_interview_tts_ws_url)'),
        ('"language_type": "English" if self.settings.product_edition == "global" else "Chinese"', '"language_type": "Chinese"'),
    ]
    for old, new in branches:
        assert source.count(old) == 1, "local TTS source unexpectedly diverged"
        source = source.replace(old, new, 1)
    ast.parse(source)
    return source


def fields(name):
    names = guards.MODEL_FIELDS + ("mock_interview_tts_voice", "mock_interview_tts_ws_url", "product_edition")
    code = ("import sys,json;sys.path.insert(0,'/app/apps/backend');from app.core.config import Settings;s=Settings();"
            f"print(json.dumps({{k:getattr(s,k,None) for k in {names!r}}}))")
    return json.loads(guards.run(["docker", "exec", name, "python", "-B", "-c", code]).stdout)


def rendered(target):
    return json.loads(guards.run(["docker", "compose", "-p", "compose", "--env-file", target["envFile"],
                                 "-f", target["composeFile"], "config", "--format", "json"]).stdout)


def prepare():
    assert ROOT.is_dir() and not (ROOT / "prepared.json").exists(), "inspect existing preparation first"
    before = guards.inspect("compose-backend-1")
    assert before["Image"] == BASE_IMAGE and before["State"]["Running"]
    labels = before["Config"]["Labels"]
    compose_file = labels["com.docker.compose.project.config_files"]
    assert "," not in compose_file
    release = Path(labels["com.docker.compose.project.working_dir"]).parents[1]
    target = {"container": "compose-backend-1", "service": "backend", "baseImage": before["Image"],
              "runtimeTag": before["Config"]["Image"], "beforeId": before["Id"], "release": str(release),
              "composeFile": compose_file, "envFile": str(release / ".env.production"),
              "newTag": "offersteady-cn-backend:mock-tts-qwen-audio-plus-20261009-1"}
    assert target["runtimeTag"] == "compose-backend"
    env = guards.environment(before)
    assert all(str(v) == env.get(k) for k, v in rendered(target)["services"]["backend"]["environment"].items())
    actual = fields(target["container"])
    assert actual["product_edition"] == "cn" and actual["chat_qwen_model"] == "deepseek-v4.1-flash"
    assert all(actual[k.lower().removeprefix("offersteady_")] == values[0] for k, values in CHANGES.items()), "effective TTS baseline changed"
    old_source = guards.run(["docker", "exec", target["container"], "python", "-B", "-c",
                             f"from pathlib import Path;print(Path({SOURCE!r}).read_text(),end='')"]).stdout
    assert hashlib.sha256(old_source).hexdigest() == BASE_SOURCE_SHA
    # Verify the reviewed local legacy source is exactly this runtime baseline.
    assert cn_source((ROOT / "local-before.py").read_text()).encode() == old_source
    source = cn_source((ROOT / "local-candidate.py").read_text())
    assert source.count('async def _stream_audio_plus') == 1
    backup = Path(target["envFile"]).read_bytes()
    replacement(backup)  # Validate existing values; defaults checked above.
    directory = ROOT / "backend"
    directory.mkdir(mode=0o700, exist_ok=False)
    (directory / "container-before.json").write_text(json.dumps(before))
    (directory / "env.before").write_bytes(backup)
    (directory / "mock_interview_tts.before.py").write_bytes(old_source)
    (directory / "mock_interview_tts.py").write_text(source)
    candidate_env = env | {k: values[1] for k, values in CHANGES.items()}
    assert all("\n" not in v and "\r" not in v for v in candidate_env.values())
    (directory / "probe.env").write_text("\n".join(f"{k}={v}" for k, v in candidate_env.items()) + "\n")
    base_tag = "offersteady-cn-base:mock-tts-20261009"
    guards.run(["docker", "tag", before["Image"], base_tag])
    (directory / "Dockerfile").write_text(f"FROM {base_tag}\nCOPY mock_interview_tts.py {SOURCE}\n")
    guards.run(["docker", "build", "--network=none", "-t", target["newTag"], str(directory)], timeout=90)
    candidate = guards.inspect(target["newTag"])
    assert candidate["Config"] == guards.inspect(before["Image"])["Config"]
    target.update(newImage=candidate["Id"], envSha256=hashlib.sha256(backup).hexdigest(),
                  newSourceSha256=hashlib.sha256(source.encode()).hexdigest())
    non_targets = {}
    names = guards.run(["docker", "ps", "--format", "{{.Names}}"]).stdout.decode().splitlines()
    for name in names:
        if name != target["container"]:
            d = guards.inspect(name)
            non_targets[name] = {"id": d["Id"], "image": d["Image"], "started": d["State"]["StartedAt"]}
    manifest = {"targets": [target], "nonTargets": non_targets}
    (ROOT / "prepared.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"prepared": True, "productionChanged": False, "target": "backend", "image": candidate["Id"]}), flush=True)


def invariant(before, after, target):
    expected = guards.environment(before) | {k: values[1] for k, values in CHANGES.items()}
    assert guards.environment(after) == expected, "unrelated environment changed"
    assert after["Image"] == target["newImage"]
    for key in ("Cmd", "Entrypoint", "WorkingDir", "User", "ExposedPorts", "Healthcheck"):
        assert before["Config"].get(key) == after["Config"].get(key), "container configuration changed"
    for key in ("RestartPolicy", "PortBindings", "NetworkMode", "Memory", "NanoCpus", "ShmSize", "SecurityOpt", "ReadonlyRootfs", "Privileged", "LogConfig", "Binds"):
        assert before["HostConfig"].get(key) == after["HostConfig"].get(key), "host configuration changed"
    assert before["Mounts"] == after["Mounts"], "mounts changed"


def deploy(*, preflight_only=False):
    assert not (ROOT / "deployed.json").exists(), "already deployed; inspect before rerunning"
    manifest = json.loads((ROOT / "prepared.json").read_text())
    assert len(manifest["targets"]) == 1
    target = manifest["targets"][0]
    assert target["container"] == "compose-backend-1" and target["service"] == "backend" and target["baseImage"] == BASE_IMAGE
    directory = ROOT / "backend"
    before = json.loads((directory / "container-before.json").read_text())
    now = guards.inspect(target["container"])
    assert now["Id"] == before["Id"] == target["beforeId"] and now["Config"] == before["Config"]
    assert now["Image"] == BASE_IMAGE
    old_env = (directory / "env.before").read_bytes()
    assert Path(target["envFile"]).read_bytes() == old_env and hashlib.sha256(old_env).hexdigest() == target["envSha256"]
    new_env = replacement(old_env)
    candidate = guards.inspect(target["newTag"])
    assert candidate["Id"] == target["newImage"] and candidate["Config"] == guards.inspect(BASE_IMAGE)["Config"]
    report = json.loads((directory / "provider-probe.json").read_text().splitlines()[-1])
    assert report["passed"] and report["cancelPassed"] and report["allConnectionsClosed"] and len(report["checks"]) == 2
    assert report["model"] == CHANGES["OFFERSTEADY_MOCK_INTERVIEW_TTS_MODEL"][1]
    before_fields = fields(target["container"])
    assert before_fields["product_edition"] == "cn"
    assert all(before_fields[k.lower().removeprefix("offersteady_")] == values[0] for k, values in CHANGES.items())
    assert all(str(v) == guards.environment(now).get(k) for k, v in rendered(target)["services"]["backend"]["environment"].items())
    guards.verify_non_targets(manifest)
    guards.idle_gate()
    if preflight_only:
        print(json.dumps({"preflightPassed": True, "productionChanged": False}), flush=True)
        return
    # Second user-work gate immediately before touching production config.
    guards.idle_gate()
    try:
        guards.atomic_write(Path(target["envFile"]), new_env)
        guards.run(["docker", "tag", target["newTag"], target["runtimeTag"]])
        guards.compose(target)
        after = guards.wait_healthy(target)
        invariant(before, after, target)
        expected = before_fields | {k.lower().removeprefix("offersteady_"): values[1] for k, values in CHANGES.items()}
        actual = fields(target["container"])
        assert actual == expected, "effective model or TTS settings changed unexpectedly"
        source_sha = guards.run(["docker", "exec", target["container"], "python", "-B", "-c",
                                f"from pathlib import Path;import hashlib;print(hashlib.sha256(Path({SOURCE!r}).read_bytes()).hexdigest())"]).stdout.decode().strip()
        assert source_sha == target["newSourceSha256"]
        guards.verify_non_targets(manifest)
        with urlopen("https://mianshiwen.cn/healthz", timeout=10) as response:
            assert response.status == 200 and json.loads(response.read())["data"]["status"] == "ok"
        result = {"deployed": True, "atMs": int(time.time()*1000), "services": ["backend"], "models": actual,
                  "nonTargetsUnchanged": True, "image": target["newImage"]}
        (ROOT / "deployed.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except Exception as exc:
        rollback_ok = False
        try:
            guards.atomic_write(Path(target["envFile"]), old_env)
            guards.run(["docker", "tag", BASE_IMAGE, target["runtimeTag"]])
            guards.compose(target)
            guards.wait_healthy(target)
            assert guards.inspect(target["container"])["Image"] == BASE_IMAGE
            rollback_ok = True
        finally:
            print(json.dumps({"deployed": False, "errorType": type(exc).__name__, "rollbackHealthy": rollback_ok}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "preflight", "deploy"])
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepare() if args.action == "prepare" else deploy(preflight_only=args.action == "preflight")
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__,
                          "reason": str(exc) if isinstance(exc, AssertionError) else "release guard failed"}), flush=True)
        raise SystemExit(1) from None
