"""Actual-image Global mock/companion cutover; execute only on the Global host.

prepare builds private candidates; preflight is read-only; deploy/rollback touch
only approved application containers. Secrets and inspections stay on the host.
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

ROOT = Path('/opt/offersteady-global/releases/20261015-global-mock-companion-135-1')
PROJECT = 'offersteady-global'
APP = '/app/apps/backend/app/'
HTML = '/usr/share/nginx/html/'
MANIFEST = 'global_desktop_release_manifest.json'
BASES = {
    'backend': ('2ba21fad6df4cbabf56c2910d5f16b0341b77c89e8c244109ceb76a531711ca2',
        'sha256:54e8e804a8bd8a39ad0adf91d7db414add952153ee8914482dac5b9df8a3a688'),
    'web': ('e3a62fdcdbf2d0b7136b788a4016abc502c84aa1874cd92475311ae2cc06fd36',
        'sha256:aa40ed431a67f81c36263b9051621cb63371b982fee55d25bc4769c29142c7c5'),
}
BACKEND = {
    'modules/mock_interview.py': '5898bf28caa004c495a12ec099fd2ecd7fc596a20adea8ac590a2cc61805faf5',
    'services/mock_interview_audio.py': 'e285d62ea12eefe2f4ef6edd29944409931fee529e0657f4555e87d1b1ba5a73',
    'services/mock_interview_diagnostics.py': 'd6d40594f9c2a003c8df5541034946adf512b2fefa294cde4b8a611b28af1aea',
    'services/mock_interview_generation.py': '60712e9638ed355f9c8976f28b9df61389be8aaba8130cd52c96964ef38022f4',
    'services/mock_interview_jobs.py': '9a24a2fc10969e0a6c443d54b09fbbc0e1bb34881b4366336ed87d9d15ba6322',
    'services/mock_interview_runtime.py': '2c08d5235f27a5226d02de26d5741ca990a3c2aa37a7514a9c45183c73fd6cf5',
}
GATES = (
    Path('/opt/offersteady-global/releases/20261011-global-performance-parity-1/deploy/check-idle.py'),
    Path('/opt/offersteady-global/releases/20260929-global-web-entry-1/deploy-web-entry/check-mock-idle.py'),
)
MODEL_FIELDS = ('product_edition', 'environment', 'chat_qwen_model', 'chat_qwen_base_url',
    'chat_quick_model', 'chat_detail_model', 'mock_interview_tts_model', 'mock_interview_tts_voice',
    'global_mock_interview_tts_ws_url', 'realtime_asr_model', 'realtime_asr_ws_url',
    'embedding_model', 'rerank_model', 'screenshot_vision_model',
    'realtime_desktop_heartbeat_write_min_interval_seconds', 'runtime_performance_ack_session_cache_seconds')
INSTALLER_NAMES = {
    ('windows', 'x64'): 'OfferSteady-Companion-Global-Setup-1.3.5-Windows-x64.exe',
    ('macos', 'arm64'): 'OfferSteady-Companion-Global-1.3.5-macOS-arm64.dmg',
    ('macos', 'x64'): 'OfferSteady-Companion-Global-1.3.5-macOS-x64.dmg',
}
INSTALLER_MIME = {'windows': 'application/vnd.microsoft.portable-executable', 'macos': 'application/x-apple-diskimage'}


class GuardError(RuntimeError):
    """Only fixed, non-sensitive validation messages may enter this exception."""


def require(condition, message):
    if not condition:
        raise GuardError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    path.write_bytes(json.dumps(value, indent=2).encode() + b'\n')
    path.chmod(0o600)


def run(args, *, cwd=None, timeout=60, input=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, check=True, timeout=timeout, input=input)


def inspect(name):
    return json.loads(run(['docker', 'inspect', name], timeout=15).stdout)[0]


def environment(container):
    return dict(item.split('=', 1) for item in container['Config'].get('Env', []) if '=' in item)


def read_container(name, path):
    return run(['docker', 'exec', name, 'cat', path]).stdout


def file_hashes(name, *, image=False, web=False):
    if web:
        args = ['sh', '-c', 'cd ' + HTML + ' && find . -type f -exec sha256sum {} +']
        command = ['docker', 'run', '--rm', '--network=none', '--entrypoint', args[0], name] + args[1:] if image else ['docker', 'exec', name] + args
        result = {}
        for line in run(command).stdout.decode().splitlines():
            checksum, path = line.split(maxsplit=1)
            require(len(checksum) == 64 and path.startswith('./'), 'invalid static checksum output')
            result[path[2:]] = checksum
        return result
    code = ("from pathlib import Path;import hashlib,json;root=Path(" + repr(APP) + ");"
        "print(json.dumps({p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() "
        "for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}))")
    args = ['python', '-B', '-c', code]
    command = ['docker', 'run', '--rm', '--network=none', '--entrypoint', args[0], name] + args[1:] if image else ['docker', 'exec', name] + args
    return json.loads(run(command).stdout)


def models(name):
    code = ("import sys,json;sys.path.insert(0,'/app/apps/backend');from app.core.config import Settings;s=Settings();"
        + 'print(json.dumps({k:getattr(s,k,None) for k in ' + repr(MODEL_FIELDS) + '}))')
    return json.loads(run(['docker', 'exec', name, 'python', '-B', '-c', code]).stdout)


def validate_manifest(manifest, proof):
    entries = manifest.get('entries', [])
    require(manifest.get('version') == 1 and len(entries) == 3, 'incomplete Global manifest')
    require({(e.get('platform'), e.get('architecture')) for e in entries} ==
        {('windows', 'x64'), ('macos', 'arm64'), ('macos', 'x64')}, 'invalid Global platforms')
    verified = proof.get('entries', [])
    require(len(verified) == 3, 'incomplete installer verification')
    for entry in entries:
        require(entry.get('version') == '1.3.5' and entry.get('protocolVersion') == '2.0'
            and entry.get('distributionStatus') == 'published' and entry.get('developmentOnly') is False,
            'invalid Global release metadata')
        name = INSTALLER_NAMES[(entry['platform'], entry['architecture'])]
        require(entry.get('fileName') == name, 'invalid platform installer filename')
        require(entry.get('objectKey') == 'global-desktop-releases/' + entry['platform'] + '/' + entry['architecture'] + '/1.3.5/' + name,
            'invalid Global platform object namespace')
        require(isinstance(entry.get('fileSizeBytes'), int) and entry['fileSizeBytes'] > 1_000_000
            and isinstance(entry.get('sha256'), str) and len(entry['sha256']) == 64
            and all(c in '0123456789abcdef' for c in entry['sha256']),
            'invalid installer integrity metadata')
        require(entry.get('signingStatus') == ('verified' if entry['platform'] == 'macos' else 'unsigned')
            and entry.get('notarized') is (entry['platform'] == 'macos'), 'invalid signature metadata')
        matches = [p for p in verified if (p.get('platform'), p.get('architecture')) == (entry['platform'], entry['architecture'])]
        require(len(matches) == 1, 'duplicate installer verification')
        checked = matches[0]
        keys = ('platform', 'architecture', 'version', 'fileName', 'objectKey', 'fileSizeBytes',
            'sha256', 'signingStatus', 'notarized')
        require(all(checked.get(k) == entry.get(k) for k in keys), 'installer proof does not match manifest')
        require(checked.get('localVerified') is True and checked.get('objectReadbackVerified') is True,
            'complete local and immutable object verification required')
        require(checked.get('contentType') == INSTALLER_MIME[entry['platform']], 'invalid platform installer MIME proof')


def check_inputs(plan):
    require(plan.get('backend') == BACKEND, 'unexpected or unverified backend delta')
    require(plan.get('verified', {}).get('backendPassed', 0) > 0
        and plan['verified'].get('syntheticOnly') is True, 'synthetic backend verification required')
    require(len(plan.get('backendBefore', {})) >= 150 and MANIFEST in plan['backendBefore'],
        'complete actual backend preservation hashes required')
    for path, checksum in BACKEND.items():
        require(digest((ROOT / 'input/backend' / path).read_bytes()) == checksum, 'backend input checksum mismatch')
    raw = (ROOT / 'input' / MANIFEST).read_bytes()
    require(digest(raw) == plan.get('manifestSha'), 'manifest input checksum mismatch')
    proof = read_json(ROOT / 'installers-verification.json')
    require(proof.get('manifestSha') == plan['manifestSha'], 'installer proof manifest mismatch')
    validate_manifest(json.loads(raw), proof)
    require(digest((ROOT / 'extra_idle_gate.py').read_bytes()) == plan.get('extraGateSha'), 'extra gate checksum mismatch')
    if plan.get('web'):
        web = plan['web']
        require(web.get('tag', '').startswith('offersteady-global-web:') and web.get('image', '').startswith('sha256:'),
            'invalid Global web candidate identity')
        require({'index.html', 'offersteady-global-build.json'} <= set(web.get('files', {})), 'incomplete web payload')
        require(set(web.get('beforeFiles', {})) <= set(web['files']), 'existing public web file missing')
        require(all(web['files'].get(k) == v for k, v in web.get('beforeFiles', {}).items() if k.startswith('assets/')),
            'existing immutable web asset changed or missing')


def compose_args(target, *, frozen=False, overlay=None):
    args = ['docker', 'compose', '-p', PROJECT, '--project-directory', target['composeDirectory']]
    for path in target['frozenEnvFiles'] if frozen else target['envFiles']:
        args.extend(['--env-file', path])
    for path in target['frozenComposeFiles'] if frozen else target['composeFiles']:
        args.extend(['-f', path])
    if overlay:
        args.extend(['-f', str(overlay)])
    return args


def rendered(target, *, frozen=False, overlay=None):
    return json.loads(run(compose_args(target, frozen=frozen, overlay=overlay) + ['config', '--format', 'json']).stdout)


def expected_overlay(rendered_before, service, image_tag):
    result = json.loads(json.dumps(rendered_before))
    result['services'][service]['image'] = image_tag
    return result


def context(before, service):
    labels = before['Config']['Labels']
    require(labels.get('com.docker.compose.project') == PROJECT
        and labels.get('com.docker.compose.service') == service, 'wrong Global Compose identity')
    files = labels['com.docker.compose.project.config_files'].split(',')
    envs = labels.get('com.docker.compose.project.environment_file', '').split(',')
    require(files and envs and all(Path(p).is_absolute() and p.startswith('/opt/offersteady-global/releases/') for p in files + envs),
        'invalid Global private Compose context')
    return {'composeDirectory': labels['com.docker.compose.project.working_dir'], 'composeFiles': files, 'envFiles': envs}


def runtime_baseline(source, before, service):
    """Restore only the historical runtime version override, never other drift."""
    result = json.loads(json.dumps(source))
    declared = result['services'][service].get('environment', {})
    actual = environment(before)
    mismatches = {key for key, value in declared.items() if str(value) != actual.get(key)}
    require(not mismatches or service == 'backend' and mismatches == {'OFFERSTEADY_APP_VERSION'},
        'rendered/runtime environment mismatch outside historical app version')
    if mismatches:
        require(isinstance(actual.get('OFFERSTEADY_APP_VERSION'), str) and bool(actual['OFFERSTEADY_APP_VERSION']),
            'actual runtime version missing')
        declared['OFFERSTEADY_APP_VERSION'] = actual['OFFERSTEADY_APP_VERSION']
    return result, bool(mismatches)


def verify_frozen_files(target, before):
    for group in ('Compose', 'Env'):
        originals, frozen = target[group.lower() + 'Files'], target['frozen' + group + 'Files']
        extra = 1 if group == 'Compose' and target.get('runtimeVersionOverlay') else 0
        require(len(frozen) == len(originals) + extra, 'frozen context file count changed')
        for path, backup in zip(originals, frozen[:len(originals)]):
            require(digest(Path(backup).read_bytes()) == target['sourceHashes'][path], 'frozen private context file changed')
    if target.get('runtimeVersionOverlay'):
        path = Path(target['runtimeVersionOverlay'])
        require(target['service'] == 'backend' and target['frozenComposeFiles'][-1] == str(path)
            and digest(path.read_bytes()) == target['runtimeVersionOverlaySha'], 'runtime version overlay changed')
        require(read_json(path) == {'services': {'backend': {'environment': {
            'OFFERSTEADY_APP_VERSION': environment(before).get('OFFERSTEADY_APP_VERSION')}}}},
            'runtime version overlay changed fields outside historical app version')


def freeze(before, service):
    target = context(before, service)
    directory = ROOT / service
    directory.mkdir(mode=0o700)
    write_json(directory / 'container-before.json', before)
    target['frozenComposeFiles'], target['frozenEnvFiles'] = [], []
    target['sourceHashes'] = {}
    for group, names in (('Compose', target['composeFiles']), ('Env', target['envFiles'])):
        for index, path in enumerate(names):
            data = Path(path).read_bytes()
            frozen = directory / f'{group.lower()}-{index}.before'
            frozen.write_bytes(data)
            frozen.chmod(0o600)
            target['frozen' + group + 'Files'].append(str(frozen))
            target['sourceHashes'][path] = digest(data)
    source = rendered(target)
    require(rendered(target, frozen=True) == source, 'frozen Compose does not reproduce original configuration')
    write_json(directory / 'rendered-source-before.json', source)
    target['sourceRenderedSha'] = digest(canonical(source))
    effective, needs_override = runtime_baseline(source, before, service)
    if needs_override:
        private_overlay = directory / 'runtime-baseline.compose.json'
        write_json(private_overlay, {'services': {service: {'environment': {
            'OFFERSTEADY_APP_VERSION': environment(before)['OFFERSTEADY_APP_VERSION']}}}})
        target['runtimeVersionOverlay'] = str(private_overlay)
        target['runtimeVersionOverlaySha'] = digest(private_overlay.read_bytes())
        target['frozenComposeFiles'].append(str(private_overlay))
    require(rendered(target, frozen=True) == effective, 'runtime baseline overlay changed unrelated configuration')
    write_json(directory / 'rendered-before.json', effective)
    target['renderedSha'] = digest(canonical(effective))
    target.update(service=service, container=f'{PROJECT}-{service}-1', beforeId=before['Id'],
        baseImage=before['Image'], beforeTag=before['Config']['Image'])
    require(source['services'][service]['image'] == target['beforeTag'], 'rendered/runtime image identity mismatch')
    require(all(str(value) == environment(before).get(key)
        for key, value in effective['services'][service].get('environment', {}).items()), 'rendered/runtime environment mismatch')
    return target


def build(directory, base_image, tag, copies):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    base_tag = 'offersteady-global-mock-base:' + base_image.removeprefix('sha256:')[:12]
    run(['docker', 'tag', base_image, base_tag])
    require(inspect(base_tag)['Id'] == base_image, 'base image identity drift')
    (directory / 'Dockerfile').write_text('FROM ' + base_tag + '\n' + ''.join(copies))
    run(['docker', 'build', '--network=none', '-t', tag, str(directory)], timeout=120)
    image = inspect(tag)
    verify_image_base(image, inspect(base_image))
    return image['Id']


def verify_image_base(candidate, base):
    require(candidate['Config'] == base['Config'], 'candidate image configuration changed')
    original = base['RootFS']['Layers']
    require(candidate['RootFS']['Layers'][:len(original)] == original, 'candidate does not derive from actual running image')


def write_overlay(target, kind, image_id):
    require(image_id.startswith('sha256:') and len(image_id) == 71, 'immutable image ID required')
    path = ROOT / target['service'] / (kind + '-image.compose.json')
    write_json(path, {'services': {target['service']: {'image': image_id}}})
    target[kind + 'Overlay'] = str(path)
    target[kind + 'OverlaySha'] = digest(path.read_bytes())
    before = read_json(ROOT / target['service'] / 'rendered-before.json')
    require(rendered(target, frozen=True, overlay=path) == expected_overlay(before, target['service'], image_id),
        'overlay changed configuration outside target image')


def verify_non_targets(manifest):
    for name, before in manifest['nonTargets'].items():
        after = inspect(name)
        require((after['Id'], after['Image'], after['State']['StartedAt']) ==
            (before['id'], before['image'], before['started']), 'unrelated component changed')


def prepare():
    require(not (ROOT / 'prepared.json').exists(), 'preparation already recorded')
    plan = read_json(ROOT / 'input.json')
    check_inputs(plan)
    services = ['backend'] + (['web'] if plan.get('web') else [])
    initial = read_json(ROOT / 'initial-safe-snapshot.json')
    non_targets = {name: row for name, row in initial.items() if name not in [f'{PROJECT}-{s}-1' for s in services]}
    for name in run(['docker', 'ps', '--format', '{{.Names}}']).stdout.decode().splitlines():
        if name not in non_targets and name not in [f'{PROJECT}-{s}-1' for s in services]:
            before = inspect(name)
            non_targets[name] = {'id': before['Id'], 'image': before['Image'], 'started': before['State']['StartedAt']}
    targets = []
    for service in services:
        name = f'{PROJECT}-{service}-1'
        before = inspect(name)
        require((before['Id'], before['Image']) == BASES[service]
            and initial[name]['id'] == before['Id'] and initial[name]['image'] == before['Image'], 'actual baseline drift')
        require(before['State']['Running'] and before['RestartCount'] == 0, 'baseline service not stable')
        target = freeze(before, service)
        target['newTag'] = f'offersteady-global-{service}:mock-companion-135-20261015-1'
        target['rollbackTag'] = f'offersteady-global-{service}:mock-companion-135-rollback-20261015-1'
        if service == 'backend':
            require(file_hashes(name) == plan['backendBefore'], 'actual backend source drift')
            old = read_container(name, APP + MANIFEST)
            require(digest(old) == plan['backendBefore'][MANIFEST], 'old manifest drift')
            (ROOT / service / 'manifest-before.json').write_bytes(old)
            copies = []
            for path in BACKEND:
                output = ROOT / 'build/backend' / path
                output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                output.write_bytes((ROOT / 'input/backend' / path).read_bytes())
                output.chmod(0o644)
                copies.append(f'COPY {path} {APP + path}\n')
            for kind, data in (('backend', (ROOT / 'input' / MANIFEST).read_bytes()), ('rollback', old)):
                output = ROOT / 'build' / kind / MANIFEST
                output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                output.write_bytes(data)
                output.chmod(0o644)
            target['rollbackImage'] = build(ROOT / 'build/rollback', before['Image'], target['rollbackTag'],
                ['COPY ' + MANIFEST + ' ' + APP + MANIFEST + '\n'])
            target['newImage'] = build(ROOT / 'build/backend', before['Image'], target['newTag'],
                copies + ['COPY ' + MANIFEST + ' ' + APP + MANIFEST + '\n'])
            require(file_hashes(target['rollbackImage'], image=True) == plan['backendBefore'], 'rollback source does not preserve actual app')
            require(file_hashes(target['newImage'], image=True) == plan['backendBefore'] | BACKEND | {MANIFEST: plan['manifestSha']},
                'candidate includes unapproved backend source')
        else:
            web = plan['web']
            require(file_hashes(name, web=True) == web['beforeFiles'], 'actual web asset drift')
            require(digest(read_container(name, '/etc/nginx/conf.d/default.conf')) == web['nginxSha'], 'actual web routing drift')
            require(inspect(web['tag'])['Id'] == web['image'], 'web candidate image identity mismatch')
            verify_image_base(inspect(web['image']), inspect(before['Image']))
            require(file_hashes(web['image'], image=True, web=True) == web['files'], 'web candidate payload mismatch')
            require(digest(run(['docker', 'run', '--rm', '--network=none', '--entrypoint', 'cat', web['image'],
                '/etc/nginx/conf.d/default.conf']).stdout) == web['nginxSha'], 'web candidate routing changed')
            target['newImage'], target['newTag'] = web['image'], web['tag']
            target['rollbackImage'] = before['Image']
            run(['docker', 'tag', target['rollbackImage'], target['rollbackTag']])
        write_overlay(target, 'new', target['newImage'])
        write_overlay(target, 'rollback', target['rollbackImage'])
        targets.append(target)
        print(json.dumps({'prepared': service, 'image': target['newImage'], 'productionChanged': False}), flush=True)
    manifest = {'targets': targets, 'nonTargets': non_targets, 'models': models(f'{PROJECT}-backend-1'),
        'inputSha': digest((ROOT / 'input.json').read_bytes()),
        'installersProofSha': digest((ROOT / 'installers-verification.json').read_bytes()),
        'gateHashes': {str(p): digest(p.read_bytes()) for p in (*GATES, ROOT / 'extra_idle_gate.py')}}
    require(manifest['models']['product_edition'] == 'global' and manifest['models']['environment'] == 'production', 'wrong effective edition')
    verify_non_targets(manifest)
    (ROOT / 'input.prepared.json').write_bytes((ROOT / 'input.json').read_bytes())
    write_json(ROOT / 'prepared.json', manifest)


def attach_web():
    """Allow one verified Web image to join a prepared, unswitched backend."""
    require(not (ROOT / 'deployed.json').exists(), 'cannot amend a deployed release')
    manifest = read_json(ROOT / 'prepared.json')
    old, plan = read_json(ROOT / 'input.prepared.json'), read_json(ROOT / 'input.json')
    require(not old.get('web') and plan.get('web') and [t['service'] for t in manifest['targets']] == ['backend'],
        'only a first Web candidate may be attached')
    require({k: v for k, v in plan.items() if k != 'web'} == old, 'backend release inputs changed while attaching Web')
    require(digest((ROOT / 'input.prepared.json').read_bytes()) == manifest['inputSha']
        and digest((ROOT / 'installers-verification.json').read_bytes()) == manifest['installersProofSha'],
        'verified installer/backend inputs changed')
    check_inputs(plan)
    verify_baseline(manifest, old)
    name, web = f'{PROJECT}-web-1', plan['web']
    before = inspect(name)
    require((before['Id'], before['Image']) == BASES['web'], 'actual Web baseline drift')
    target = freeze(before, 'web')
    require(before['State']['Running'] and before['RestartCount'] == 0, 'Web baseline service not stable')
    require(file_hashes(name, web=True) == web['beforeFiles'], 'actual Web asset drift')
    require(digest(read_container(name, '/etc/nginx/conf.d/default.conf')) == web['nginxSha'], 'actual Web routing drift')
    require(inspect(web['tag'])['Id'] == web['image'], 'Web candidate image identity mismatch')
    verify_image_base(inspect(web['image']), inspect(before['Image']))
    require(file_hashes(web['image'], image=True, web=True) == web['files'], 'Web candidate payload mismatch')
    require(digest(run(['docker', 'run', '--rm', '--network=none', '--entrypoint', 'cat', web['image'],
        '/etc/nginx/conf.d/default.conf']).stdout) == web['nginxSha'], 'Web candidate routing changed')
    target.update(newImage=web['image'], newTag=web['tag'], rollbackImage=before['Image'],
        rollbackTag='offersteady-global-web:mock-companion-135-rollback-20261015-1')
    run(['docker', 'tag', target['rollbackImage'], target['rollbackTag']])
    write_overlay(target, 'new', target['newImage'])
    write_overlay(target, 'rollback', target['rollbackImage'])
    manifest['targets'].append(target)
    manifest['nonTargets'].pop(name)
    manifest['inputSha'] = digest((ROOT / 'input.json').read_bytes())
    (ROOT / 'input.prepared.json').write_bytes((ROOT / 'input.json').read_bytes())
    verify_non_targets(manifest)
    write_json(ROOT / 'prepared.json', manifest)
    print(json.dumps({'prepared': 'web', 'image': target['newImage'], 'productionChanged': False}), flush=True)


def verify_baseline(manifest, plan):
    require([t['service'] for t in manifest['targets']] == ['backend'] + (['web'] if plan.get('web') else []), 'target scope mismatch')
    for target in manifest['targets']:
        service, name = target['service'], target['container']
        before = read_json(ROOT / service / 'container-before.json')
        current = inspect(name)
        require(name == f'{PROJECT}-{service}-1' and (target['beforeId'], target['baseImage']) == BASES[service], 'target identity changed')
        require(current['Id'] == before['Id'] == target['beforeId'] and current['Image'] == target['baseImage']
            and current['Config'] == before['Config'], 'runtime baseline drift')
        require(context(current, service) == {k: target[k] for k in ('composeDirectory', 'composeFiles', 'envFiles')}, 'Compose identity drift')
        for path, checksum in target['sourceHashes'].items():
            require(digest(Path(path).read_bytes()) == checksum, 'private deployment source drift')
        original = rendered(target)
        require(digest(canonical(original)) == target['sourceRenderedSha'], 'complete original rendered Compose drift')
        effective, _ = runtime_baseline(original, before, service)
        verify_frozen_files(target, before)
        require(rendered(target, frozen=True) == effective and digest(canonical(effective)) == target['renderedSha'],
            'complete effective frozen Compose drift')
        for kind in ('new', 'rollback'):
            require(inspect(target[kind + 'Tag'])['Id'] == target[kind + 'Image'], 'immutable image tag drift')
            require(digest(Path(target[kind + 'Overlay']).read_bytes()) == target[kind + 'OverlaySha'], 'image-only overlay drift')
            before_config = read_json(ROOT / service / 'rendered-before.json')
            require(rendered(target, frozen=True, overlay=target[kind + 'Overlay']) ==
                expected_overlay(before_config, service, target[kind + 'Image']), 'image-only rendered config drift')
    require(file_hashes(f'{PROJECT}-backend-1') == plan['backendBefore'], 'backend preservation source drift')
    require(models(f'{PROJECT}-backend-1') == manifest['models'], 'effective models/configuration drift')
    if plan.get('web'):
        require(file_hashes(f'{PROJECT}-web-1', web=True) == plan['web']['beforeFiles'], 'web preservation drift')
    verify_non_targets(manifest)


def idle_gate(manifest):
    for script, checksum in manifest['gateHashes'].items():
        data = Path(script).read_bytes()
        require(digest(data) == checksum, 'reviewed idle gate changed')
        result = subprocess.run(['docker', 'exec', '-i', '-w', '/app/apps/backend', f'{PROJECT}-backend-1', 'python', '-B', '-'],
            input=data, capture_output=True, timeout=25)
        # Print only status: old subprocess output must never escape on failure.
        print(json.dumps({'gate': Path(script).name, 'passed': result.returncode == 0}), flush=True)
        require(result.returncode == 0, 'protected Global user work; cutover deferred')


def invariant(before, after, expected_image):
    require(after['Image'] == expected_image and environment(before) == environment(after), 'effective image or environment changed')
    # Only generated container hostname, image reference, equivalent Env order
    # and Compose bookkeeping may differ after an image-only recreation.
    def application_config(container):
        return {k: v for k, v in container['Config'].items() if k not in ('Hostname', 'Image', 'Env', 'Labels')}
    require(application_config(before) == application_config(after), 'complete container configuration changed')
    require(before['HostConfig'] == after['HostConfig'], 'complete host configuration changed')
    def application_labels(container):
        return {k: v for k, v in container['Config'].get('Labels', {}).items() if not k.startswith('com.docker.compose.')}
    require(application_labels(before) == application_labels(after), 'application labels changed')
    def mounts(container):
        return sorted(container['Mounts'], key=lambda item: (item.get('Type', ''), item.get('Destination', '')))
    require(mounts(before) == mounts(after), 'data volume or mount changed')


def switch(target, kind):
    require(inspect(target[kind + 'Tag'])['Id'] == target[kind + 'Image'], 'candidate/rollback tag drift')
    before_config = read_json(ROOT / target['service'] / 'rendered-before.json')
    require(digest(canonical(before_config)) == target['renderedSha'], 'frozen rendered configuration changed')
    before = read_json(ROOT / target['service'] / 'container-before.json')
    verify_frozen_files(target, before)
    require(digest(Path(target[kind + 'Overlay']).read_bytes()) == target[kind + 'OverlaySha'], 'switch image overlay changed')
    require(rendered(target, frozen=True, overlay=target[kind + 'Overlay']) ==
        expected_overlay(before_config, target['service'], target[kind + 'Image']), 'switch configuration drift')
    run(compose_args(target, frozen=True, overlay=target[kind + 'Overlay']) +
        ['up', '-d', '--no-build', '--no-deps', '--pull', 'never', '--force-recreate', target['service']], timeout=120)
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        after = inspect(target['container'])
        if after['State']['Running'] and after['RestartCount'] == 0:
            health = after['State'].get('Health', {}).get('Status')
            if health == 'healthy' or health is None and time.monotonic() > deadline-40:
                require(after['Config']['Image'] == target[kind + 'Image'], 'effective immutable image reference changed')
                invariant(read_json(ROOT / target['service'] / 'container-before.json'), after, target[kind + 'Image'])
                return
        time.sleep(1)
    raise GuardError('application health check failed')


def verify_live(manifest, plan, *, rolled_back=False):
    expected = plan['backendBefore'] if rolled_back else plan['backendBefore'] | BACKEND | {MANIFEST: plan['manifestSha']}
    require(file_hashes(f'{PROJECT}-backend-1') == expected, 'effective backend source mismatch')
    require(models(f'{PROJECT}-backend-1') == manifest['models'], 'effective Global model/configuration changed')
    if plan.get('web'):
        expected_web = plan['web']['beforeFiles'] if rolled_back else plan['web']['files']
        require(file_hashes(f'{PROJECT}-web-1', web=True) == expected_web, 'effective static assets mismatch')
        require(digest(read_container(f'{PROJECT}-web-1', '/etc/nginx/conf.d/default.conf')) == plan['web']['nginxSha'], 'routing changed')
    verify_non_targets(manifest)
    with urlopen('https://offersteady.com/healthz', timeout=15) as response:
        require(response.status == 200 and json.loads(response.read())['data']['status'] == 'ok', 'public health check failed')


def rollback(manifest, plan, touched):
    success = True
    for target in reversed(touched):
        try:
            switch(target, 'rollback')
        except Exception:
            success = False
    if success:
        try:
            verify_live(manifest, plan, rolled_back=True)
        except Exception:
            success = False
    write_json(ROOT / 'rollback-result.json', {'rolledBack': success, 'atMs': int(time.time()*1000)})
    if (ROOT / 'deployed.json').exists():
        deployed = read_json(ROOT / 'deployed.json')
        deployed.update(deployed=False, rolledBack=success)
        write_json(ROOT / 'deployed.json', deployed)
    print(json.dumps({'rolledBack': success, 'completeConfigurationVerified': success}), flush=True)
    return success


def manual_rollback():
    """Refuse to overwrite another release or interrupted user work."""
    manifest, plan = read_json(ROOT / 'prepared.json'), read_json(ROOT / 'input.json')
    require(digest((ROOT / 'input.json').read_bytes()) == manifest['inputSha']
        and digest((ROOT / 'installers-verification.json').read_bytes()) == manifest['installersProofSha'],
        'verified rollback inputs changed')
    check_inputs(plan)
    require([target['service'] for target in manifest['targets']] == ['backend'] + (['web'] if plan.get('web') else []),
        'rollback target scope changed')
    for target in manifest['targets']:
        service, name = target['service'], target['container']
        require(name == f'{PROJECT}-{service}-1' and (target['beforeId'], target['baseImage']) == BASES[service],
            'rollback target identity changed')
        before = read_json(ROOT / service / 'container-before.json')
        current = inspect(name)
        require(current['Image'] in {target['baseImage'], target['newImage'], target['rollbackImage']},
            'another release is running; rollback refused')
        context(current, service)
        invariant(before, current, current['Image'])
    verify_non_targets(manifest)
    idle_gate(manifest)
    require(rollback(manifest, plan, manifest['targets']), 'rollback verification failed')


def deploy(*, preflight_only=False):
    require(not (ROOT / 'deployed.json').exists(), 'deployment already recorded')
    manifest, plan = read_json(ROOT / 'prepared.json'), read_json(ROOT / 'input.json')
    require(digest((ROOT / 'input.json').read_bytes()) == manifest['inputSha']
        and digest((ROOT / 'installers-verification.json').read_bytes()) == manifest['installersProofSha'], 'verified release inputs changed')
    check_inputs(plan)
    report = read_json(ROOT / 'candidate-verification.json')
    require(report.get('passed') is True and report.get('images') == {t['service']: t['newImage'] for t in manifest['targets']},
        'actual candidate image verification required')
    if plan.get('web'):
        require(report.get('browserPassed') is True and report.get('webFilesSha') == digest(canonical(plan['web']['files'])),
            'actual candidate browser/payload verification required')
    verify_baseline(manifest, plan)
    idle_gate(manifest)
    if preflight_only:
        print(json.dumps({'preflightPassed': True, 'productionChanged': False}), flush=True)
        return
    touched = []
    try:
        idle_gate(manifest)
        verify_baseline(manifest, plan)
        for target in manifest['targets']:
            touched.append(target)
            switch(target, 'new')
            print(json.dumps({'switched': target['service'], 'image': target['newImage']}), flush=True)
        verify_live(manifest, plan)
        result = {'deployed': True, 'atMs': int(time.time()*1000), 'images': report['images'],
            'manifestSha': plan['manifestSha'], 'configurationUnchanged': True, 'nonTargetsUnchanged': True}
        write_json(ROOT / 'deployed.json', result)
        print(json.dumps(result), flush=True)
    except Exception as exc:
        success = rollback(manifest, plan, touched)
        print(json.dumps({'deployed': False, 'errorType': type(exc).__name__, 'rollbackHealthy': success}), flush=True)
        raise SystemExit(1) from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'attach-web', 'preflight', 'deploy', 'rollback'))
    action = parser.parse_args().action
    os.umask(0o077)
    try:
        if action == 'prepare':
            prepare()
        elif action == 'attach-web':
            attach_web()
        elif action == 'rollback':
            manual_rollback()
        else:
            deploy(preflight_only=action == 'preflight')
    except Exception as exc:
        print(json.dumps({'completed': False, 'errorType': type(exc).__name__,
            'reason': str(exc) if isinstance(exc, GuardError) else 'inspect private server evidence'}), flush=True)
        raise SystemExit(1) from None
