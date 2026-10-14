"""Start only the isolated local mock preview and open its compiled Mac app."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts/mock-local-20261015"
APP = ARTIFACTS / "macos/mac-arm64/面试稳 本地测试.app"
PG = "offersteady-mock-local-pg-20261015"
REDIS = "offersteady-mock-local-redis-20261015"


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def ensure_container(name: str, create_args: list[str]) -> None:
    found = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", name],
        text=True, capture_output=True,
    )
    if found.returncode:
        run("docker", "run", "-d", "--name", name, *create_args)
    elif found.stdout.strip() != "true":
        run("docker", "start", name)


def wait_until(check, seconds: float = 30) -> None:
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        if check():
            return
        sleep(0.25)
    raise RuntimeError("本地服务未能及时启动，请查看 artifacts/mock-local-20261015 中的日志。")


def backend_ready() -> bool:
    try:
        with urlopen("http://127.0.0.1:8015/healthz", timeout=1) as response:
            data = json.load(response)["data"]
        if data.get("version") != "mock-local-20261015.1" or data.get("environment") != "test":
            raise RuntimeError("8015 端口被其他服务占用，不能复用为本地测试后端。")
        return True
    except OSError:
        return False


def web_ready() -> bool:
    try:
        with urlopen("http://127.0.0.1:5175/app/mock-interviews", timeout=1) as response:
            body = response.read()
        if body != (ARTIFACTS / "web-dist/index.html").read_bytes():
            raise RuntimeError("5175 端口被其他网页占用，不能复用为本轮本地测试。")
        return True
    except OSError:
        return False


def start_background(args: list[str], log_name: str) -> None:
    with (ARTIFACTS / log_name).open("ab") as log:
        subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=log, start_new_session=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true")
    options = parser.parse_args()
    if not APP.is_dir() or not (ARTIFACTS / "web-dist/index.html").is_file():
        raise RuntimeError("本地编译产物不存在，请先完成本轮编译。")
    ARTIFACTS.mkdir(exist_ok=True, parents=True)
    ensure_container(PG, [
        "-e", "POSTGRES_USER=synthetic_local", "-e", "POSTGRES_PASSWORD=synthetic-local-only",
        "-e", "POSTGRES_DB=synthetic_mock_tests", "-p", "127.0.0.1:55445:5432",
        "--tmpfs", "/var/lib/postgresql/data:rw", "pgvector/pgvector:pg16",
    ])
    ensure_container(REDIS, ["-p", "127.0.0.1:56385:6379", "redis:7.4-alpine"])
    wait_until(lambda: subprocess.run(
        ["docker", "exec", PG, "pg_isready", "-U", "synthetic_local"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0)
    present = run("docker", "exec", PG, "psql", "-U", "synthetic_local", "-d", "postgres",
                  "-Atc", "SELECT 1 FROM pg_database WHERE datname='local_mock_preview'")
    if present != "1":
        run("docker", "exec", PG, "createdb", "-U", "synthetic_local", "local_mock_preview")
    if not backend_ready():
        start_background([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/local_mock_preview.py")], "backend.log")
        wait_until(backend_ready)
    if not web_ready():
        start_background([
            "npm", "run", "preview", "-w", "@offersteady/web", "--", "--mode", "development",
            "--port", "5175", "--outDir", "../../artifacts/mock-local-20261015/web-dist",
        ], "web.log")
        wait_until(web_ready)
    if not options.no_open:
        run("open", "-n", str(APP))
        run("open", "http://127.0.0.1:5175/app/mock-interviews")
    print("本地测试已就绪：http://127.0.0.1:5175/app/mock-interviews")
    print("合成手机号：19900000001；模拟验证码：123456。不会发送短信。")


if __name__ == "__main__":
    main()
