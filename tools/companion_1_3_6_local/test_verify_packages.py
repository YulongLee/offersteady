"""Synthetic package checks; never build/run the companion or contact services."""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("companion136_verifier", Path(__file__).with_name("verify_packages.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def pe(path, machine=0x8664):
    value = bytearray(90)
    value[:2] = b"MZ"
    struct.pack_into("<I", value, 0x3C, 64)
    value[64:68] = b"PE\x00\x00"
    struct.pack_into("<H", value, 68, machine)
    struct.pack_into("<H", value, 88, 0x20B if machine == 0x8664 else 0x10B)
    Path(path).write_bytes(value)


def macho(path, cpu=0x100000C):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xcf\xfa\xed\xfe" + struct.pack("<I", cpu) + b"synthetic")


def stripped_macho(vmsize=0x4000):
    data = bytearray(112)
    data[:8] = b"\xcf\xfa\xed\xfe" + struct.pack("<I", 0x100000C)
    struct.pack_into("<II", data, 16, 1, 72)
    struct.pack_into("<II", data, 32, 0x19, 72)
    data[40:56] = b"__LINKEDIT".ljust(16, b"\0")
    struct.pack_into("<QQQ", data, 64, vmsize, 104, 8)
    data[104:] = b"payload!"
    return bytes(data)


def fixture(root):
    (root / "apps/desktop/src").mkdir(parents=True)
    (root / "apps/desktop/src/test.ts").write_text("// synthetic fixture")
    (root / "apps/desktop/package.json").write_text(json.dumps({"name": "@offersteady/desktop", "version": "1.3.6", "main": "dist/main/index.js"}))
    (root / "package-lock.json").write_text("{}")
    dist = root / "apps/desktop/dist"
    (dist / "main").mkdir(parents=True)
    (dist / "renderer").mkdir()
    (dist / "main/index.js").write_text("// synthetic " + " ".join(M.CN_URLS))
    (dist / "renderer/index.html").write_text("<div>Synthetic</div>")
    return dist


class ManifestTests(unittest.TestCase):
    def test_runtime_compilation_cannot_ship_a_regression_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); dist = fixture(root)
            (dist / "main/accidental.test.js").write_text("// synthetic regression, not product runtime")
            with self.assertRaisesRegex(M.VerificationError, "runtime_test_file_rejected"):
                M.freeze_dist(root, dist, root / "manifest.json")

    def test_frozen_source_and_dist_are_complete_then_reject_late_edits(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); dist = fixture(root); out = root / "frozen.json"
            value = M.freeze_dist(root, dist, out)
            self.assertEqual(value["distFileCount"], 2)
            self.assertEqual(M.load_manifest(out, root), value)
            (root / "apps/desktop/src/test.ts").write_text("changed")
            with self.assertRaisesRegex(M.VerificationError, "frozen_source_drift"):
                M.load_manifest(out, root)

    def test_version_defaults_and_configuration_override_fail_closed(self):
        for mutation, reason in (("version", "app_version_or_entry_changed"),
                                 ("defaults", "cn_default_urls_missing"),
                                 ("override", "runtime_override_or_secret_file")):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root = Path(d); dist = fixture(root)
                if mutation == "version":
                    p = root / "apps/desktop/package.json"
                    p.write_text(p.read_text().replace("1.3.6", "1.3.5"))
                elif mutation == "defaults":
                    (dist / "main/index.js").write_text("// wrong target")
                else:
                    (dist / "local-test-runtime.json").write_text("{}")
                with self.assertRaisesRegex(M.VerificationError, reason):
                    M.freeze_dist(root, dist, root / "out.json")

    def test_native_signatures_are_normalized_only_on_temporary_copies(self):
        with tempfile.TemporaryDirectory() as d:
            native = Path(d) / "native"
            native.write_bytes(b"synthetic-code+signature")
            def remove(args, **kwargs):
                copied = Path(args[-1]); self.assertNotEqual(copied, native)
                copied.write_bytes(stripped_macho())
                return subprocess.CompletedProcess(args, 0, b"", b"")
            with patch.object(M.subprocess, "run", side_effect=remove):
                self.assertEqual(M.canonical_native_digest(native), M.digest(stripped_macho()))
            self.assertEqual(native.read_bytes(), b"synthetic-code+signature")

    def test_only_derived_linkedit_allocation_and_zero_padding_are_normalized(self):
        self.assertEqual(M.normalize_linkedit_vmsize(stripped_macho(0x8000) + b"\0" * 16), stripped_macho())
        changed = bytearray(stripped_macho()); changed[105] ^= 1
        self.assertNotEqual(M.normalize_linkedit_vmsize(changed), stripped_macho())
        with self.assertRaises(M.VerificationError): M.normalize_linkedit_vmsize(stripped_macho() + b"unexpected")

    def test_intel_signature_offset_alignment_adds_only_known_zero_padding(self):
        source = bytearray(stripped_macho())
        # An unsigned Intel segment can end eight bytes before the next 16-byte
        # signature boundary; codesign expands only filesize/vmsize and zeros.
        struct.pack_into("<I", source, 4, 0x1000007)
        struct.pack_into("<Q", source, 72, 112)  # segment fileoff
        source.extend(b"payload!")
        signed_removed = bytearray(source)
        struct.pack_into("<Q", signed_removed, 64, 0x8000)
        struct.pack_into("<Q", signed_removed, 80, 16)  # segment filesize
        signed_removed.extend(b"\0" * 8)
        self.assertEqual(M.normalize_linkedit_vmsize(source), M.normalize_linkedit_vmsize(signed_removed))
        changed = bytearray(signed_removed); changed[113] ^= 1
        self.assertNotEqual(M.normalize_linkedit_vmsize(source), M.normalize_linkedit_vmsize(changed))

    @unittest.skipUnless(sys.platform == "darwin" and shutil.which("clang") and shutil.which("codesign"), "requires local Apple binary tools")
    def test_real_synthetic_macho_resigning_does_not_change_compiled_payload(self):
        with tempfile.TemporaryDirectory() as d:
            for target in (None, "x86_64-apple-macos14.2"):
                with self.subTest(target=target):
                    binary = Path(d) / "synthetic-runtime"
                    args = ["clang", "-x", "c", "-", "-o", str(binary)]
                    if target: args.extend(["-target", target])
                    c = subprocess.run(args, input=b"int main(void){return 0;}\n", capture_output=True, timeout=60)
                    self.assertEqual(c.returncode, 0)
                    before = M.canonical_native_digest(binary)
                    c = subprocess.run(["codesign", "--force", "--sign", "-", "--timestamp=none", "--entitlements", str(M.ROOT / "apps/desktop/build/entitlements.mac.release.plist"), str(binary)], capture_output=True, timeout=30)
                    self.assertEqual(c.returncode, 0)
                    self.assertEqual(M.canonical_native_digest(binary), before)

    def test_dist_cannot_add_delete_or_alter_files(self):
        manifest = {"distFiles": {"main/index.js": "a" * 64, "renderer/index.html": "b" * 64,
                                  "native/macos-capture/OfferSteadyCaptureRuntime": "c" * 64}}
        files = {"dist/main/index.js": "a" * 64, "dist/renderer/index.html": "b" * 64, "package.json": "d" * 64}
        M.compare_dist(files, manifest)
        for changed in (files | {"dist/extra.js": "e" * 64}, files | {"dist/main/index.js": "e" * 64},
                        {k: v for k, v in files.items() if k != "dist/main/index.js"}):
            with self.subTest(changed=changed), self.assertRaisesRegex(M.VerificationError, "packaged_dist_drift"):
                M.compare_dist(changed, manifest)


class PathAndBinaryTests(unittest.TestCase):
    def test_rejects_archive_traversal_absolute_windows_and_nul(self):
        for name in ("../secret", "dir/../../secret", "/secret", "C:\\secret", "x\x00y", ""):
            with self.subTest(name=name), self.assertRaises(M.VerificationError):
                M.safe_name(name)
        self.assertEqual(M.safe_name("$PLUGINSDIR/app-64.7z"), "$PLUGINSDIR/app-64.7z")

    def test_payload_links_and_out_of_bundle_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "root"; root.mkdir(); (root / "file").write_text("synthetic")
            (root / "link").symlink_to("file")
            with self.assertRaisesRegex(M.VerificationError, "unexpected_payload_link"):
                M.inventory(root)
            self.assertEqual(M.inventory(root, allow_links=True)["link"], "link:file")
            (root / "link").unlink(); (root / "link").symlink_to("../outside")
            with self.assertRaisesRegex(M.VerificationError, "unsafe_bundle_link"):
                M.inventory(root, allow_links=True)

    def test_actual_pe_machine_and_optional_header_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "app.exe"
            pe(p); self.assertEqual(M.pe_machine(p), "x64")
            pe(p, 0x14C); self.assertEqual(M.pe_machine(p), "x86")
            p.write_bytes(b"MZ" + b"x" * 100)
            with self.assertRaises(M.VerificationError): M.pe_machine(p)
            pe(p); value = bytearray(p.read_bytes()); value[64:68] = b"fake"; p.write_bytes(value)
            with self.assertRaisesRegex(M.VerificationError, "invalid_pe_signature"): M.pe_machine(p)

    def test_macho_arm_and_intel_are_not_interchangeable(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "app"; macho(p); self.assertEqual(M.macho_architecture(p), "arm64")
            macho(p, 0x1000007); self.assertEqual(M.macho_architecture(p), "x64")
            p.write_bytes(b"not-macho")
            with self.assertRaises(M.VerificationError): M.macho_architecture(p)

    def test_archive_listing_is_validated_before_extraction(self):
        for name in ("../secret", "/absolute", "C:\\secret"):
            with patch.object(M, "run", return_value=f"Path = /outer.exe\n----------\nPath = {name}\n".encode()):
                with self.assertRaisesRegex(M.VerificationError, "unsafe_archive_path"):
                    M.archive_listing("7zz", "outer.exe")
        with patch.object(M, "run", return_value=b"Path = /outer.exe\n----------\nPath = $PLUGINSDIR/app-64.7z\n"):
            M.archive_listing("7zz", "outer.exe")
        with patch.object(M, "run", return_value=b"----------\nPath = link\nSymbolic Link = target\n"):
            with self.assertRaisesRegex(M.VerificationError, "archive_link_rejected"):
                M.archive_listing("7zz", "outer.exe")

    def test_config_and_credentials_names_are_rejected(self):
        for n in ("app/local-test-runtime.json", "global-runtime-config.json", "app/.env", "AuthKey_test.p8", "test.keychain-db"):
            self.assertTrue(M.forbidden_name(n), n)
        self.assertFalse(M.forbidden_name("dist/main/local-test-runtime.js"))


class PackageTests(unittest.TestCase):
    def test_nsis_inner_payload_must_equal_complete_prepackaged_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); dist = fixture(root)
            manifest = M.freeze_dist(root, dist, root / "manifest.json")
            package = root / "package"; app = package / "resources/app"; app.mkdir(parents=True)
            shutil.copytree(dist, app / "dist")
            shutil.copyfile(root / "apps/desktop/package.json", app / "package.json")
            pe(package / "OfferSteady.exe")
            installer = root / "setup.exe"; pe(installer, 0x14C)
            with installer.open("ab") as stream: stream.truncate(10 * 1024 * 1024)
            seven = root / "7zz"; seven.write_text("synthetic"); seven.chmod(0o700)
            mutate = False
            def extract(_seven, archive, destination):
                if Path(archive).resolve() == installer.resolve():
                    (destination / "app-64.7z").write_text("synthetic")
                else:
                    shutil.copytree(package, destination / "app", dirs_exist_ok=True)
                    if mutate: (destination / "app/resources/app/dist/main/index.js").write_text("bad")
            with patch.object(M, "extract_checked", side_effect=extract):
                value = M.check_windows(package, installer, manifest, seven)
                self.assertTrue(value["innerPayloadExactlyMatchesPackage"])
                self.assertEqual(value["installerStubArchitecture"], "x86")
                mutate = True
                with self.assertRaisesRegex(M.VerificationError, "windows_installer_payload_drift"):
                    M.check_windows(package, installer, manifest, seven)

    def test_mac_bundle_checks_identity_arch_dist_and_actual_verifier_invocation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); dist = fixture(root); manifest = M.freeze_dist(root, dist, root / "manifest.json")
            app = root / "Synthetic.app"; resources = app / "Contents/Resources"; resources.mkdir(parents=True)
            info = {"CFBundleIdentifier": M.BUNDLE_ID, "CFBundleVersion": M.VERSION,
                    "CFBundleShortVersionString": M.VERSION, "CFBundleExecutable": "Synthetic", "LSMinimumSystemVersion": "14.2.0"}
            (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
            macho(app / "Contents/MacOS/Synthetic")
            native = resources / "app/native/macos-capture/OfferSteadyCaptureRuntime"; macho(native)
            helper = app / "Contents/Frameworks/Synthetic Helper (Renderer).app/Contents/MacOS/Synthetic Helper (Renderer)"; macho(helper)
            manifest["distFiles"]["native/macos-capture/OfferSteadyCaptureRuntime"] = M.file_digest(native)
            manifest["nativeSignatureNormalization"] = "codesign-remove-signature-copy-and-normalize-linkedit-vmsize"
            manifest["nativeCompiledPayloadSha256"] = M.file_digest(native)
            archive = {"files": {"dist/" + k: v for k, v in manifest["distFiles"].items() if not k.startswith("native/")},
                       "packageJson": json.loads((root / "apps/desktop/package.json").read_text())}
            with ExitStack() as stack:
                stack.enter_context(patch.object(M, "read_asar", return_value=archive))
                calls = stack.enter_context(patch.object(M, "run", return_value=b""))
                stack.enter_context(patch.object(M, "canonical_native_digest", side_effect=M.file_digest))
                value = M.check_mac(app, manifest, root, "arm64")
                self.assertTrue(value["actualSignatureAndAudioEntitlementsPassed"])
                self.assertIn("--allow-unnotarized", calls.call_args.args[0])
                with self.assertRaisesRegex(M.VerificationError, "mac_architecture_mismatch"):
                    M.check_mac(app, manifest, root, "x64")
                info["CFBundleIdentifier"] = "wrong"; (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
                with self.assertRaisesRegex(M.VerificationError, "mac_identity_or_version_changed"):
                    M.check_mac(app, manifest, root, "arm64")

    def test_zip_bad_crc_or_traversal_is_never_extracted(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "app.zip"
            with zipfile.ZipFile(archive, "w") as z: z.writestr("../outside", "synthetic")
            with patch.object(M, "run") as call:
                with self.assertRaisesRegex(M.VerificationError, "unsafe_archive_path"):
                    M.verify_mac_artifact(Path(d) / "App.app", archive)
                call.assert_not_called()

    def test_zip_link_escape_is_rejected_before_ditto(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "app.zip"
            for target in ("/outside", "../../outside", "C:\\outside"):
                with self.subTest(target=target), zipfile.ZipFile(archive, "w") as z:
                    entry = zipfile.ZipInfo("App.app/link")
                    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                    z.writestr(entry, target)
                with patch.object(M, "run") as call:
                    with self.assertRaisesRegex(M.VerificationError, "unsafe_archive_link"):
                        M.verify_mac_artifact(Path(d) / "App.app", archive)
                    call.assert_not_called()
            M.safe_archive_link("App.app/Framework/Versions/Current", "A")

    def test_mac_archive_byte_comparison_includes_framework_links(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a", Path(d) / "b"; a.mkdir(); b.mkdir()
            for p in (a, b): (p / "file").write_text("synthetic"); (p / "link").symlink_to("file")
            M.compare_packaged_app(a, b)
            (b / "file").write_text("changed")
            with self.assertRaisesRegex(M.VerificationError, "mac_archive_payload_drift"):
                M.compare_packaged_app(a, b)

    def test_asar_reader_reads_bytes_without_executing_product_code(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root / "app"; source.mkdir()
            (source / "package.json").write_text(json.dumps({"name": "synthetic", "version": "1.3.6"}))
            (source / "throw.js").write_text("throw new Error('must-not-execute');")
            archive = root / "app.asar"
            command = "const a=require('@electron/asar');a.createPackage(process.argv[1],process.argv[2]);"
            result = subprocess.run(["node", "-e", command, str(source), str(archive)], capture_output=True, cwd=M.ROOT)
            self.assertEqual(result.returncode, 0, result.stderr)
            read = M.read_asar(archive)
            self.assertEqual(read["files"]["throw.js"], M.file_digest(source / "throw.js"))


if __name__ == "__main__":
    unittest.main()
