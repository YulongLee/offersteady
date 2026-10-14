"""Restore one CN heartbeat method over the actual running Backend image.

Preparation never changes live tags or containers. Private source/configuration
backups remain in the server release directory, not in Git. An explicit deploy
requires local evidence, an immutable-image synthetic probe, and two idle gates.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.request import urlopen

import cutover_cn_shared_text_model as guards

ROOT = Path("/opt/offersteady/releases/20261014-cn-heartbeat-restore-1")
BASE_IMAGE = "sha256:567ddaf392216bad2b23644cf94f65b8b4c0b5f9cb982e6ae15be8891cac06e1"
SOURCE_PATH = "services/realtime_speech_service.py"
SOURCE_BEFORE_SHA256 = "0f0b280f284b35625fc75d7615c1c2f43bf731f68230928ef6881c1fd86875a7"
SESSION_BEFORE_SHA256 = "b1e064bc4e15a97b0a14c6c37bcc71048adf09e6d5d7e6e25e4e4ebb6e23175f"
REPLACEMENT_NODE_SHA256 = "766bbe79dcce76f10bc81cf7dc846707610c1cf0d102493799325b6f207e5412"
CLASS_NAME = "RealtimeSpeechService"
METHOD_NAME = "record_web_session_heartbeat"
APP_ROOT = "/app/apps/backend/app/"
NEW_TAG = "offersteady-cn-backend:heartbeat-restore-20261014-1"
ROLLBACK_TAG = "offersteady-cn-backend:heartbeat-restore-20261014-rollback"
SUPPORT_PATHS = (
    "ports/interview_session.py",
    "services/interview_session_repository.py",
    "services/postgres_interview_session_repository.py",
    "services/session_service.py",
)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def node_digest(node: ast.AST) -> str:
    # ast.dump empty-field output differs between host Python 3.13 and image 3.12.
    def canonical(value):
        if isinstance(value, ast.AST):
            return {"node": type(value).__name__, **{
                key: canonical(item) for key, item in ast.iter_fields(value)
                if item is not None and item != []
            }}
        if isinstance(value, list):
            return [canonical(item) for item in value]
        if value is Ellipsis:
            return {"constantType": "ellipsis"}
        if isinstance(value, bytes):
            return {"constantType": "bytes", "hex": value.hex()}
        if isinstance(value, complex):
            return {"constantType": "complex", "real": value.real, "imag": value.imag}
        return value
    return digest(json.dumps(canonical(node), sort_keys=True, separators=(",", ":")))


def heartbeat_node(tree: ast.Module) -> ast.FunctionDef:
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == CLASS_NAME]
    assert len(classes) == 1, "heartbeat class missing/duplicated"
    methods = [node for node in classes[0].body if isinstance(node, ast.FunctionDef) and node.name == METHOD_NAME]
    assert len(methods) == 1, "heartbeat method missing/duplicated"
    return methods[0]


def method_span(source: str, node: ast.FunctionDef) -> tuple[int, int, str]:
    start = min([node.lineno] + [decorator.lineno for decorator in node.decorator_list]) - 1
    return start, node.end_lineno, "".join(source.splitlines(keepends=True)[start:node.end_lineno])


def overlay(before: str, local: str) -> str:
    """Only the reviewed method can enter the candidate; imports stay untouched."""
    original_tree, local_tree = ast.parse(before), ast.parse(local)
    original, replacement = heartbeat_node(original_tree), heartbeat_node(local_tree)
    assert node_digest(replacement) == REPLACEMENT_NODE_SHA256, "reviewed heartbeat method drift"
    assert node_digest(original) != node_digest(replacement), "heartbeat is already restored"
    start, end, _ = method_span(before, original)
    _, _, new_source = method_span(local, replacement)
    lines = before.splitlines(keepends=True)
    result = "".join(lines[:start]) + new_source + "".join(lines[end:])
    changed_tree = ast.parse(result)
    target_class = next(node for node in changed_tree.body if isinstance(node, ast.ClassDef) and node.name == CLASS_NAME)
    target_class.body = [deepcopy(original) if isinstance(node, ast.FunctionDef) and node.name == METHOD_NAME else node
                         for node in target_class.body]
    assert node_digest(changed_tree) == node_digest(original_tree), "unrelated AST changed"
    compile(result, SOURCE_PATH, "exec")
    return result


def runtime_source(name: str, path: str) -> bytes:
    return guards.run(["docker", "exec", name, "python", "-B", "-c",
        f"from pathlib import Path;print(Path({(APP_ROOT + path)!r}).read_text(),end='')"]).stdout


def compose_args(target: dict) -> list[str]:
    args = ["docker", "compose", "-p", target["project"], "--env-file", target["envFile"]]
    for path in target["composeFiles"]:
        args.extend(["-f", path])
    return args


def rendered_config(target: dict) -> dict:
    return json.loads(guards.run(compose_args(target) + ["config", "--format", "json"],
                                cwd=target["workingDir"]).stdout)


def config_digest(rendered: dict) -> str:
    return digest(json.dumps(rendered, sort_keys=True, separators=(",", ":")))


def verify_compose(target: dict, current: dict, rendered: dict) -> None:
    service = rendered["services"]["backend"]
    effective_image = service.get("image") or target["project"] + "-backend"
    assert effective_image == target["runtimeTag"], "compose image differs from running image tag"
    # Compare complete effective env, including unchanged defaults from base image.
    expected = guards.environment(guards.inspect(BASE_IMAGE))
    expected.update({key: str(value) for key, value in service.get("environment", {}).items()})
    assert expected == guards.environment(current), "compose environment differs from actual runtime"


def compose(target: dict) -> None:
    guards.run(compose_args(target) + ["up", "-d", "--no-build", "--no-deps", "--force-recreate", "backend"],
               cwd=target["workingDir"], timeout=90)


def invariant(before: dict, after: dict, target: dict) -> None:
    assert guards.environment(before) == guards.environment(after), "runtime environment drift"
    assert after["Image"] == target["newImage"], "unexpected effective image"
    for key in ("Cmd", "Entrypoint", "WorkingDir", "User", "ExposedPorts", "Healthcheck"):
        assert before["Config"].get(key) == after["Config"].get(key), "container configuration drift"
    for key in ("RestartPolicy", "PortBindings", "NetworkMode", "Memory", "NanoCpus", "ShmSize",
                "SecurityOpt", "ReadonlyRootfs", "Privileged", "LogConfig", "Binds"):
        assert before["HostConfig"].get(key) == after["HostConfig"].get(key), "container host configuration drift"
    assert before["Mounts"] == after["Mounts"], "mount drift"


def verify_candidate_sources(target: dict) -> None:
    paths = {SOURCE_PATH: target["sourceAfterSha256"], **target["protectedSourceHashes"]}
    code = ("import hashlib,json;from pathlib import Path;"
            f"paths={paths!r};print(json.dumps({{p:hashlib.sha256(Path({APP_ROOT!r}+p).read_bytes()).hexdigest() for p in paths}}))")
    actual = json.loads(guards.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python",
                                   target["newImage"], "-B", "-c", code], timeout=30).stdout)
    assert actual == paths, "candidate source drift"


def verify_candidate_image(image: dict, baseline: dict) -> None:
    assert image["Config"] == baseline["Config"], "candidate image configuration drift"
    original_layers = baseline["RootFS"]["Layers"]
    assert image["RootFS"]["Layers"][:-1] == original_layers, "candidate image layer baseline drift"
    assert len(image["RootFS"]["Layers"]) == len(original_layers) + 1, "candidate image overlay scope drift"


def verify_evidence(local: dict, probe: dict, target: dict) -> None:
    assert local.get("passed") is True, "local verification missing/failed"
    assert type(local.get("tests")) is int and local["tests"] > 0, "local test count missing"
    assert local.get("baseImage") == BASE_IMAGE, "local verification baseline drift"
    assert local.get("sourceBeforeSha256") == SOURCE_BEFORE_SHA256, "local verification source baseline drift"
    assert local.get("sourceAfterSha256") == target["sourceAfterSha256"], "local verification candidate drift"
    assert re.fullmatch(r"[0-9a-f]{40}", str(local.get("gitCommit", ""))), "Git verification missing"
    assert probe.get("passed") is True, "candidate verification missing/failed"
    assert type(probe.get("checks")) is int and probe["checks"] >= 12, "candidate checks incomplete"
    assert probe.get("syntheticOnly") is True and probe.get("networkRequired") is False, "unsafe candidate verification"
    assert probe.get("candidateImage") == target["newImage"], "candidate verification image drift"
    assert probe.get("sourceAfterSha256") == target["sourceAfterSha256"], "candidate verification source drift"


def prepare(root: Path, local_source: Path) -> None:
    assert root.is_dir() and not (root / "prepared.json").exists(), "release missing/already prepared"
    before = guards.inspect("compose-backend-1")
    assert before["Image"] == BASE_IMAGE and before["State"]["Running"], "runtime image baseline drift"
    assert before["RestartCount"] == 0 and before["State"].get("Health", {}).get("Status") == "healthy", "baseline unhealthy"
    labels = before["Config"]["Labels"]
    assert labels["com.docker.compose.service"] == "backend", "unexpected target service"
    target = {
        "container": "compose-backend-1", "service": "backend", "baseImage": BASE_IMAGE,
        "beforeId": before["Id"], "runtimeTag": before["Config"]["Image"],
        "project": labels["com.docker.compose.project"],
        "workingDir": labels["com.docker.compose.project.working_dir"],
        "composeFiles": labels["com.docker.compose.project.config_files"].split(","),
        "envFile": labels["com.docker.compose.project.environment_file"],
        "newTag": NEW_TAG, "rollbackTag": ROLLBACK_TAG,
    }
    assert target["project"] == "compose" and target["runtimeTag"] == "compose-backend", "unexpected compose baseline"
    assert not before["Mounts"], "unexpected source/configuration mount"
    rendered = rendered_config(target)
    verify_compose(target, before, rendered)
    source = runtime_source(target["container"], SOURCE_PATH)
    assert digest(source) == SOURCE_BEFORE_SHA256, "runtime source baseline drift"
    candidate = overlay(source.decode(), local_source.read_text()).encode()
    protected = {path: digest(runtime_source(target["container"], path)) for path in SUPPORT_PATHS}
    assert protected["services/session_service.py"] == SESSION_BEFORE_SHA256, "supporting session source drift"
    # All private artifacts are created only in this host directory with umask 077.
    directory = root / "backend"
    directory.mkdir(mode=0o700)
    (directory / "container-before.json").write_text(json.dumps(before))
    env_bytes = Path(target["envFile"]).read_bytes()
    (directory / "env.before").write_bytes(env_bytes)
    (directory / "realtime_speech_service.before.py").write_bytes(source)
    (directory / "realtime_speech_service.py").write_bytes(candidate)
    (directory / "Dockerfile").write_text(f"FROM {ROLLBACK_TAG}\nCOPY realtime_speech_service.py {APP_ROOT}{SOURCE_PATH}\n")
    target.update(
        envSha256=digest(env_bytes), composeHashes={path: digest(Path(path).read_bytes()) for path in target["composeFiles"]},
        composeRenderedSha256=config_digest(rendered), sourceBeforeSha256=digest(source),
        sourceAfterSha256=digest(candidate), methodAfterSha256=REPLACEMENT_NODE_SHA256,
        protectedSourceHashes=protected,
    )
    non_targets = {}
    for name in guards.run(["docker", "ps", "--format", "{{.Names}}"] ).stdout.decode().splitlines():
        if name != target["container"]:
            info = guards.inspect(name)
            non_targets[name] = {"id": info["Id"], "image": info["Image"], "started": info["State"]["StartedAt"]}
    guards.run(["docker", "tag", BASE_IMAGE, ROLLBACK_TAG])
    guards.run(["docker", "build", "--network=none", "-t", NEW_TAG, str(directory)], timeout=90)
    image = guards.inspect(NEW_TAG)
    verify_candidate_image(image, guards.inspect(BASE_IMAGE))
    target["newImage"] = image["Id"]
    verify_candidate_sources(target)
    manifest = {"targets": [target], "nonTargets": non_targets, "models": guards.models(target["container"])}
    guards.verify_non_targets(manifest)
    assert guards.inspect(target["container"])["Id"] == before["Id"], "runtime changed during preparation"
    (root / "prepared.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"prepared": True, "productionChanged": False, "image": image["Id"],
                      "sourceAfterSha256": target["sourceAfterSha256"], "filesChanged": 1}), flush=True)


def preflight(root: Path) -> tuple[dict, dict, dict]:
    assert not (root / "deployed.json").exists(), "deployment already recorded"
    manifest = json.loads((root / "prepared.json").read_text())
    assert len(manifest["targets"]) == 1, "unexpected deployment scope"
    target = manifest["targets"][0]
    assert target["service"] == "backend" and target["container"] == "compose-backend-1", "unexpected target"
    assert target["baseImage"] == BASE_IMAGE and target["sourceBeforeSha256"] == SOURCE_BEFORE_SHA256, "baseline manifest drift"
    assert target["methodAfterSha256"] == REPLACEMENT_NODE_SHA256, "method manifest drift"
    assert set(target["protectedSourceHashes"]) == set(SUPPORT_PATHS), "supporting source scope drift"
    assert target["protectedSourceHashes"]["services/session_service.py"] == SESSION_BEFORE_SHA256, "supporting session manifest drift"
    assert target["newTag"] == NEW_TAG and target["rollbackTag"] == ROLLBACK_TAG, "target image tag drift"
    before = json.loads((root / "backend/container-before.json").read_text())
    current = guards.inspect(target["container"])
    assert current["Id"] == before["Id"] == target["beforeId"] and current["Image"] == BASE_IMAGE, "container baseline drift"
    assert current["Config"] == before["Config"] and current["HostConfig"] == before["HostConfig"] and current["Mounts"] == before["Mounts"], "configuration baseline drift"
    assert current["State"]["Running"] and current["RestartCount"] == 0, "runtime no longer healthy"
    labels = current["Config"]["Labels"]
    assert target["project"] == labels["com.docker.compose.project"] and target["workingDir"] == labels["com.docker.compose.project.working_dir"], "compose labels drift"
    assert target["composeFiles"] == labels["com.docker.compose.project.config_files"].split(",") and target["envFile"] == labels["com.docker.compose.project.environment_file"], "compose paths drift"
    assert target["runtimeTag"] == current["Config"]["Image"] == "compose-backend", "running image tag drift"
    assert digest(Path(target["envFile"]).read_bytes()) == target["envSha256"] == digest((root / "backend/env.before").read_bytes()), "environment file drift"
    assert {path: digest(Path(path).read_bytes()) for path in target["composeFiles"]} == target["composeHashes"], "compose file drift"
    rendered = rendered_config(target)
    assert config_digest(rendered) == target["composeRenderedSha256"], "rendered compose drift"
    verify_compose(target, current, rendered)
    assert guards.inspect(NEW_TAG)["Id"] == target["newImage"], "candidate tag drift"
    assert guards.inspect(ROLLBACK_TAG)["Id"] == BASE_IMAGE, "rollback image drift"
    verify_candidate_image(guards.inspect(target["newImage"]), guards.inspect(BASE_IMAGE))
    candidate = (root / "backend/realtime_speech_service.py").read_bytes()
    original = (root / "backend/realtime_speech_service.before.py").read_bytes()
    assert digest(candidate) == target["sourceAfterSha256"] and digest(original) == SOURCE_BEFORE_SHA256, "prepared source drift"
    assert overlay(original.decode(), candidate.decode()).encode() == candidate, "candidate overlay scope drift"
    assert digest(runtime_source(target["container"], SOURCE_PATH)) == SOURCE_BEFORE_SHA256, "runtime source drift"
    assert {path: digest(runtime_source(target["container"], path)) for path in SUPPORT_PATHS} == target["protectedSourceHashes"], "supporting runtime source drift"
    verify_candidate_sources(target)
    verify_evidence(json.loads((root / "local-verification.json").read_text()),
                    json.loads((root / "candidate-verification.json").read_text()), target)
    assert guards.models(target["container"]) == manifest["models"], "model configuration drift"
    guards.verify_non_targets(manifest)
    return manifest, target, before


def verify_public() -> None:
    with urlopen("https://mianshiwen.cn/healthz", timeout=10) as response:
        assert response.status == 200 and json.loads(response.read())["data"]["status"] == "ok", "public health failed"
    with urlopen("https://mianshiwen.cn/api/v1/mock-interviews/capabilities", timeout=10) as response:
        assert response.status == 200 and json.loads(response.read())["data"]["enabled"] is True, "mock interview capability changed"


def deploy(root: Path, *, preflight_only: bool = False) -> None:
    manifest, target, before = preflight(root)
    guards.idle_gate()  # Ordinary interview, recent page/audio/answers, mock and material work.
    if preflight_only:
        print(json.dumps({"preflightPassed": True, "productionChanged": False}), flush=True)
        return
    guards.idle_gate()  # Repeat immediately before touching only the Backend tag.
    try:
        guards.run(["docker", "tag", target["newImage"], target["runtimeTag"]])
        compose(target)
        after = guards.wait_healthy(target)
        invariant(before, after, target)
        assert guards.models(target["container"]) == manifest["models"], "effective model configuration drift"
        assert digest(runtime_source(target["container"], SOURCE_PATH)) == target["sourceAfterSha256"], "effective heartbeat source drift"
        assert {path: digest(runtime_source(target["container"], path)) for path in SUPPORT_PATHS} == target["protectedSourceHashes"], "effective supporting source drift"
        guards.verify_non_targets(manifest)
        verify_public()
        result = {"deployed": True, "atMs": int(time.time() * 1000), "services": ["backend"],
                  "image": target["newImage"], "sourceAfterSha256": target["sourceAfterSha256"],
                  "rollbackImage": BASE_IMAGE, "modelsUnchanged": True, "environmentUnchanged": True,
                  "nonTargetsUnchanged": True}
        (root / "deployed.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except Exception as exc:
        rollback_ok = False
        try:
            guards.run(["docker", "tag", BASE_IMAGE, target["runtimeTag"]])
            compose(target)
            reverted = guards.wait_healthy(target)
            invariant(before, reverted, {"newImage": BASE_IMAGE})
            guards.verify_non_targets(manifest)
            rollback_ok = True
        except Exception:
            pass
        print(json.dumps({"deployed": False, "errorType": type(exc).__name__, "rollbackHealthy": rollback_ok}), flush=True)
        raise SystemExit(1) from None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "preflight", "deploy"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--local-source", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if args.action == "prepare":
        assert args.local_source is not None, "prepare requires --local-source"
        prepare(args.root, args.local_source)
    else:
        deploy(args.root, preflight_only=args.action == "preflight")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"completed": False, "errorType": type(exc).__name__,
                          "reason": str(exc) if isinstance(exc, AssertionError) else "inspect private host evidence"}), flush=True)
        raise SystemExit(1) from None
