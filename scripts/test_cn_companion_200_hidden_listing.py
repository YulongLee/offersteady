"""Run actual candidate functions with a synthetic manifest; no network or user data."""
import ast
from copy import deepcopy
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_MANIFEST = ROOT / 'docs/releases/companion-1.3.6-cn-20261102/desktop_release_manifest.json'


def sealed_bytes(name):
    with tarfile.open(ROOT / 'releases/20261115.1/cn/backend-runtime.tar.gz', 'r:gz') as archive:
        member = archive.extractfile('apps/backend/app/' + name)
        assert member is not None
        return member.read()


def candidate_source():
    return sealed_bytes('modules/web.py').decode()


def baseline_source():
    with tarfile.open(ROOT / 'releases/20261106.1/cn/backend-runtime.tar.gz', 'r:gz') as archive:
        member = archive.extractfile('apps/backend/app/modules/web.py')
        assert member is not None
        return member.read().decode()


def old_manifest():
    return json.loads(OLD_MANIFEST.read_text())


def new_manifest():
    return json.loads(sealed_bytes('desktop_release_manifest.json'))


def functions(source, manifest):
    tree = ast.parse(source)
    names = {'_release_manifest', '_published_desktop_entry', '_is_public_desktop_entry'}
    body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in body} == names
    namespace = {'_published_desktop_manifest': lambda: manifest}
    exec(compile(ast.Module(body=body, type_ignores=[]), '<candidate>', 'exec'), namespace)
    return namespace


def test_only_listing_changes_and_every_old_download_is_still_allowed():
    old = old_manifest()
    new = new_manifest()
    candidate = functions(candidate_source(), new)
    before = functions(baseline_source(), old)
    assert candidate['_release_manifest']()['entries'] == [x for x in candidate['_release_manifest']()['entries'] if x['version'] == '2.0.0']
    assert len(candidate['_release_manifest']()['entries']) == 3
    for entry in old['entries']:
        match = candidate['_published_desktop_entry'](entry['fileName'])
        assert {k: v for k, v in match.items() if k != 'hiddenFromListing'} == entry
        assert candidate['_is_public_desktop_entry'](match)
    assert functions(candidate_source(), old)['_release_manifest']() == before['_release_manifest']()


def test_only_literal_boolean_true_hides_and_private_marker_is_not_exposed():
    old = old_manifest()
    for marker in (False, 'true', 1, None):
        value = deepcopy(old)
        value['entries'][0]['hiddenFromListing'] = marker
        output = functions(candidate_source(), value)['_release_manifest']()
        assert len(output['entries']) == 3
        assert 'hiddenFromListing' not in output['entries'][0]


def test_filter_delta_is_exact_and_touches_no_other_code():
    source = baseline_source()
    candidate = candidate_source()
    restored = candidate.replace('if not isinstance(raw_entry, dict) or raw_entry.get("hiddenFromListing") is True:', 'if not isinstance(raw_entry, dict):').replace('if key not in ("objectKey", "hiddenFromListing")', 'if key != "objectKey"')
    assert restored == source


def test_candidate_download_router_serves_six_exact_filenames_without_user_data(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.deps import storage_port
    from app.modules import web

    manifest = new_manifest()
    monkeypatch.setattr(web, '_published_desktop_manifest', lambda: manifest)
    monkeypatch.setattr(web, '_desktop_release_dir', lambda: tmp_path)
    monkeypatch.setattr(web, 'record_desktop_download_completion', lambda **kwargs: None)
    candidate_tree = ast.parse(candidate_source())
    function = next(n for n in candidate_tree.body if isinstance(n, ast.FunctionDef) and n.name == '_release_manifest')
    namespace = dict(web.__dict__)
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<candidate>', 'exec'), namespace)
    monkeypatch.setattr(web, '_release_manifest', namespace['_release_manifest'])
    application = FastAPI()
    application.include_router(web.router, prefix='/api/v1')
    class SyntheticStorage:
        def create_signed_download_url(self, *, object_key, expires_seconds):
            assert object_key.startswith('desktop-releases/') and expires_seconds == 600
            return 'https://example.invalid/synthetic'
    application.dependency_overrides[storage_port] = lambda: SyntheticStorage()
    with TestClient(application) as client:
        for entry in manifest['entries']:
            response = client.get('/api/v1/web/downloads/desktop/' + entry['fileName'], follow_redirects=False)
            assert response.status_code == 307
            assert response.headers['location'] == 'https://example.invalid/synthetic'
        response = client.get('/api/v1/web/downloads/desktop/OfferSteady-Companion-unknown.dmg')
        assert response.status_code == 404
    assert {x['version'] for x in web._release_manifest()['entries']} == {'2.0.0'}


def test_real_version_gate_selects_newest_despite_archived_entries(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from app.services import realtime_speech_service as realtime

    backend = tmp_path / 'app'
    (backend / 'services').mkdir(parents=True)
    (backend / 'desktop_release_manifest.json').write_bytes(sealed_bytes('desktop_release_manifest.json'))
    monkeypatch.setattr(realtime, '__file__', str(backend / 'services/realtime_speech_service.py'))
    synthetic = SimpleNamespace(settings=SimpleNamespace(product_edition='cn'))
    for platform, arch in [('macos', 'arm64'), ('macos', 'x64'), ('windows', 'x64')]:
        assert realtime.RealtimeSpeechService._latest_companion_version(synthetic, platform=platform, architecture=arch) == '2.0.0'
