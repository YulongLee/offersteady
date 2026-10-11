"""Fixed-scope CN heartbeat overlay, idle-gated and rollbackable.

Prepare does not mutate running services. Private backups stay on the CN host.
"""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import urlopen

import cutover_cn_shared_text_model as guards

ROOT = Path("/opt/offersteady/releases/20261010-cn-web-heartbeat-1")
BASE_IMAGE = "sha256:866a5e920cc8db962d9474ad3dff5995fd3348a17c3e2b2f778f9f1e43962384"
BASE = "/app/apps/backend/app/"
HASHES = {
    "ports/interview_session.py": "414525cea92dd2a6b6777b231824a8107cc00ae69e40bbc1e82f338d78752698",
    "services/interview_session_repository.py": "f8ba61ba67b3303a44eb33f86279c8af75914eb269bc8a4eb542960873f0702c",
    "services/postgres_interview_session_repository.py": "78000ffd41cd491884a557722be76e6d836715d473a441f802faa56de8695b31",
    "services/session_service.py": "26af06feb04e536bb10d16e2b8fc8397fb25cddb5dfb0d674453078e18c81aa6",
    "services/realtime_speech_service.py": "26e25e8f03ed40810cc978b484c58860f3866ef2f175a885937a71fbb9d6e9bc",
}
CLASSES = dict(zip(HASHES, ["InterviewSessionRepository", "InMemoryInterviewSessionRepository",
    "PostgresInterviewSessionRepository", "SessionService", "RealtimeSpeechService"]))
ADDED = {p: ["get_heartbeat_state"] for p in list(HASHES)[:3]}
ADDED["services/session_service.py"] = ["heartbeat_idle_status", "_idle_status_from_session"]
ADDED["services/realtime_speech_service.py"] = []
REPLACED = {"services/session_service.py": ["idle_status"],
            "services/realtime_speech_service.py": ["record_web_session_heartbeat"]}
REPLACED_HASHES = {"idle_status": "4f4fd672b881f1f50384ee3b8fdb623eeb1462f334026d8f2614213dc3b8d7d8",
    "record_web_session_heartbeat": "6bb5c65a431e3ada8894fafde59746d43620106d8aaafc2e0cdf2f64dcc921f5"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def node_digest(node):
    # Python 3.13 changed ast.dump's empty-field output. Canonicalize fields so
    # the host and image verify identical semantics across Python versions.
    def canonical(value):
        if isinstance(value, ast.AST):
            return {"node":type(value).__name__, **{k:canonical(v) for k,v in ast.iter_fields(value)
                if v is not None and v != []}}
        if isinstance(value, list):
            return [canonical(v) for v in value]
        return value
    return digest(json.dumps(canonical(node), sort_keys=True, separators=(",", ":")).encode())


def class_node(source, name):
    return next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == name)


def method(source, cls, name):
    return next(n for n in class_node(source, cls).body if isinstance(n, ast.FunctionDef) and n.name == name)


def span(source, node):
    start = min([node.lineno] + [n.lineno for n in getattr(node, "decorator_list", [])])
    return "".join(source.splitlines(keepends=True)[start-1:node.end_lineno])


def overlay(path, before, local):
    """Import only reviewed heartbeat nodes, preserving all other CN nodes."""
    assert path in HASHES
    result = before
    cls = CLASSES[path]
    old_nodes = {}
    for name in REPLACED.get(path, []):
        old = method(result, cls, name)
        assert node_digest(old) == REPLACED_HASHES[name], "legacy method changed"
        old_nodes[name] = deepcopy(old)
        lines = result.splitlines(keepends=True)
        lines[old.lineno-1:old.end_lineno] = [span(local, method(local, cls, name))]
        result = "".join(lines)
    for name in ADDED[path]:
        node = class_node(result, cls)
        assert not any(isinstance(n, ast.FunctionDef) and n.name == name for n in node.body)
        lines = result.splitlines(keepends=True)
        lines.insert(node.end_lineno, "\n" + span(local, method(local, cls, name)))
        result = "".join(lines)
    if path == "ports/interview_session.py":
        node = class_node(result, cls)
        lines = result.splitlines(keepends=True)
        lines.insert(node.lineno-1, span(local, class_node(local, "SessionHeartbeatState")) + "\n\n")
        result = "".join(lines)
    elif path != "services/realtime_speech_service.py":
        node = next(n for n in ast.parse(result).body if isinstance(n, ast.ImportFrom) and n.module == "app.ports.interview_session")
        lines = result.splitlines(keepends=True)
        lines.insert(node.end_lineno, "from app.ports.interview_session import SessionHeartbeatState\n")
        result = "".join(lines)
    # Remove the explicitly allowed new nodes; restore only the two changed
    # methods. The resulting AST must equal the actual production source.
    normalized = ast.parse(result)
    normalized.body = [n for n in normalized.body if not (
        isinstance(n, ast.ClassDef) and n.name == "SessionHeartbeatState") and not (
        isinstance(n, ast.ImportFrom) and n.module == "app.ports.interview_session"
        and [a.name for a in n.names] == ["SessionHeartbeatState"])]
    target = next(n for n in normalized.body if isinstance(n, ast.ClassDef) and n.name == cls)
    target.body = [old_nodes.get(n.name, n) if isinstance(n, ast.FunctionDef) else n for n in target.body
                   if not (isinstance(n, ast.FunctionDef) and n.name in ADDED[path])]
    assert ast.dump(normalized, include_attributes=False) == ast.dump(ast.parse(before), include_attributes=False), "unrelated code changed"
    compile(result, path, "exec")
    return result


def source(name, path):
    return guards.run(["docker", "exec", name, "python", "-B", "-c",
        f"from pathlib import Path;print(Path({(BASE+path)!r}).read_text(),end='')"]).stdout


def prepare():
    assert ROOT.is_dir() and not (ROOT / "prepared.json").exists()
    before = guards.inspect("compose-backend-1")
    assert before["Image"] == BASE_IMAGE and before["State"]["Running"]
    labels = before["Config"]["Labels"]
    release = Path(labels["com.docker.compose.project.working_dir"]).parents[1]
    target = {"container":"compose-backend-1", "service":"backend", "baseImage":BASE_IMAGE,
        "beforeId":before["Id"], "runtimeTag":before["Config"]["Image"], "release":str(release),
        "composeFile":labels["com.docker.compose.project.config_files"], "envFile":str(release/".env.production"),
        "newTag":"offersteady-cn-backend:web-heartbeat-20261010-1"}
    assert target["runtimeTag"] == "compose-backend" and "," not in target["composeFile"]
    directory = ROOT / "backend"
    if directory.exists():
        saved = json.loads((directory/"container-before.json").read_text())
        assert saved["Id"] == before["Id"] and saved["Config"] == before["Config"], "partial preparation baseline drift"
        assert (directory/"env.before").read_bytes() == Path(target["envFile"]).read_bytes()
    directory.mkdir(mode=0o700, exist_ok=True)
    (directory / "container-before.json").write_text(json.dumps(before))
    env = Path(target["envFile"]).read_bytes()
    (directory / "env.before").write_bytes(env)
    hashes = {}
    copies = []
    for path in HASHES:
        original = source(target["container"], path)
        assert digest(original) == HASHES[path], "source baseline drift"
        candidate = overlay(path, original.decode(), (ROOT/"local"/path).read_text()).encode()
        destination = directory/path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(candidate)
        (destination.with_suffix(".before.py")).write_bytes(original)
        hashes[path] = digest(candidate)
        copies.append(f"COPY {path} {BASE+path}\n")
    base_tag = "offersteady-cn-base:web-heartbeat-20261010"
    guards.run(["docker", "tag", BASE_IMAGE, base_tag])
    (directory/"Dockerfile").write_text(f"FROM {base_tag}\n"+"".join(copies))
    guards.run(["docker", "build", "--network=none", "-t", target["newTag"], str(directory)], timeout=90)
    image = guards.inspect(target["newTag"])
    assert image["Config"] == guards.inspect(BASE_IMAGE)["Config"]
    target.update(newImage=image["Id"], envSha256=digest(env), sourceHashes=hashes)
    others = {}
    for name in guards.run(["docker", "ps", "--format", "{{.Names}}"] ).stdout.decode().splitlines():
        if name != target["container"]:
            info = guards.inspect(name)
            others[name] = {"id":info["Id"], "image":info["Image"], "started":info["State"]["StartedAt"]}
    (ROOT/"prepared.json").write_text(json.dumps({"targets":[target],"nonTargets":others,"models":guards.models(target["container"])}, indent=2))
    print(json.dumps({"prepared":True,"productionChanged":False,"image":image["Id"],"files":len(hashes)}))


def invariant(before, after, target):
    assert guards.environment(before) == guards.environment(after), "environment drift"
    assert after["Image"] == target["newImage"]
    for key in ("Cmd", "Entrypoint", "WorkingDir", "User", "ExposedPorts", "Healthcheck"):
        assert before["Config"].get(key) == after["Config"].get(key)
    for key in ("RestartPolicy", "PortBindings", "NetworkMode", "Memory", "NanoCpus", "ShmSize", "SecurityOpt", "ReadonlyRootfs", "Privileged", "LogConfig", "Binds"):
        assert before["HostConfig"].get(key) == after["HostConfig"].get(key)
    assert before["Mounts"] == after["Mounts"]


def deploy(*, preflight_only=False):
    assert not (ROOT/"deployed.json").exists()
    manifest = json.loads((ROOT/"prepared.json").read_text())
    assert len(manifest["targets"]) == 1
    target = manifest["targets"][0]
    assert target["service"] == "backend" and target["container"] == "compose-backend-1" and target["baseImage"] == BASE_IMAGE
    before = json.loads((ROOT/"backend/container-before.json").read_text())
    current = guards.inspect(target["container"])
    assert current["Id"] == before["Id"] == target["beforeId"] and current["Config"] == before["Config"] and current["Image"] == BASE_IMAGE
    assert digest(Path(target["envFile"]).read_bytes()) == target["envSha256"]
    assert guards.inspect(target["newTag"])["Id"] == target["newImage"]
    report = json.loads((ROOT/"candidate-verification.json").read_text())
    assert report["passed"] and report["checks"] >= 8
    rendered = json.loads(guards.run(["docker","compose","-p","compose","--env-file",target["envFile"],"-f",target["composeFile"],"config","--format","json"]).stdout)
    assert all(str(v) == guards.environment(current).get(k) for k,v in rendered["services"]["backend"]["environment"].items())
    for path, checksum in target["sourceHashes"].items():
        assert digest((ROOT/"backend"/path).read_bytes()) == checksum
    guards.verify_non_targets(manifest)
    guards.idle_gate()
    if preflight_only:
        print(json.dumps({"preflightPassed":True,"productionChanged":False})); return
    guards.idle_gate()
    try:
        guards.run(["docker","tag",target["newTag"],target["runtimeTag"]])
        guards.compose(target)
        after = guards.wait_healthy(target)
        invariant(before, after, target)
        assert guards.models(target["container"]) == manifest["models"]
        for path, checksum in target["sourceHashes"].items():
            assert digest(source(target["container"],path)) == checksum
        guards.verify_non_targets(manifest)
        with urlopen("https://mianshiwen.cn/healthz", timeout=10) as response:
            assert response.status == 200 and json.loads(response.read())["data"]["status"] == "ok"
        result = {"deployed":True,"atMs":int(time.time()*1000),"services":["backend"],"image":target["newImage"],"modelsUnchanged":True,"environmentUnchanged":True,"nonTargetsUnchanged":True}
        (ROOT/"deployed.json").write_text(json.dumps(result, indent=2)); print(json.dumps(result))
    except Exception as exc:
        rollback_ok = False
        try:
            guards.run(["docker","tag",BASE_IMAGE,target["runtimeTag"]]); guards.compose(target); guards.wait_healthy(target)
            assert guards.inspect(target["container"])["Image"] == BASE_IMAGE
            rollback_ok = True
        finally:
            print(json.dumps({"deployed":False,"errorType":type(exc).__name__,"rollbackHealthy":rollback_ok}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["prepare","preflight","deploy"])
    args = parser.parse_args(); os.umask(0o077)
    try:
        prepare() if args.action == "prepare" else deploy(preflight_only=args.action == "preflight")
    except Exception as exc:
        print(json.dumps({"completed":False,"errorType":type(exc).__name__,"reason":str(exc) if isinstance(exc,AssertionError) else "inspect private server evidence"}))
        raise SystemExit(1) from None
