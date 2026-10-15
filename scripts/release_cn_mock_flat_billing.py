"""CN-only, actual-image based mock billing cutover. Run on the CN host.

Secrets and complete container inspections remain in the private release dir.
Preparation builds candidates without touching services or deployment tags.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import urlopen

import cutover_cn_shared_text_model as guards

ROOT = Path('/opt/offersteady/releases/20261015-cn-mock-flat-billing-1')
BASES = {
    'backend': ('6c16f7bf71385ed4d9d8d1dc409b7c7d8704861bbf7b66596e191bb64cbaf025',
                'sha256:ec510532ca598878e147c4277e6da9776924fbf056ed942ab4cc2bf110f398bb'),
    'web': ('5e7114849b9cfd08589ef47adf6bac7efe669b615418f0b02c234336e1cacfcf',
            'sha256:df74779852799933e49aee117d1c45aaf3b789d29c8413caa994219ae50ab6a3'),
}
BACKEND_FILES = {
    'services/mock_interview_repository.py', 'services/mock_interview_runtime.py',
    'services/mock_interview_jobs.py', 'services/mock_interview_audio.py',
    'services/realtime_speech_service.py',
}
MANIFEST_SHA = '76ba8b6009071d4c4c0b824b6bbbf1c05c7d848f95c1ab08649c9e9e05c4a76a'
APP = '/app/apps/backend/app/'
HTML = '/usr/share/nginx/html/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_container(name, path):
    return guards.run(['docker', 'exec', name, 'cat', path]).stdout


def backend_hashes(name, paths):
    code = ('from pathlib import Path;import hashlib,json;root=Path(' + repr(APP) + ');'
        'paths=' + repr(list(paths)) + ';print(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}))')
    return json.loads(guards.run(['docker', 'exec', name, 'python', '-B', '-c', code]).stdout)


def web_hashes(name):
    lines = guards.run(['docker', 'exec', '-w', HTML, name, 'sh', '-c',
        'find . -type f -exec sha256sum {} +'], timeout=60).stdout.decode().splitlines()
    result = {}
    for line in lines:
        checksum, path = line.split(maxsplit=1)
        assert len(checksum) == 64 and path.startswith('./'), 'invalid static checksum output'
        result[path.removeprefix('./')] = checksum
    return result


def check_inputs(plan):
    assert set(plan['backend']) == BACKEND_FILES, 'unexpected backend scope'
    assert plan['verified']['backendPassed'] > 0 and plan['verified']['webPassed'] > 0
    assert plan['verified']['webGraphVerified'] and plan['verified']['localSyntheticOnly']
    assert set(plan['web']) >= {'index.html', 'offersteady-build.json'}
    for path, checksum in plan['backend'].items():
        assert digest((ROOT / 'input/backend' / path).read_bytes()) == checksum
    for path, checksum in plan['web'].items():
        assert path in ('index.html', 'guide.html', 'terms.html', 'privacy.html', 'offersteady-build.json') or (
            path.startswith('assets/') and '/' not in path[7:]
            and path.endswith(('.js', '.css')) and '..' not in path)
        assert digest((ROOT / 'input/web' / path).read_bytes()) == checksum
    assert digest((ROOT / 'extra_idle_gate.py').read_bytes()) == plan['extraGateSha']


def build(directory, base_image, tag, copies):
    directory.mkdir(mode=0o700, exist_ok=True)
    base_tag = 'offersteady-cn-base:mock-flat-billing-' + base_image.removeprefix('sha256:')[:12]
    guards.run(['docker', 'tag', base_image, base_tag])
    (directory / 'Dockerfile').write_text(f'FROM {base_tag}\n' + ''.join(copies))
    guards.run(['docker', 'build', '--network=none', '-t', tag, str(directory)], timeout=90)
    image = guards.inspect(tag)
    assert image['Config'] == guards.inspect(base_image)['Config'], 'image configuration changed'
    return image['Id']


def prepare():
    assert not (ROOT / 'prepared.json').exists(), 'preparation already recorded'
    plan = json.loads((ROOT / 'input.json').read_text())
    check_inputs(plan)
    targets = []
    names = guards.run(['docker', 'ps', '--format', '{{.Names}}']).stdout.decode().splitlines()
    non_targets = {}
    for name in names:
        current = guards.inspect(name)
        if name not in ('compose-backend-1', 'compose-web-1'):
            non_targets[name] = {'id': current['Id'], 'image': current['Image'], 'started': current['State']['StartedAt']}
    for service in ('backend', 'web'):
        name = f'compose-{service}-1'
        current = guards.inspect(name)
        assert (current['Id'], current['Image']) == BASES[service], 'runtime baseline drift'
        assert current['State']['Running'] and current['RestartCount'] == 0
        labels = current['Config']['Labels']
        compose_file = labels['com.docker.compose.project.config_files']
        assert ',' not in compose_file
        release = Path(labels['com.docker.compose.project.working_dir']).parents[1]
        env_file = release / '.env.production'
        directory = ROOT / service
        directory.mkdir(mode=0o700, exist_ok=False)
        (directory / 'container-before.json').write_text(json.dumps(current))
        env = env_file.read_bytes()
        (directory / 'env.before').write_bytes(env)
        target = {'container': name, 'service': service, 'baseImage': current['Image'],
                  'beforeId': current['Id'], 'composeFile': compose_file,
                  'release': str(release), 'envFile': str(env_file), 'envSha': digest(env),
                  'runtimeTag': current['Config']['Image'],
                  'newTag': f'offersteady-cn-{service}:mock-flat-billing-20261015-1',
                  'rollbackTag': f'offersteady-cn-{service}:mock-flat-billing-rollback-20261015-1'}
        assert target['runtimeTag'] == 'compose-' + service
        compose_source = Path(compose_file).read_bytes()
        (directory / 'compose.before').write_bytes(compose_source)
        target['composeSha'] = digest(compose_source)
        target['renderedSha'] = rendered_sha(target)
        copies = []
        if service == 'backend':
            assert backend_hashes(name, plan['backendBefore']) == plan['backendBefore'], 'live source drift'
            live_manifest = read_container(name, APP + 'desktop_release_manifest.json')
            assert digest(live_manifest) == MANIFEST_SHA
            (directory / 'desktop_release_manifest.json').write_bytes(live_manifest)
            # Writable-layer 1.3.5 manifest must survive both publish and rollback.
            rollback_dir = directory / 'rollback'
            rollback_dir.mkdir(mode=0o700)
            (rollback_dir / 'desktop_release_manifest.json').write_bytes(live_manifest)
            (rollback_dir / 'desktop_release_manifest.json').chmod(0o644)
            (directory / 'desktop_release_manifest.json').chmod(0o644)
            target['rollbackImage'] = build(rollback_dir, current['Image'], target['rollbackTag'],
                ['COPY desktop_release_manifest.json ' + APP + 'desktop_release_manifest.json\n'])
            for path in sorted(BACKEND_FILES):
                out = directory / path
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes((ROOT / 'input/backend' / path).read_bytes())
                out.chmod(0o644)
                copies.append(f'COPY {path} {APP + path}\n')
            copies.append('COPY desktop_release_manifest.json ' + APP + 'desktop_release_manifest.json\n')
        else:
            assert digest(read_container(name, '/etc/nginx/conf.d/default.conf')) == plan['nginxSha']
            assert web_hashes(name) == plan['webBefore'], 'live static asset drift'
            for path in plan['web']:
                if path.startswith('assets/'):
                    assert path not in plan['webBefore'], 'cannot mutate immutable old assets'
                out = directory / 'web' / path
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes((ROOT / 'input/web' / path).read_bytes())
                out.chmod(0o644)
            (directory / 'web').chmod(0o755)
            (directory / 'web/assets').chmod(0o755)
            copies.append(f'COPY web/ {HTML}\n')
            guards.run(['docker', 'tag', current['Image'], target['rollbackTag']])
            target['rollbackImage'] = current['Image']
        target['newImage'] = build(directory, current['Image'], target['newTag'], copies)
        targets.append(target)
        print(json.dumps({'prepared': service, 'image': target['newImage'], 'productionChanged': False}), flush=True)
    manifest = {'targets': targets, 'nonTargets': non_targets, 'models': guards.models('compose-backend-1'),
                'inputSha': digest((ROOT / 'input.json').read_bytes())}
    (ROOT / 'prepared.json').write_text(json.dumps(manifest, indent=2))


def idle_gate():
    guards.idle_gate()
    result = subprocess.run(['docker', 'exec', '-i', '-w', '/app/apps/backend',
        'compose-backend-1', 'python', '-B', '-'], input=(ROOT / 'extra_idle_gate.py').read_bytes(),
        capture_output=True, timeout=20)
    print(json.dumps({'gate': 'mock-flat-billing-extra', 'exitCode': result.returncode,
                      'counts': result.stdout.decode().strip()}), flush=True)
    assert result.returncode == 0, 'protected user work; cutover deferred'


def invariant(before, after, target):
    assert after['Image'] == target['newImage']
    assert guards.environment(before) == guards.environment(after), 'runtime environment changed'
    for key in ('Cmd', 'Entrypoint', 'WorkingDir', 'User', 'ExposedPorts', 'Healthcheck', 'Volumes', 'StopSignal'):
        assert before['Config'].get(key) == after['Config'].get(key), 'container configuration changed'
    for key, value in before['Config'].get('Labels', {}).items():
        if not key.startswith('com.docker.compose.'):
            assert after['Config'].get('Labels', {}).get(key) == value, 'application label changed'
    for key in ('RestartPolicy', 'PortBindings', 'NetworkMode', 'Memory', 'NanoCpus', 'ShmSize',
                'SecurityOpt', 'ReadonlyRootfs', 'Privileged', 'LogConfig', 'Binds'):
        assert before['HostConfig'].get(key) == after['HostConfig'].get(key), 'host configuration changed'
    assert before['Mounts'] == after['Mounts'], 'mount configuration changed'


def rendered_sha(target):
    rendered = json.loads(guards.run(['docker', 'compose', '-p', 'compose', '--env-file', target['envFile'],
        '-f', target['composeFile'], 'config', '--format', 'json']).stdout)
    return digest(json.dumps(rendered, sort_keys=True, separators=(',', ':')).encode())


def verify_baseline(manifest, plan):
    assert [target['service'] for target in manifest['targets']] == ['backend', 'web'], 'unexpected targets'
    for target in manifest['targets']:
        assert target['container'] == 'compose-' + target['service'] + '-1'
        assert (target['beforeId'], target['baseImage']) == BASES[target['service']]
        current = guards.inspect(target['container'])
        saved = json.loads((ROOT / target['service'] / 'container-before.json').read_text())
        assert target['runtimeTag'] == current['Config']['Image'] == 'compose-' + target['service'], 'runtime tag drift'
        labels = current['Config']['Labels']
        expected_release = Path(labels['com.docker.compose.project.working_dir']).parents[1]
        assert target['composeFile'] == labels['com.docker.compose.project.config_files'], 'compose identity drift'
        assert target['release'] == str(expected_release), 'release identity drift'
        assert target['envFile'] == str(expected_release / '.env.production'), 'environment identity drift'
        assert current['Id'] == saved['Id'] == target['beforeId'] and current['Config'] == saved['Config']
        assert current['Image'] == target['baseImage']
        assert digest(Path(target['envFile']).read_bytes()) == target['envSha']
        assert digest(Path(target['composeFile']).read_bytes()) == target['composeSha'], 'compose source drift'
        assert rendered_sha(target) == target['renderedSha'], 'rendered compose drift'
        assert guards.inspect(target['newTag'])['Id'] == target['newImage']
        assert guards.inspect(target['rollbackTag'])['Id'] == target['rollbackImage'], 'rollback image drift'
        rendered = json.loads(guards.run(['docker', 'compose', '-p', 'compose', '--env-file', target['envFile'],
            '-f', target['composeFile'], 'config', '--format', 'json']).stdout)
        assert all(str(v) == guards.environment(current).get(k)
            for k, v in rendered['services'][target['service']].get('environment', {}).items()), 'compose environment drift'
    assert backend_hashes('compose-backend-1', plan['backendBefore']) == plan['backendBefore'], 'live source drift'
    assert web_hashes('compose-web-1') == plan['webBefore'], 'live static asset drift'
    assert digest(read_container('compose-web-1', '/etc/nginx/conf.d/default.conf')) == plan['nginxSha']
    guards.verify_non_targets(manifest)


def verify_live(plan):
    expected_backend = plan['backendBefore'] | plan['backend']
    assert backend_hashes('compose-backend-1', expected_backend) == expected_backend, 'backend source changed'
    assert expected_backend['desktop_release_manifest.json'] == MANIFEST_SHA
    assert digest(read_container('compose-web-1', '/etc/nginx/conf.d/default.conf')) == plan['nginxSha']
    assert web_hashes('compose-web-1') == (plan['webBefore'] | plan['web']), 'static file missing or changed'
    with urlopen('https://mianshiwen.cn/healthz', timeout=10) as response:
        assert response.status == 200 and json.loads(response.read())['data']['status'] == 'ok'


def deploy(*, preflight_only=False):
    assert not (ROOT / 'deployed.json').exists(), 'already deployed; inspect before rerun'
    manifest = json.loads((ROOT / 'prepared.json').read_text())
    plan = json.loads((ROOT / 'input.json').read_text())
    assert digest((ROOT / 'input.json').read_bytes()) == manifest['inputSha']
    check_inputs(plan)
    report = json.loads((ROOT / 'candidate-verification.json').read_text())
    assert report['passed'] and report['images'] == {t['service']: t['newImage'] for t in manifest['targets']}
    assert report.get('browserPassed'), 'actual candidate browser verification required'
    assert report.get('webFilesSha') == digest(json.dumps(plan['web'], sort_keys=True).encode()), 'browser payload mismatch'
    verify_baseline(manifest, plan)
    idle_gate()
    if preflight_only:
        print(json.dumps({'preflightPassed': True, 'productionChanged': False}), flush=True)
        return
    touched = []
    try:
        idle_gate()
        verify_baseline(manifest, plan)
        for target in manifest['targets']:
            touched.append(target)
            guards.run(['docker', 'tag', target['newImage'], target['runtimeTag']])
            guards.compose(target)
            after = guards.wait_healthy(target)
            before = json.loads((ROOT / target['service'] / 'container-before.json').read_text())
            invariant(before, after, target)
            print(json.dumps({'switched': target['service'], 'image': after['Image']}), flush=True)
        assert guards.models('compose-backend-1') == manifest['models'], 'effective model changed'
        verify_live(plan)
        guards.verify_non_targets(manifest)
        result = {'deployed': True, 'atMs': int(time.time() * 1000),
            'images': {t['service']: t['newImage'] for t in manifest['targets']},
            'environmentUnchanged': True, 'modelsUnchanged': True,
            'otherServicesUnchanged': True, 'manifestSha': MANIFEST_SHA}
        (ROOT / 'deployed.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result), flush=True)
    except Exception as exc:
        rollback_ok = True
        for target in reversed(touched):
            try:
                assert digest(Path(target['composeFile']).read_bytes()) == target['composeSha'], 'compose drift during rollback'
                assert digest(Path(target['envFile']).read_bytes()) == target['envSha'], 'environment drift during rollback'
                guards.run(['docker', 'tag', target['rollbackImage'], target['runtimeTag']])
                guards.compose(target)
                restored = guards.wait_healthy(target)
                before = json.loads((ROOT / target['service'] / 'container-before.json').read_text())
                invariant(before, restored, target | {'newImage': target['rollbackImage']})
            except Exception:
                rollback_ok = False
        print(json.dumps({'deployed': False, 'errorType': type(exc).__name__, 'rollbackHealthy': rollback_ok}), flush=True)
        raise SystemExit(1) from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'preflight', 'deploy'))
    args = parser.parse_args()
    os.umask(0o077)
    try:
        prepare() if args.action == 'prepare' else deploy(preflight_only=args.action == 'preflight')
    except Exception as exc:
        print(json.dumps({'completed': False, 'errorType': type(exc).__name__,
            'reason': str(exc) if isinstance(exc, AssertionError) else 'inspect private server evidence'}), flush=True)
        raise SystemExit(1) from None
