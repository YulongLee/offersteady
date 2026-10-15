"""Backend-only CN prefetch release, run inside its private CN release directory.

No shared tags, environment files, other service images or application data are
changed. Full Docker/configuration snapshots and error diagnostics stay private.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
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

ROOT = Path('/opt/offersteady/releases/20261015-cn-question-prefetch-1')
CONTAINER = 'compose-backend-1'
BASE_ID = '781edda9fa92f74742450a35625f4a3a8744f9f53d9ade3832cc170440673b7b'
BASE_IMAGE = 'sha256:eb242b56fded1473659c2f4517f07b42eeaff138b59029e5819fbaa972b12488'
NEW_TAG = 'offersteady-cn-backend:question-prefetch-20261015-1'
ROLLBACK_TAG = 'offersteady-cn-backend:question-prefetch-rollback-20261015-1'
FILES = {f'apps/backend/app/services/{name}.py' for name in (
    'chat_service', 'realtime_speech_service', 'question_prefetch_scheduler')}
GATES = {'legacy-gates/idle_gate.py', 'legacy-gates/check-idle.py',
         'legacy-gates/readiness-idle.py', 'extra_idle_gate.py', 'active_work_gate.py'}


class ReleaseError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise ReleaseError(code)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def run(args, *, data=None, timeout=30, cwd=None):
    try:
        result = subprocess.run(args, input=data, capture_output=True, timeout=timeout, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired):
        raise ReleaseError('command_unavailable_or_timeout') from None
    if result.returncode:
        # May contain credentials or raw backend diagnostics: never print them.
        (ROOT / 'last-command.stderr.private').write_bytes(result.stderr)
        raise ReleaseError('command_failed')
    return result.stdout


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def environment(container):
    return dict(item.split('=', 1) for item in container['Config']['Env'] if '=' in item)


INVENTORY = """from pathlib import Path
import hashlib,json
root=Path('/app')
files=[p for folder in ('apps/backend/app','ai/prompts') for p in (root/folder).rglob('*')
       if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'
       and p.name!='.desktop-release-manifest.lock']
print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
"""


def inventory(name):
    return json.loads(run(['docker', 'exec', name, 'python', '-B', '-c', INVENTORY]))


def compose_args(manifest, overlay=None):
    args = ['docker', 'compose', '--project-directory', manifest['workDir'], '-p', 'compose',
            '--env-file', manifest['envFile']]
    for path in manifest['composeFiles']:
        args += ['-f', path]
    if overlay:
        args += ['-f', str(ROOT / overlay)]
    return args


def render(manifest, overlay=None):
    return json.loads(run(compose_args(manifest, overlay) + ['config', '--format', 'json'],
                          cwd=manifest['workDir']))


def check_inputs():
    plan = json.loads((ROOT / 'input.json').read_text())
    require(plan['baselineImage'] == BASE_IMAGE and plan['baselineContainer'] == BASE_ID, 'input_baseline')
    require(set(plan['files']) == FILES, 'input_scope')
    require(len(plan['gates']) == len(GATES) and set(plan['gates']) == GATES, 'incomplete_protected_work_gates')
    require(plan['verified']['candidateTests'] == 221 and plan['verified']['answerTests'] == 16,
            'local_verification_missing')
    for path, expected in plan['files'].items():
        require(digest((ROOT / 'input' / path).read_bytes()) == expected, 'payload_source_drift')
    for path, expected in plan['supportFiles'].items():
        require(digest((ROOT / path).read_bytes()) == expected, 'payload_support_drift')
    require(GATES.issubset(plan['supportFiles']), 'unbound_protected_work_gate')
    report = json.loads((ROOT / 'candidate-verification.json').read_text())
    require(report['passed'] and report['sourceFrozenAfterTests'] and report['candidateHashes'] == plan['files'],
            'candidate_test_source_mismatch')
    require(all(item['returncode'] == 0 for item in report['records']), 'candidate_tests_failed')
    return plan


def non_targets():
    result = {}
    for name in run(['docker', 'ps', '--format', '{{.Names}}']).decode().splitlines():
        if name == CONTAINER:
            continue
        value = inspect(name)
        result[name] = {'id': value['Id'], 'image': value['Image'], 'startedAt': value['State']['StartedAt']}
    return result


def verify_non_targets(manifest):
    for name, expected in manifest['nonTargets'].items():
        value = inspect(name)
        require((value['Id'], value['Image'], value['State']['StartedAt']) == (
            expected['id'], expected['image'], expected['startedAt']), 'unrelated_container_drift')


def config_digest():
    fields = json.loads((ROOT / 'probe/probe-expectations.json').read_text())['runtimeConfigFields']
    code = ("import hashlib,json;from app.core.config import Settings;s=Settings(_env_file=None);"
        f"fields={fields!r};assert all(hasattr(s,k) for k in fields);"
        "assert s.product_edition=='cn' and s.environment=='production';"
        "data={k:getattr(s,k) for k in fields};"
        "print(hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())")
    value = run(['docker', 'exec', '-w', '/app/apps/backend', CONTAINER, 'python', '-B', '-c', code]).decode().strip()
    require(re.fullmatch('[0-9a-f]{64}', value) is not None, 'config_digest_failed')
    return value


def probe(manifest, *, live=False):
    command = ['python', '-B', '/verify/candidate-probe.py', '--expectations',
               '/verify/probe-expectations.json', '--expected-config-sha', manifest['runtimeConfigSha']]
    if live:
        # Only files with no secrets are copied into a new /tmp directory.
        # Running application code, settings files and image source remain read-only.
        target = '/tmp/offersteady-prefetch-readonly-probe-20261015'
        run(['docker', 'exec', CONTAINER, 'mkdir', '-p', target])
        for name in ('candidate-probe.py', 'probe-expectations.json'):
            run(['docker', 'cp', str(ROOT / 'probe' / name), CONTAINER + ':' + target + '/' + name])
        command[2] = target + '/candidate-probe.py'
        command[4] = target + '/probe-expectations.json'
        output = run(['docker', 'exec', '-w', '/app/apps/backend', CONTAINER] + command)
    else:
        output = run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '64', '--memory', '512m',
            '--env-file', str(ROOT / 'runtime.env.private'), '--mount',
            f'type=bind,src={ROOT / "probe"},dst=/verify,readonly', '--workdir', '/app/apps/backend',
            '--entrypoint', 'python', manifest['newImage']] + command[1:], timeout=45)
    result = json.loads(output)
    require(result['passed'], 'candidate_probe_failed')
    return result


def prepare():
    require(not (ROOT / 'prepared.json').exists(), 'already_prepared')
    plan = check_inputs()
    before = inspect(CONTAINER)
    require(before['Id'] == BASE_ID and before['Image'] == BASE_IMAGE, 'actual_baseline_drift')
    require(before['State']['Running'] and before['RestartCount'] == 0, 'baseline_unhealthy')
    require(inventory(CONTAINER) == plan['beforeInventory'], 'live_source_drift')
    labels = before['Config']['Labels']
    files = labels['com.docker.compose.project.config_files'].split(',')
    workdir = labels['com.docker.compose.project.working_dir']
    require(files and all(Path(path).is_file() for path in files), 'compose_files_missing')
    envfile = Path(workdir).parents[1] / '.env.production'
    require(envfile.is_file(), 'environment_file_missing')
    save('container-before.private.json', before)
    (ROOT / 'environment-before.private').write_bytes(envfile.read_bytes())
    envlines = before['Config']['Env']
    require(all('\n' not in item and '\r' not in item for item in envlines), 'multiline_runtime_environment')
    (ROOT / 'runtime.env.private').write_text('\n'.join(envlines) + '\n')
    manifest = {'baselineImage': BASE_IMAGE, 'beforeId': BASE_ID, 'oldRuntimeImage': before['Config']['Image'],
        'composeFiles': files, 'workDir': workdir, 'envFile': str(envfile), 'envSha': digest(envfile.read_bytes()),
        'composeHashes': {path: digest(Path(path).read_bytes()) for path in files},
        'nonTargets': non_targets(), 'inputSha': digest((ROOT / 'input.json').read_bytes())}
    original = render(manifest)
    require(all(str(v) == environment(before).get(k) for k, v in original['services']['backend'].get('environment', {}).items()),
            'rendered_runtime_environment_drift')
    save('compose-before.private.json', original)
    manifest['renderedBeforeSha'] = digest(canonical(original))
    manifest['runtimeConfigSha'] = config_digest()
    # Refuse loss of application changes in the container's writable layer.
    bare = json.loads(run(['docker', 'run', '--rm', '--network', 'none', '--read-only',
        '--entrypoint', 'python', BASE_IMAGE, '-B', '-c', INVENTORY]))
    require(bare == plan['beforeInventory'], 'base_image_writable_source_mismatch')
    context = ROOT / 'build'
    context.mkdir(exist_ok=False)
    base_tag = 'offersteady-cn-baseline:question-prefetch-20261015-1'
    run(['docker', 'tag', BASE_IMAGE, base_tag])
    run(['docker', 'tag', BASE_IMAGE, ROLLBACK_TAG])
    lines = ['FROM ' + base_tag]
    for path in sorted(FILES):
        output = context / path
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'input' / path, output)
        output.chmod(0o644)
        lines.append(f'COPY {path} /app/{path}')
    (context / 'Dockerfile').write_text('\n'.join(lines) + '\n')
    run(['docker', 'build', '--network=none', '--pull=false', '-t', NEW_TAG, str(context)], timeout=90)
    image = inspect(NEW_TAG)
    require(image['Config'] == inspect(BASE_IMAGE)['Config'], 'candidate_image_config_drift')
    manifest['newImage'] = image['Id']
    manifest['rollbackImage'] = BASE_IMAGE
    for name, image_id in (('compose.prefetch.json', image['Id']), ('compose.rollback.json', BASE_IMAGE)):
        save(name, {'services': {'backend': {'image': image_id}}})
    expected = deepcopy(original)
    expected['services']['backend']['image'] = image['Id']
    require(render(manifest, 'compose.prefetch.json') == expected, 'unrelated_compose_change')
    manifest['renderedAfterSha'] = digest(canonical(expected))
    manifest['overlaySha'] = digest((ROOT / 'compose.prefetch.json').read_bytes())
    manifest['rollbackOverlaySha'] = digest((ROOT / 'compose.rollback.json').read_bytes())
    report = probe(manifest)
    require(inventory(CONTAINER) == plan['beforeInventory'], 'source_changed_during_prepare')
    verify_non_targets(manifest)
    save('candidate-image-probe.json', report)
    save('prepared.json', manifest)
    print(json.dumps({'prepared': True, 'newImage': image['Id'], 'productionChanged': False}), flush=True)


def verify_release_files(manifest, plan, *, check_non_targets=True):
    require(digest((ROOT / 'input.json').read_bytes()) == manifest['inputSha'], 'input_manifest_drift')
    require(digest(Path(manifest['envFile']).read_bytes()) == manifest['envSha'], 'environment_file_drift')
    require(all(digest(Path(path).read_bytes()) == value for path, value in manifest['composeHashes'].items()), 'compose_file_drift')
    require(digest(canonical(render(manifest))) == manifest['renderedBeforeSha'], 'rendered_baseline_drift')
    require(digest(canonical(render(manifest, 'compose.prefetch.json'))) == manifest['renderedAfterSha'], 'rendered_candidate_drift')
    require(digest((ROOT / 'compose.prefetch.json').read_bytes()) == manifest['overlaySha'], 'overlay_drift')
    require(digest((ROOT / 'compose.rollback.json').read_bytes()) == manifest['rollbackOverlaySha'], 'rollback_overlay_drift')
    require(inspect(NEW_TAG)['Id'] == manifest['newImage'] and inspect(ROLLBACK_TAG)['Id'] == BASE_IMAGE, 'prepared_image_drift')
    if check_non_targets:
        verify_non_targets(manifest)


def verify_prepared(manifest, plan):
    verify_release_files(manifest, plan)
    current = inspect(CONTAINER)
    saved = json.loads((ROOT / 'container-before.private.json').read_text())
    require(current['Id'] == saved['Id'] == manifest['beforeId'] and current['Image'] == BASE_IMAGE,
            'container_changed_before_cutover')
    require(current['Config'] == saved['Config'] and current['HostConfig'] == saved['HostConfig'], 'runtime_config_drift')
    require(current['Mounts'] == saved['Mounts'], 'runtime_mount_drift')
    require(inventory(CONTAINER) == plan['beforeInventory'], 'live_source_drift')
    require(config_digest() == manifest['runtimeConfigSha'], 'effective_settings_drift')
    verify_non_targets(manifest)


def safe_gate_counts(path, counts):
    require(isinstance(counts, dict), 'invalid_gate_summary')
    if path == 'legacy-gates/readiness-idle.py':
        phases = counts.get('mockPhases')
        require(isinstance(phases, dict), 'invalid_mock_phase_summary')
        require(all(type(value) is int and value >= 0 for value in phases.values()), 'invalid_mock_phase_count')
        allowed = {'preparing', 'generating_question', 'speaking', 'listening', 'paused', 'generating_report', 'completed'}
        return {'mockPhases': {key: value for key, value in phases.items() if key in allowed},
                'unknownPhaseCount': sum(value for key, value in phases.items() if key not in allowed)}
    if path == 'legacy-gates/idle_gate.py':
        allowed = {'atMs', 'liveInterviews', 'recentPreparing', 'sampleAgeMs',
                   'activeInterviews', 'activeWebSessions', 'activeAudioStreams'}
    elif path == 'legacy-gates/check-idle.py':
        allowed = {'live_interviews', 'live_page_leases', 'recent_audio_tracks', 'unfinished_answers'}
    else:
        allowed = {'ignoredLegacyFailedQueuedTasks'}
        for node in ast.parse((ROOT / path).read_text()).body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in
                    ('MOCK_FIELDS', 'PROTECTED') for target in node.targets):
                allowed.update(ast.literal_eval(node.value))
        require(set(counts).issubset(allowed), 'unknown_gate_summary_field')
    selected = {key: counts[key] for key in allowed if key in counts}
    required = allowed if path.startswith('legacy-gates/') else set(counts)
    require(required.issubset(selected) and selected, 'missing_gate_summary_field')
    require(all(type(value) is int and value >= 0 for value in selected.values()), 'invalid_gate_summary_count')
    return selected


def idle_gates(plan):
    records = []
    for path in plan['gates']:
        require(digest((ROOT / path).read_bytes()) == plan['supportFiles'][path], 'gate_source_drift')
        try:
            value = subprocess.run(['docker', 'exec', '-i', '-w', '/app/apps/backend', CONTAINER,
                'python', '-B', '-'], input=(ROOT / path).read_bytes(), capture_output=True, timeout=25)
            counts = safe_gate_counts(path, json.loads(value.stdout))
        except Exception:
            raise ReleaseError('protected_work_gate_unavailable') from None
        record = {'gate': path, 'exitCode': value.returncode, 'counts': counts}
        records.append(record)
        print(json.dumps(record), flush=True)
        if value.returncode:
            save('last-idle-gates.json', records)
            raise ReleaseError('protected_user_work_cutover_deferred')
    save('last-idle-gates.json', records)


def wait_healthy(expected_image):
    deadline = time.monotonic() + 55
    while time.monotonic() < deadline:
        value = inspect(CONTAINER)
        if (value['Image'] == expected_image and value['State']['Running'] and value['RestartCount'] == 0
                and value['State'].get('Health', {}).get('Status') == 'healthy'):
            return value
        time.sleep(1)
    raise ReleaseError('backend_health_failed')


def runtime_invariant(before, after, expected_image):
    require(after['Image'] == expected_image and environment(before) == environment(after), 'runtime_image_or_env_changed')
    for key in set(before['Config']) | set(after['Config']):
        if key in ('Image', 'Hostname', 'Labels', 'Env'):
            continue
        require(before['Config'].get(key) == after['Config'].get(key), 'container_configuration_changed')
    before_hostname = before['Config'].get('Hostname')
    expected_hostname = after['Id'][:12] if before_hostname == before['Id'][:12] else before_hostname
    require(after['Config'].get('Hostname') == expected_hostname, 'hostname_changed')
    labels = lambda value: {k: v for k, v in value['Config'].get('Labels', {}).items()
                            if not k.startswith('com.docker.compose.')}
    require(labels(before) == labels(after), 'application_label_changed')
    require(before['HostConfig'] == after['HostConfig'], 'host_configuration_changed')
    require(before['Mounts'] == after['Mounts'], 'mounts_changed')


def compose_switch(manifest, overlay):
    require(overlay in ('compose.prefetch.json', 'compose.rollback.json'), 'unexpected_overlay')
    key = 'overlaySha' if overlay == 'compose.prefetch.json' else 'rollbackOverlaySha'
    require(digest((ROOT / overlay).read_bytes()) == manifest[key], 'switch_overlay_drift')
    original = json.loads((ROOT / 'compose-before.private.json').read_text())
    require(digest(canonical(original)) == manifest['renderedBeforeSha'], 'saved_render_drift')
    expected = deepcopy(original)
    expected['services']['backend']['image'] = manifest['newImage'] if overlay == 'compose.prefetch.json' else BASE_IMAGE
    require(render(manifest, overlay) == expected, 'switch_unrelated_compose_drift')
    run(compose_args(manifest, overlay) + ['up', '-d', '--no-build', '--no-deps', '--pull', 'never', 'backend'],
        cwd=manifest['workDir'], timeout=90)


def refresh_proxy_if_needed(before, after):
    def ips(container):
        return {key: value['IPAddress'] for key, value in container['NetworkSettings']['Networks'].items()}
    if ips(before) == ips(after):
        return []
    refreshed = []
    for name in ('compose-web-1', 'compose-admin-1'):
        run(['docker', 'exec', name, 'nginx', '-t'])
        run(['docker', 'exec', name, 'nginx', '-s', 'reload'])
        refreshed.append(name)
    return refreshed


def verify_live(manifest, plan):
    after = inspect(CONTAINER)
    before = json.loads((ROOT / 'container-before.private.json').read_text())
    runtime_invariant(before, after, manifest['newImage'])
    require(inventory(CONTAINER) == (plan['beforeInventory'] | plan['files']), 'released_source_inventory_mismatch')
    require(config_digest() == manifest['runtimeConfigSha'], 'released_settings_mismatch')
    report = probe(manifest, live=True)
    with urlopen(Request('https://mianshiwen.cn/healthz', headers={'Cache-Control': 'no-cache'}), timeout=10) as response:
        require(response.status == 200 and json.loads(response.read())['data']['status'] == 'ok', 'public_health_failed')
    with urlopen('https://mianshiwen.cn/login', timeout=10) as response:
        require(response.status == 200, 'public_login_failed')
    code = "import json;from urllib.request import urlopen;d=json.load(urlopen('http://127.0.0.1:8000/openapi.json',timeout=10));print(json.dumps({p:sorted(m) for p,m in d['paths'].items()}))"
    routes = json.loads(run(['docker', 'exec', CONTAINER, 'python', '-B', '-c', code]))
    expected_routes = json.loads((ROOT / 'probe/probe-expectations.json').read_text())['routes']['http']
    require(all(routes.get(path) == methods for path, methods in expected_routes.items()), 'live_api_routes_mismatch')
    require(inspect(manifest['oldRuntimeImage'])['Id'] == BASE_IMAGE, 'shared_runtime_tag_changed')
    require(digest(Path(manifest['envFile']).read_bytes()) == manifest['envSha'], 'environment_file_changed')
    require(all(digest(Path(path).read_bytes()) == value for path, value in manifest['composeHashes'].items()), 'base_compose_changed')
    verify_non_targets(manifest)
    save('live-probe.json', report)
    return {'deployed': True, 'atMs': int(time.time()*1000), 'image': after['Image'], 'container': after['Id'],
        'healthy': True, 'restartCount': after['RestartCount'], 'environmentUnchanged': True,
        'effectiveConfigUnchanged': True, 'otherContainersUnchanged': True, 'sharedRuntimeTagUnchanged': True,
        'applicationFiles': report['applicationFiles'], 'promptFiles': report['promptFiles'],
        'httpPathsVerified': len(expected_routes), 'modelsUnchanged': True, 'backendOnly': True}


def rollback(manifest, plan, *, owned_container_id=None):
    require(digest((ROOT / 'input.json').read_bytes()) == manifest['inputSha'], 'rollback_input_drift')
    check_inputs()
    verify_release_files(manifest, plan, check_non_targets=owned_container_id is None)
    require(digest(Path(manifest['envFile']).read_bytes()) == manifest['envSha'], 'rollback_environment_drift')
    require(all(digest(Path(path).read_bytes()) == value for path, value in manifest['composeHashes'].items()), 'rollback_compose_drift')
    require(digest((ROOT / 'compose.rollback.json').read_bytes()) == manifest['rollbackOverlaySha'], 'rollback_overlay_drift')
    current = inspect(CONTAINER)
    require(current['Image'] in (BASE_IMAGE, manifest['newImage']), 'rollback_would_replace_other_release')
    if owned_container_id is not None:
        # Failed validation of our new container is exactly why automatic
        # recovery is needed; do not require its faulty source/env to pass first.
        require(current['Id'] == owned_container_id, 'automatic_rollback_container_owner_drift')
        if current['Image'] == BASE_IMAGE:
            require(current['Id'] == manifest['beforeId'], 'automatic_rollback_base_owner_drift')
    else:
        runtime_invariant(json.loads((ROOT / 'container-before.private.json').read_text()), current, current['Image'])
        expected_inventory = plan['beforeInventory'] | (plan['files'] if current['Image'] == manifest['newImage'] else {})
        require(inventory(CONTAINER) == expected_inventory, 'rollback_current_source_drift')
        if (ROOT / 'deployed.json').exists() and current['Image'] == manifest['newImage']:
            require(current['Id'] == json.loads((ROOT / 'deployed.json').read_text())['container'], 'rollback_container_owner_drift')
    compose_switch(manifest, 'compose.rollback.json')
    restored = wait_healthy(BASE_IMAGE)
    runtime_invariant(json.loads((ROOT / 'container-before.private.json').read_text()), restored, BASE_IMAGE)
    refresh_proxy_if_needed(current, restored)
    require(inventory(CONTAINER) == plan['beforeInventory'], 'rollback_source_mismatch')
    require(config_digest() == manifest['runtimeConfigSha'], 'rollback_settings_mismatch')
    if owned_container_id is None:
        verify_non_targets(manifest)
    save('rollback-result.json', {'restored': True, 'image': restored['Image'], 'container': restored['Id']})


def deploy(*, preflight=False):
    require(not (ROOT / 'deployed.json').exists(), 'already_deployed')
    plan = check_inputs()
    manifest = json.loads((ROOT / 'prepared.json').read_text())
    verify_prepared(manifest, plan)
    idle_gates(plan)
    if preflight:
        print(json.dumps({'preflightPassed': True, 'productionChanged': False}), flush=True)
        return
    # Repeat immediately before the sole production mutation; no candidate
    # build, route probe or provider call can widen this final idle window.
    verify_prepared(manifest, plan)
    idle_gates(plan)
    verify_prepared(manifest, plan)
    touched = False
    owned_container_id = None
    try:
        touched = True
        compose_switch(manifest, 'compose.prefetch.json')
        switched = inspect(CONTAINER)
        require(switched['Image'] == manifest['newImage'], 'cutover_image_owner_mismatch')
        owned_container_id = switched['Id']
        after = wait_healthy(manifest['newImage'])
        refreshed = refresh_proxy_if_needed(json.loads((ROOT / 'container-before.private.json').read_text()), after)
        result = verify_live(manifest, plan)
        result['proxyReloaded'] = refreshed
        save('deployed.json', result)
        print(json.dumps(result), flush=True)
    except Exception:
        restored = False
        if touched:
            try:
                if owned_container_id is None:
                    current = inspect(CONTAINER)
                    expected_files = ','.join(manifest['composeFiles'] + [str(ROOT / 'compose.prefetch.json')])
                    owned_new = current['Image'] == manifest['newImage'] and current['Config']['Labels'].get(
                        'com.docker.compose.project.config_files') == expected_files
                    owned_old = current['Id'] == manifest['beforeId'] and current['Image'] == BASE_IMAGE
                    require(owned_new or owned_old, 'failed_cutover_container_owner_unknown')
                    owned_container_id = current['Id']
                rollback(manifest, plan, owned_container_id=owned_container_id)
                restored = True
            except Exception:
                pass
        save('failed-cutover.json', {'failed': True, 'rollbackSucceeded': restored})
        raise ReleaseError('cutover_failed_rollback_' + ('succeeded' if restored else 'needs_attention')) from None


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'preflight', 'deploy', 'verify', 'rollback'))
    action = parser.parse_args().action
    require(ROOT.is_dir(), 'private_release_directory_missing')
    with (ROOT / '.operation.lock').open('a') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ReleaseError('another_release_operation_is_running') from None
        if action == 'prepare':
            prepare()
        elif action in ('preflight', 'deploy'):
            deploy(preflight=action == 'preflight')
        else:
            plan = check_inputs()
            manifest = json.loads((ROOT / 'prepared.json').read_text())
            if action == 'verify':
                print(json.dumps(verify_live(manifest, plan)), flush=True)
            else:
                idle_gates(plan)
                rollback(manifest, plan)
                print(json.dumps({'rollbackSucceeded': True}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'passed': False, 'errorCode': str(exc) if isinstance(exc, ReleaseError)
                          else 'unexpected_release_error', 'errorType': type(exc).__name__,
                          'privateValuesPrinted': False}), flush=True)
        raise SystemExit(1) from None
