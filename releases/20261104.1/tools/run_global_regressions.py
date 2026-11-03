"""Run frozen synthetic Global business tests against restored public source."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
from restore_snapshot import restore

def main():
    release=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='offersteady-global-seal-20261104-') as directory:
        root=Path(directory).resolve();backend=root/'candidate-initial'
        restore('global-backend',backend)
        shutil.copytree(release/'global/tests/business',root/'tests')
        shutil.copytree(release/'global/ai-evals',backend/'ai/evals')
        old=root/'backend-baseline/apps/backend/app/global_desktop_release_manifest.json'
        old.parent.mkdir(parents=True)
        shutil.copyfile(release/'global/test-fixtures/global-desktop-release-manifest-before.json',old)
        old=backend/'releases/global-20261019.1/fixtures/screenshot_answer_service_before.py'
        old.parent.mkdir(parents=True)
        shutil.copyfile(release/'global/test-fixtures/screenshot_answer_service_before.py',old)
        env={k:v for k,v in os.environ.items() if not k.startswith(('OFFERSTEADY_','PG'))}
        env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(map(str,[backend/'apps/backend',root/'tests'])))
        return subprocess.call([sys.executable,'-B','-m','pytest','-q',str(root/'tests'),
            '-k','not persistent and not actual_postgres'],cwd=root,env=env)

if __name__=='__main__':raise SystemExit(main())
