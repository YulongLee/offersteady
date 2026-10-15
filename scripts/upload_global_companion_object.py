"""Run inside the existing Global backend with one staged, verified installer.

Writes only an immutable Global installer object; never updates a manifest or
latest pointer. Uses existing server credentials without exporting them.
"""
from pathlib import Path
import hashlib
import json
import logging
import re
import sys

from app.core.config import Settings


def main():
    import oss2
    logging.getLogger('oss2').setLevel(logging.CRITICAL)
    settings = Settings()
    assert settings.product_edition == 'global', 'wrong product edition'
    metadata = json.loads(Path(sys.argv[1]).read_text())
    artifact = Path(sys.argv[2])
    assert metadata['version'] == '1.3.5' and not metadata['developmentOnly']
    target = (metadata['platform'], metadata['architecture'])
    assert target in {('windows', 'x64'), ('macos', 'arm64'), ('macos', 'x64')}
    assert artifact.name == metadata['fileName']
    expected_name = ('OfferSteady-Companion-Global-Setup-1.3.5-Windows-x64.exe' if target[0] == 'windows'
        else f'OfferSteady-Companion-Global-1.3.5-macOS-{target[1]}.dmg')
    assert artifact.name == expected_name
    assert re.fullmatch(r'[0-9a-f]{64}', metadata['sha256'])
    assert metadata['protocolVersion'] == '2.0'
    if target[0] == 'macos':
        assert metadata['signingStatus'] == 'verified' and metadata['notarized']
    else:
        assert metadata['signingStatus'] == 'unsigned' and not metadata['notarized']
    hasher = hashlib.sha256()
    with artifact.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(chunk)
    assert artifact.stat().st_size == metadata['fileSizeBytes']
    assert hasher.hexdigest() == metadata['sha256']
    endpoint = str(settings.oss_endpoint)
    if not endpoint.startswith(('https://', 'http://')):
        endpoint = 'https://' + endpoint
    assert all((settings.oss_access_key_id, settings.oss_access_key_secret, settings.oss_bucket))
    bucket = oss2.Bucket(oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret),
                        endpoint, settings.oss_bucket, connect_timeout=15)
    key = f'global-desktop-releases/{target[0]}/{target[1]}/1.3.5/{artifact.name}'
    content_type = 'application/x-apple-diskimage' if target[0] == 'macos' else 'application/vnd.microsoft.portable-executable'
    existing = bucket.object_exists(key)
    if not existing:
        result = oss2.resumable_upload(bucket, key, str(artifact),
            headers={'Content-Type': content_type}, multipart_threshold=8*1024*1024,
            part_size=4*1024*1024, num_threads=2)
        assert result.status in (200, 201, 204)
    head = bucket.head_object(key)
    assert int(head.content_length) == metadata['fileSizeBytes'], 'immutable object size mismatch'
    assert {k.lower(): v for k,v in head.headers.items()}.get('content-type') == content_type, 'immutable object MIME mismatch'
    downloaded = bucket.get_object(key)
    readback = hashlib.sha256()
    size = 0
    while True:
        chunk = downloaded.read(1024*1024)
        if not chunk:
            break
        size += len(chunk)
        readback.update(chunk)
    assert size == metadata['fileSizeBytes'] and readback.hexdigest() == metadata['sha256'], 'immutable object checksum mismatch'
    print(json.dumps({'platform': target[0], 'architecture': target[1], 'fileName': artifact.name,
        'version': '1.3.5', 'fileSizeBytes': size, 'sha256': readback.hexdigest(),
        'contentType': content_type, 'objectKey': key, 'objectReadbackVerified': True,
        'existingObjectReused': existing, 'publicManifestChanged': False}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Provider exceptions can contain credentials/signed URLs: suppress them.
        print(json.dumps({'uploaded': False, 'errorType': type(exc).__name__,
                          'reason': 'inspect private upload evidence'}))
        raise SystemExit(1) from None
