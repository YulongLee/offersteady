"""Assemble reviewed Global release inputs locally; no remote/process calls.

Missing final-image, complete-schema or object-readback evidence is an error.
The output is review material only. It never prepares or deploys a release.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


RELEASE = "20261102-global-performance-companion-136-1"
SUPPORT_HASHES = {
    "controller.py": "835b29c09a19db58bcdd52fff7b9f803b2851fe4e312eb49fb57c040a69c5ece",
    "base_helpers.py": "c3c51df28e828de704e2d83dc14220e07d8879ca002e711470f9040e77fc6cc0",
    "ownership_primitives.py": "30f6ca9d6c992df3853600a2a8e9f6e2d41dde13d7f22bced947dce6d625a3dd",
    "probe.py": "6a5c0c36fecc751bc55c390b8ac19305585de26769437ef5071ea9c6cfb27f31",
    "legacy-gates/check-idle.py": "3fb49a2991e86677e142fd17e8a24ef5af7de92802ee4050055a764be6574f1d",
    "legacy-gates/check-mock-idle.py": "daf3f0f8a6b63e5ebb9eab04fb4f948407b301234e1c1e3e24fbea658bbc81f4",
    "global_mock_companion_idle_gate.py": "898e496cae5638d8e56137fb6c50a92cd0e151a9d29707efd9fe09d9d51ae63f",
    "extra_idle_gate.py": "e48f0f6c7f8edd126eade0fafada21053f77d2713e55bbe6044aff3761669cbe",
    "active_work_gate.py": "917e010c7a2a9933915349cfbd2b5cd2bbcadced2ae9f3db367863e06eaae054",
    "resume_optimizer_idle_gate.py": "63b808d88e6b06abd792379130c43fe9c1aebf8ad564fe48dc908f2b41373d27",
    "global_financial_idle_gate.py": "929bf823000bedb46af46e0b2a5d8423e092e315afb15729fcfce798692a04a7",
    "backend_tcp_idle_gate.py": "4d102932c1076a89126144a0687d7519345c3fcf4a50cf960d6ff4eb3591d291",
}
TARGETS = {"mac-arm64": ("macos", "arm64"), "mac-x64": ("macos", "x64"),
           "windows-x64": ("windows", "x64")}
RUNTIME = {"productEdition": "global", "releaseChannel": "global",
           "webWorkspaceUrl": "https://offersteady.com/app", "apiBaseUrl": "https://offersteady.com/api/v1"}
ARTIFACT_FIELDS = ("fileName", "fileSizeBytes", "sha256")
METADATA_FIELDS = ("id", "platform", "architecture", "displayName", "version", "minimumOs",
                   *ARTIFACT_FIELDS, "signingStatus", "notarized", "protocolVersion",
                   "captureRuntime", "developmentOnly", "capabilities")
PROBE_ZERO = {"providerCalls": 0, "databaseWrites": 0, "workersStarted": 0,
              "lifespanStarted": False, "settingsUnchanged": True, "schemaAllowedDelta": True}


class AssemblyError(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise AssemblyError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


class Sources:
    """Capture each source once so later input construction uses the same bytes."""

    def __init__(self):
        self.files = {}

    def read(self, path):
        path = Path(path).absolute()
        require(path.is_file() and not path.is_symlink(), f"required_file_missing_or_linked:{path.name}")
        require(path.resolve() == path, f"source_parent_linked:{path.name}")
        if path not in self.files:
            self.files[path] = path.read_bytes()
        return self.files[path]

    def json(self, path):
        try:
            return json.loads(self.read(path), object_pairs_hook=unique_object)
        except (ValueError, UnicodeDecodeError):
            raise AssemblyError(f"invalid_json:{Path(path).name}") from None


def checked_probe(report, count):
    require(isinstance(report, dict) and report.get("passed") is True
            and all(type(report.get(k)) is type(v) and report.get(k) == v for k, v in PROBE_ZERO.items()),
            "final_backend_offline_probe_failed")
    checks = report.get("checks")
    require(isinstance(checks, list) and len(checks) == count and len(set(checks)) == count
            and all(isinstance(v, str) and v and all(c.islower() or c.isdigit() or c == "_" for c in v) for v in checks),
            "final_backend_probe_checks_incomplete")


def checked_images(value, backend=False):
    require(isinstance(value, dict) and set(value) == {"new", "rollback"}, "image_evidence_incomplete")
    for kind, report in value.items():
        require(isinstance(report, dict) and report.get("configAndOriginalLayerPrefixPreserved") is True,
                "final_image_config_or_layer_proof_missing")
        require(isinstance(report.get("inventory"), dict) and len(report["inventory"]) == (303 if backend else 251),
                "final_image_full_inventory_missing")
        if backend:
            checked_probe(report.get("probe"), 9 if kind == "new" else 3)
    return {"image": value["new"]["image"], "rollbackImage": value["rollback"]["image"],
            "inventory": value["new"]["inventory"], "rollbackInventory": value["rollback"]["inventory"]}


def public_routes(web_manifest, candidate):
    changed, mapping = web_manifest["modifiedOriginals"], web_manifest["moduleMapping"]
    require(len(changed) == 17 and len(set(changed)) == 17
            and sum(p.endswith(".html") for p in changed) == 16 and len(mapping) == 16,
            "web_reviewed_delta_counts_changed")
    require(set(candidate["inventory"]) - set(web_manifest["baselineInventory"]) == set(mapping.values())
            and web_manifest["inventory"] == candidate["inventory"]
            and web_manifest["rollbackInventory"] == candidate["rollbackInventory"]
            and web_manifest.get("metadataOnly") is True and web_manifest.get("wholeSourceBuildUsed") is False
            and web_manifest.get("allOriginalImmutableBytesRetained") is True and web_manifest.get("nginxChanged") is False,
            "web_image_and_review_manifest_differ")
    routes = {"/": "index.html", "/login": "index.html"}
    for name in sorted(set(changed) | set(mapping.values())):
        if name == "index.html":
            continue
        if name.endswith("/index.html"):
            routes["/" + name[:-len("/index.html")]] = name
        else:
            require(not name.endswith(".html"), "unreviewed_public_html_url")
            routes["/" + name] = name
    return routes


def package_evidence(sources, repo, artifact_root, desktop_root, manifest):
    handoff = sources.json(desktop_root / "local-package-handoff.json")
    require(handoff.get("version") == "1.3.6" and handoff.get("edition") == "global"
            and handoff.get("readyForControlledUpload") is True and handoff.get("sourceInputCount") == 94
            and handoff.get("nonNativeDistCount") == 27 and handoff.get("desktopTypecheckPassed") is True,
            "desktop_handoff_not_ready")
    require(isinstance(handoff.get("artifacts"), list) and len(handoff["artifacts"]) == 3,
            "desktop_handoff_targets_missing")
    review = sources.json(artifact_root / "independent-artifact-review.json")
    require(review.get("passed") is True and review.get("blockingFindings") == []
            and isinstance(review.get("frozenFiles"), dict) and review["frozenFiles"], "independent_artifact_review_failed")
    for name, checksum in review.get("frozenFiles", {}).items():
        require(digest(sources.read(repo / name)) == checksum, "reviewed_package_or_web_tool_drift")
    proof_names = {"mac-arm64": "independent-arm64-package.json", "mac-x64": "independent-x64-package.json",
                   "windows-x64": "independent-windows-package.json"}
    proofs, source_maps, dist_maps = [], [], []
    for prefix, target in TARGETS.items():
        entries = [e for e in manifest["entries"] if (e.get("platform"), e.get("architecture")) == target]
        require(len(entries) == 1, "desktop_manifest_target_missing_or_duplicate")
        entry = entries[0]
        metadata = sources.json(artifact_root / (prefix + "-public-metadata.json"))
        require(all(metadata.get(k) == entry.get(k) for k in METADATA_FIELDS), "desktop_metadata_manifest_mismatch")
        handed = [e for e in handoff["artifacts"] if (e.get("platform"), e.get("architecture")) == target]
        require(len(handed) == 1 and all(handed[0].get(k) == entry.get(k) for k in ARTIFACT_FIELDS),
                "desktop_handoff_artifact_mismatch")
        srcpath = desktop_root / (prefix + "-source.json")
        source = sources.json(srcpath)
        require(source.get("version") == "1.3.6" and source.get("edition") == "global" and source.get("runtime") == RUNTIME
                and isinstance(source.get("sourceFiles"), dict) and len(source["sourceFiles"]) == 94
                and isinstance(source.get("distFiles"), dict), "desktop_frozen_global_source_invalid")
        source_maps.append(source["sourceFiles"])
        dist_maps.append({k: v for k, v in source["distFiles"].items() if not k.startswith("native/")})
        for proof_path in (desktop_root / (prefix + "-package.json"), artifact_root / proof_names[prefix]):
            proof = sources.json(proof_path)
            require(proof.get("passed") is True and (proof.get("platform"), proof.get("architecture")) == target
                    and proof.get("version") == "1.3.6" and proof.get("globalRuntimeVerified") is True
                    and proof.get("frozenDistFilesVerified") == 27
                    and all(proof.get("artifact", {}).get(k) == entry.get(k) for k in ARTIFACT_FIELDS)
                    and all(proof.get(k) == entry.get(k) for k in ("signingStatus", "notarized")),
                    "desktop_package_proof_mismatch")
            if proof_path.parent == desktop_root:
                require(proof.get("sourceManifestSha256") == digest(sources.read(srcpath)), "desktop_source_proof_not_bound")
            if target[0] == "macos":
                require(all(proof.get(k) is True for k in ("actualSignatureAndAudioEntitlementsPassed",
                        "appAndDmgNotarizedStapledGatekeeperPassed", "nativeCompiledPayloadVerified",
                        "nativeGlobalIdentityAndEnglishPermissionsVerified"))
                        and proof.get("machOComponentsArchitectureVerified") == 16
                        and proof.get("artifact", {}).get("payloadExactlyMatchesVerifiedApp") is True,
                        "desktop_mac_proof_incomplete")
            else:
                require(proof.get("authenticode") == "unsigned-certificate-tables-zero"
                        and proof.get("applicationArchitecture") == "x64"
                        and proof.get("installerPayloadExactlyMatchesPreparedPackage") is True
                        and proof.get("outerAndInnerArchiveIntegrityPassed") is True, "desktop_windows_proof_incomplete")
        report = sources.json(artifact_root / (prefix + "-oss.json"))
        require(report.get("publicManifestChanged") is False and report.get("latestPointerChanged") is False,
                "uploader_changed_public_pointer")
        proofs.append(report)
    require(all(v == source_maps[0] for v in source_maps) and all(len(v) == 27 and v == dist_maps[0] for v in dist_maps),
            "desktop_cross_platform_source_or_dist_drift")
    return proofs


def load_controller(path, root):
    spec = importlib.util.spec_from_file_location("global136_local_input_validation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    # check_plan has no process/network path. Deny such calls if it ever changes.
    def forbidden(*args, **kwargs):
        raise AssemblyError("unexpected_external_action_during_local_assembly")
    module.run = module.H.run = module.P.run = forbidden
    module.inspect = module.H.inspect = module.P.inspect = forbidden
    module.urlopen = forbidden
    return module


def assemble(repo, artifact_root=None, desktop_root=None, openapi_after=None, output=None):
    repo = Path(repo).absolute()
    artifact_root = Path(artifact_root or repo / "artifacts/global-performance-companion-20261102").absolute()
    desktop_root = Path(desktop_root or repo / "artifacts/global-companion-1.3.6-20261102").absolute()
    output = Path(output or artifact_root / "payload").absolute()
    require(not output.is_symlink() and output.resolve() == output, "output_path_linked")
    sources = Sources()
    locked = sources.json(artifact_root / "controller/support-source-fingerprints.json")
    require(locked == SUPPORT_HASHES, "reviewed_support_lock_changed")
    blobs = {}
    for name, checksum in SUPPORT_HASHES.items():
        path = repo / ("scripts/release_global_performance_companion_136.py" if name == "controller.py"
                       else "scripts/release_support/global_performance_companion_136/" + name)
        blobs[name] = sources.read(path)
        require(digest(blobs[name]) == checksum, "reviewed_support_source_drift:" + name)
    signatures = sources.json(artifact_root / "baseline/component-signatures.before.json")
    legacy = sources.json(artifact_root / "legacy-stopped-container-preservation.json")
    require(legacy.get("name") == "zealous_bhaskara" and legacy.get("matchesOctober22FrozenNonTarget") is True
            and legacy.get("running") is False
            and legacy.get("actualSignature") == signatures.get("zealous_bhaskara")
            and legacy["actualSignature"].get("running") is False,
            "historical_stopped_preservation_proof_missing_or_changed")
    actual = sources.json(repo / "artifacts/global-performance-20261102/actual-inventories.before.json")
    settings = sources.json(artifact_root / "private-probe-settings-summary.json")
    require(settings.get("privateEnvironmentExported") is False, "private_environment_exported")
    baseline_seal = sources.json(artifact_root / "baseline/manifest.json")
    before = sources.json(repo / "artifacts/global-performance-20261102/openapi.before.json")
    require(before == sources.json(artifact_root / "baseline/openapi.json")
            and len(before.get("paths", {})) == baseline_seal.get("openapiPathCount") == 223
            and digest(canonical(before)) == baseline_seal.get("openapiCanonicalSha256"), "actual_schema_baseline_changed")
    after_path = Path(openapi_after or artifact_root / "openapi-after.json")
    after = sources.json(after_path)
    backend = checked_images(sources.json(artifact_root / "backend-images.json"), backend=True)
    web = checked_images(sources.json(artifact_root / "web-images.json"))
    web_manifest = sources.json(artifact_root / "web/manifest.json")
    manifest_path = artifact_root / "global_desktop_release_manifest.json"
    manifest = sources.json(manifest_path)
    proofs = package_evidence(sources, repo, artifact_root, desktop_root, manifest)
    boundary = sources.json(artifact_root / "public-boundary.before.json")
    old_manifest = boundary.get("/api/v1/web/state", {}).get("releaseManifest", {})
    require(boundary.get("/healthz", {}).get("healthy") is True and boundary.get("/login", {}).get("status") == 200
            and len(old_manifest.get("entries", [])) == 3 and all(e.get("version") == "1.3.5" for e in old_manifest["entries"]),
            "public_actual_baseline_missing")
    require(actual.get("worker", {}).get("count") == 267 and actual["worker"].get("matchesSeal") is True,
            "independent_worker_baseline_missing")
    baselines = {}
    for service in ("backend", "web"):
        signature = signatures.get("offersteady-global-" + service + "-1", {})
        inv = actual.get(service, {})
        require(inv.get("matchesSeal") is True and inv.get("count") == len(inv.get("manifest", {})), "actual_inventory_not_sealed")
        baselines[service] = {k: signature.get(k) for k in ("id", "image", "startedAt")}
        baselines[service].update(signature=signature, inventory=inv["manifest"])
    baselines["backend"].update(settingsSha256=settings.get("settingsSha256"), settingsFields=settings.get("settingsFields"))
    baselines["web"]["nginxSha256"] = digest(sources.read(artifact_root / "baseline/nginx.conf"))
    require(baselines["web"]["nginxSha256"] == baseline_seal.get("artifacts", {}).get("nginx.conf"), "baseline_nginx_changed")
    for service, filename in (("backend", "backend-runtime-manifest.json"), ("web", "web-static-manifest.json")):
        require(baselines[service]["inventory"] == sources.json(artifact_root / "baseline" / filename), "actual_inventory_and_seal_differ")
    require(baselines["web"]["inventory"] == web_manifest["baselineInventory"], "web_actual_baseline_differ")
    allowed = {name: checksum for name, checksum in backend["inventory"].items()
               if checksum != baselines["backend"]["inventory"].get(name)}
    blobs["input/global_desktop_release_manifest.json"] = sources.read(manifest_path)
    blobs["input/openapi-before.json"] = sources.read(repo / "artifacts/global-performance-20261102/openapi.before.json")
    blobs["input/openapi-after.json"] = sources.read(after_path)
    plan = {"releaseId": RELEASE, "baselines": baselines, "candidates": {"backend": backend, "web": web},
            "nonTargets": {k: v for k, v in signatures.items() if k not in {"offersteady-global-backend-1", "offersteady-global-web-1"}},
            "allowedBackend": allowed, "allowedWebChanged": sorted(web_manifest["modifiedOriginals"]),
            "globalManifest": {"path": "input/global_desktop_release_manifest.json", "sha256": digest(sources.read(manifest_path))},
            "objectsReadback": proofs, "supportFiles": SUPPORT_HASHES, "publicRoutes": public_routes(web_manifest, web)}
    for key, schema, name in (("openapiBefore", before, "openapi-before.json"), ("openapiAfter", after, "openapi-after.json")):
        plan[key] = {"path": "input/" + name, "schemaSha256": digest(canonical(schema)), "pathCount": len(schema.get("paths", {}))}
    blobs["input.json"] = json_bytes(plan)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".assemble-global136-", dir=output.parent))
    try:
        for name, data in blobs.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        controller = load_controller(stage / "controller.py", stage)
        try:
            require(controller.check_plan() == plan, "controller_input_roundtrip_changed")
        except controller.GuardError as error:
            raise AssemblyError(str(error)) from None
        # Import validation may create pycache. It is never shipped to the server.
        for path in stage.rglob("__pycache__"):
            shutil.rmtree(path)
        fingerprint = {name: digest(data) for name, data in sorted(blobs.items())}
        if output.exists():
            require(output.is_dir() and {str(p.relative_to(output)): digest(p.read_bytes()) for p in output.rglob("*") if p.is_file()} == fingerprint
                    and not any(p.is_symlink() for p in output.rglob("*")), "existing_payload_differs_refusing_overwrite")
        else:
            os.rename(stage, output)
        return {"passed": True, "releaseId": RELEASE, "inputSha256": digest(blobs["input.json"]),
                "payloadFiles": fingerprint, "publicRoutes": len(plan["publicRoutes"]),
                "sourceEvidence": {str(p.relative_to(repo)) if p.is_relative_to(repo) else p.name: digest(data)
                                   for p, data in sorted(sources.files.items())},
                "remoteActions": 0, "productionWrites": 0, "privateConfigurationCopied": False}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--desktop-root", type=Path)
    parser.add_argument("--openapi-after", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = assemble(args.repo, args.artifact_root, args.desktop_root, args.openapi_after, args.output)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_bytes(json_bytes(report))
        print(json.dumps({k: v for k, v in report.items() if k not in {"payloadFiles", "sourceEvidence"}}, sort_keys=True))
        return 0
    except (AssemblyError, KeyError, TypeError, OSError) as error:
        # Files are public/evidence only. Do not print full JSON or exception traces.
        reason = str(error) if isinstance(error, AssemblyError) else "assembly_input_shape_or_io_error"
        print(json.dumps({"passed": False, "reason": reason, "remoteActions": 0, "productionWrites": 0}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
