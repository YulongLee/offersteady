"""Offline local 1.3.6 package verification. Never builds, uploads or runs the app.

Mac verification uses the repository's existing strict signature/entitlement
verifier in its explicitly unnotarized mode. Archive payloads are read/extracted
only into new temporary directories. All product files remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = "1.3.6"
BUNDLE_ID = "com.offersteady.companion"
CONFIG_NAMES = {"local-test-runtime.json", "global-runtime-config.json", "global-runtime.json"}
CN_URLS = ("https://mianshiwen.cn/api/v1", "https://mianshiwen.cn/app")


class VerificationError(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise VerificationError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_native_digest(path):
    """Compare compiled payloads after removing signatures on disposable copies.

    Signing modifies a Mach-O's signature/linkedit bytes. The original unsigned
    build and final Developer ID binary cannot have the same whole-file hash.
    Neither original is edited and the real artifact is verified separately.
    """
    with tempfile.TemporaryDirectory(prefix="companion136-native-") as temporary:
        copy = Path(temporary) / "runtime"
        shutil.copyfile(path, copy)
        result = subprocess.run(["codesign", "--remove-signature", str(copy)], capture_output=True, timeout=30)
        require(result.returncode == 0 or b"is not signed at all" in result.stderr, "native_signature_normalization_failed")
        return digest(normalize_linkedit_vmsize(copy.read_bytes()))


def normalize_linkedit_vmsize(value):
    """Normalize signing-only LINKEDIT virtual allocation and 16-byte padding.

    Apple removal can leave virtual allocation and align the former signature
    start to 16 bytes. Add at most 15 zero bytes to both canonical forms rather
    than dropping original code/data. UUID, offsets, payload and all other
    commands remain compared. Unexpected trailing nonzero data is rejected.
    """
    data = bytearray(value)
    require(len(data) >= 32 and data[:4] == b"\xcf\xfa\xed\xfe", "native_macho64_required")
    cpu, commands, command_bytes = struct.unpack_from("<I", data, 4)[0], struct.unpack_from("<I", data, 16)[0], struct.unpack_from("<I", data, 20)[0]
    require(cpu in {0x100000C, 0x1000007} and 0 < commands <= 4096
            and 32 + command_bytes <= len(data), "native_load_commands_invalid")
    position, found, end = 32, 0, len(data)
    for _ in range(commands):
        require(position + 8 <= 32 + command_bytes, "native_load_commands_invalid")
        command, size = struct.unpack_from("<II", data, position)
        require(size >= 8 and position + size <= 32 + command_bytes, "native_load_commands_invalid")
        require(command != 0x1D, "native_signature_not_removed")
        if command == 0x19 and bytes(data[position + 8:position + 24]).rstrip(b"\0") == b"__LINKEDIT":
            require(size >= 72, "native_linkedit_invalid")
            fileoff, filesize = struct.unpack_from("<QQ", data, position + 40)
            require(filesize > 0 and 32 + command_bytes <= fileoff < len(data)
                    and fileoff + filesize <= len(data), "native_linkedit_invalid")
            end = ((fileoff + filesize + 15) // 16) * 16
            aligned_filesize = end - fileoff
            page = 0x4000 if cpu == 0x100000C else 0x1000
            struct.pack_into("<Q", data, position + 32, ((aligned_filesize + page - 1) // page) * page)
            struct.pack_into("<Q", data, position + 48, aligned_filesize)
            found += 1
        position += size
    require(found == 1 and position == 32 + command_bytes and not any(data[end:]), "native_linkedit_or_trailing_data_invalid")
    if end > len(data):
        data.extend(b"\0" * (end - len(data)))
    return bytes(data[:end])


def safe_name(value):
    value = unicodedata.normalize("NFC", value.replace("\\", "/"))
    path = PurePosixPath(value)
    require(bool(value) and not path.is_absolute() and ".." not in path.parts
            and not re.match(r"^[A-Za-z]:", value) and "\x00" not in value, "unsafe_archive_path")
    return value


def forbidden_name(name):
    parts = PurePosixPath(name).parts
    return any(part in CONFIG_NAMES or part in {".env", "runtime.env.private"}
               or part.endswith((".p8", ".p12", ".keychain", ".keychain-db")) for part in parts)


def safe_archive_link(name, target):
    """Archive links may stay within the extraction root, never escape it."""
    target = target.replace("\\", "/")
    require(bool(target) and "\x00" not in target and not PurePosixPath(target).is_absolute()
            and not re.match(r"^[A-Za-z]:", target), "unsafe_archive_link")
    parts = list(PurePosixPath(safe_name(name)).parent.parts)
    for part in PurePosixPath(target).parts:
        if part == "..":
            require(bool(parts), "unsafe_archive_link")
            parts.pop()
        elif part not in {".", ""}:
            parts.append(part)


def inventory(directory, *, allow_links=False):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "invalid_inventory_directory")
    result = {}
    for path in sorted(directory.rglob("*")):
        name = safe_name(path.relative_to(directory).as_posix())
        if path.is_symlink():
            require(allow_links, "unexpected_payload_link")
            target = os.readlink(path)
            # Electron framework links are relative and confined to the bundle.
            resolved = path.resolve()
            require(not Path(target).is_absolute() and resolved.is_relative_to(directory.resolve()), "unsafe_bundle_link")
            result[name] = "link:" + unicodedata.normalize("NFC", target)
        elif path.is_file():
            require(name not in result, "normalized_path_collision")
            result[name] = file_digest(path)
        else:
            require(path.is_dir(), "unsupported_payload_entry")
    return result


def source_inventory(root):
    root = Path(root)
    names = ["apps/desktop/package.json", "package-lock.json"]
    names.extend(p.relative_to(root).as_posix() for p in (root / "apps/desktop").glob("*.yml"))
    for folder, suffixes in (("apps/desktop/src", None),
                             ("apps/desktop/resources", None),
                             ("apps/desktop/scripts", {".mjs", ".mts"}),
                             ("apps/desktop/native/macos-capture", {".swift", ".plist"}),
                             ("apps/desktop/build", {".plist"})):
        require(not (root / folder).is_symlink(), "source_link_rejected")
        for path in (root / folder).rglob("*"):
            require(not path.is_symlink(), "source_link_rejected")
            if path.is_file() and "build" not in path.relative_to(root / folder).parts:
                if suffixes is None or path.suffix in suffixes:
                    names.append(path.relative_to(root).as_posix())
    result = {}
    for name in sorted(set(names)):
        path = root / name
        require(path.is_file() and not path.is_symlink(), "source_input_missing")
        result[name] = file_digest(path)
    return result


def assert_package_json(value):
    require(value.get("version") == VERSION and value.get("name") == "@offersteady/desktop"
            and value.get("main") == "dist/main/index.js", "app_version_or_entry_changed")


def assert_cn_defaults(main_bytes):
    text = main_bytes.decode("utf8")
    require(all(url in text for url in CN_URLS), "cn_default_urls_missing")


def freeze_dist(root, dist, output):
    root, dist = Path(root).resolve(), Path(dist).resolve()
    source = source_inventory(root)
    assert_package_json(json.loads((root / "apps/desktop/package.json").read_text()))
    files = inventory(dist)
    require("main/index.js" in files and "renderer/index.html" in files, "dist_entry_missing")
    require(not any(forbidden_name(n) for n in files), "runtime_override_or_secret_file")
    require(not any(name.endswith((".test.js", ".test.mjs", ".spec.js", ".spec.mjs")) for name in files), "runtime_test_file_rejected")
    assert_cn_defaults((dist / "main/index.js").read_bytes())
    value = {"schemaVersion": 1, "version": VERSION, "productEdition": "domestic",
             "sourceFiles": source, "distFiles": files, "sourceFileCount": len(source),
             "distFileCount": len(files), "configurationOverridesIncluded": False}
    native = dist / "native/macos-capture/OfferSteadyCaptureRuntime"
    if native.is_file():
        value["nativeCompiledPayloadSha256"] = canonical_native_digest(native)
        value["nativeSignatureNormalization"] = "codesign-remove-signature-copy-and-normalize-linkedit-vmsize"
        value["nativeSignatureAlignmentBytes"] = 16
    save(output, value)
    return value


def load_manifest(path, root):
    value = json.loads(Path(path).read_text())
    require(value.get("schemaVersion") == 1 and value.get("version") == VERSION
            and value.get("productEdition") == "domestic", "manifest_contract_invalid")
    require(value.get("sourceFiles") == source_inventory(root), "frozen_source_drift")
    require(isinstance(value.get("distFiles"), dict) and value["distFiles"], "dist_manifest_missing")
    for name, sha in value["distFiles"].items():
        safe_name(name)
        require(re.fullmatch(r"[0-9a-f]{64}", sha) and not forbidden_name(name), "dist_manifest_invalid")
    return value


def compare_dist(files, manifest):
    actual = {n.removeprefix("dist/"): h for n, h in files.items() if n.startswith("dist/")}
    expected = {n: h for n, h in manifest["distFiles"].items() if not n.startswith("native/")}
    require(actual == expected, "packaged_dist_drift")


def run(args, *, timeout=120):
    result = subprocess.run([str(a) for a in args], capture_output=True, timeout=timeout)
    require(result.returncode == 0, "verification_command_failed")
    return result.stdout


def pe_machine(path):
    with Path(path).open("rb") as f:
        header = f.read(64)
        require(len(header) == 64 and header[:2] == b"MZ", "invalid_pe_dos_header")
        offset = struct.unpack_from("<I", header, 0x3C)[0]
        require(64 <= offset <= 1024 * 1024, "invalid_pe_header_offset")
        f.seek(offset)
        coff = f.read(26)
        require(len(coff) == 26 and coff[:4] == b"PE\x00\x00", "invalid_pe_signature")
        machine, optional_magic = struct.unpack_from("<H", coff, 4)[0], struct.unpack_from("<H", coff, 24)[0]
        require((machine, optional_magic) in {(0x8664, 0x20B), (0x14C, 0x10B)}, "unsupported_pe_architecture")
        return "x64" if machine == 0x8664 else "x86"


def macho_architecture(path):
    with Path(path).open("rb") as f:
        header = f.read(8)
    require(len(header) == 8 and header[:4] == b"\xcf\xfa\xed\xfe", "expected_thin_macho64")
    cpu = struct.unpack_from("<I", header, 4)[0]
    require(cpu in {0x100000C, 0x1000007}, "unsupported_macho_architecture")
    return "arm64" if cpu == 0x100000C else "x64"


def read_asar(archive):
    data = json.loads(run(["node", Path(__file__).with_name("asar_inventory.mjs"), archive]))
    require(isinstance(data.get("files"), dict) and data["files"], "asar_inventory_missing")
    require(not any(forbidden_name(n) for n in data["files"]), "runtime_override_or_secret_file")
    return data


def check_mac(app, manifest, root, arch):
    app = Path(app).resolve()
    require(arch in {"arm64", "x64"} and app.suffix == ".app" and app.is_dir(), "mac_app_or_arch_invalid")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    require(info.get("CFBundleIdentifier") == BUNDLE_ID and info.get("CFBundleShortVersionString") == VERSION
            and info.get("CFBundleVersion") == VERSION, "mac_identity_or_version_changed")
    require(str(info.get("LSMinimumSystemVersion")) in {"14.2", "14.2.0"}, "mac_minimum_os_changed")
    executable = app / "Contents/MacOS" / info["CFBundleExecutable"]
    native = app / "Contents/Resources/app/native/macos-capture/OfferSteadyCaptureRuntime"
    require(macho_architecture(executable) == arch and macho_architecture(native) == arch, "mac_architecture_mismatch")
    native_key = "native/macos-capture/OfferSteadyCaptureRuntime"
    require(native_key in manifest["distFiles"] and manifest.get("nativeSignatureNormalization")
            == "codesign-remove-signature-copy-and-normalize-linkedit-vmsize"
            and canonical_native_digest(native) == manifest.get("nativeCompiledPayloadSha256"), "native_runtime_drift")
    resources = inventory(app / "Contents/Resources")
    require(not any(forbidden_name(n) for n in resources), "runtime_override_or_secret_file")
    archive = read_asar(app / "Contents/Resources/app.asar")
    assert_package_json(archive["packageJson"])
    compare_dist(archive["files"], manifest)
    # Existing verifier checks Developer ID/team, trusted timestamps, Hardened
    # Runtime and actual audio-input/JIT on main/Renderer/native signatures.
    run(["node", Path(root) / "apps/desktop/scripts/verify-release-mac.mjs", "--app", app,
         "--bundle-id", BUNDLE_ID, "--allow-unnotarized"], timeout=240)
    helpers = list((app / "Contents/Frameworks").glob("* Helper*.app/Contents/MacOS/*"))
    require(any("Helper (Renderer)" in str(p) for p in helpers), "renderer_helper_missing")
    require(all(macho_architecture(p) == arch for p in helpers if p.is_file()), "mac_helper_architecture_mismatch")
    return {"platform": "macos", "architecture": arch, "version": VERSION,
            "bundleId": BUNDLE_ID, "distFilesVerified": len([n for n in manifest["distFiles"] if not n.startswith("native/")]),
            "nativeRuntimeVerified": True, "actualSignatureAndAudioEntitlementsPassed": True,
            "notarized": False, "gatekeeper": "not-claimed-local-unnotarized", "helperCount": len(helpers)}


def compare_packaged_app(expected, actual):
    require(inventory(expected, allow_links=True) == inventory(actual, allow_links=True), "mac_archive_payload_drift")


def verify_mac_artifact(app, artifact):
    artifact = Path(artifact).resolve()
    if artifact.suffix.lower() == ".zip":
        with zipfile.ZipFile(artifact) as archive:
            require(archive.testzip() is None, "zip_crc_failed")
            for item in archive.infolist():
                safe_name(item.filename.rstrip("/"))
                if stat.S_ISLNK(item.external_attr >> 16):
                    safe_archive_link(item.filename, archive.read(item).decode("utf8"))
        with tempfile.TemporaryDirectory(prefix="companion136-zip-") as temporary:
            run(["ditto", "-x", "-k", artifact, temporary])
            apps = list(Path(temporary).glob("*.app")) + list(Path(temporary).glob("*/*.app"))
            apps = [p for p in apps if p.name == Path(app).name]
            require(len(apps) == 1, "zip_app_payload_ambiguous")
            compare_packaged_app(app, apps[0])
    elif artifact.suffix.lower() == ".dmg":
        run(["hdiutil", "verify", artifact])
        with tempfile.TemporaryDirectory(prefix="companion136-dmg-") as temporary:
            mount = Path(temporary) / "mount"
            mount.mkdir()
            attached = False
            try:
                run(["hdiutil", "attach", "-readonly", "-nobrowse", "-noautoopen", "-mountpoint", mount, artifact])
                attached = True
                candidate = mount / Path(app).name
                require(candidate.is_dir(), "dmg_app_payload_missing")
                compare_packaged_app(app, candidate)
            finally:
                if attached:
                    run(["hdiutil", "detach", mount])
    else:
        raise VerificationError("unsupported_mac_artifact")
    return {"fileName": artifact.name, "fileSizeBytes": artifact.stat().st_size,
            "sha256": file_digest(artifact), "payloadExactlyMatchesVerifiedApp": True}


def archive_listing(sevenzip, archive):
    text = run([sevenzip, "l", "-slt", archive]).decode("utf8", errors="replace")
    # Only member records after the separator, not the absolute outer path.
    require("----------" in text, "archive_member_listing_missing")
    members = text.split("----------", 1)[1]
    names = re.findall(r"^Path = (.+)$", members, re.M)
    require(names, "archive_is_empty")
    for name in names:
        safe_name(name.strip())
    require(not re.search(r"^(?:Symbolic Link|Hard Link) = .+", members, re.M), "archive_link_rejected")


def extract_checked(sevenzip, archive, destination):
    archive_listing(sevenzip, archive)
    run([sevenzip, "t", archive], timeout=180)
    run([sevenzip, "x", "-y", "-o" + str(destination), archive], timeout=180)
    inventory(destination)  # Reject links and special entries after extraction.


def check_windows(package, installer, manifest, sevenzip):
    package, installer, sevenzip = Path(package).resolve(), Path(installer).resolve(), Path(sevenzip).resolve()
    require(sevenzip.is_file() and os.access(sevenzip, os.X_OK), "sevenzip_executable_missing")
    files = inventory(package)
    require(not any(forbidden_name(n) for n in files), "runtime_override_or_secret_file")
    app_root = package / "resources/app"
    assert_package_json(json.loads((app_root / "package.json").read_text()))
    compare_dist({n.removeprefix("resources/app/"): h for n, h in files.items() if n.startswith("resources/app/")}, manifest)
    require(not (app_root / "dist/native").exists(), "mac_native_in_windows_payload")
    assert_cn_defaults((app_root / "dist/main/index.js").read_bytes())
    require(pe_machine(package / "OfferSteady.exe") == "x64", "windows_app_not_x64")
    installer_arch = pe_machine(installer)
    require(installer.stat().st_size >= 10 * 1024 * 1024, "windows_installer_too_small")
    with tempfile.TemporaryDirectory(prefix="companion136-nsis-") as temporary:
        outer, inner = Path(temporary) / "outer", Path(temporary) / "inner"
        outer.mkdir(); inner.mkdir()
        extract_checked(sevenzip, installer, outer)
        archives = list(outer.rglob("app-64.7z"))
        require(len(archives) == 1, "nsis_x64_payload_missing_or_ambiguous")
        extract_checked(sevenzip, archives[0], inner)
        executables = list(inner.rglob("OfferSteady.exe"))
        require(len(executables) == 1, "inner_app_executable_ambiguous")
        payload = executables[0].parent
        require(inventory(payload) == files, "windows_installer_payload_drift")
        require(pe_machine(executables[0]) == "x64", "inner_windows_app_not_x64")
    return {"platform": "windows", "architecture": "x64", "version": VERSION,
            "installerStubArchitecture": installer_arch, "packagedFilesVerified": len(files),
            "outerAndInnerArchiveIntegrityPassed": True, "innerPayloadExactlyMatchesPackage": True,
            "distFilesVerified": len([n for n in manifest["distFiles"] if not n.startswith("native/")]),
            "authenticode": "unsigned-not-claimed", "artifact": {"fileName": installer.name,
            "fileSizeBytes": installer.stat().st_size, "sha256": file_digest(installer)}}


def save(path, value):
    path = Path(path)
    require(not path.is_symlink(), "output_symlink_rejected")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze-dist")
    freeze.add_argument("--root", type=Path, default=ROOT)
    freeze.add_argument("--dist", type=Path, default=ROOT / "apps/desktop/dist")
    freeze.add_argument("--output", type=Path, required=True)
    for name in ("verify-mac", "verify-win"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=Path, default=ROOT)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
        if name == "verify-mac":
            p.add_argument("--app", type=Path, required=True)
            p.add_argument("--arch", choices=("arm64", "x64"), required=True)
            p.add_argument("--artifact", type=Path)
        else:
            p.add_argument("--package", type=Path, required=True)
            p.add_argument("--installer", type=Path, required=True)
            p.add_argument("--sevenzip", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze-dist":
        value = freeze_dist(args.root, args.dist, args.output)
        print(json.dumps({"passed": True, "version": VERSION, "sourceFiles": value["sourceFileCount"], "distFiles": value["distFileCount"]}))
        return
    manifest = load_manifest(args.manifest, args.root)
    if args.command == "verify-mac":
        value = check_mac(args.app, manifest, args.root, args.arch)
        if args.artifact:
            value["artifact"] = verify_mac_artifact(args.app, args.artifact)
    else:
        value = check_windows(args.package, args.installer, manifest, args.sevenzip)
    value.update(passed=True, sourceManifestSha256=file_digest(args.manifest),
                 providerOrAudioTestsPerformed=False, productionOrDistributionUpdated=False)
    save(args.output, value)
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        reason = str(exc) if isinstance(exc, VerificationError) else "package_verification_failed"
        print(json.dumps({"passed": False, "reason": reason}))
        raise SystemExit(1) from None
