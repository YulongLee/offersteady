"""Read only the existing container's safe config digest, never print values."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", default="/app/apps/backend/app")
    parser.add_argument("--expectations", required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("cn_probe", Path(__file__).with_name("candidate-probe.py"))
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    probe.install_guards()
    expectations = json.loads(Path(args.expectations).read_text())
    probe.require(expectations["runtimeConfigFields"] == list(probe.CONFIG_FIELDS), "config_field_list_mismatch")
    sys.path.insert(0, str(Path(args.app_root).resolve().parent))
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    probe.require(settings.product_edition == "cn" and settings.environment == "production", "production_edition_mismatch")
    probe.require(all(hasattr(settings, key) for key in probe.CONFIG_FIELDS), "runtime_config_field_missing")
    data = {key: getattr(settings, key) for key in probe.CONFIG_FIELDS}
    print(probe.digest(probe.canonical(data)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__, "privateValuesPrinted": False}))
        raise SystemExit(1) from None
