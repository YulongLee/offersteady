"""Synthetic local input assembly regressions; no Docker, SSH or network."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("global136_assembly_test", HERE / "assemble_input.py")
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def h(value):
    return hashlib.sha256(value.encode()).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(A.json_bytes(value))


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    art = repo / "artifacts/global-performance-companion-20261102"
    audit = repo / "artifacts/global-performance-20261102"
    desktop = repo / "artifacts/global-companion-1.3.6-20261102"
    real_repo = HERE.parents[1]
    for name in A.SUPPORT_HASHES:
        rel = ("scripts/release_global_performance_companion_136.py" if name == "controller.py"
               else "scripts/release_support/global_performance_companion_136/" + name)
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(real_repo / rel, dest)
    put(art / "controller/support-source-fingerprints.json", A.SUPPORT_HASHES)
    controller = A.load_controller(repo / "scripts/release_global_performance_companion_136.py", tmp_path)
    backend_old = {p: h("old " + p) for p in controller.BACKEND_FILES | {controller.MANIFEST}}
    backend_old.update({f"apps/backend/app/synthetic_{i}.py": h(str(i)) for i in range(302 - len(backend_old))})
    manifest = {"version": 1, "generatedAtMs": 123456789, "entries": []}
    handoff = {"version": "1.3.6", "edition": "global", "readyForControlledUpload": True,
               "sourceInputCount": 94, "nonNativeDistCount": 27, "desktopTypecheckPassed": True, "artifacts": []}
    sources = {f"source/{i}.ts": h(str(i)) for i in range(94)}
    dist = {f"dist/{i}.js": h(str(i)) for i in range(27)}
    proofnames = {"mac-arm64": "independent-arm64-package.json", "mac-x64": "independent-x64-package.json",
                  "windows-x64": "independent-windows-package.json"}
    for prefix, (platform, arch) in A.TARGETS.items():
        mac = platform == "macos"
        name = (f"OfferSteady-Companion-Global-1.3.6-macOS-{arch}.dmg" if mac
                else "OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe")
        entry = {"id": prefix + "-136", "platform": platform, "architecture": arch,
                 "displayName": prefix, "version": "1.3.6", "minimumOs": "macOS 14.2+" if mac else "Windows 10 22H2+",
                 "fileName": name, "fileSizeBytes": 1000, "sha256": h(name), "signingStatus": "verified" if mac else "unsigned",
                 "notarized": mac, "protocolVersion": "2.0", "captureRuntime": "electron-single-owner" if mac else "electron-wasapi-loopback",
                 "developmentOnly": False, "capabilities": {"microphone": True, "screenCapture": True},
                 "distributionStatus": "published", "publishedAtMs": manifest["generatedAtMs"],
                 "objectKey": f"global-desktop-releases/{platform}/{arch}/1.3.6/{name}"}
        manifest["entries"].append(entry)
        put(art / (prefix + "-public-metadata.json"), {k: entry[k] for k in A.METADATA_FIELDS})
        artifact = {k: entry[k] for k in A.ARTIFACT_FIELDS}
        handoff["artifacts"].append({"platform": platform, "architecture": arch, **artifact})
        src = {"version": "1.3.6", "edition": "global", "runtime": A.RUNTIME, "sourceFiles": sources,
               "distFiles": {**dist, "native/runtime": h(prefix)}}
        srcpath = desktop / (prefix + "-source.json")
        put(srcpath, src)
        proof = {"platform": platform, "architecture": arch, "version": "1.3.6", "passed": True,
                 "globalRuntimeVerified": True, "frozenDistFilesVerified": 27,
                 "signingStatus": entry["signingStatus"], "notarized": mac,
                 "artifact": artifact, "sourceManifestSha256": A.digest(srcpath.read_bytes())}
        if mac:
            proof.update(actualSignatureAndAudioEntitlementsPassed=True, appAndDmgNotarizedStapledGatekeeperPassed=True,
                         nativeCompiledPayloadVerified=True, nativeGlobalIdentityAndEnglishPermissionsVerified=True,
                         machOComponentsArchitectureVerified=16)
            proof["artifact"]["payloadExactlyMatchesVerifiedApp"] = True
        else:
            proof.update(authenticode="unsigned-certificate-tables-zero", applicationArchitecture="x64",
                         installerPayloadExactlyMatchesPreparedPackage=True, outerAndInnerArchiveIntegrityPassed=True)
        put(desktop / (prefix + "-package.json"), proof)
        put(art / proofnames[prefix], proof)
        put(art / (prefix + "-oss.json"), {k: entry[k] for k in ("platform", "architecture", "version", *A.ARTIFACT_FIELDS, "objectKey")} |
            {"objectReadbackVerified": True, "contentType": "application/x-apple-diskimage" if mac else "application/vnd.microsoft.portable-executable",
             "publicManifestChanged": False, "latestPointerChanged": False})
    put(art / "global_desktop_release_manifest.json", manifest)
    put(desktop / "local-package-handoff.json", handoff)
    guard = repo / "tools/synthetic_guard.py"
    guard.parent.mkdir(parents=True, exist_ok=True)
    guard.write_text("# Synthetic artifact only\n")
    put(art / "independent-artifact-review.json", {"passed": True, "blockingFindings": [],
        "frozenFiles": {"tools/synthetic_guard.py": A.digest(guard.read_bytes())}})
    backend_new = {**backend_old, **{p: h("new " + p) for p in controller.BACKEND_FILES},
                   controller.HISTORY: h("history"), controller.MANIFEST: A.digest((art / "global_desktop_release_manifest.json").read_bytes())}
    backend_rb = {**backend_old, controller.HISTORY: h("history"), controller.MANIFEST: backend_new[controller.MANIFEST],
                  "apps/backend/app/modules/web.py": h("compatibility web")}
    html = ["index.html"] + [f"page{i}/index.html" for i in range(15)]
    web_old = {name: h("old " + name) for name in html + ["offersteady-global-build.json"]}
    web_old.update({f"assets/old{i}.js": h("oldjs " + str(i)) for i in range(235 - len(web_old))})
    mapping = {f"assets/old{i}.js": f"assets/new{i}.js" for i in range(16)}
    newjs = {name: h(name) for name in mapping.values()}
    changed = html + ["offersteady-global-build.json"]
    web_new = {**web_old, **{name: h("new " + name) for name in changed}, **newjs}
    web_rb = {**web_old, **newjs}
    for name, inv in (("backend", backend_old), ("web", web_old)):
        put(art / "baseline" / ("backend-runtime-manifest.json" if name == "backend" else "web-static-manifest.json"), inv)
    put(audit / "actual-inventories.before.json", {"backend": {"count": 302, "matchesSeal": True, "manifest": backend_old},
        "worker": {"count": 267, "matchesSeal": True, "manifest": {f"worker/{i}": h(str(i)) for i in range(267)}},
        "web": {"count": 235, "matchesSeal": True, "manifest": web_old}})
    signatures = {"offersteady-global-" + service + "-1": {"id": cid, "image": image, "startedAt": "2026-10-21T17:40:06.734602223Z"}
                  for service, (cid, image) in controller.BASES.items()}
    signatures.update({name: {"image": "sha256:" + h(name)} for name in controller.EXPECTED_NAMES - set(signatures)})
    signatures[controller.LEGACY_STOPPED_NAME] = deepcopy(controller.LEGACY_STOPPED_SIGNATURE)
    put(art / "baseline/component-signatures.before.json", signatures)
    put(art / "legacy-stopped-container-preservation.json", {"name": controller.LEGACY_STOPPED_NAME,
        "matchesOctober22FrozenNonTarget": True, "running": False, "actualSignature": controller.LEGACY_STOPPED_SIGNATURE})
    put(art / "private-probe-settings-summary.json", {"settingsFields": 379, "settingsSha256": h("settings"), "privateEnvironmentExported": False})
    before = {"openapi": "3.1.0", "paths": {controller.NEXT_PATH: {"get": {"parameters": [{"in": "path", "name": "device_id", "required": True}]}}}}
    before["paths"].update({"/synthetic/" + str(i): {"get": {}} for i in range(222)})
    after = deepcopy(before)
    after["paths"][controller.NEXT_PATH]["get"]["parameters"] += [{"in": "query", "name": n, "required": False} for n in ("sessionId", "requestId")]
    put(audit / "openapi.before.json", before)
    put(art / "baseline/openapi.json", before)
    put(art / "openapi-after.json", after)
    nginx = art / "baseline/nginx.conf"
    nginx.write_text("# Synthetic nginx baseline\n")
    put(art / "baseline/manifest.json", {"openapiPathCount": 223, "openapiCanonicalSha256": A.digest(A.canonical(before)),
        "artifacts": {"nginx.conf": A.digest(nginx.read_bytes())}})
    put(art / "public-boundary.before.json", {"/healthz": {"healthy": True}, "/login": {"status": 200},
        "/api/v1/web/state": {"releaseManifest": {"entries": [{"version": "1.3.5"} for _ in range(3)]}}})
    for name, invs in (("backend", (backend_new, backend_rb)), ("web", (web_new, web_rb))):
        evidence = {}
        for kind, inventory, count in (("new", invs[0], 9), ("rollback", invs[1], 3)):
            evidence[kind] = {"image": "sha256:" + h(name + kind), "inventory": inventory,
                              "configAndOriginalLayerPrefixPreserved": True}
            if name == "backend":
                evidence[kind]["probe"] = {"passed": True, "checks": ["synthetic_check_" + str(i) for i in range(count)], **A.PROBE_ZERO}
        put(art / (name + "-images.json"), evidence)
    put(art / "web/manifest.json", {"baselineInventory": web_old, "inventory": web_new, "rollbackInventory": web_rb,
        "moduleMapping": mapping, "modifiedOriginals": changed, "metadataOnly": True, "wholeSourceBuildUsed": False,
        "allOriginalImmutableBytesRetained": True, "nginxChanged": False})
    # An accidental future invocation of these surfaces must fail in all tests.
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("unexpected subprocess"))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("unexpected process"))
    return repo, art, desktop


def mutate(path, fn):
    value = json.loads(path.read_text())
    fn(value)
    put(path, value)


def test_complete_bundle_generates_exact_flat_payload_and_canonical_public_routes(bundle):
    repo, art, _ = bundle
    report = A.assemble(repo)
    assert report["passed"] is True and report["remoteActions"] == report["productionWrites"] == 0
    assert len(report["payloadFiles"]) == 16
    assert set(report["payloadFiles"]) == {*A.SUPPORT_HASHES, "input.json", "input/global_desktop_release_manifest.json",
                                           "input/openapi-before.json", "input/openapi-after.json"}
    plan = json.loads((art / "payload/input.json").read_text())
    assert len(plan["publicRoutes"]) == 34
    assert plan["publicRoutes"]["/page0"] == "page0/index.html"
    assert not any("index.html" in p for p in plan["publicRoutes"])
    assert len(plan["allowedBackend"]) == 10
    assert A.assemble(repo) == report  # Identical assembly is idempotent, never replaces bytes.


@pytest.mark.parametrize("relative", ["backend-images.json", "openapi-after.json", "windows-x64-oss.json",
                                      "legacy-stopped-container-preservation.json"])
def test_missing_final_evidence_never_creates_payload(bundle, relative):
    repo, art, _ = bundle
    (art / relative).unlink()
    with pytest.raises(A.AssemblyError, match="required_file_missing"):
        A.assemble(repo)
    assert not (art / "payload").exists()
    assert not list(art.glob(".assemble-*"))


@pytest.mark.parametrize("which", ["controller.py", "probe.py", "legacy-gates/check-idle.py"])
def test_every_frozen_support_byte_is_checked(bundle, which):
    repo, art, _ = bundle
    path = repo / ("scripts/release_global_performance_companion_136.py" if which == "controller.py"
                   else "scripts/release_support/global_performance_companion_136/" + which)
    path.write_text(path.read_text() + "\n# drift\n")
    with pytest.raises(A.AssemblyError, match="reviewed_support_source_drift"):
        A.assemble(repo)
    assert not (art / "payload").exists()


@pytest.mark.parametrize("relative,fn,reason", [
    ("legacy-stopped-container-preservation.json", lambda v: v.update(matchesOctober22FrozenNonTarget=False), "stopped_preservation"),
    ("baseline/component-signatures.before.json", lambda v: v["zealous_bhaskara"].update(running=True), "stopped_preservation"),
    ("backend-images.json", lambda v: v["new"].pop("configAndOriginalLayerPrefixPreserved"), "final_image_config"),
    ("backend-images.json", lambda v: v["rollback"]["probe"].update(providerCalls=1), "offline_probe"),
    ("mac-arm64-oss.json", lambda v: v.update(objectReadbackVerified=False), "object_readback"),
    ("mac-x64-oss.json", lambda v: v.update(sha256="f" * 64), "object_readback"),
    ("windows-x64-oss.json", lambda v: v.update(latestPointerChanged=True), "uploader_changed"),
    ("windows-x64-public-metadata.json", lambda v: v.update(signingStatus="verified"), "metadata_manifest"),
    ("independent-arm64-package.json", lambda v: v.update(appAndDmgNotarizedStapledGatekeeperPassed=False), "mac_proof"),
    ("independent-windows-package.json", lambda v: v.update(applicationArchitecture="arm64"), "windows_proof"),
    ("web/manifest.json", lambda v: v.update(wholeSourceBuildUsed=True), "web_image_and_review"),
    ("openapi-after.json", lambda v: v["paths"].update({"/unapproved": {"get": {}}}), "api_contract_changed"),
])
def test_mismatched_proof_or_scope_never_publishes_partial_payload(bundle, relative, fn, reason):
    repo, art, _ = bundle
    mutate(art / relative, fn)
    with pytest.raises(Exception, match=reason):
        A.assemble(repo)
    assert not (art / "payload").exists()
    assert not list(art.glob(".assemble-*"))


def test_cross_platform_source_drift_is_rejected_even_with_rebound_package_proof(bundle):
    repo, art, desktop = bundle
    source = desktop / "mac-x64-source.json"
    mutate(source, lambda v: v["sourceFiles"].update({"source/0.ts": "f" * 64}))
    mutate(desktop / "mac-x64-package.json", lambda v: v.update(sourceManifestSha256=A.digest(source.read_bytes())))
    with pytest.raises(A.AssemblyError, match="cross_platform_source"):
        A.assemble(repo)
    assert not (art / "payload").exists()


def test_existing_payload_is_preserved_on_different_valid_input(bundle):
    repo, art, _ = bundle
    A.assemble(repo)
    original = (art / "payload/input.json").read_bytes()
    mutate(art / "private-probe-settings-summary.json", lambda v: v.update(settingsSha256="a" * 64))
    with pytest.raises(A.AssemblyError, match="refusing_overwrite"):
        A.assemble(repo)
    assert (art / "payload/input.json").read_bytes() == original


def test_duplicate_json_keys_are_rejected(bundle):
    repo, art, _ = bundle
    (art / "windows-x64-oss.json").write_text('{"sha256":"a","sha256":"b"}')
    with pytest.raises(A.AssemblyError, match="duplicate_json_key"):
        A.assemble(repo)


def test_unknown_container_signature_cannot_expand_fixed_host_set(bundle):
    repo, art, _ = bundle
    mutate(art / "baseline/component-signatures.before.json", lambda v: v.update({"unknown-stopped-builder": {"image": "sha256:" + "f" * 64}}))
    with pytest.raises(A.AssemblyError, match="non_target_baseline_missing"):
        A.assemble(repo)
    assert not (art / "payload").exists()


def test_rebound_historical_proof_cannot_replace_the_fixed_stopped_identity(bundle):
    repo, art, _ = bundle
    mutate(art / "baseline/component-signatures.before.json", lambda v: v["zealous_bhaskara"].update(id="f" * 64))
    mutate(art / "legacy-stopped-container-preservation.json", lambda v: v["actualSignature"].update(id="f" * 64))
    with pytest.raises(A.AssemblyError, match="historical_stopped_baseline_changed"):
        A.assemble(repo)
    assert not (art / "payload").exists()


def test_linked_source_and_output_are_rejected(bundle, tmp_path):
    repo, art, _ = bundle
    linked = tmp_path / "linked"
    linked.symlink_to(art, target_is_directory=True)
    with pytest.raises(A.AssemblyError, match="source_parent_linked"):
        A.assemble(repo, artifact_root=linked, output=art / "payload")
    with pytest.raises(A.AssemblyError, match="output_path_linked"):
        A.assemble(repo, output=linked / "payload")
