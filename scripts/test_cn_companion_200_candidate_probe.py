"""Offline source checks; do not claim an actual-image probe passed."""
import ast
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'scripts/test_fixtures/cn_companion_200'
SEALED = ROOT / 'releases/20261115.1/cn/backend-runtime.tar.gz'


def sealed_bytes(name):
    with tarfile.open(SEALED, 'r:gz') as archive:
        member = archive.extractfile(name)
        assert member is not None
        return member.read()


def test_candidate_probe_is_frozen_to_actual_baseline_plus_two_reviewed_files():
    source = (FIXTURES / 'candidate-probe.py').read_text()
    tree = ast.parse(source)
    assignments = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                   if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                   and n.targets[0].id in {'EXPECTED', 'DESKTOP_MANIFEST_SHA256'}}
    expected = assignments['EXPECTED']
    baseline = json.loads((ROOT / 'docs/releases/cn-mock-control-20261107.1/backend-runtime-manifest.json').read_text())
    differences = {k for k in baseline if baseline[k] != expected['inventory'][k]}
    assert len(baseline) == len(expected['inventory']) == 238
    assert differences == {'apps/backend/app/modules/web.py', 'apps/backend/app/desktop_release_manifest.json'}
    for key in ('apps/backend/app/modules/web.py', 'apps/backend/app/desktop_release_manifest.json'):
        assert hashlib.sha256(sealed_bytes(key)).hexdigest() == expected['inventory'][key]
    assert assignments['DESKTOP_MANIFEST_SHA256'] == expected['inventory']['apps/backend/app/desktop_release_manifest.json']
    assert expected['httpPaths'] == 203 and len(expected['dependencies']) == 44


def test_probe_enforces_offline_and_listing_contract():
    source = (FIXTURES / 'candidate-probe.py').read_text()
    for required in ('install_guards()', 'forbid_lifespan(application.app)', 'release_listing_invalid',
                     'release_history_invalid', 'databaseOperations', 'networkRequests', 'fileWrites'):
        assert required in source
    compile(source, 'candidate-probe.py', 'exec')


def test_local_staging_has_no_fabricated_image_or_probe_receipt():
    # The public fixture must not masquerade as an executable deployment plan.
    assert {p.name for p in FIXTURES.iterdir()} == {'candidate-probe.py'}


def test_image_context_contains_only_two_frozen_overlay_files():
    from scripts.test_build_cn_companion_200_candidate import make_context
    with tempfile.TemporaryDirectory() as directory:
        ctx=make_context(Path(directory)/'context')
        assert (ctx/'Dockerfile').read_text() == 'FROM sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43\nCOPY overlay/ /app/\n'
        files=sorted(f.relative_to(ctx).as_posix() for f in ctx.rglob('*') if f.is_file())
        assert files==['Dockerfile','overlay/apps/backend/app/desktop_release_manifest.json','overlay/apps/backend/app/modules/web.py']
        assert all((ctx/name).read_bytes()==sealed_bytes(name.removeprefix('overlay/')) for name in files[1:])
