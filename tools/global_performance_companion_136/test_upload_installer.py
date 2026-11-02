"""Synthetic immutable-upload regressions: no SSH, OSS or user data."""
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "global_companion_136_upload_under_test", Path(__file__).with_name("upload_installer.py"))
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)
PAYLOAD = b"synthetic installer bytes\0not executable\n" * 17


def metadata(platform="macos", architecture="arm64"):
    mac = platform == "macos"
    filename = (f"OfferSteady-Companion-Global-1.3.6-macOS-{architecture}.dmg" if mac
                else "OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe")
    return {
        "version": "1.3.6", "developmentOnly": False,
        "platform": platform, "architecture": architecture, "fileName": filename,
        "fileSizeBytes": len(PAYLOAD), "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
        "protocolVersion": "2.0", "signingStatus": "verified" if mac else "unsigned",
        "notarized": mac, "minimumOs": "macOS 14.2+" if mac else "Windows 10 22H2+",
    }


class ProviderError(Exception):
    def __init__(self, status):
        super().__init__("synthetic-private-signed-url-and-credential")
        self.status = status


class FakeBucket:
    def __init__(self, *, existing=None, conflict=None, race_bytes=PAYLOAD,
                 upload_status=200, mime=None, readback=None, head_size=None):
        self.objects = {} if existing is None else {"initial": existing}
        self.conflict = conflict
        self.race_bytes = race_bytes
        self.upload_status = upload_status
        self.mime = mime
        self.readback = readback
        self.head_size = head_size
        self.calls = []
        self.result_stream = None

    def object_exists(self, key):
        self.calls.append(("exists", key))
        if "initial" in self.objects:
            self.objects[key] = self.objects.pop("initial")
        return key in self.objects

    def put_object_from_file(self, key, filename, *, headers):
        self.calls.append(("put", key, dict(headers)))
        if self.conflict:
            self.objects[key] = self.race_bytes
            raise ProviderError(self.conflict)
        self.objects[key] = Path(filename).read_bytes()
        return SimpleNamespace(status=self.upload_status)

    def head_object(self, key):
        self.calls.append(("head", key))
        size = len(self.objects[key]) if self.head_size is None else self.head_size
        default_mime = ("application/x-apple-diskimage" if key.endswith(".dmg")
                        else "application/vnd.microsoft.portable-executable")
        return SimpleNamespace(content_length=size,
                               headers={"Content-Type": self.mime or default_mime})

    def get_object(self, key):
        self.calls.append(("get", key))
        self.result_stream = io.BytesIO(self.objects[key] if self.readback is None else self.readback)
        return self.result_stream


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def artifact(self, value):
        path = self.root / value["fileName"]
        path.write_bytes(PAYLOAD)
        return path

    def test_new_three_platform_objects_are_conditional_and_fully_verified(self):
        for platform, architecture in sorted(U.TARGETS):
            with self.subTest(platform=platform, architecture=architecture):
                value, bucket = metadata(platform, architecture), FakeBucket()
                report = U.upload_verified(bucket, value, self.artifact(value))
                key = f"global-desktop-releases/{platform}/{architecture}/1.3.6/{value['fileName']}"
                self.assertEqual([c[0] for c in bucket.calls], ["exists", "put", "head", "get"])
                self.assertTrue(all(c[1] == key for c in bucket.calls))
                self.assertEqual(bucket.calls[1][2]["x-oss-forbid-overwrite"], "true")
                self.assertTrue(report["objectReadbackVerified"])
                self.assertFalse(report["existingObjectReused"])
                self.assertFalse(report["publicManifestChanged"])
                self.assertFalse(report["latestPointerChanged"])
                self.assertTrue(bucket.result_stream.closed)
                self.assertNotIn(str(self.root), json.dumps(report))

    def test_existing_exact_object_is_read_only(self):
        value, bucket = metadata(), FakeBucket(existing=PAYLOAD)
        report = U.upload_verified(bucket, value, self.artifact(value))
        self.assertEqual([c[0] for c in bucket.calls], ["exists", "head", "get"])
        self.assertTrue(report["existingObjectReused"])

    def test_existing_different_object_is_rejected_without_write(self):
        value, bucket = metadata(), FakeBucket(existing=b"X" * len(PAYLOAD))
        with self.assertRaisesRegex(U.UploadGuardError, "object_bytes_mismatch"):
            U.upload_verified(bucket, value, self.artifact(value))
        self.assertFalse(any(c[0] == "put" for c in bucket.calls))
        self.assertTrue(bucket.result_stream.closed)

    def test_conflicts_only_reuse_exact_read_back_bytes(self):
        for status in (409, 412):
            with self.subTest(status=status):
                value, bucket = metadata(), FakeBucket(conflict=status)
                report = U.upload_verified(bucket, value, self.artifact(value))
                self.assertTrue(report["existingObjectReused"])
                self.assertEqual(sum(c[0] == "put" for c in bucket.calls), 1)

    def test_conflict_different_bytes_fails_without_retrying_write(self):
        value, bucket = metadata(), FakeBucket(conflict=409, race_bytes=b"X" * len(PAYLOAD))
        with self.assertRaisesRegex(U.UploadGuardError, "object_bytes_mismatch"):
            U.upload_verified(bucket, value, self.artifact(value))
        self.assertEqual(sum(c[0] == "put" for c in bucket.calls), 1)

    def test_other_provider_error_does_not_retry_or_assume_success(self):
        value, bucket = metadata(), FakeBucket(conflict=503)
        with self.assertRaises(ProviderError):
            U.upload_verified(bucket, value, self.artifact(value))
        self.assertEqual([c[0] for c in bucket.calls], ["exists", "put"])

    def test_bad_upload_status_stops_before_success(self):
        value, bucket = metadata(), FakeBucket(upload_status=202)
        with self.assertRaisesRegex(U.UploadGuardError, "object_upload_failed"):
            U.upload_verified(bucket, value, self.artifact(value))

    def test_head_and_full_stream_are_each_required(self):
        for kwargs, reason in (({"head_size": len(PAYLOAD) + 1}, "object_size_mismatch"),
                               ({"mime": "application/zip"}, "object_mime_mismatch"),
                               ({"readback": b"X" * len(PAYLOAD)}, "object_bytes_mismatch"),
                               ({"readback": PAYLOAD[:-1]}, "object_bytes_mismatch")):
            with self.subTest(kwargs=kwargs):
                value, bucket = metadata(), FakeBucket(**kwargs)
                with self.assertRaisesRegex(U.UploadGuardError, reason):
                    U.upload_verified(bucket, value, self.artifact(value))

    def test_metadata_and_local_byte_drift_fail_before_oss_calls(self):
        fields = {
            "version": "1.3.5", "developmentOnly": True, "platform": "linux",
            "architecture": "armv7", "protocolVersion": "1.0", "signingStatus": "local-development",
            "notarized": False, "minimumOs": "macOS 13.4+", "sha256": "0" * 64,
            "fileSizeBytes": len(PAYLOAD) + 1,
        }
        for field, different in fields.items():
            with self.subTest(field=field):
                value, bucket = metadata(), FakeBucket()
                artifact = self.artifact(value)
                value[field] = different
                with self.assertRaises(U.UploadGuardError):
                    U.upload_verified(bucket, value, artifact)
                self.assertEqual(bucket.calls, [])

    def test_version_filename_and_edition_cannot_be_renamed(self):
        for name in ("OfferSteady-Companion-Global-1.3.6-Local-r3-macOS-arm64.dmg",
                     "OfferSteady-Companion-1.3.6-macOS-arm64.dmg",
                     "OfferSteady-Companion-1.3.5-macOS-arm64.dmg", "latest.json"):
            value, bucket = metadata(), FakeBucket()
            artifact = self.artifact(value)
            value["fileName"] = name
            with self.assertRaisesRegex(U.UploadGuardError, "filename_invalid"):
                U.upload_verified(bucket, value, artifact)
            self.assertEqual(bucket.calls, [])

    def test_all_boolean_and_oversized_sizes_are_rejected(self):
        for size in (True, False, 0, -1, "500", 2_000_000_000):
            value = metadata()
            artifact = self.artifact(value)
            value["fileSizeBytes"] = size
            with self.subTest(size=size), self.assertRaisesRegex(U.UploadGuardError, "size_invalid"):
                U.prepare_artifact(value, artifact)

    def test_unsigned_windows_only_and_no_windows_arm(self):
        for fields in ({"signingStatus": "verified"}, {"signingStatus": "local-development"},
                       {"notarized": True}, {"architecture": "arm64"}):
            value = metadata("windows", "x64")
            artifact = self.artifact(value)
            value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(U.UploadGuardError):
                U.prepare_artifact(value, artifact)

    def test_artifact_symlink_is_rejected(self):
        value = metadata()
        target = self.root / "target"
        target.write_bytes(PAYLOAD)
        artifact = self.root / value["fileName"]
        artifact.symlink_to(target)
        with self.assertRaisesRegex(U.UploadGuardError, "artifact_missing_or_linked"):
            U.prepare_artifact(value, artifact)

    def test_full_digest_uses_bounded_reads(self):
        class Stream(io.BytesIO):
            def read(self, n=-1):
                self.assertion(n)
                return super().read(n)
        stream = Stream(PAYLOAD)
        stream.assertion = lambda n: self.assertEqual(n, U.CHUNK_BYTES)
        self.assertEqual(U.stream_digest(stream), (len(PAYLOAD), hashlib.sha256(PAYLOAD).hexdigest()))


class EnvironmentTests(unittest.TestCase):
    def test_wrong_edition_and_missing_configuration_never_construct_bucket(self):
        oss = SimpleNamespace(Auth=lambda *args: self.fail("must not initialize credentials"))
        settings = SimpleNamespace(product_edition="cn")
        with self.assertRaisesRegex(U.UploadGuardError, "wrong_product_edition"):
            U.create_bucket(settings, oss)
        settings = SimpleNamespace(product_edition="global", oss_access_key_id="", oss_access_key_secret="",
                                   oss_bucket="", oss_endpoint="")
        with self.assertRaisesRegex(U.UploadGuardError, "oss_unconfigured"):
            U.create_bucket(settings, oss)

    def test_existing_server_settings_are_used_without_export(self):
        calls = []
        oss = SimpleNamespace(Auth=lambda *args: ("private-auth", args),
                              Bucket=lambda *args, **kwargs: calls.append((args, kwargs)) or "bucket")
        settings = SimpleNamespace(product_edition="global", oss_access_key_id="fake-id",
                                   oss_access_key_secret="fake-key", oss_bucket="fake-bucket",
                                   oss_endpoint="oss.example.invalid")
        self.assertEqual(U.create_bucket(settings, oss), "bucket")
        self.assertEqual(calls[0][0][1], "https://oss.example.invalid")
        self.assertEqual(calls[0][1], {"connect_timeout": 15})

    def test_cli_suppresses_provider_text_and_traceback(self):
        out = io.StringIO()
        with patch.object(U, "main", side_effect=ProviderError(503)), redirect_stdout(out):
            self.assertEqual(U.cli(), 1)
        report = json.loads(out.getvalue())
        self.assertEqual(report, {"uploaded": False, "errorType": "ProviderError",
                                  "reason": "inspect private upload evidence"})
        self.assertNotIn("signed-url", out.getvalue())
        self.assertNotIn("Traceback", out.getvalue())


if __name__ == "__main__":
    unittest.main()
