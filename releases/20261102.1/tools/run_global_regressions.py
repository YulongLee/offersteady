"""Run the frozen synthetic Global regressions from an isolated restored tree."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

from restore_snapshot import restore


def main():
    release = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='offersteady-global-seal-') as directory:
        root = Path(directory).resolve()
        backend = root / 'backend-candidate'
        restore('global-backend', backend)
        shutil.copytree(release / 'global/tests', root / 'tests')
        shutil.copytree(release / 'global/ai-evals', backend / 'ai/evals')
        old_manifest = root / 'backend-baseline/apps/backend/app/global_desktop_release_manifest.json'
        old_manifest.parent.mkdir(parents=True)
        shutil.copyfile(release / 'global/test-fixtures/global-desktop-release-manifest-before.json', old_manifest)
        old_service = backend / 'releases/global-20261019.1/fixtures/screenshot_answer_service_before.py'
        old_service.parent.mkdir(parents=True)
        shutil.copyfile(release / 'global/test-fixtures/screenshot_answer_service_before.py', old_service)
        environment = dict(os.environ)
        # Avoid inheriting local API/provider configuration. conftest also
        # rejects real network calls; dedicated PostgreSQL cases are excluded.
        for key in list(environment):
            if key.startswith('OFFERSTEADY_'):
                environment.pop(key)
        environment['PYTHONPATH'] = str(backend / 'apps/backend')
        return subprocess.call([
            sys.executable, '-m', 'pytest', '-q', str(root / 'tests'),
            '-k', 'not persistent and not actual_postgres',
        ], cwd=root, env=environment)


if __name__ == '__main__':
    raise SystemExit(main())
