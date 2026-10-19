"""Global resume optimizer release. Private Compose snapshots stay on server.

Configuration-freezing primitives are preserved from the reviewed Global
mock/companion controller; cutover/recovery use independent baseline activity
checks, immutable images and strict ownership rather than the candidate's code.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path('/opt/offersteady-global/releases/20261017-global-resume-optimizer-1')
PROJECT = 'offersteady-global'
CONTAINER = PROJECT + '-backend-1'
BASE_IMAGE = 'sha256:c0503cb8a166dc4cfb64e3d4ca1f98792e788cdb29147d8282a8e43d0146726a'
BASES = {
 'backend': ('e82bbc37821cc6f72112b66593f5492b6f5276f331245e2e703aae97bc2842e3', BASE_IMAGE),
 'web': ('acf077948f491bacb9ba8fc5224fafb4f615d734e3c36e139bf68397647c15c0', 'sha256:ab7706981124579a9fb6e703702202c299817af1a78330068637bd7ba6eaca0c'),
}
FLAG = 'OFFERSTEADY_GLOBAL_RESUME_OPTIMIZER_ENABLED'
GATES = frozenset({'legacy-gates/check-idle.py', 'legacy-gates/check-mock-idle.py', 'global_mock_companion_idle_gate.py', 'extra_idle_gate.py', 'active_work_gate.py', 'resume_optimizer_idle_gate.py'})


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

def verify_image_base(candidate, base):
    require(candidate['Config'] == base['Config'], 'candidate image configuration changed')
    original = base['RootFS']['Layers']
    require(candidate['RootFS']['Layers'][:len(original)] == original, 'candidate does not derive from actual running image')


def save(name, value):
    write_json(ROOT / name, value)


@contextmanager
def release_lock():
    with (ROOT / 'release.lock').open('a') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GuardError('another_release_action_is_running') from None
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def backend_inventory(name):
    code = """from pathlib import Path
import hashlib,json
r=Path('/app');paths=[p for d in ('apps/backend/app','apps/backend/migrations','ai/prompts') for p in (r/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='.desktop-release-manifest.lock'];paths.append(r/'apps/backend/pyproject.toml');print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}))
"""
    return json.loads(run(['docker', 'exec', name, 'python', '-B', '-c', code]).stdout)


def web_inventory(name, *, image=False):
    args = ['sh', '-c', 'cd /usr/share/nginx/html && find . -type f -exec sha256sum {} +']
    command = ['docker', 'run', '--rm', '--read-only', '--network=none', '--entrypoint', args[0], name] + args[1:] if image else ['docker', 'exec', name] + args
    result = {}
    for line in run(command).stdout.decode().splitlines():
        checksum, path = line.split(maxsplit=1)
        require(re.fullmatch('[0-9a-f]{64}', checksum) and path.startswith('./'), 'invalid_public_inventory')
        result[path[2:]] = checksum
    return result


def gate_contract(path):
    if path == 'legacy-gates/check-idle.py':
        return {'liveInterviews', 'recentPreparing', 'livePageLeases', 'recentAudioTracks', 'unfinishedTasks', 'runningMaterialJobs'}, {'atMs'}
    if path == 'legacy-gates/check-mock-idle.py':
        return {'activeOrRecentMockInterviews'}, set()
    if path == 'global_mock_companion_idle_gate.py':
        return {'mockControlOrGenerationLeases', 'material_processing_jobs', 'material_deletion_jobs', 'material_reconcile_jobs', 'protectedMaterialTasks', 'activeEntityOrLegacyPageLeases'}, set()
    if path == 'resume_optimizer_idle_gate.py':
        return {'resumeOptimizerQueuedOrRunning', 'unknownResumeOptimizerStates', 'resumeOptimizerReadFailures'}, set()
    require(path in ('active_work_gate.py', 'extra_idle_gate.py'), 'unknown_protection_gate')
    values = {}
    for node in ast.parse((ROOT / path).read_text()).body:
        if isinstance(node, ast.Assign):
            for name in node.targets:
                if isinstance(name, ast.Name) and name.id in ('PROTECTED', 'MOCK_FIELDS'):
                    values[name.id] = set(ast.literal_eval(node.value))
    protected = values['PROTECTED']
    informational = values.get('MOCK_FIELDS', set()) - protected
    if path == 'active_work_gate.py':
        informational.add('ignoredLegacyFailedQueuedTasks')
    require(bool(protected), 'empty_protection_contract')
    return protected, informational


def exact_payload(directory, expected):
    paths = list(directory.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'payload_symlink_rejected')
    require({str(p.relative_to(directory)) for p in paths if p.is_file()} == set(expected), 'unlisted_payload_file')


def check_inputs():
    plan = read_json(ROOT / 'input.json')
    require(plan['baselines'] == {s: {'id': v[0], 'image': v[1]} for s, v in BASES.items()}, 'baseline_input_mismatch')
    require(set(plan['gates']) == GATES, 'incomplete_user_protection')
    for gate in GATES:
        protected, informational = gate_contract(gate)
        require(set(plan['gateFields'][gate]) == protected and set(plan['gateInformationalFields'].get(gate, [])) == informational, 'protected_gate_contract_changed')
    require(plan['verified']['passed'] is True and plan['verified']['syntheticOnly'] is True
            and plan['verified']['backendTests'] > 0 and plan['verified']['webTests'] > 0
            and plan['verified']['browserScenarios'] >= 26 and plan['verified']['exportsRendered'] is True,
            'required_actual_local_verification_missing')
    require(plan['files'] and plan['webFiles'] and plan['wheels'], 'missing_verified_payload')
    for directory, files in (('input', plan['files']), ('web-input', plan['webFiles']), ('wheels', plan['wheels'])):
        exact_payload(ROOT / directory, files)
    for path, checksum in plan['files'].items():
        require(path in plan['approvedFiles'] and '..' not in Path(path).parts and not Path(path).is_absolute(), 'unapproved_source_path')
        require(digest((ROOT / 'input' / path).read_bytes()) == checksum, 'source_payload_drift')
    require(set(plan['approvedFiles']) == set(plan['files']), 'source_scope_changed')
    for path, checksum in plan['webFiles'].items():
        require(not Path(path).is_absolute() and '..' not in Path(path).parts, 'invalid_static_path')
        require(digest((ROOT / 'web-input' / path).read_bytes()) == checksum, 'static_payload_drift')
        require(not (path.startswith('assets/') and path in plan['webBefore'] and checksum != plan['webBefore'][path]), 'immutable_web_asset_overwrite')
    for path, checksum in plan['wheels'].items():
        require(Path(path).name == path and path == 'reportlab-4.4.9-py3-none-any.whl', 'unapproved_runtime_dependency')
        require(digest((ROOT / 'wheels' / path).read_bytes()) == checksum, 'dependency_wheel_drift')
    require({Path(__file__).name, *GATES, 'probe/candidate-probe.py', 'probe/expectations.json', 'candidate-verification.json'} <= set(plan['supportFiles']), 'release_support_unbound')
    for path, checksum in plan['supportFiles'].items():
        require(not Path(path).is_absolute() and '..' not in Path(path).parts, 'invalid_support_path')
        require(digest((ROOT / path).read_bytes()) == checksum, 'release_support_drift')
    verification = read_json(ROOT / 'candidate-verification.json')
    require(verification['passed'] is True and verification['sourceFrozenAfterTests'] is True
            and verification['files'] == plan['files'] and verification['webFiles'] == plan['webFiles'], 'verification_payload_mismatch')
    require(verification['verified'] == plan['verified'] and verification['records']
            and all(record['returncode'] == 0 for record in verification['records']), 'actual_verification_results_mismatch')
    return plan


def current_schema():
    code = "import json;from urllib.request import urlopen;print(json.dumps(json.load(urlopen('http://127.0.0.1:8000/openapi.json',timeout=10))))"
    return json.loads(run(['docker', 'exec', CONTAINER, 'python', '-B', '-c', code]).stdout)


def assert_schema(actual, expected):
    require(actual == expected, 'complete_runtime_api_schema_drift')


def settings_digest(plan):
    code = ("from app.core.config import Settings;import json,hashlib;s=Settings(_env_file=None);"
            f"data={{k:getattr(s,k) for k in {plan['configFields']!r}}};"
            "print(json.dumps({'sha':hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'enabled':getattr(s,'global_resume_optimizer_enabled',False)}))")
    return json.loads(run(['docker', 'exec', '-w', '/app/apps/backend', CONTAINER, 'python', '-B', '-c', code]).stdout)


def verify_non_targets(manifest):
    for name, expected in manifest['nonTargets'].items():
        c = inspect(name)
        require((c['Id'], c['Image'], c['State']['StartedAt']) == (expected['id'], expected['image'], expected['startedAt']), 'non_target_identity_changed')
    for tag, expected in manifest['sharedTags'].items():
        require(inspect(tag)['Id'] == expected, 'shared_runtime_tag_changed')


def expected_config(before, target, kind):
    value = expected_overlay(before, target['service'], target[kind + 'Image'])
    if kind == 'new' and target['service'] == 'backend':
        value['services']['backend'].setdefault('environment', {})[FLAG] = 'true'
    return value


def write_overlay(target, kind):
    value = {'services': {target['service']: {'image': target[kind + 'Image']}}}
    if target['service'] == 'backend' and kind == 'new':
        value['services']['backend']['environment'] = {FLAG: 'true'}
    path = ROOT / target['service'] / (kind + '-image.compose.json')
    write_json(path, value)
    target[kind + 'Overlay'] = str(path)
    target[kind + 'OverlaySha'] = digest(path.read_bytes())
    before = read_json(ROOT / target['service'] / 'rendered-before.json')
    require(rendered(target, frozen=True, overlay=path) == expected_config(before, target, kind), 'unrelated_rendered_configuration_change')


def verify_files(manifest, plan):
    require(digest((ROOT / 'input.json').read_bytes()) == manifest['inputSha'], 'release_manifest_drift')
    require(digest((ROOT / 'runtime.env.private').read_bytes()) == manifest['runtimeEnvSha'], 'recovery_environment_drift')
    for target in manifest['targets']:
        before = read_json(ROOT / target['service'] / 'container-before.json')
        require(digest(canonical(before)) == target['beforeInspectSha'], 'frozen_inspection_drift')
        for path, sha in target['sourceHashes'].items():
            require(digest(Path(path).read_bytes()) == sha, 'private_original_context_drift')
        verify_frozen_files(target, before)
        require(digest(canonical(rendered(target))) == target['sourceRenderedSha'], 'original_complete_compose_drift')
        require(digest(canonical(rendered(target, frozen=True))) == target['renderedSha'], 'frozen_complete_compose_drift')
        for kind in ('new', 'rollback'):
            require(inspect(target[kind + 'Tag'])['Id'] == target[kind + 'Image'], 'fixed_image_tag_drift')
            require(digest(Path(target[kind + 'Overlay']).read_bytes()) == target[kind + 'OverlaySha'], 'image_overlay_drift')
            require(rendered(target, frozen=True, overlay=target[kind + 'Overlay']) == expected_config(read_json(ROOT / target['service'] / 'rendered-before.json'), target, kind), 'complete_rendered_overlay_drift')
    verify_non_targets(manifest)


def baseline_command(manifest, image=BASE_IMAGE):
    before = read_json(ROOT / 'backend/container-before.json')
    network = before['HostConfig']['NetworkMode']
    require(re.fullmatch('[A-Za-z0-9_.-]+', network) and network not in ('host', 'none'), 'invalid_protected_network')
    return ['docker', 'run', '--rm', '-i', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '64', '--memory', '512m', '--network', network, '--env-file', str(ROOT / 'runtime.env.private'), '--workdir', '/app/apps/backend', '--entrypoint', 'python', image, '-B', '-']


def idle_gates(manifest, plan):
    """Always independent of candidate code, environment, health and lifespan."""
    records = []
    for path in plan['gates']:
        require(digest((ROOT / path).read_bytes()) == plan['supportFiles'][path], 'protected_gate_source_drift')
        try:
            result = subprocess.run(baseline_command(manifest), input=(ROOT / path).read_bytes(), capture_output=True, timeout=25)
            counts = json.loads(result.stdout)
            protected = plan['gateFields'][path]
            require(isinstance(counts, dict) and set(counts) == set(protected) | set(plan['gateInformationalFields'].get(path, [])), 'gate_summary_shape_changed')
            require(all(type(v) is int and v >= 0 for v in counts.values()), 'invalid_gate_aggregate')
        except Exception:
            raise GuardError('protected_work_gate_unavailable') from None
        records.append({'gate': path, 'exitCode': result.returncode, 'counts': counts})
        save('last-idle-gates.json', records)
        require(result.returncode == 0 and all(counts[k] == 0 for k in protected), 'protected_user_work_cutover_deferred')
    return records


def runtime_invariant(before, after, target, kind):
    require(after['Image'] == target[kind + 'Image'], 'runtime_image_changed')
    expected = environment(before)
    if target['service'] == 'backend' and kind == 'new':
        expected[FLAG] = 'true'
    require(environment(after) == expected, 'runtime_environment_changed')
    for key in set(before['Config']) | set(after['Config']):
        if key not in ('Image', 'Hostname', 'Labels', 'Env'):
            require(before['Config'].get(key) == after['Config'].get(key), 'application_configuration_changed')
    hostname = after['Id'][:12] if before['Config']['Hostname'] == before['Id'][:12] else before['Config']['Hostname']
    require(after['Config']['Hostname'] == hostname, 'container_hostname_changed')
    labels = lambda c: {k: v for k, v in c['Config'].get('Labels', {}).items() if not k.startswith('com.docker.compose.')}
    require(labels(before) == labels(after) and before['HostConfig'] == after['HostConfig'] and before['Mounts'] == after['Mounts'], 'host_mount_or_label_changed')


def assert_owned(manifest, target, progress):
    current = inspect(target['container'])
    if target['service'] not in progress:
        require((current['Id'], current['Image']) == BASES[target['service']], 'baseline_container_owner_changed')
        require(current['Config'] == read_json(ROOT / target['service'] / 'container-before.json')['Config'], 'baseline_container_config_changed')
        return 'rollback'
    entry = progress[target['service']]
    require(current['Id'] == entry['id'] and current['Image'] == entry['image'], 'release_container_owner_changed')
    kind = entry['kind']
    expected_files = ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']])
    labels = current['Config']['Labels']
    require(labels.get('com.docker.compose.project') == PROJECT and labels.get('com.docker.compose.service') == target['service'] and labels.get('com.docker.compose.project.config_files') == expected_files
            and labels.get('com.docker.compose.project.working_dir') == target['composeDirectory']
            and labels.get('com.docker.compose.project.environment_file') == ','.join(target['frozenEnvFiles']), 'released_compose_owner_changed')
    return kind


def probe(manifest):
    target = manifest['targets'][0]
    command = ['docker', 'run', '--rm', '--read-only', '--network=none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '64', '--memory', '768m', '--env-file', str(ROOT / 'runtime.env.private'), '-e', FLAG + '=true', '--mount', 'type=bind,src=' + str(ROOT / 'probe') + ',dst=/verify,readonly', '--workdir', '/app/apps/backend', '--entrypoint', 'python', target['newImage'], '-B', '/verify/candidate-probe.py']
    report = json.loads(run(command, timeout=60).stdout)
    require(report['passed'] is True, 'actual_candidate_probe_failed')
    return report


def reconcile_intent(manifest, progress):
    if not (ROOT / 'switch-intent.json').exists():
        return
    intent = read_json(ROOT / 'switch-intent.json')
    if progress != intent['previousProgress']:
        return
    verify_files(manifest, check_inputs())
    target = next(t for t in manifest['targets'] if t['service'] == intent['service'])
    kind = intent['kind']
    require(kind in ('new', 'rollback'), 'invalid_pending_switch_kind')
    current = inspect(target['container'])
    labels = current['Config']['Labels']
    expected_files = ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']])
    if current['Image'] == target[kind + 'Image'] and labels.get('com.docker.compose.project') == PROJECT and labels.get('com.docker.compose.service') == target['service'] and labels.get('com.docker.compose.project.config_files') == expected_files:
        require(labels.get('com.docker.compose.project.working_dir') == target['composeDirectory']
                and labels.get('com.docker.compose.project.environment_file') == ','.join(target['frozenEnvFiles']), 'pending_switch_context_drift')
        runtime_invariant(read_json(ROOT / target['service'] / 'container-before.json'), current, target, kind)
        progress[target['service']] = {'id': current['Id'], 'image': current['Image'], 'kind': kind}
        save('progress.json', progress)


def prepare():
    require(not (ROOT / 'prepared.json').exists(), 'already_prepared')
    plan = check_inputs()
    require(backend_inventory(CONTAINER) == plan['beforeInventory'], 'actual_backend_source_drift')
    require(web_inventory(PROJECT + '-web-1') == plan['webBefore'], 'actual_web_source_drift')
    assert_schema(current_schema(), plan['openapiBefore'])
    require(settings_digest(plan) == {'sha': plan['configBeforeSha'], 'enabled': False}, 'effective_baseline_configuration_drift')
    non_targets = {}
    for name in run(['docker', 'ps', '--format', '{{.Names}}']).stdout.decode().splitlines():
        if name not in (CONTAINER, PROJECT + '-web-1'):
            c = inspect(name)
            non_targets[name] = {'id': c['Id'], 'image': c['Image'], 'startedAt': c['State']['StartedAt']}
    require(all(non_targets.get(name) == value for name, value in plan['nonTargets'].items()), 'initial_non_target_identity_drift')
    require({name for name in non_targets if name.startswith(PROJECT + '-')} == set(plan['nonTargets']), 'initial_global_component_set_drift')
    targets = []
    for service in ('backend', 'web'):
        c = inspect(PROJECT + '-' + service + '-1')
        require((c['Id'], c['Image']) == BASES[service] and c['State']['Running'] and c['RestartCount'] == 0, 'actual_runtime_baseline_changed')
        frozen_path = ROOT / service / 'frozen-target.json'
        if frozen_path.exists():
            target = read_json(frozen_path)
            require(target['beforeId'] == c['Id'] and target['baseImage'] == c['Image'], 'interrupted_prepare_baseline_changed')
            prior = read_json(ROOT / service / 'container-before.json')
            require(all(prior[k] == c[k] for k in ('Config', 'HostConfig', 'Mounts')), 'interrupted_prepare_runtime_changed')
            verify_frozen_files(target, c)
            require(all(digest(Path(p).read_bytes()) == sha for p, sha in target['sourceHashes'].items()), 'interrupted_prepare_context_changed')
            require(digest(canonical(rendered(target))) == target['sourceRenderedSha'] and digest(canonical(rendered(target, frozen=True))) == target['renderedSha'], 'interrupted_prepare_full_render_changed')
        else:
            target = freeze(c, service)
            write_json(frozen_path, target)
        target.update(beforeInspectSha=digest(canonical(read_json(ROOT / service / 'container-before.json'))), newTag=f'offersteady-global-{service}:resume-optimizer-20261017-1', rollbackTag=f'offersteady-global-{service}:resume-optimizer-rollback-20261017-1', rollbackImage=c['Image'])
        run(['docker', 'tag', c['Image'], target['rollbackTag']])
        build = ROOT / 'build' / service
        if build.exists():
            shutil.rmtree(build)
        build.mkdir(parents=True)
        base_tag = 'offersteady-global-resume-base:' + service
        run(['docker', 'tag', c['Image'], base_tag])
        require(inspect(base_tag)['Id'] == c['Image'], 'build_base_tag_drift')
        lines = ['FROM ' + base_tag]
        if service == 'backend':
            shutil.copytree(ROOT / 'input', build / 'input')
            shutil.copytree(ROOT / 'wheels', build / 'wheels')
            lines += ['COPY input/ /app/', 'COPY wheels/ /tmp/resume-export-wheels/', 'RUN python -m pip install --no-index --no-deps /tmp/resume-export-wheels/reportlab-4.4.9-py3-none-any.whl && rm -rf /tmp/resume-export-wheels']
        else:
            shutil.copytree(ROOT / 'web-input', build / 'web')
            lines += ['COPY web/ /usr/share/nginx/html/']
        (build / 'Dockerfile').write_text('\n'.join(lines) + '\n')
        run(['docker', 'build', '--network=none', '--pull=false', '-t', target['newTag'], str(build)], timeout=180)
        image = inspect(target['newTag'])
        verify_image_base(image, inspect(c['Image']))
        target['newImage'] = image['Id']
        write_overlay(target, 'new')
        write_overlay(target, 'rollback')
        targets.append(target)
    before = read_json(ROOT / 'backend/container-before.json')
    env = environment(before)
    require(all('\n' not in k + v and '\r' not in k + v for k, v in env.items()), 'unsupported_private_environment_value')
    private_env = ROOT / 'runtime.env.private'
    private_env.write_text(''.join(k + '=' + v + '\n' for k, v in sorted(env.items())))
    private_env.chmod(0o600)
    manifest = {'targets': targets, 'nonTargets': non_targets, 'sharedTags': {t: inspect(t)['Id'] for t in plan['sharedTags']}, 'runtimeEnvSha': digest(private_env.read_bytes()), 'inputSha': digest((ROOT / 'input.json').read_bytes())}
    require(web_inventory(targets[1]['newImage'], image=True) == plan['webBefore'] | plan['webFiles'], 'candidate_did_not_preserve_all_static_assets')
    require(digest(run(['docker', 'run', '--rm', '--network=none', '--entrypoint', 'cat', targets[1]['newImage'], '/etc/nginx/conf.d/default.conf']).stdout) == plan['nginxSha'], 'candidate_nginx_changed')
    save('candidate-image-probe.json', probe(manifest))
    verify_files(manifest, plan)
    save('prepared.json', manifest)
    print(json.dumps({'prepared': True, 'images': {t['service']: t['newImage'] for t in targets}, 'productionChanged': False}), flush=True)


def verify_current(manifest, plan, progress, *, final=False):
    verify_files(manifest, plan)
    for target in manifest['targets']:
        kind = assert_owned(manifest, target, progress)
        current = inspect(target['container'])
        require(current['State']['Running'] and current['RestartCount'] == 0, 'application_unhealthy')
        runtime_invariant(read_json(ROOT / target['service'] / 'container-before.json'), current, target, kind)
        if target['service'] == 'backend':
            require(current['State'].get('Health', {}).get('Status') == 'healthy', 'backend_unhealthy')
            require(backend_inventory(CONTAINER) == plan['beforeInventory'] | (plan['files'] if kind == 'new' else {}), 'runtime_source_mismatch')
            assert_schema(current_schema(), plan['openapiAfter'] if kind == 'new' else plan['openapiBefore'])
            require(settings_digest(plan) == {'sha': plan['configBeforeSha'], 'enabled': kind == 'new'}, 'runtime_settings_mismatch')
        else:
            require(web_inventory(target['container']) == plan['webBefore'] | (plan['webFiles'] if kind == 'new' else {}), 'runtime_static_mismatch')
            require(digest(read_container(target['container'], '/etc/nginx/conf.d/default.conf')) == plan['nginxSha'], 'runtime_nginx_changed')
        if final:
            require(kind == 'new', 'release_incomplete')


def switch(manifest, target, kind, progress):
    verify_files(manifest, check_inputs())
    assert_owned(manifest, target, progress)
    save('switch-intent.json', {'service': target['service'], 'kind': kind, 'previousProgress': progress})
    old = inspect(target['container'])
    try:
        run(compose_args(target, frozen=True, overlay=target[kind + 'Overlay']) + ['up', '-d', '--no-build', '--no-deps', '--pull', 'never', target['service']], timeout=120)
    finally:
        current = inspect(target['container'])
        if current['Image'] == target[kind + 'Image'] and current['Config']['Labels'].get('com.docker.compose.project.config_files') == ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']]):
            labels = current['Config']['Labels']
            require(labels.get('com.docker.compose.project') == PROJECT and labels.get('com.docker.compose.service') == target['service']
                    and labels.get('com.docker.compose.project.working_dir') == target['composeDirectory']
                    and labels.get('com.docker.compose.project.environment_file') == ','.join(target['frozenEnvFiles']), 'completed_switch_context_drift')
            runtime_invariant(read_json(ROOT / target['service'] / 'container-before.json'), current, target, kind)
            progress[target['service']] = {'id': current['Id'], 'image': current['Image'], 'kind': kind}
            save('progress.json', progress)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        current = inspect(target['container'])
        if current['Image'] == target[kind + 'Image'] and current['State']['Running'] and current['RestartCount'] == 0 and (current['State'].get('Health', {}).get('Status') == 'healthy' or target['service'] == 'web'):
            runtime_invariant(read_json(ROOT / target['service'] / 'container-before.json'), current, target, kind)
            if target['service'] == 'backend':
                addresses = lambda c: {k: v.get('IPAddress') for k, v in c['NetworkSettings']['Networks'].items()}
                if addresses(old) != addresses(current):
                    for name in (PROJECT + '-web-1', PROJECT + '-admin-1'):
                        run(['docker', 'exec', name, 'nginx', '-t'])
                        run(['docker', 'exec', name, 'nginx', '-s', 'reload'])
                    save('proxy-refresh.json', {'proxyReloaded': [PROJECT + '-web-1', PROJECT + '-admin-1']})
            return
        time.sleep(1)
    raise GuardError('target_health_failed')


def migrate(manifest):
    code = """from pathlib import Path
import psycopg
from app.core.config import Settings
from app.services.postgres_migrations import apply_sql_migrations
s=Settings(_env_file=None)
with psycopg.connect(s.database_url,connect_timeout=3,options='-c lock_timeout=2000 -c statement_timeout=10000') as c:
 with c.cursor() as cursor:
  apply_sql_migrations(cursor,[Path('/app/apps/backend/migrations/versions/0053_global_resume_optimizer.sql')])
print('{"migrationApplied":true}')
"""
    result = json.loads(run(baseline_command(manifest, manifest['targets'][0]['newImage']), input=code.encode(), timeout=20).stdout)
    require(result == {'migrationApplied': True}, 'additive_migration_failed')
    save('migration-result.json', result)


def public_checks():
    results = []
    for path in ('/healthz', '/login', '/offersteady-global-build.json', '/app/resume-optimizer'):
        with urlopen(Request('https://offersteady.com' + path, headers={'Cache-Control': 'no-cache'}), timeout=15) as response:
            require(response.status == 200, 'public_route_unavailable')
            data = response.read()
            if path == '/healthz':
                require(json.loads(data)['data']['status'] == 'ok', 'public_health_unavailable')
            results.append({'path': path, 'status': 200, 'sha256': digest(data)})
    for path in ('/api/v1/resume-optimizer/capabilities', '/api/v1/resume-optimizer/jobs/synthetic-invalid/export?format=pdf&expectedRevision=1&factsConfirmed=true'):
        try:
            urlopen(Request('https://offersteady.com' + path, headers={'Cache-Control': 'no-cache'}), timeout=15)
        except HTTPError as response:
            require(response.code == 401 and response.headers.get('Cache-Control') == 'private, no-store', 'anonymous_optimizer_guard_failed')
            results.append({'path': path, 'status': 401, 'privateNoStore': True})
        else:
            raise GuardError('anonymous_optimizer_guard_failed')
    return results


def _deploy(*, preflight=False):
    plan, manifest = check_inputs(), read_json(ROOT / 'prepared.json')
    progress = read_json(ROOT / 'progress.json') if (ROOT / 'progress.json').exists() else {}
    reconcile_intent(manifest, progress)
    require(not (ROOT / 'rollback-result.json').exists(), 'release_was_rolled_back_prepare_a_new_revision')
    if (ROOT / 'deployed.json').exists():
        verify_current(manifest, plan, progress, final=True)
        print(json.dumps({'alreadyDeployed': True, 'verified': True}), flush=True)
        return
    verify_current(manifest, plan, progress)
    idle_gates(manifest, plan)
    if preflight:
        print(json.dumps({'preflightPassed': True, 'productionChanged': False}), flush=True)
        return
    verify_current(manifest, plan, progress)
    idle_gates(manifest, plan)
    migrate(manifest)
    for target in manifest['targets']:
        if progress.get(target['service'], {}).get('kind') == 'new':
            continue
        # Independent checks again immediately before each service recreation.
        verify_current(manifest, plan, progress)
        idle_gates(manifest, plan)
        switch(manifest, target, 'new', progress)
    verify_current(manifest, plan, progress, final=True)
    result = {'deployed': True, 'atMs': int(time.time() * 1000), 'components': progress, 'public': public_checks(), 'otherContainersUnchanged': True, 'existingConfigurationUnchanged': True, 'optimizerEnabled': True}
    save('deployed.json', result)
    print(json.dumps(result), flush=True)


def deploy(*, preflight=False):
    try:
        _deploy(preflight=preflight)
    except Exception as exc:
        deferred = isinstance(exc, GuardError) and str(exc) in ('protected_user_work_cutover_deferred', 'protected_work_gate_unavailable')
        recoverable = not isinstance(exc, GuardError) or str(exc) in {'target_health_failed', 'application_unhealthy', 'backend_unhealthy', 'public_route_unavailable', 'public_health_unavailable'}
        # A busy result preserves a safe partial release for a later resume.
        # Other failures attempt recovery only after ownership and independent
        # baseline gates pass. A faulty candidate is never a gate dependency.
        if not preflight and not deferred and recoverable and (ROOT / 'progress.json').exists():
            try:
                rollback()
            except Exception as recovery:
                save('recovery-failure.json', {'errorType': type(recovery).__name__, 'reason': str(recovery) if isinstance(recovery, GuardError) else 'private_evidence_required', 'automaticCutoverStopped': True})
        raise


def rollback():
    plan, manifest = check_inputs(), read_json(ROOT / 'prepared.json')
    verify_files(manifest, plan)
    progress = read_json(ROOT / 'progress.json') if (ROOT / 'progress.json').exists() else {}
    reconcile_intent(manifest, progress)
    for target in manifest['targets']:
        assert_owned(manifest, target, progress)
    for target in reversed(manifest['targets']):
        if progress.get(target['service'], {}).get('kind') != 'new':
            continue
        idle_gates(manifest, plan)
        switch(manifest, target, 'rollback', progress)
    verify_current(manifest, plan, progress)
    save('rollback-result.json', {'restored': True, 'atMs': int(time.time() * 1000), 'additiveTablesRetained': True})
    if (ROOT / 'deployed.json').exists():
        result = read_json(ROOT / 'deployed.json')
        result.update(deployed=False, rolledBack=True)
        save('deployed.json', result)
    print(json.dumps({'restored': True, 'additiveTablesRetained': True}), flush=True)


def verify():
    plan, manifest = check_inputs(), read_json(ROOT / 'prepared.json')
    progress = read_json(ROOT / 'progress.json')
    reconcile_intent(manifest, progress)
    verify_current(manifest, plan, progress, final=True)
    result = {'verified': True, 'atMs': int(time.time() * 1000), 'components': progress, 'public': public_checks()}
    save('independent-verify.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'preflight', 'deploy', 'verify', 'rollback'))
    action = parser.parse_args().action
    os.umask(0o077)
    try:
        with release_lock():
            if action == 'prepare':
                prepare()
            elif action == 'rollback':
                rollback()
            elif action == 'verify':
                verify()
            else:
                deploy(preflight=action == 'preflight')
    except Exception as exc:
        print(json.dumps({'completed': False, 'errorType': type(exc).__name__, 'reason': str(exc) if isinstance(exc, GuardError) else 'Inspect private server evidence; no further automatic cutover.'}), flush=True)
        raise SystemExit(1) from None
