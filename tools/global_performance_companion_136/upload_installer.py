"""Upload one verified Global 1.3.6 installer from the existing Global backend.

Credentials stay in the backend environment. This tool never writes a release
manifest, latest pointer, user record or existing installer object. Each new
object uses a conditional, streaming PutObject and is fully read back before
success is reported. Re-running only reuses an exact existing object.
"""
from pathlib import Path
import hashlib
import json
import logging
import re
import sys


VERSION = "1.3.6"
TARGETS = {("windows", "x64"), ("macos", "arm64"), ("macos", "x64")}
CHUNK_BYTES = 1024 * 1024


class UploadGuardError(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise UploadGuardError(reason)


def stream_digest(handle):
    size, hasher = 0, hashlib.sha256()
    for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
        size += len(chunk)
        hasher.update(chunk)
    return size, hasher.hexdigest()


def prepare_artifact(metadata, artifact):
    """Validate local bytes and public publication metadata before OSS access."""
    artifact = Path(artifact)
    require(isinstance(metadata, dict), "metadata_invalid")
    require(metadata.get("version") == VERSION
            and metadata.get("developmentOnly") is False, "not_production_136")
    target = (metadata.get("platform"), metadata.get("architecture"))
    require(all(isinstance(value, str) for value in target)
            and target in TARGETS, "target_invalid")
    expected_name = (f"OfferSteady-Companion-Global-Setup-{VERSION}-Windows-x64.exe"
                     if target[0] == "windows"
                     else f"OfferSteady-Companion-Global-{VERSION}-macOS-{target[1]}.dmg")
    require(artifact.name == expected_name
            and metadata.get("fileName") == expected_name, "filename_invalid")
    require(artifact.is_file() and not artifact.is_symlink(), "artifact_missing_or_linked")
    checksum = metadata.get("sha256")
    require(isinstance(checksum, str) and re.fullmatch(r"[0-9a-f]{64}", checksum)
            and checksum != "0" * 64, "checksum_invalid")
    size = metadata.get("fileSizeBytes")
    require(type(size) is int and 0 < size < 2_000_000_000, "size_invalid")
    require(metadata.get("protocolVersion") == "2.0", "protocol_changed")
    if target[0] == "macos":
        require(metadata.get("signingStatus") == "verified"
                and metadata.get("notarized") is True, "mac_trust_unverified")
        require(metadata.get("minimumOs") == "macOS 14.2+", "mac_os_changed")
    else:
        require(metadata.get("signingStatus") == "unsigned"
                and metadata.get("notarized") is False, "windows_trust_untruthful")
        require(metadata.get("minimumOs") == "Windows 10 22H2+", "windows_os_changed")
    with artifact.open("rb") as handle:
        local_size, local_checksum = stream_digest(handle)
    require(local_size == size and local_checksum == checksum, "local_bytes_mismatch")
    key = f"global-desktop-releases/{target[0]}/{target[1]}/{VERSION}/{expected_name}"
    content_type = ("application/x-apple-diskimage" if target[0] == "macos"
                    else "application/vnd.microsoft.portable-executable")
    return artifact, target, key, content_type


def verify_object(bucket, key, metadata, content_type):
    head = bucket.head_object(key)
    require(int(head.content_length) == metadata["fileSizeBytes"], "object_size_mismatch")
    headers = {str(k).lower(): v for k, v in head.headers.items()}
    require(headers.get("content-type") == content_type, "object_mime_mismatch")
    downloaded = bucket.get_object(key)
    try:
        size, checksum = stream_digest(downloaded)
    finally:
        downloaded.close()
    require(size == metadata["fileSizeBytes"] and checksum == metadata["sha256"],
            "object_bytes_mismatch")
    return size, checksum


def upload_verified(bucket, metadata, artifact):
    artifact, target, key, content_type = prepare_artifact(metadata, artifact)
    existing = bool(bucket.object_exists(key))
    if not existing:
        try:
            # A single streaming PutObject forwards this conditional header.
            # The installed resumable uploader does not forward it at multipart
            # completion, so it cannot protect this immutable key from a race.
            result = bucket.put_object_from_file(
                key, str(artifact),
                headers={"Content-Type": content_type, "x-oss-forbid-overwrite": "true"},
            )
            require(result.status in {200, 201, 204}, "object_upload_failed")
        except Exception as exc:
            # A concurrent writer may win after object_exists. Never retry a
            # write: only exact bytes and MIME may be reused after a conflict.
            if getattr(exc, "status", None) not in {409, 412}:
                raise
            existing = True
    size, checksum = verify_object(bucket, key, metadata, content_type)
    return {
        "platform": target[0], "architecture": target[1],
        "fileName": artifact.name, "version": VERSION,
        "fileSizeBytes": size, "sha256": checksum,
        "contentType": content_type, "objectKey": key,
        "objectReadbackVerified": True, "existingObjectReused": existing,
        "publicManifestChanged": False, "latestPointerChanged": False,
    }


def create_bucket(settings, oss):
    require(settings.product_edition == "global", "wrong_product_edition")
    require(all((settings.oss_access_key_id, settings.oss_access_key_secret,
                 settings.oss_bucket, settings.oss_endpoint)), "oss_unconfigured")
    endpoint = str(settings.oss_endpoint)
    if not endpoint.startswith(("https://", "http://")):
        endpoint = "https://" + endpoint
    return oss.Bucket(oss.Auth(settings.oss_access_key_id, settings.oss_access_key_secret),
                      endpoint, settings.oss_bucket, connect_timeout=15)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    require(len(args) == 2, "usage_metadata_and_artifact_required")
    # Import only in the server execution path; synthetic tests never need the
    # application environment or a real OSS connection.
    from app.core.config import Settings
    import oss2

    logging.getLogger("oss2").setLevel(logging.CRITICAL)
    metadata = json.loads(Path(args[0]).read_text())
    bucket = create_bucket(Settings(), oss2)
    report = upload_verified(bucket, metadata, Path(args[1]))
    print(json.dumps(report))
    return 0


def cli():
    try:
        return main()
    except Exception as exc:
        # Provider/configuration exceptions can contain secrets or signed URLs.
        # Export only the exception class, never text, traceback or provider data.
        print(json.dumps({"uploaded": False, "errorType": type(exc).__name__,
                          "reason": "inspect private upload evidence"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(cli())
