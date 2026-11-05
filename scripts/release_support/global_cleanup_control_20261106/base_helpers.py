"""Reviewed release freezing/signature helpers adapted to the Global project.
Only freezing, configuration equality, signatures and aggregate gate contracts.
Source: artifacts/cn-written-multi-screen-20261019-release-r2/payload/release_cn_written_multi_screen.py
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
ROOT=Path('/opt/offersteady-global/releases/20261022-global-model1017-1')
PROJECT='offersteady-global'
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
        and labels.get('com.docker.compose.service') == service, 'wrong_Global_Compose_identity')
    files = labels['com.docker.compose.project.config_files'].split(',')
    envs = labels.get('com.docker.compose.project.environment_file', '').split(',')
    require(files and envs and all(Path(p).is_absolute() and p.startswith('/opt/offersteady-global/') for p in files + envs),
        'invalid_Global_private_Compose_context')
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

def assert_rendered_image(source, before, service):
    declared = source['services'][service]
    actual = before['Config']['Image']
    if 'image' not in declared:
        # Compose gives build-only services an implicit project-service tag.
        # Accept that precise historical form only; never infer an arbitrary
        # runtime tag or alter the rendered baseline to hide configuration drift.
        require(service in {'web', 'material-worker'} and bool(declared.get('build')) and actual == f'{PROJECT}-{service}',
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

def gate_contract(path):
    if path == 'legacy-gates/check-idle.py':
        return {'liveInterviews','recentPreparing','livePageLeases','recentAudioTracks','unfinishedTasks','runningMaterialJobs'}, {'atMs'}
    if path == 'legacy-gates/check-mock-idle.py':
        return {'activeOrRecentMockInterviews'}, set()
    if path == 'global_mock_companion_idle_gate.py':
        return {'mockControlOrGenerationLeases','material_processing_jobs','material_deletion_jobs','material_reconcile_jobs','protectedMaterialTasks','activeEntityOrLegacyPageLeases'}, set()
    require(path in ('active_work_gate.py','extra_idle_gate.py','resume_optimizer_idle_gate.py','global_financial_idle_gate.py'), 'unknown_protection_gate')
    values={}
    for node in ast.parse((ROOT/path).read_text()).body:
        if isinstance(node,ast.Assign):
            for name in node.targets:
                if isinstance(name,ast.Name) and name.id in ('PROTECTED','MOCK_FIELDS','INFORMATIONAL'):
                    values[name.id]=set(ast.literal_eval(node.value))
    require('PROTECTED' in values and bool(values['PROTECTED']), 'gate_protection_fields_missing')
    protected=values['PROTECTED']
    informational=(values.get('MOCK_FIELDS',set())|values.get('INFORMATIONAL',set()))-protected
    if path == 'active_work_gate.py':
        informational.add('ignoredLegacyFailedQueuedTasks')
    return protected,informational

def normalize_gate(path, counts):
    require(isinstance(counts,dict), 'invalid_gate_summary')
    protected,informational=gate_contract(path)
    require(set(counts) == protected|informational and all(type(v) is int and v >= 0 for v in counts.values()), 'invalid_gate_aggregate')
    if path == 'legacy-gates/check-idle.py':
        require(0 <= int(time.time()*1000)-counts['atMs'] < 90_000, 'stale_global_gate_summary')
    return counts

def gate_is_idle(path, counts):
    protected,_=gate_contract(path)
    return all(counts[key] == 0 for key in protected)

def gate_has_read_or_unknown_failure(path, counts):
    return any(value != 0 and ('unknown' in name.lower() or 'readfail' in name.lower()
        or 'invalid' in name.lower() or name == 'scanLimitExceeded') for name,value in counts.items())

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

def stopped_process(container):
    state=container.get('State',{})
    return (state.get('Running') is False and type(state.get('Pid')) is int and state['Pid']==0
            and state.get('Status')=='exited' and state.get('Restarting') is False
            and state.get('Dead') is False and state.get('Paused') is False)

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
