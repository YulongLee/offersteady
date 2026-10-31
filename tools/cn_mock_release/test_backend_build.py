"""Release-overlay fail-closed tests; fixtures are wholly synthetic."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mock_backend_release_builder", HERE / "build_backend.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BackendOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.baseline_source = self.root / "baseline"
        self.output = self.root / "output"
        self.baseline = {"image": "sha256:" + "a" * 64, "python": "3.13.15",
            "settingsSha256": "b" * 64, "openapiSha256": "c" * 64, "httpPaths": 203,
            "dependencies": {f"synthetic-{i}": "1.0" for i in range(24)},
            "inventory": {f"apps/backend/app/synthetic_{i}.py": "d" * 64 for i in range(160)},
            "privateIgnoredField": "synthetic-private-marker"}
        self.baseline["inventory"]["apps/backend/pyproject.toml"] = "e" * 64
        frozen = {}
        for name in builder.CHANGED:
            data = b"SYNTHETIC_VERSION = 2\n"
            p = self.source / name
            p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
            frozen[name] = builder.sha(data)
            if name != builder.DIAGNOSTICS:
                old = b"SYNTHETIC_VERSION = 1\n"
                p = self.baseline_source / name
                p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(old)
                self.baseline["inventory"][name] = builder.sha(old)
        self.handoff = {"backend": frozen, "web": {"not-part-of-backend": "f" * 64}}

    def build(self):
        return builder.prepare(self.baseline, self.baseline_source, self.handoff, self.source, self.output)

    def test_exact_five_file_overlay_preserves_all_other_inputs_and_dependencies(self):
        manifest = self.build()
        self.assertEqual(set(manifest["changes"]), builder.CHANGED)
        self.assertEqual(set(manifest["inventory"]), set(self.baseline["inventory"]) | {builder.DIAGNOSTICS})
        for name, value in self.baseline["inventory"].items():
            if name not in builder.CHANGED:
                self.assertEqual(manifest["inventory"][name], value)
        self.assertEqual(manifest["dependencies"], self.baseline["dependencies"])
        dockerfile = (self.output / "backend/Dockerfile").read_text()
        self.assertEqual(dockerfile.splitlines()[0], "FROM " + builder.BASE_ALIAS)
        self.assertEqual(len([line for line in dockerfile.splitlines() if line.startswith("COPY ")]), 5)
        self.assertNotIn("RUN", dockerfile)
        self.assertNotIn("synthetic-private-marker", (self.output / "candidate-probe.py").read_text())
        self.assertEqual(manifest["probeSha256"], builder.sha((self.output / "candidate-probe.py").read_bytes()))

    def test_floating_image_rejected(self):
        self.baseline["image"] = "offersteady-backend:latest"
        with self.assertRaisesRegex(ValueError, "baseline_image_must_be_fixed"): self.build()

    def test_extra_source_in_handoff_rejected(self):
        self.handoff["backend"]["apps/backend/app/main.py"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "handoff_scope_changed"): self.build()

    def test_frozen_source_drift_rejected(self):
        (self.source / sorted(builder.CHANGED)[0]).write_text("DRIFT = True\n")
        with self.assertRaisesRegex(ValueError, "frozen_source_drift"): self.build()

    def test_original_source_drift_rejected(self):
        name = sorted(builder.CHANGED - {builder.DIAGNOSTICS})[0]
        (self.baseline_source / name).write_text("DRIFT = True\n")
        with self.assertRaisesRegex(ValueError, "baseline_source_drift"): self.build()

    def test_existing_diagnostics_baseline_rejected(self):
        self.baseline["inventory"][builder.DIAGNOSTICS] = "f" * 64
        with self.assertRaisesRegex(ValueError, "unexpected_mock_baseline"): self.build()

    def test_path_traversal_rejected(self):
        self.baseline["inventory"]["apps/backend/app/../../private.py"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "unsafe_inventory_path"): self.build()

    def test_missing_manifest_or_route_drift_rejected(self):
        for key, value in (("httpPaths", 202), ("settingsSha256", "private-value"), ("inventory", {})):
            with self.subTest(key=key):
                baseline = deepcopy(self.baseline); baseline[key] = value
                with self.assertRaises(ValueError): builder.baseline_contract(baseline)

    def test_symlink_source_rejected(self):
        path = self.source / sorted(builder.CHANGED)[0]
        outside = self.root / "outside.py"; outside.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink_source_rejected"): self.build()

    def test_nonempty_output_and_output_symlink_rejected(self):
        self.output.mkdir(); (self.output / "existing").write_text("preserve")
        with self.assertRaisesRegex(ValueError, "output_not_empty"): self.build()
        self.assertEqual((self.output / "existing").read_text(), "preserve")
        (self.output / "existing").unlink(); self.output.rmdir()
        outside = self.root / "other-output"; outside.mkdir()
        self.output.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "output_not_empty"): self.build()
        self.assertEqual(list(outside.iterdir()), [])

    def test_syntax_error_rejected_before_any_output(self):
        name = sorted(builder.CHANGED)[0]
        data = b"def invalid(\n"; (self.source / name).write_bytes(data)
        self.handoff["backend"][name] = builder.sha(data)
        with self.assertRaises(SyntaxError): self.build()
        self.assertFalse(self.output.exists())

    def test_guarded_actual_runtime_and_mock_provider_scenarios(self):
        # Separate process: audit hooks and guarded global APIs cannot leak into
        # the test runner or another local task.
        code = '''
import asyncio, importlib.util, json, sys
from app.core.config import Settings
s=importlib.util.spec_from_file_location("mock_probe_synthetic",sys.argv[1])
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
m.install_guards()
result=asyncio.run(m.scenarios(Settings(_env_file=None,environment="test",product_edition="cn")))
for worker in m.WORKERS: worker.join(timeout=3)
assert not any(worker.is_alive() for worker in m.WORKERS)
result["workerThreadsStarted"]=len(m.WORKERS)
print(json.dumps(result,sort_keys=True))
'''
        env = os.environ | {"PYTHONPATH": str(builder.ROOT / "apps/backend"), "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run([sys.executable, "-B", "-c", code, str(builder.ROOT / "scripts/release_support/cn_mock_20261101/candidate_probe.py")],
            env=env, capture_output=True, timeout=30, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value, {"syntheticRuntimeCases": 4, "syntheticProviderRequests": 3,
            "externalProviderRequests": 0, "diagnosticPrivacyPassed": True, "workerThreadsStarted": 4})


if __name__ == "__main__":
    unittest.main()
