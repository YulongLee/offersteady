"""Offline byte verification of the CN seal. No Docker, service or network calls."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile


RELEASE_ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def read_json(path):
    return json.loads(path.read_bytes())


def safe_relative(key, scope='artifact'):
    require(isinstance(key, str) and bool(key) and '\x00' not in key and '\\' not in key, 'unsafe_relative_path')
    path = PurePosixPath(key)
    require(not path.is_absolute() and '..' not in path.parts and str(path) != '.'
            and '.git' not in path.parts, 'unsafe_relative_path')
    if scope == 'runtime':
        require(key == 'apps/backend/pyproject.toml' or any(key.startswith(prefix) for prefix in
                ('apps/backend/app/', 'ai/prompts/', 'apps/backend/migrations/')), 'runtime_path_outside_scope')
    return str(path)


def contained_path(root, relative, scope='artifact'):
    relative = safe_relative(relative, scope)
    path = root/relative
    require(path.resolve().is_relative_to(root.resolve()), 'resolved_path_outside_root')
    require(not path.is_symlink(), 'snapshot_symlink_refused')
    return path


def archive_entries(path):
    result = {}
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts, 'unsafe_archive_path')
            if member.isdir():
                continue
            require(member.isfile() and not member.issym() and not member.islnk(), 'unsafe_archive_entry')
            key = safe_relative(str(name))
            require(key != '.' and key not in result, 'duplicate_archive_entry')
            require(0 <= member.size <= 80*1024*1024, 'oversized_archive_entry')
            data = archive.extractfile(member).read()
            require(len(data) == member.size, 'truncated_archive_entry')
            result[key] = (data, member.mode & 0o777)
    return result


def runtime_inventory(root):
    files = [path for scope in ('apps/backend/app', 'ai/prompts', 'apps/backend/migrations')
             for path in (root/scope).rglob('*')]
    files.append(root/'apps/backend/pyproject.toml')
    return {str(path.relative_to(root)): sha(path.read_bytes()) for path in files
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'
            and path.name != '.desktop-release-manifest.lock'}


def verify(*, release_root=RELEASE_ROOT, repo_root=None):
    repo_root = repo_root or release_root.parents[1]
    manifest = read_json(release_root/'manifest.json')
    require(manifest['version'] == 'cn-20261022.1', 'wrong_release')
    require(not manifest['applicationSecretsIncluded'] and not manifest['rawUserDataIncluded'], 'private_scope_refused')
    require(isinstance(manifest['sourceFiles'], dict) and manifest['sourceFiles'], 'complete_source_manifest_missing')
    prefix = 'releases/cn-20261022.1/'
    actual_release = {str(path.relative_to(release_root)) for path in release_root.rglob('*')
                      if (path.is_file() or path.is_symlink()) and path.name != 'manifest.json'
                      and '__pycache__' not in path.parts and path.suffix != '.pyc'}
    expected_release = {key[len(prefix):] for key in manifest['sourceFiles'] if key.startswith(prefix)}
    require(actual_release == expected_release, 'release_file_scope_changed')
    for relative, checksum in manifest['sourceFiles'].items():
        require(relative != prefix+'manifest.json' and isinstance(checksum, str)
                and re.fullmatch('[0-9a-f]{64}', checksum), 'source_manifest_entry_invalid')
        path = contained_path(repo_root, relative)
        require(path.is_file() and sha(path.read_bytes()) == checksum, 'sealed_source_file_changed')
    backend = read_json(release_root/'backend-runtime-manifest.json')
    worker = read_json(release_root/'material-worker-runtime-manifest.json')
    web = read_json(release_root/'web-static-manifest.json')
    require(len(backend) == 230 and len(worker) == 196 and len(web) == 328, 'scope_count_changed')
    for key in (*backend, *worker):
        safe_relative(key, 'runtime')
    for key in web:
        safe_relative(key)
    live_bytes = (release_root/'live-verification.json').read_bytes()
    require(sha(live_bytes) == manifest['freshVerification']['sha256'], 'fresh_verification_changed')
    live = json.loads(live_bytes)
    require(live['region'] == 'cn' and live['productionChanged'] is False
            and live['privateConfigurationExported'] is False
            and live['rawUserLogsExported'] is False, 'fresh_verification_scope_changed')
    for role, expected in (('backend', backend), ('material-worker', worker), ('web', web)):
        actual = live['components'][role]
        require(actual['image'] == manifest[role]['image'] and actual['runtimeInputs'] == expected
                and actual['running'] is True and actual['restartCount'] == 0, 'fresh_component_changed')
        if role != 'web':
            require(actual['settings'] == manifest[role]['settings'], 'fresh_settings_summary_changed')
    require(live['components']['web']['nginxSha256'] == manifest['web']['nginxSha256']
            and live['openapiSchemaSha256'] == manifest['api']['schemaSha256'], 'fresh_api_or_nginx_changed')
    require(runtime_inventory(repo_root) == backend, 'backend_runtime_source_changed')
    for archive, expected in (('material-worker-runtime.tar.gz', worker), ('web-static.tar.gz', web)):
        data = (release_root/archive).read_bytes()
        require(sha(data) == manifest['archives'][archive], 'archive_checksum_changed')
        actual = {key: sha(value[0]) for key, value in archive_entries(release_root/archive).items()}
        require(actual == expected, 'archive_runtime_source_changed')
    require(sha((release_root/'nginx/default.conf').read_bytes()) == manifest['web']['nginxSha256'], 'nginx_bytes_changed')
    schema = read_json(release_root/'openapi.json')
    encoded = json.dumps(schema, sort_keys=True, separators=(',', ':')).encode()
    require(len(schema['paths']) == 203 and sha(encoded) == manifest['api']['schemaSha256'], 'api_schema_changed')
    overrides = read_json(release_root/'model-overrides.compose.json')
    expected_keys = {'backend': {'OFFERSTEADY_CHAT_QWEN_MODEL', 'OFFERSTEADY_CHAT_QUICK_MODEL',
                                 'OFFERSTEADY_CHAT_DETAIL_MODEL', 'OFFERSTEADY_SCREENSHOT_VISION_MODEL'},
                     'material-worker': {'OFFERSTEADY_CHAT_QWEN_MODEL', 'OFFERSTEADY_CHAT_QUICK_MODEL',
                                         'OFFERSTEADY_CHAT_DETAIL_MODEL'}}
    require(set(overrides) == {'services'} and set(overrides['services']) == set(expected_keys), 'model_component_scope_changed')
    for service, keys in expected_keys.items():
        item = overrides['services'][service]
        require(set(item) == {'environment'} and set(item['environment']) == keys
                and set(item['environment'].values()) == {'deepseek-v4.1-flash-1017'}, 'model_keys_changed')
        fields = {'OFFERSTEADY_CHAT_QWEN_MODEL': 'chat_qwen_model', 'OFFERSTEADY_CHAT_QUICK_MODEL': 'chat_quick_model',
                  'OFFERSTEADY_CHAT_DETAIL_MODEL': 'chat_detail_model', 'OFFERSTEADY_SCREENSHOT_VISION_MODEL': 'screenshot_vision_model'}
        require(manifest[service]['settings']['models'] == {fields[key]: value for key, value in item['environment'].items()}, 'live_model_selectors_changed')
    return {'passed': True, 'backendRuntimeInputs': 230, 'workerRuntimeInputs': 196,
            'webStaticFiles': 328, 'apiPaths': 203, 'modelEnvironmentKeys': 7,
            'productionChanges': 0, 'privateConfigurationRead': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo-root', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(repo_root=args.repo_root), separators=(',', ':')))
    except Exception:
        print(json.dumps({'passed': False, 'reason': 'snapshot_verification_failed'}))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
