"""Pinned CN written multi-screen Backend/Web incremental release.
Private environment/Compose evidence stays on server. No migration, dependency
installation, full Web rebuild, real user business writes or provider calls.
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
import stat
import subprocess
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

ROOT=Path('/opt/offersteady/releases/20261019-cn-written-multi-screen-2')
PROJECT='compose'
CONTAINER=PROJECT+'-backend-1'
BASE_IMAGE='sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa'
BASES={'backend': ('4d3653af6000dd031e6f090e1dbc2e50b22839d2cc0b2c39f6301335949210b2', BASE_IMAGE), 'web': ('11f545c3b82e42b27c4467b71f3d1982006b6ab97280bae5527047927b8b0c97', 'sha256:2124eee829453776d6191b669c29a28c06f83a011bb6b8461432fefd1393463d')}
BASELINE_SHA='078084d37b8e909ec608f23f9dd7bb4e4bcfa18af3efaf22927b4dd2b001704f'
AUTHORIZATION_SHA='a7fd15c5d157ac65f00606cf2daf7dc721b27ec0f55fdfd9a9b0e120704fbcbb'
APPROVED_FILES=frozenset(('apps/backend/app/modules/screenshot_answer.py','apps/backend/app/ports/screenshot_answer.py','apps/backend/app/schemas/screenshot_answer.py','apps/backend/app/services/redis_live_task_repositories.py','apps/backend/app/services/screenshot_answer_repository.py','apps/backend/app/services/screenshot_answer_service.py'))
GATES=frozenset({'legacy-gates/idle_gate.py','legacy-gates/check-idle.py','legacy-gates/readiness-idle.py','extra_idle_gate.py','active_work_gate.py','resume_optimizer_idle_gate.py','financial_idle_gate.py'})
TCP_GATE='backend_tcp_idle_gate.py'
class GuardError(RuntimeError):
    """Fixed privacy-safe reasons only."""


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
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, check=True, timeout=timeout, input=input)
    except subprocess.CalledProcessError as exc:
        # Configuration/render diagnostics may contain secrets. Keep them only
        # in the private release directory; public output contains fixed codes.
        if ROOT.is_dir():
            write_json(ROOT / 'last-command-error.private.json', {'arguments': args, 'returncode': exc.returncode,
                'stdout': exc.stdout.decode(errors='replace'), 'stderr': exc.stderr.decode(errors='replace')})
        raise


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
        and labels.get('com.docker.compose.service') == service, 'wrong_CN_Compose_identity')
    files = labels['com.docker.compose.project.config_files'].split(',')
    envs = labels.get('com.docker.compose.project.environment_file', '').split(',')
    require(files and envs and all(Path(p).is_absolute() and p.startswith('/opt/offersteady/') for p in files + envs),
        'invalid_CN_private_Compose_context')
    return {'composeDirectory': labels['com.docker.compose.project.working_dir'], 'composeFiles': files, 'envFiles': envs}


def runtime_baseline(source, before, service):
    declared = source['services'][service].get('environment', {})
    require(all(str(value) == environment(before).get(key) for key, value in declared.items()),
        'rendered/runtime_environment_mismatch')
    return json.loads(json.dumps(source)), False


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


def assert_rendered_image(source, before, service):
    declared = source['services'][service]
    actual = before['Config']['Image']
    if 'image' not in declared:
        # Compose gives build-only services an implicit project-service tag.
        # Accept that precise historical form only; never infer an arbitrary
        # runtime tag or alter the rendered baseline to hide configuration drift.
        require(service == 'web' and bool(declared.get('build')) and actual == f'{PROJECT}-{service}',
            'implicit_compose_image_mismatch')
        require(inspect(actual)['Id'] == before['Image'], 'implicit_compose_image_tag_drift')
    else:
        require(declared['image'] == actual, 'rendered/runtime image identity mismatch')


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
    assert_rendered_image(source, before, service)
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
    if path == 'legacy-gates/idle_gate.py':
        return {'liveInterviews', 'recentPreparing', 'activeInterviews', 'activeWebSessions', 'activeAudioStreams'}, {'atMs', 'sampleAgeMs'}
    if path == 'legacy-gates/check-idle.py':
        return {'live_interviews', 'live_page_leases', 'recent_audio_tracks', 'unfinished_answers'}, set()
    if path == 'legacy-gates/readiness-idle.py':
        return {'unknownPhaseCount', 'activeMockPhases'}, set()
    require(path in ('active_work_gate.py', 'extra_idle_gate.py', 'financial_idle_gate.py', 'resume_optimizer_idle_gate.py'), 'unknown_protection_gate')
    values = {}
    for node in ast.parse((ROOT / path).read_text()).body:
        if isinstance(node, ast.Assign):
            for name in node.targets:
                if isinstance(name, ast.Name) and name.id in ('PROTECTED', 'MOCK_FIELDS'):
                    values[name.id] = set(ast.literal_eval(node.value))
    require('PROTECTED' in values, 'gate_protection_fields_missing')
    protected = values['PROTECTED']
    informational = values.get('MOCK_FIELDS', set()) - protected
    if path == 'active_work_gate.py':
        informational.add('ignoredLegacyFailedQueuedTasks')
    require(bool(protected), 'empty_protection_contract')
    return protected, informational


def normalize_gate(path, counts):
    require(isinstance(counts, dict), 'invalid_gate_summary')
    if path == 'legacy-gates/readiness-idle.py':
        require(set(counts) == {'mockPhases'} and isinstance(counts['mockPhases'], dict), 'invalid_mock_phase_summary')
        phases = counts['mockPhases']
        require(all(type(v) is int and v >= 0 for v in phases.values()), 'invalid_mock_phase_count')
        allowed = {'preparing', 'generating_question', 'speaking', 'listening', 'paused', 'generating_report', 'completed'}
        # Preparing work is protected by the independent freshness/lease gate.
        return {'unknownPhaseCount': sum(v for k,v in phases.items() if k not in allowed),
                'activeMockPhases': sum(v for k,v in phases.items() if k not in {'preparing','completed'})}
    protected, informational = gate_contract(path)
    if path == 'legacy-gates/check-idle.py':
        require(set(counts) == protected | {'checked_at'} and isinstance(counts['checked_at'], str), 'live_gate_summary_changed')
        counts = {k:v for k,v in counts.items() if k != 'checked_at'}
    require(set(counts) == protected | informational and all(type(v) is int and v >= 0 for v in counts.values()), 'invalid_gate_aggregate')
    return counts


def gate_is_idle(path, counts):
    protected, _ = gate_contract(path)
    return all(counts[k] == 0 for k in protected) and (path != 'legacy-gates/idle_gate.py' or counts['sampleAgeMs'] < 90_000)


def gate_has_read_or_unknown_failure(path, counts):
    if path == 'legacy-gates/idle_gate.py' and counts['sampleAgeMs'] >= 90_000:
        return True
    return any(value != 0 and ('unknown' in name.lower() or 'readfail' in name.lower()
        or name in {'invalidRuntimeMetadata', 'scanLimitExceeded'}) for name,value in counts.items())


def exact_payload(directory, expected):
    paths = list(directory.rglob('*'))
    require(not any(p.is_symlink() for p in paths), 'payload_symlink_rejected')
    require({str(p.relative_to(directory)) for p in paths if p.is_file()} == set(expected), 'unlisted_payload_file')


def current_schema():
    code = "import json;from urllib.request import urlopen;print(json.dumps(json.load(urlopen('http://127.0.0.1:8000/openapi.json',timeout=10))))"
    return json.loads(run(['docker', 'exec', CONTAINER, 'python', '-B', '-c', code]).stdout)


def assert_schema(actual, expected):
    require(actual == expected, 'complete_runtime_api_schema_drift')


def settings_digest(plan):
    code = ("from app.core.config import Settings;import json,hashlib;s=Settings(_env_file=None);"
            f"assert sorted(Settings.model_fields)=={plan['configFields']!r};"
            "data=s.model_dump(mode='json');"
            "print(json.dumps({'sha':hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'enabled':s.cn_resume_optimizer_enabled}))")
    return json.loads(run(['docker', 'exec', '-w', '/app/apps/backend', CONTAINER, 'python', '-B', '-c', code]).stdout)


def canonical_mounts(mounts):
    require(type(mounts) is list and all(type(mount) is dict for mount in mounts), 'invalid_mount_inventory')
    return sorted(mounts, key=canonical)


def container_signature(container):
    return {'id': container['Id'], 'image': container['Image'], 'imageReference': container['Config']['Image'],
        'startedAt': container['State']['StartedAt'], 'health': container['State'].get('Health', {}).get('Status'),
        'running': container['State']['Running'], 'restartCount': container['RestartCount'],
        'configSha256': digest(canonical(container['Config'])), 'hostConfigSha256': digest(canonical(container['HostConfig'])),
        'mountsSha256': digest(canonical(canonical_mounts(container['Mounts']))),
        'networkSettingsSha256': digest(canonical(container['NetworkSettings']['Networks'])),
        'networks': sorted(container['NetworkSettings']['Networks'])}


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
            counts = normalize_gate(path, json.loads(result.stdout))
        except Exception:
            raise GuardError('protected_work_gate_unavailable') from None
        records.append({'gate': path, 'exitCode': result.returncode, 'counts': counts})
        save('last-idle-gates.json', records)
        require(not gate_has_read_or_unknown_failure(path, counts), 'protected_work_gate_unavailable')
        require(result.returncode == 0 or not gate_is_idle(path, counts), 'protected_work_gate_unavailable')
        require(result.returncode == 0 and gate_is_idle(path, counts), 'protected_user_work_cutover_deferred')
    return records


def runtime_invariant(before, after, target, kind):
    require(target['service'] in ('backend', 'web') and after['Image'] == target[kind+'Image'], 'runtime_image_changed')
    require(environment(after) == environment(before), 'runtime_environment_changed')
    for key in set(before['Config']) | set(after['Config']):
        if key not in ('Image', 'Hostname', 'Labels', 'Env'):
            require(before['Config'].get(key) == after['Config'].get(key), 'application_configuration_changed')
    hostname = after['Id'][:12] if before['Config']['Hostname'] == before['Id'][:12] else before['Config']['Hostname']
    require(after['Config']['Hostname'] == hostname, 'container_hostname_changed')
    labels = lambda c: {k:v for k,v in c['Config'].get('Labels', {}).items() if not k.startswith('com.docker.compose.')}
    require(labels(before) == labels(after) and before['HostConfig'] == after['HostConfig'] and canonical_mounts(before['Mounts']) == canonical_mounts(after['Mounts']), 'host_mount_or_label_changed')
    old_networks = before['NetworkSettings']['Networks']; new_networks = after['NetworkSettings']['Networks']
    require(set(old_networks) == set(new_networks), 'target_network_set_changed')
    for name, old in old_networks.items():
        new = new_networks[name]
        for key in ('IPAMConfig', 'Links', 'DriverOpts', 'GwPriority'):
            require(old.get(key) == new.get(key), 'target_network_configuration_changed')
        aliases = lambda c,n: sorted(a for a in n.get('Aliases') or [] if a not in (c['Id'], c['Id'][:12]))
        require(aliases(before, old) == aliases(after, new), 'target_network_aliases_changed')


def stopped_process(container):
    state=container.get('State',{})
    return (state.get('Running') is False and type(state.get('Pid')) is int and state['Pid']==0
            and state.get('Status')=='exited' and state.get('Restarting') is False
            and state.get('Dead') is False and state.get('Paused') is False)


def assert_owned(manifest, target, progress, *, allow_stopped_recovery=False):
    current = inspect(target['container'])
    if target['service'] not in progress:
        require((current['Id'], current['Image']) == BASES[target['service']], 'baseline_container_owner_changed')
        require({k:v for k,v in container_signature(current).items() if k != 'health'} == {k:v for k,v in read_json(ROOT / 'baseline.json')['components'][target['service']].items() if k != 'health'}, 'baseline_container_signature_changed')
        return 'rollback'
    entry = progress[target['service']]
    require(current['Id'] == entry['id'] and current['Image'] == entry['image'], 'release_container_owner_changed')
    ignored={'health'}
    if allow_stopped_recovery and current['State']['Running'] is False:
        require(entry['kind']=='new' and current['Image']==target['newImage'] and stopped_process(current),
                'stopped_process_proof_unavailable')
        ignored.add('running')
    require({k:v for k,v in container_signature(current).items() if k not in ignored} == {k:v for k,v in entry['signature'].items() if k not in ignored}, 'released_container_signature_changed')
    kind = entry['kind']
    expected_files = ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']])
    labels = current['Config']['Labels']
    require(labels.get('com.docker.compose.project') == PROJECT and labels.get('com.docker.compose.service') == target['service'] and labels.get('com.docker.compose.project.config_files') == expected_files
            and labels.get('com.docker.compose.project.working_dir') == target['composeDirectory']
            and labels.get('com.docker.compose.project.environment_file') == ','.join(target['frozenEnvFiles']), 'released_compose_owner_changed')
    return kind


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
        progress[target['service']] = {'id': current['Id'], 'image': current['Image'], 'kind': kind, 'signature': container_signature(current)}
        save('progress.json', progress)


def switch(manifest, target, kind, progress):
    verify_files(manifest, check_inputs())
    assert_owned(manifest, target, progress,allow_stopped_recovery=kind=='rollback')
    save('switch-intent.json', {'service': target['service'], 'kind': kind, 'previousProgress': progress})
    old = inspect(target['container'])
    tcp_idle_guard(manifest, check_inputs(), progress,recovery=kind=='rollback' and target['service']=='backend')
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
            progress[target['service']] = {'id': current['Id'], 'image': current['Image'], 'kind': kind, 'signature': container_signature(current)}
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


def deploy(*, preflight=False):
    try:
        _deploy(preflight=preflight)
    except Exception as exc:
        deferred = isinstance(exc, GuardError) and str(exc) in {'protected_user_work_cutover_deferred', 'protected_work_gate_unavailable'}
        recoverable = isinstance(exc, GuardError) and str(exc) in {'target_health_failed', 'application_unhealthy', 'backend_unhealthy', 'public_route_unavailable', 'public_health_unavailable', 'public_build_identity_mismatch', 'public_html_identity_mismatch', 'public_static_identity_mismatch', 'anonymous_optimizer_guard_failed'}
        if not preflight and not recoverable and (ROOT / 'progress.json').exists() and not (isinstance(exc, GuardError) and str(exc) == 'protected_user_work_cutover_deferred'):
            reason = 'command_failed_requires_owned_state_inspection' if isinstance(exc, subprocess.CalledProcessError) else 'cutover_stopped_requires_owned_state_inspection'
            save('cutover-failure.json', {'completed':False, 'reason':reason, 'automaticRecoveryAttempted':False, 'ownershipMustBeReverified':True})
        if not preflight and not deferred and recoverable and (ROOT / 'progress.json').exists():
            try:
                rollback()
            except Exception as recovery:
                save('recovery-failure.json', {'errorType':type(recovery).__name__, 'reason':str(recovery) if isinstance(recovery, GuardError) else 'private_evidence_required', 'automaticCutoverStopped':True})
        raise


def verify_non_targets(manifest):
    names=set(run(['docker','ps','--format','{{.Names}}']).stdout.decode().splitlines())
    require(names|{CONTAINER,PROJECT+'-web-1'}=={CONTAINER,PROJECT+'-web-1',*manifest['nonTargets']},'running_container_set_changed')
    for name,expected in manifest['nonTargets'].items():
        actual=container_signature(inspect(name))
        require({k:v for k,v in actual.items() if k!='health'}=={k:v for k,v in expected.items() if k!='health'},'non_target_identity_or_configuration_changed')
    for tag,expected in manifest['sharedTags'].items():
        require(inspect(tag)['Id']==expected,'shared_runtime_tag_changed')


def expected_config(before,target,kind):
    require(target['service'] in ('backend','web'),'unknown_target_rejected')
    return expected_overlay(before,target['service'],target[kind+'Image'])


def write_overlay(target,kind):
    require(target['service'] in ('backend','web'),'unknown_target_rejected')
    service=target['service'];path=ROOT/service/(kind+'-image.compose.json')
    write_json(path,{'services':{service:{'image':target[kind+'Image']}}})
    target[kind+'Overlay']=str(path);target[kind+'OverlaySha']=digest(path.read_bytes())
    before=read_json(ROOT/service/'rendered-before.json')
    require(rendered(target,frozen=True,overlay=path)==expected_config(before,target,kind),'unrelated_rendered_configuration_change')


def verify_files(manifest,plan):
    require([t['service'] for t in manifest['targets']]==['backend','web'],'target_scope_changed')
    require(manifest['nonTargets']==plan['nonTargets'] and manifest['sharedTags']==plan['sharedTags'],'non_target_manifest_changed')
    require(digest((ROOT/'input.json').read_bytes())==manifest['inputSha'],'release_manifest_drift')
    require(digest((ROOT/'runtime.env.private').read_bytes())==manifest['runtimeEnvSha'],'recovery_environment_drift')
    for target in manifest['targets']:
        service=target['service'];before=read_json(ROOT/service/'container-before.json')
        require(digest(canonical(before))==target['beforeInspectSha'],'frozen_inspection_drift')
        require(container_signature(before)==read_json(ROOT/'baseline.json')['components'][service],'frozen_runtime_baseline_changed')
        for path,checksum in target['sourceHashes'].items():require(digest(Path(path).read_bytes())==checksum,'private_original_context_drift')
        verify_frozen_files(target,before)
        require(digest(canonical(rendered(target)))==target['sourceRenderedSha'],'original_complete_compose_drift')
        require(digest(canonical(rendered(target,frozen=True)))==target['renderedSha'],'frozen_complete_compose_drift')
        for kind in ('new','rollback'):
            require(inspect(target[kind+'Tag'])['Id']==target[kind+'Image'],'fixed_image_tag_drift')
            require(digest(Path(target[kind+'Overlay']).read_bytes())==target[kind+'OverlaySha'],'image_overlay_drift')
            require(rendered(target,frozen=True,overlay=target[kind+'Overlay'])==expected_config(read_json(ROOT/service/'rendered-before.json'),target,kind),'complete_rendered_overlay_drift')
    verify_non_targets(manifest)


def prepare():
    require(not (ROOT/'prepared.json').exists(),'already_prepared')
    plan=check_inputs();baseline=read_json(ROOT/'baseline.json')
    require(backend_inventory(CONTAINER)==plan['beforeInventory'],'actual_backend_source_drift')
    assert_schema(current_schema(),plan['openapiBefore'])
    require(settings_digest(plan)=={'sha':plan['configBeforeSha'],'enabled':True},'actual_backend_settings_drift')
    manifest={'targets':[],'nonTargets':plan['nonTargets'],'sharedTags':plan['sharedTags']};verify_non_targets(manifest)
    require(web_inventory(PROJECT+'-web-1')==plan['webBefore'],'actual_web_source_drift')
    require(digest(read_container(PROJECT+'-web-1','/etc/nginx/conf.d/default.conf'))==plan['nginxBeforeSha'],'actual_nginx_drift')
    targets=[]
    for service in ('backend','web'):
        current=inspect(PROJECT+'-'+service+'-1')
        require(container_signature(current)==baseline['components'][service],'actual_runtime_baseline_changed')
        require(current['State']['Running'] and current['RestartCount']==0,'baseline_unhealthy')
        if service=='backend':require(current['State'].get('Health',{}).get('Status')=='healthy','baseline_backend_unhealthy')
        frozen_path=ROOT/service/'frozen-target.json'
        if frozen_path.exists():
            target=read_json(frozen_path);before=read_json(ROOT/service/'container-before.json')
            require(container_signature(before)==baseline['components'][service],'interrupted_prepare_baseline_changed')
            require(all(before[k]==current[k] for k in ('Config','HostConfig')) and canonical_mounts(before['Mounts'])==canonical_mounts(current['Mounts']),'interrupted_prepare_runtime_changed')
            verify_frozen_files(target,before)
            require(all(digest(Path(p).read_bytes())==sha for p,sha in target['sourceHashes'].items()),'interrupted_prepare_context_changed')
            require(digest(canonical(rendered(target)))==target['sourceRenderedSha'] and digest(canonical(rendered(target,frozen=True)))==target['renderedSha'],'interrupted_prepare_full_render_changed')
        else:
            target=freeze(current,service);write_json(frozen_path,target)
        target.update(beforeInspectSha=digest(canonical(read_json(ROOT/service/'container-before.json'))),newTag='offersteady-cn-'+service+':written-multi-screen-20261019-2',
            rollbackTag='offersteady-cn-'+service+':written-multi-screen-recovery-20261019-2',rollbackImage=current['Image'])
        run(['docker','tag',current['Image'],target['rollbackTag']])
        build=ROOT/'build'/service
        if build.exists():shutil.rmtree(build)
        build.mkdir(parents=True)
        base_tag='offersteady-cn-written-multi-screen-base-20261019-2:'+service
        run(['docker','tag',current['Image'],base_tag]);require(inspect(base_tag)['Id']==current['Image'],'build_base_tag_drift')
        directory='input' if service=='backend' else 'web-input'
        shutil.copytree(ROOT/directory,build/'input')
        lines=['FROM '+base_tag,'COPY input/ '+('/app/' if service=='backend' else '/usr/share/nginx/html/')]
        (build/'Dockerfile').write_text('\n'.join(lines)+'\n')
        run(['docker','build','--network=none','--pull=false','-t',target['newTag'],str(build)],timeout=180)
        image=inspect(target['newTag']);verify_image_base(image,inspect(current['Image']));target['newImage']=image['Id']
        write_overlay(target,'new');write_overlay(target,'rollback');targets.append(target)
    before=read_json(ROOT/'backend/container-before.json');env=environment(before)
    require(all('\n' not in k+v and '\r' not in k+v for k,v in env.items()),'unsupported_private_environment_value')
    private_env=ROOT/'runtime.env.private';private_env.write_text(''.join(k+'='+v+'\n' for k,v in sorted(env.items())));private_env.chmod(0o600)
    manifest.update(targets=targets,runtimeEnvSha=digest(private_env.read_bytes()),inputSha=digest((ROOT/'input.json').read_bytes()))
    require(web_inventory(targets[1]['newImage'],image=True)==plan['webBefore']|plan['webFiles'],'candidate_did_not_preserve_all_static_assets')
    require(digest(run(['docker','run','--rm','--read-only','--network=none','--entrypoint','cat',targets[1]['newImage'],'/etc/nginx/conf.d/default.conf']).stdout)==plan['nginxBeforeSha'],'candidate_nginx_changed')
    save('web-public-mode-probe.json',web_public_mode_probe(targets[1]['newImage'],plan))
    save('candidate-image-probe.json',probe(manifest));verify_files(manifest,plan);save('prepared.json',manifest)
    print(json.dumps({'prepared':True,'images':{t['service']:t['newImage'] for t in targets},'productionChanged':False}),flush=True)


def verify_current(manifest,plan,progress,*,final=False):
    verify_files(manifest,plan)
    for target in manifest['targets']:
        service=target['service'];kind=assert_owned(manifest,target,progress);current=inspect(target['container'])
        require(current['State']['Running'] and current['RestartCount']==0,'application_unhealthy')
        runtime_invariant(read_json(ROOT/service/'container-before.json'),current,target,kind)
        if service=='backend':
            require(current['State'].get('Health',{}).get('Status')=='healthy','backend_unhealthy')
            require(backend_inventory(CONTAINER)==plan['beforeInventory']|(plan['files'] if kind=='new' else {}),'runtime_source_mismatch')
            assert_schema(current_schema(),plan['openapiAfter'] if kind=='new' else plan['openapiBefore'])
            require(settings_digest(plan)=={'sha':plan['configBeforeSha'],'enabled':True},'runtime_settings_mismatch')
        else:
            require(web_inventory(target['container'])==plan['webBefore']|(plan['webFiles'] if kind=='new' else {}),'runtime_static_mismatch')
            require(digest(read_container(target['container'],'/etc/nginx/conf.d/default.conf'))==plan['nginxBeforeSha'],'runtime_nginx_changed')
        if final:require(kind=='new','release_incomplete')


PUBLIC_HTML_ROUTES={'index.html':'/login','guide.html':'/guide','terms.html':'/terms','privacy.html':'/privacy'}

def public_static_route(file):
    if file in PUBLIC_HTML_ROUTES:return PUBLIC_HTML_ROUTES[file]
    if file.startswith('assets/') and '\\' not in file and '..' not in file.split('/'):
        return '/'+file
    raise ValueError('unapproved_public_file_route')

def public_checks():
    plan=read_json(ROOT/'input.json');results=[]
    progress=read_json(ROOT/'progress.json') if (ROOT/'progress.json').exists() else {}
    expected_web=plan['webBefore']|(plan['webFiles'] if progress.get('web',{}).get('kind')=='new' else {})
    def flush():save('public-checks.json',{'atMs':int(time.time()*1000),'checks':results})
    def check(path,*,source=None,expected_status=200,expected_sha=None,health=False,no_store=False):
        record={'path':path,'sourceFile':source,'expectedStatus':expected_status,'status':None,'state':'requesting','attempts':[]}
        results.append(record);flush();began=time.monotonic()
        reason='anonymous_optimizer_guard_failed' if expected_status==401 else 'public_route_unavailable'
        for attempt in range(1,4):
            row={'number':attempt,'status':None,'state':'requesting'}
            record['attempts'].append(row);record['state']='requesting';flush();transient=False
            try:
                try:
                    response=urlopen(Request('https://mianshiwen.cn'+path,headers={'Cache-Control':'no-cache'}),timeout=15)
                except HTTPError as error:response=error
                with response:
                    record['status']=row['status']=response.status
                    if response.status!=expected_status:
                        transient=response.status in (502,503)
                        raise GuardError(reason)
                    if no_store and response.headers.get('Cache-Control')!='private, no-store':raise GuardError(reason)
                    if expected_status==200:
                        data=response.read(4*1024*1024+1)
                        if len(data)>4*1024*1024:raise GuardError('public_response_size_exceeded')
                        record['sha256']=digest(data)
                        if expected_sha is not None and record['sha256']!=expected_sha:
                            raise GuardError('public_static_identity_mismatch')
                        if health and json.loads(data)['data']['status']!='ok':raise GuardError('public_health_unavailable')
                record['state']=row['state']='passed';record['elapsedMs']=round((time.monotonic()-began)*1000);flush();return
            except GuardError as error:
                row.update(state='failed',reason=str(error),errorType='GuardError')
                record.update(state='retrying' if transient and attempt<3 else 'failed',reason=str(error),errorType='GuardError')
                record['elapsedMs']=round((time.monotonic()-began)*1000);flush()
                if not transient or attempt==3:raise
            except Exception as error:
                transient=isinstance(error,(URLError,TimeoutError))
                error_type=type(error).__name__ if type(error) in (URLError,TimeoutError,OSError,ValueError,KeyError,json.JSONDecodeError) else 'OtherTransportOrDecodeError'
                row.update(state='failed',reason=reason,errorType=error_type)
                record.update(state='retrying' if transient and attempt<3 else 'failed',reason=reason,errorType=error_type)
                record['elapsedMs']=round((time.monotonic()-began)*1000);flush()
                if not transient or attempt==3:raise GuardError(reason) from None
            time.sleep(1)
    for path in ('/healthz','/login','/offersteady-build.json','/app/resume-optimizer','/app/mock-interviews','/app/interviews/new','/app/written-exams'):
        source=None if path=='/healthz' else 'offersteady-build.json' if path=='/offersteady-build.json' else 'index.html'
        check(path,source=source,expected_sha=expected_web[source] if source else None,health=path=='/healthz')
    for path in ('/api/v1/resume-optimizer/capabilities','/api/v1/resume-optimizer/jobs/synthetic-invalid/export?format=pdf&expectedRevision=1&factsConfirmed=true'):
        check(path,expected_status=401,no_store=True)
    for file,expected in sorted(plan['webFiles'].items()):
        check(public_static_route(file),source=file,expected_sha=expected)
    return results


def inspect_release():
    plan=check_inputs();prepared=(ROOT/'prepared.json').exists()
    result={'inputsVerified':True,'prepared':prepared,'deployedRecord':(ROOT/'deployed.json').exists()}
    if prepared:
        manifest=read_json(ROOT/'prepared.json');progress=read_json(ROOT/'progress.json') if (ROOT/'progress.json').exists() else {}
        reconcile_intent(manifest,progress);verify_current(manifest,plan,progress)
        result.update(images={t['service']:t['newImage'] for t in manifest['targets']},currentKinds={t['service']:assert_owned(manifest,t,progress) for t in manifest['targets']})
    else:
        for service in ('backend','web'):require(container_signature(inspect(PROJECT+'-'+service+'-1'))==read_json(ROOT/'baseline.json')['components'][service],'actual_baseline_drift')
        verify_non_targets({'nonTargets':plan['nonTargets'],'sharedTags':plan['sharedTags']})
    print(json.dumps(result),flush=True)


def verify():
    plan=check_inputs();manifest=read_json(ROOT/'prepared.json');progress=read_json(ROOT/'progress.json')
    reconcile_intent(manifest,progress);verify_current(manifest,plan,progress,final=True)
    result={'verified':True,'atMs':int(time.time()*1000),'components':progress,'public':public_checks(),
        'targetComponents':['backend','web'],'otherContainersUnchanged':True}
    save('independent-verify.json',result);print(json.dumps(result),flush=True)


def rollback():
    plan, manifest = check_inputs(), read_json(ROOT / 'prepared.json')
    verify_files(manifest, plan)
    progress = read_json(ROOT / 'progress.json') if (ROOT / 'progress.json').exists() else {}
    reconcile_intent(manifest, progress)
    for target in manifest['targets']:
        assert_owned(manifest, target, progress,allow_stopped_recovery=progress.get(target['service'],{}).get('kind')=='new')
    for target in reversed(manifest['targets']):
        if progress.get(target['service'], {}).get('kind') != 'new':
            continue
        idle_gates(manifest, plan)
        switch(manifest, target, 'rollback', progress)
    verify_current(manifest, plan, progress)
    save('rollback-result.json', {'restored': True, 'atMs': int(time.time() * 1000), 'dataAndConfigurationUnchanged': True})
    if (ROOT / 'deployed.json').exists():
        result = read_json(ROOT / 'deployed.json')
        result.update(deployed=False, rolledBack=True)
        save('deployed.json', result)
    print(json.dumps({'restored': True, 'dataAndConfigurationUnchanged': True}), flush=True)




def assert_public_input_modes(plan):
    public = ROOT / 'web-input'
    directories = [public, *(p for p in public.rglob('*') if p.is_dir())]
    require(all(not p.is_symlink() and stat.S_IMODE(p.stat().st_mode) == 0o755 for p in directories),
        'public_payload_directory_mode_must_be_0755')
    files = [public / p for p in plan['webFiles']]
    require(all(not p.is_symlink() and p.is_file() and stat.S_IMODE(p.stat().st_mode) == 0o644 for p in files),
        'public_payload_file_mode_must_be_0644')

def web_public_mode_probe(image, plan):
    # Execute only a shell as the actual NGINX worker user: no ports, service
    # startup, production network, config mount or user/model operations.
    paths = ['/usr/share/nginx/html/' + p for p in sorted(plan['webFiles'])] + ['/etc/nginx/conf.d/default.conf']
    script = ("for path do [ -r \"$path\" ] && [ \"$(stat -c '%a' \"$path\")\" = 644 ] || exit 23; done; "
              "printf '{\"passed\":true,\"readableFiles\":%s}\\n' \"$#\"")
    try:
        output = run(['docker', 'run', '--rm', '--read-only', '--network=none', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '32', '--memory', '64m', '--user', 'nginx',
            '--entrypoint', 'sh', image, '-c', script, 'public-file-readability', *paths], timeout=30).stdout
        report = json.loads(output)
    except Exception:
        raise GuardError('candidate_public_file_permissions_failed') from None
    require(report == {'passed': True, 'readableFiles': len(paths)}, 'candidate_public_file_permissions_failed')
    return report

def check_inputs():
    plan=read_json(ROOT/'input.json');baseline=read_json(ROOT/'baseline.json')
    require(digest((ROOT/'baseline.json').read_bytes())==BASELINE_SHA,'fresh_baseline_drift')
    require(baseline['passed'] is True and baseline['readOnly'] is True and baseline['productionWrites']==0
        and baseline['providerCalls']==0 and baseline['privateConfigurationExported'] is False,'invalid_actual_baseline')
    expected={'beforeInventory':baseline['runtimeInputs'],'openapiBefore':baseline['openapi'],
        'configFields':baseline['settings']['fields'],'configBeforeSha':baseline['settings']['sha256'],'webBefore':baseline['staticFiles'],
        'nginxBeforeSha':baseline['nginxSha256'],'nonTargets':{k:v for k,v in baseline['nonTargets'].items() if k!='compose-web-1'},
        'sharedTags':baseline['sharedTags'],'baselines':{k:{'id':v[0],'image':v[1]} for k,v in BASES.items()},'tcpGate':TCP_GATE}
    require(set(plan)==set(expected)|{'files','webFiles','openapiAfter','gates','gateFields','gateInformationalFields','supportFiles','verified','probeExpected','publicRouteDiagnosisSha256'},'unexpected_plan_fields')
    for key,value in expected.items():require(plan[key]==value,'frozen_baseline_changed')
    require(len(plan['beforeInventory'])==230 and len(plan['webBefore'])==315 and len(plan['configFields'])==340
        and len(plan['openapiBefore']['paths'])==202 and len(plan['openapiAfter']['paths'])==203 and len(plan['nonTargets'])==6,'incomplete_baseline')
    require(digest((ROOT/'authorization.json').read_bytes())==AUTHORIZATION_SHA,'release_authorization_drift')
    authorization=read_json(ROOT/'authorization.json')
    require(authorization=={'authorized':True,'scope':'CN Backend and Web written multi-screen increment only','files':plan['files'],'webFiles':plan['webFiles'],
        'openapiAfterSha256':digest(canonical(plan['openapiAfter'])),'verified':plan['verified'],'probeExpected':plan['probeExpected'],
        'providerCalls':0,'productionBusinessTestWrites':0,'gitActions':0,'preserveSavedDocumentsJobsAndAccounting':True,'publicRouteDiagnosisSha256':plan['publicRouteDiagnosisSha256']},'release_scope_not_authorized')
    require(set(plan['files'])==APPROVED_FILES and all(k in plan['beforeInventory'] and plan['beforeInventory'][k]!=v for k,v in plan['files'].items()),'unapproved_backend_scope')
    require(plan['webFiles'] and set(plan['webFiles'])-{'index.html','guide.html','terms.html','privacy.html'} <= {p for p in plan['webFiles'] if p.startswith('assets/')},'unapproved_web_scope')
    require({'index.html','guide.html','terms.html','privacy.html'} <= set(plan['webFiles']),'missing_web_entrypoint')
    for directory,files in (('input',plan['files']),('web-input',plan['webFiles'])):
        exact_payload(ROOT/directory,files)
        for path,checksum in files.items():
            require(not Path(path).is_absolute() and '..' not in Path(path).parts and re.fullmatch('[0-9a-f]{64}',checksum) is not None,'invalid_payload_path_or_hash')
            require(digest((ROOT/directory/path).read_bytes())==checksum,'source_payload_drift')
    for path,checksum in plan['webFiles'].items():
        require(not(path.startswith('assets/') and path in plan['webBefore'] and checksum!=plan['webBefore'][path]),'immutable_web_asset_overwrite')
    assert_public_input_modes(plan)
    require(len(plan['gates'])==7 and set(plan['gates'])==GATES,'incomplete_user_protection')
    for gate in GATES:
        protected,information=gate_contract(gate)
        require(set(plan['gateFields'][gate])==protected and set(plan['gateInformationalFields'][gate])==information,'protected_gate_contract_changed')
    require(read_json(ROOT/'probe/expectations.json')=={'inventory':plan['beforeInventory']|plan['files'],'configFields':plan['configFields'],
        'configBeforeSha':plan['configBeforeSha'],'openapiBefore':plan['openapiBefore'],'openapiAfter':plan['openapiAfter']},'probe_expectations_changed')
    required={Path(__file__).name,*GATES,TCP_GATE,'baseline.json','authorization.json','probe/offline-probe.py','probe/expectations.json','public-route-diagnosis.json'}
    require(set(plan['supportFiles'])==required,'support_unbound_or_extra')
    for path,checksum in plan['supportFiles'].items():
        candidate=ROOT/path
        require(not Path(path).is_absolute() and '..' not in Path(path).parts and candidate.is_file() and not candidate.is_symlink()
            and digest(candidate.read_bytes())==checksum,'release_support_drift')
    require(digest((ROOT/'public-route-diagnosis.json').read_bytes())==plan['publicRouteDiagnosisSha256'],'public_route_diagnosis_drift')
    verification=plan['verified']
    require(verification['passed'] is True and verification['syntheticOnly'] is True and verification['sourceFrozenAfterTests'] is True
        and verification['webTests']>=598 and verification['backendTests']>=32 and verification['typecheck'] is True and verification['openspecStrict'] is True,'required_local_verification_missing')
    return plan


def running_process_identity(container):
    state=container.get('State',{})
    require(state.get('Running') is True and type(state.get('Pid')) is int and state['Pid']>0
            and state.get('Status')=='running' and state.get('Restarting') is False
            and state.get('Dead') is False and state.get('Paused') is False
            and isinstance(state.get('StartedAt'),str) and bool(state['StartedAt']),
            'protected_tcp_gate_unavailable')
    return tuple(container.get(key) for key in ('Id','Image'))+tuple(state[key] for key in
        ('StartedAt','Pid','Status','Restarting','Dead','Paused'))


def host_network_namespace(container):
    running_process_identity(container)
    try:
        value=str(Path('/proc/'+str(container['State']['Pid'])+'/ns/net').readlink())
    except Exception:
        raise GuardError('protected_tcp_gate_unavailable') from None
    require(re.fullmatch(r'net:\[[1-9][0-9]*\]',value) is not None,'protected_tcp_gate_unavailable')
    return digest(value.encode('ascii'))


def tcp_idle_guard(manifest,plan,progress,*,recovery=False):
    require(digest((ROOT/TCP_GATE).read_bytes())==plan['supportFiles'][TCP_GATE],'tcp_gate_source_drift')
    target=next(t for t in manifest['targets'] if t['service']=='backend')
    assert_owned(manifest,target,progress,allow_stopped_recovery=recovery)
    current=inspect(CONTAINER)
    expected=progress.get('backend',{}).get('id',BASES['backend'][0])
    expected_image=progress.get('backend',{}).get('image',BASES['backend'][1])
    require(current['Id']==expected and current['Image']==expected_image,'tcp_gate_container_owner_changed')
    if current['State']['Running'] is False:
        require(recovery and progress.get('backend',{}).get('kind')=='new'
                and current['Image']==target['newImage'] and stopped_process(current),'stopped_process_proof_unavailable')
        after=inspect(CONTAINER)
        require(stopped_process(after) and container_signature(current)==container_signature(after)
                and current['State']['StartedAt']==after['State']['StartedAt'],'stopped_process_proof_unavailable')
        assert_owned(manifest,target,progress,allow_stopped_recovery=True)
        proof={'passed':True,'atMs':int(time.time()*1000),'method':'stoppedProcessProof',
               'sameOwnedCandidate':True,'observations':2,'running':False,'pid':0,'status':'exited'}
        save('last-tcp-idle-gate.json',proof)
        return proof
    identity=running_process_identity(current)
    namespace=host_network_namespace(current)
    try:
        response=subprocess.run(['docker','exec','-i',current['Id'],'python','-B','-'],
                                input=(ROOT/TCP_GATE).read_bytes(),capture_output=True,timeout=10)
        value=json.loads(response.stdout)
    except Exception:
        raise GuardError('protected_tcp_gate_unavailable') from None
    fields={'passed','atMs','establishedPort8000','tablesRead','scannedRows','scope','networkNamespaceSha256'}
    require(response.returncode==0 and type(value) is dict and set(value)==fields and value['passed'] is True
            and value['scope']=='container_tcp8000_established_only','protected_tcp_gate_unavailable')
    require(all(type(value[key]) is int and value[key]>=0 for key in ('atMs','establishedPort8000','tablesRead','scannedRows'))
            and value['tablesRead']==2 and value['scannedRows']<=200_000
            and value['establishedPort8000']<=value['scannedRows']
            and 0<=int(time.time()*1000)-value['atMs']<=10_000,'protected_tcp_gate_unavailable')
    require(value['networkNamespaceSha256']==namespace,'protected_tcp_gate_unavailable')
    after=inspect(CONTAINER)
    require(running_process_identity(after)==identity and container_signature(after)==container_signature(current)
            and host_network_namespace(after)==namespace,'tcp_gate_container_owner_changed')
    assert_owned(manifest,target,progress)
    save('last-tcp-idle-gate.json',value)
    require(value['establishedPort8000']==0,'protected_user_work_cutover_deferred')
    return value


def probe(manifest):
    target=next(t for t in manifest['targets'] if t['service']=='backend')
    command=['docker','run','--rm','--read-only','--network=none','--cap-drop','ALL','--security-opt','no-new-privileges',
        '--pids-limit','64','--memory','768m','--env-file',str(ROOT/'runtime.env.private'),
        '--mount','type=bind,src='+str(ROOT/'probe')+',dst=/verify,readonly','--workdir','/app/apps/backend','--entrypoint','python',target['newImage'],'-B','/verify/offline-probe.py']
    report=json.loads(run(command,timeout=90).stdout)
    require(report==check_inputs()['probeExpected'] and report.get('passed') is True,'actual_candidate_image_probe_failed')
    return report


def _deploy(*,preflight=False):
    plan,manifest=check_inputs(),read_json(ROOT/'prepared.json')
    progress=read_json(ROOT/'progress.json') if (ROOT/'progress.json').exists() else {}
    reconcile_intent(manifest,progress)
    require(not (ROOT/'rollback-result.json').exists(),'release_was_rolled_back_prepare_a_new_revision')
    if (ROOT/'deployed.json').exists():
        verify_current(manifest,plan,progress,final=True)
        print(json.dumps({'alreadyDeployed':True,'verified':True}),flush=True);return
    verify_current(manifest,plan,progress);idle_gates(manifest,plan);tcp_idle_guard(manifest,plan,progress)
    if preflight:
        print(json.dumps({'preflightPassed':True,'productionChanged':False}),flush=True);return
    for target in manifest['targets']:
        if progress.get(target['service'],{}).get('kind')=='new':continue
        verify_current(manifest,plan,progress);idle_gates(manifest,plan)
        switch(manifest,target,'new',progress)
    verify_current(manifest,plan,progress,final=True)
    result={'deployed':True,'atMs':int(time.time()*1000),'components':progress,'public':public_checks(),
        'otherContainersUnchanged':True,'existingConfigurationUnchanged':True,'optimizerEnabled':True,'migrationOrDependencyChanges':False}
    save('deployed.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('inspect','prepare','preflight','deploy','verify','rollback'))
    action=parser.parse_args().action
    os.umask(0o077)
    try:
        with release_lock():
            if action=='inspect':inspect_release()
            elif action=='prepare':prepare()
            elif action=='rollback':rollback()
            elif action=='verify':verify()
            else:deploy(preflight=action=='preflight')
    except Exception as exc:
        print(json.dumps({'completed':False,'errorType':type(exc).__name__,
                          'reason':str(exc) if isinstance(exc,GuardError) else 'Inspect private server evidence; no further automatic cutover.'}),flush=True)
        raise SystemExit(1) from None

