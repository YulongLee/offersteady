"""Build minimal CN overlays; does not change running services or active env files."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path("/opt/offersteady/releases/20261008-cn-shared-text-v4-1-1")
SOURCE = "/app/apps/backend/app/services/document_processing.py"
OLD = '            "model": self.settings.chat_qwen_model,\n            "stream": False,\n            "temperature": 0.1,'
NEW = OLD.replace('            "temperature": 0.1,', '            "enable_thinking": False,\n            "temperature": 0.1,')


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def inspect(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name]))[0]


os.umask(0o077)
assert ROOT.is_dir() and not (ROOT / "prepared.json").exists(), "inspect existing preparation before retrying"
manifest = {"model": "deepseek-v4.1-flash", "targets": [], "nonTargets": {}}
names = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True).splitlines()
for name in names:
    if name.startswith("compose-") and name not in ("compose-backend-1", "compose-material-worker-1"):
        d = inspect(name)
        manifest["nonTargets"][name] = {"id": d["Id"], "image": d["Image"], "started": d["State"]["StartedAt"]}
for name, service in [("compose-backend-1", "backend"), ("compose-material-worker-1", "material-worker")]:
    d = inspect(name)
    assert d["State"]["Running"], "target is not running"
    labels = d["Config"]["Labels"]
    compose_file = labels["com.docker.compose.project.config_files"]
    assert "," not in compose_file, "unexpected compose overlay; review first"
    release = Path(labels["com.docker.compose.project.working_dir"]).parents[1]
    env_file = release / ".env.production"
    rendered = json.loads(subprocess.check_output(["docker", "compose", "-p", "compose", "--env-file", str(env_file),
                                                  "-f", compose_file, "config", "--format", "json"]))
    environment = dict(item.split("=", 1) for item in d["Config"]["Env"] if "=" in item)
    configured = rendered["services"][service]["environment"]
    assert all(str(value) == environment.get(key) for key, value in configured.items()), "environment drift; no preparation"
    assert environment["OFFERSTEADY_CHAT_QWEN_MODEL"] == "deepseek-v4-flash", "shared-model baseline drift"
    assert environment["OFFERSTEADY_CHAT_QUICK_MODEL"] == environment["OFFERSTEADY_CHAT_DETAIL_MODEL"] == manifest["model"]
    code = subprocess.check_output(["docker", "exec", name, "python", "-B", "-c",
                                    f"from pathlib import Path; print(Path({SOURCE!r}).read_text(),end='')"], text=True)
    assert code.count(OLD) == 1, "summary patch baseline drift"
    candidate = code.replace(OLD, NEW, 1)
    assert len(candidate.splitlines()) == len(code.splitlines()) + 1
    ast.parse(candidate)
    directory = ROOT / service
    directory.mkdir(mode=0o700, exist_ok=True)
    if (directory / "container-before.json").exists():
        saved = json.loads((directory / "container-before.json").read_text())
        assert saved["Id"] == d["Id"] and saved["Config"]["Env"] == d["Config"]["Env"], "preparation resume baseline drift"
        assert (directory / "env.before").read_bytes() == env_file.read_bytes(), "preparation resume environment drift"
    (directory / "document_processing.before.py").write_text(code)
    (directory / "document_processing.py").write_text(candidate)
    (directory / "container-before.json").write_text(json.dumps(d))
    (directory / "env.before").write_bytes(env_file.read_bytes())
    # This probe-only environment stays on the host and is never printed/downloaded.
    probe_env = environment.copy()
    probe_env["OFFERSTEADY_CHAT_QWEN_MODEL"] = manifest["model"]
    assert all("\n" not in value and "\r" not in value for value in probe_env.values())
    (directory / "probe.env").write_text("\n".join(f"{key}={value}" for key, value in probe_env.items()) + "\n")
    base_tag = f"offersteady-cn-base:shared-v4-1-20261008-{service}"
    new_tag = f"offersteady-cn-{service}:shared-v4-1-20261008-1"
    run(["docker", "tag", d["Image"], base_tag])
    (directory / "Dockerfile").write_text(f"FROM {base_tag}\nCOPY document_processing.py {SOURCE}\n")
    run(["docker", "build", "--network=none", "-t", new_tag, str(directory)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    candidate_image = inspect(new_tag)
    base_image = inspect(d["Image"])
    assert candidate_image["Config"] == base_image["Config"], "image runtime config drift"
    target = {"container": name, "service": service, "baseImage": d["Image"], "newImage": candidate_image["Id"],
              "newTag": new_tag, "runtimeTag": d["Config"]["Image"], "beforeId": d["Id"],
              "composeFile": compose_file, "release": str(release), "envFile": str(env_file),
              "envSha256": hashlib.sha256(env_file.read_bytes()).hexdigest(),
              "oldSourceSha256": hashlib.sha256(code.encode()).hexdigest(),
              "newSourceSha256": hashlib.sha256(candidate.encode()).hexdigest()}
    manifest["targets"].append(target)
    print(json.dumps({"prepared": service, "baseImage": d["Image"], "newImage": candidate_image["Id"], "summaryPatchLines": 1}), flush=True)
(ROOT / "prepared.json").write_text(json.dumps(manifest, indent=2))
print(json.dumps({"prepared": True, "services": 2, "runningServicesChanged": False}), flush=True)
