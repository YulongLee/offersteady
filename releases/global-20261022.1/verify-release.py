"""Verify a completed Global seal offline; never mutate or extract archives."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import tarfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def members(path):
    found = {}
    with tarfile.open(path, 'r:gz') as archive:
        for item in archive.getmembers():
            name = item.name.removeprefix('./')
            parts = PurePosixPath(name)
            assert not parts.is_absolute() and '..' not in parts.parts
            if item.isdir():
                continue
            assert item.isfile() and name not in found
            found[name] = sha(archive.extractfile(item).read())
    return found


def main():
    root = Path(__file__).resolve().parent
    repository = root.parents[1]
    manifest = json.loads((root / 'manifest.json').read_text())
    assert manifest['sealReady'] and not manifest['privateConfigurationIncluded'] and not manifest['rawUserDataIncluded']
    for name, digest in manifest['rootFiles'].items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts and '.git' not in relative.parts
        path = repository
        for part in relative.parts:
            path = path / part
            assert not path.is_symlink(), 'symlink_in_allowlisted_repository_path'
        assert path.is_file() and sha(path.read_bytes()) == digest, 'repository_artifact_drift: ' + name
    for name, digest in manifest['artifacts'].items():
        path = root / name
        assert not path.is_symlink() and path.is_file() and sha(path.read_bytes()) == digest, name
    for role, count in (('backend', 302), ('material-worker', 267)):
        expected = json.loads((root / (role + '-runtime-manifest.json')).read_text())
        assert len(expected) == count and members(root / (role + '-runtime.tar.gz')) == expected
        if role == 'backend':
            paths = [path for folder in ('apps/backend/app', 'ai/prompts', 'apps/backend/migrations')
                     for path in (repository / folder).rglob('*')]
            paths.append(repository / 'apps/backend/pyproject.toml')
            actual = {}
            for path in paths:
                if '__pycache__' in path.parts or path.suffix == '.pyc' or path.name == '.desktop-release-manifest.lock':
                    continue
                assert not path.is_symlink(), 'symlink_in_repository_runtime_inputs'
                if path.is_file():
                    actual[str(path.relative_to(repository))] = sha(path.read_bytes())
            assert actual == expected, 'repository_backend_runtime_inputs_differ'
    web = json.loads((root / 'web-static-manifest.json').read_text())
    assert len(web) == 235 and members(root / 'web-static.tar.gz') == web
    schema = json.loads((root / 'openapi.json').read_text())
    assert len(schema['paths']) == 223
    assert sha(json.dumps(schema, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()) == manifest['openapiCanonicalSha256']
    models = json.loads((root / 'model-overrides.json').read_text())
    keys = {
        'backend': {'OFFERSTEADY_CHAT_QWEN_MODEL', 'OFFERSTEADY_CHAT_QUICK_MODEL',
                    'OFFERSTEADY_CHAT_DETAIL_MODEL', 'OFFERSTEADY_SCREENSHOT_VISION_MODEL'},
        'material-worker': {'OFFERSTEADY_CHAT_QWEN_MODEL'},
    }
    assert set(models) == set(keys) and models == manifest['modelOverrides']
    assert all(set(models[role]) == required and
               all(value == 'deepseek-v4.1-flash-1017' for value in models[role].values())
               for role, required in keys.items()), 'model_override_allowlist_differs'
    print(json.dumps({'verified': True, 'backendFiles': 302, 'workerFiles': 267,
                      'webFiles': 235, 'apiPaths': 223, 'repositoryBackendExact': True,
                      'modelEnvironmentKeys': 5, 'rootFiles': len(manifest['rootFiles']),
                      'productionAccess': False}))


if __name__ == '__main__':
    main()
