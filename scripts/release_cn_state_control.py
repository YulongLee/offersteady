"""Pinned, idle-only CN Backend and Web state/control release.

The reviewed October 21 freezing/ownership primitives are imported as helpers;
none of that release's prepare/deploy entry points are called. Private snapshots
remain on the server. This controller never ends or alters protected user work.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path('/opt/offersteady/releases/20261029-cn-state-control-1')
RELEASE = 'cn-state-control-20261029.1'
BASES = {
    'backend': ('21f7de4b0ac42d20910d123cd3b773dce039ce34c73035856d3f64b94b57a483', 'sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88'),
    'web': ('15651b71a7565c971ee997752c22f9fd37308159fd5466e9568baad3f2bfd987', 'sha256:9261bdb414ae99bc16e3e7efbddef715f3ca461756ee02bc89cf2476d17b311b'),
}
SUPPORT = Path(__file__).parent / 'release_support/cn_upload20m_model1017_20261021_r2'
GATES = ('legacy-gates/idle_gate.py', 'legacy-gates/check-idle.py', 'legacy-gates/readiness-idle.py', 'extra_idle_gate.py', 'active_work_gate.py', 'resume_optimizer_idle_gate.py', 'financial_idle_gate.py')
TCP_GATE = 'backend_tcp_idle_gate.py'
POOL_DEFAULTS = {'cn_hot_database_pool_enabled': False, 'cn_hot_database_pool_max_size': 4,
                 'cn_hot_database_pool_max_waiting': 16, 'cn_hot_database_pool_timeout_seconds': 3.0}
BACKEND_ALLOWED = {
    'apps/backend/app/core/config.py', 'apps/backend/app/main.py', 'apps/backend/app/modules/web.py',
    'apps/backend/app/ports/interview_session.py', 'apps/backend/app/services/document_service.py',
    'apps/backend/app/services/interview_session_repository.py',
    'apps/backend/app/services/postgres_authentication_repository.py',
    'apps/backend/app/services/postgres_interview_session_repository.py',
    'apps/backend/app/services/realtime_speech_service.py', 'apps/backend/app/services/session_service.py',
    'apps/backend/pyproject.toml', 'apps/backend/app/platform/cn_hot_database.py',
}
WEB_HTML = {'index.html', 'guide.html', 'privacy.html', 'terms.html'}
WEB_ALLOWED = WEB_HTML | {'offersteady-build.json'}

_spec = importlib.util.spec_from_file_location('cn_state_control_reviewed_primitives', Path(__file__).with_name('release_cn_upload20m_model1017_v2.py'))
P = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = P
_spec.loader.exec_module(P)
H = P.H
GuardError, require, digest, canonical = H.GuardError, H.require, H.digest, H.canonical
read_json, run, inspect, environment = H.read_json, H.run, H.inspect, H.environment
write_json = P.atomic_write_json
H.write_json = write_json


def bind_primitives():
    """Only these pure/helper functions are reused; all mutation is below."""
    P.ROOT = H.ROOT = ROOT
    P.BASES = BASES
    P.SUPPORT = SUPPORT
    P.expected_environment = lambda before, service, kind: dict(environment(before))
    P.expected_render = lambda before, service, image, kind: H.expected_overlay(before, service, image)


bind_primitives()


def save(name, value):
    write_json(ROOT / name, value)


def emit(**value):
    print(json.dumps(value, separators=(',', ':')), flush=True)


def inventory(service, *, image=None):
    return P.inventory(service, image=image)


def expected_inventory(plan, service, kind):
    if kind == 'baseline':
        return plan['baselines'][service]['inventory']
    if service == 'backend' and kind == 'rollback':
        return plan['baselines'][service]['inventory']
    key = 'webRollback' if service == 'web' and kind == 'rollback' else service
    return plan['candidates'][key]['inventory']


def expected_settings(baseline, kind):
    value = dict(baseline)
    if kind == 'new':
        require(not (set(value) & set(POOL_DEFAULTS)), 'pool_fields_already_in_baseline')
        value.update(POOL_DEFAULTS)
    return value


def check_candidate_scope(plan):
    b, c = plan['baselines'], plan['candidates']
    require(set(c) == {'backend', 'web', 'webRollback'}, 'candidate_components_changed')
    for item in c.values():
        require(set(item) <= {'image', 'inventory', 'settingsSha256'} and {'image', 'inventory'} <= set(item)
                and re.fullmatch(r'sha256:[0-9a-f]{64}', item['image']) and isinstance(item['inventory'], dict)
                and item['inventory'] and all(re.fullmatch('[0-9a-f]{64}', v) for v in item['inventory'].values()), 'candidate_manifest_invalid')
    old, new = b['backend']['inventory'], c['backend']['inventory']
    require(set(new) == set(old) | {'apps/backend/app/platform/cn_hot_database.py'}, 'backend_input_set_changed')
    require(all(new[n] == sha or n in BACKEND_ALLOWED for n, sha in old.items()), 'unapproved_backend_input_changed')
    old, new, rollback = b['web']['inventory'], c['web']['inventory'], c['webRollback']['inventory']
    require(set(old) <= set(new) and all(new[n] == sha or n in WEB_ALLOWED for n, sha in old.items()), 'unapproved_web_input_changed')
    added = set(new) - set(old)
    require(added and all(re.fullmatch(r'assets/[A-Za-z0-9_-]+\.(?:js|css)', n) for n in added), 'new_asset_scope_changed')
    require(rollback == old | {n: new[n] for n in added}, 'compatibility_rollback_inventory_changed')
    require(c['backend']['image'] != BASES['backend'][1] and c['web']['image'] != BASES['web'][1]
            and c['webRollback']['image'] != BASES['web'][1], 'candidate_image_not_incremental')


def check_plan():
    bind_primitives()
    p = read_json(ROOT / 'input.json')
    fields = {'releaseId', 'baselines', 'candidates', 'openapiBefore', 'nginxInputs', 'supportFiles',
              'orphanAnswerContext', 'nonTargets', 'candidateProbe'}
    require(set(p) == fields and p['releaseId'] == RELEASE and set(p['baselines']) == set(BASES), 'input_scope_invalid')
    for service, (container_id, image) in BASES.items():
        b = p['baselines'][service]
        require(b['id'] == container_id and b['image'] == image and isinstance(b['inventory'], dict) and b['inventory'], 'baseline_scope_invalid')
    require(p['orphanAnswerContext'] == P.expected_orphan_context(p['baselines']['backend']), 'original_process_anchor_drift')
    prefix = 'release_support/cn_upload20m_model1017_20261021_r2/'
    expected = {Path(__file__).name, 'release_cn_upload20m_model1017_v2.py', prefix + 'base_helpers.py', *(prefix + n for n in (*GATES, TCP_GATE))}
    require(set(p['supportFiles']) == expected, 'support_scope_invalid')
    for relative, sha in p['supportFiles'].items():
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == sha, 'release_controller_drift')
    require(set(p['candidateProbe']) == {'scriptSha256', 'resultSha256'}, 'probe_contract_invalid')
    for name, key in (('candidate-probe.py', 'scriptSha256'), ('candidate-probe-result.json', 'resultSha256')):
        path = ROOT / name
        require(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == p['candidateProbe'][key], 'candidate_probe_drift')
    result = read_json(ROOT / 'candidate-probe-result.json')
    require(result.get('passed') is True and result.get('image') == p['candidates']['backend']['image'], 'candidate_probe_failed')
    require(isinstance(p['nginxInputs'], dict) and '/etc/nginx/nginx.conf' in p['nginxInputs']
            and '/etc/nginx/conf.d/default.conf' in p['nginxInputs'], 'nginx_input_inventory_missing')
    require(re.fullmatch('[0-9a-f]{64}', p['baselines']['backend']['settingsSha256'])
            and re.fullmatch('[0-9a-f]{64}', p['candidates']['backend']['settingsSha256']), 'settings_hash_missing')
    check_candidate_scope(p)
    return p


def check_files(manifest, plan):
    # The old helper remains bound to this release and has no candidate policy.
    bind_primitives()
    P.check_files(manifest, plan)


def targets_owned(manifest, progress, *, recovery=False):
    bind_primitives()
    path = ROOT / 'baseline-restorations.json'
    restorations = read_json(path) if path.exists() else {}
    require(set(restorations) <= set(BASES), 'baseline_restoration_journal_invalid')
    for service, target in manifest['targets'].items():
        current = inspect(target['container'])
        if service not in progress and service in restorations:
            before = read_json(ROOT / service / 'container-before.json')
            require((current['Id'], current['Image']) == BASES[service]
                    and P.ownership_signature(current) == P.ownership_signature(before), 'restored_baseline_owner_changed')
            actual = {k: v for k, v in H.container_signature(current).items() if k != 'health'}
            expected = {k: v for k, v in restorations[service]['signature'].items() if k != 'health'}
            require(actual == expected, 'restored_baseline_process_changed')
        elif recovery and service not in progress and not current['State']['Running']:
            baseline_stopped_proof(service, current)
        else:
            P.targets_owned({'targets': {service: target}}, progress, recovery=recovery)


def baseline_stopped_proof(service, current):
    before = read_json(ROOT / service / 'container-before.json')
    require((current['Id'], current['Image']) == BASES[service]
            and P.ownership_signature(current) == P.ownership_signature(before)
            and H.stopped_process(current), 'baseline_stopped_process_unproven')
    after = inspect(current['Id'])
    require(H.stopped_process(after) and H.container_signature(after) == H.container_signature(current)
            and P.ownership_signature(after) == P.ownership_signature(before), 'baseline_stopped_process_unproven')


def verify_runtime(manifest, plan, progress, *, final=False, recovery=False):
    targets_owned(manifest, progress, recovery=recovery)
    check_files(manifest, plan)
    for service, target in manifest['targets'].items():
        kind = progress.get(service, {}).get('kind', 'baseline')
        current = inspect(target['container'])
        require(current['State']['Running'] and current['RestartCount'] == 0, 'target_not_running')
        if service == 'backend':
            require(current['State'].get('Health', {}).get('Status') == 'healthy', 'backend_unhealthy')
        if service in progress:
            P.runtime_invariant(read_json(ROOT / service / 'container-before.json'), current, target, kind)
        require(inventory(service) == expected_inventory(plan, service, kind), 'runtime_source_or_static_drift')
        if service == 'backend':
            before = read_json(ROOT / 'backend/settings-before.private.json')
            require(P.settings(service) == expected_settings(before, kind), 'effective_settings_drift')
        if final:
            require(kind == 'new', 'partial_release_not_complete')
    require(P.nginx_inputs() == plan['nginxInputs'], 'runtime_nginx_input_tree_changed')
    P.check_schema(P.schema(), plan['openapiBefore'])


def read_image_file(image, path):
    return run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--entrypoint', 'cat', image, path]).stdout


def normalize_html_resources(data):
    """Only exact hashed asset URLs may change in the four active documents."""
    return re.sub(rb'/assets/[A-Za-z0-9_-]+\.(?:js|css)', b'/assets/RELEASE_ASSET', data)


def candidate_checks(plan, runtime_env_path):
    for service in BASES:
        b = plan['baselines'][service]
        candidate = plan['candidates'][service]
        H.verify_image_base(inspect(candidate['image']), inspect(b['image']))
        require(inventory(service, image=candidate['image']) == candidate['inventory'], 'candidate_image_inventory_drift')
    web_base = BASES['web'][1]
    for key in ('web', 'webRollback'):
        image = plan['candidates'][key]['image']
        H.verify_image_base(inspect(image), inspect(web_base))
        require(inventory('web', image=image) == plan['candidates'][key]['inventory'], 'candidate_image_inventory_drift')
        require(P.nginx_inputs(image=image) == plan['nginxInputs'], 'candidate_nginx_input_tree_changed')
        # Verify the Nginx worker can read every public file, not merely root.
        result = run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--user', 'nginx', '--entrypoint', 'sh', image,
                      '-c', 'cd /usr/share/nginx/html && find . -type f -exec sha256sum {} +'])
        readable = {line.split(None, 1)[1][2:]: line.split(None, 1)[0] for line in result.stdout.decode().splitlines()}
        require(readable == plan['candidates'][key]['inventory'], 'candidate_public_files_not_readable')
        config = read_image_file(image, '/etc/nginx/conf.d/default.conf').decode()
        hosts = set(re.findall(r'proxy_pass\s+https?://([A-Za-z0-9_.-]+)', config))
        hosts.update(re.findall(r'^\s*server\s+([A-Za-z0-9_.-]+):[0-9]+', config, re.M))
        args = ['docker', 'run', '--rm', '--network', 'none', '--read-only', '--tmpfs', '/var/cache/nginx', '--tmpfs', '/var/run']
        for host in sorted(hosts):
            require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', host) is not None, 'nginx_probe_host_invalid')
            args.extend(['--add-host', host + ':127.0.0.1'])
        run([*args, '--entrypoint', 'nginx', image, '-t'])
    for name in WEB_HTML:
        before = read_image_file(web_base, '/usr/share/nginx/html/' + name)
        after = read_image_file(plan['candidates']['web']['image'], '/usr/share/nginx/html/' + name)
        require(normalize_html_resources(before) == normalize_html_resources(after), 'public_document_content_changed')
    response = run(['docker', 'run', '--rm', '-i', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--pids-limit', '128', '--memory', '768m',
                    '--env-file', str(runtime_env_path), '-e', 'OFFERSTEADY_RELEASE_PROBE_IMAGE=' + plan['candidates']['backend']['image'],
                    '--workdir', '/app/apps/backend', '--entrypoint', 'python', plan['candidates']['backend']['image'], '-B', '-'],
                   input=(ROOT / 'candidate-probe.py').read_bytes(), timeout=90)
    require(json.loads(response.stdout) == read_json(ROOT / 'candidate-probe-result.json'), 'candidate_actual_probe_mismatch')


def prepare():
    plan = check_plan()
    if (ROOT / 'prepared.json').exists():
        manifest, progress = load_state()
        verify_runtime(manifest, plan, progress)
        return emit(prepared=True, alreadyPrepared=True, productionChanged=False)
    require(not any((ROOT / service).exists() for service in BASES), 'partial_preparation_requires_review')
    P.check_schema(P.schema(), plan['openapiBefore'])
    require(P.nginx_inputs() == P.nginx_inputs(image=BASES['web'][1]) == plan['nginxInputs'], 'baseline_nginx_inputs_drift')
    manifest = {'inputSha256': digest((ROOT / 'input.json').read_bytes()), 'targets': {}, 'privateFiles': {},
                'nonTargets': {}, 'orphanAnswerContext': deepcopy(plan['orphanAnswerContext'])}
    for service, (container_id, image) in BASES.items():
        current = inspect('compose-' + service + '-1')
        require((current['Id'], current['Image']) == (container_id, image), 'fresh_runtime_baseline_changed')
        require(all(plan['baselines'][service].get(k) == v for k, v in H.container_signature(current).items()), 'fresh_runtime_signature_changed')
        require(current['State']['Running'] and current['RestartCount'] == 0, 'baseline_unhealthy')
        if service == 'backend':
            require(current['State'].get('Health', {}).get('Status') == 'healthy', 'baseline_unhealthy')
        require(inventory(service) == inventory(service, image=image) == plan['baselines'][service]['inventory'], 'baseline_source_or_static_drift')
        target = H.freeze(current, service)
        target['newImage'] = plan['candidates'][service]['image']
        target['rollbackImage'] = plan['candidates']['webRollback']['image'] if service == 'web' else image
        if service == 'backend':
            before = P.settings(service)
            require(P.settings_sha(before) == plan['baselines'][service]['settingsSha256'], 'baseline_settings_drift')
            require(P.settings_sha(expected_settings(before, 'new')) == plan['candidates']['backend']['settingsSha256'], 'candidate_settings_scope_changed')
            save('backend/settings-before.private.json', before)
        for kind in ('new', 'rollback'):
            path = ROOT / service / (kind + '.compose.json')
            write_json(path, {'services': {service: {'image': target[kind + 'Image']}}})
            target[kind + 'Overlay'], target[kind + 'OverlaySha256'] = str(path), digest(path.read_bytes())
            require(H.rendered(target, frozen=True, overlay=path) == H.expected_overlay(read_json(ROOT / service / 'rendered-before.json'), service, target[kind + 'Image']), 'unrelated_rendered_configuration_change')
        manifest['targets'][service] = target
    names = set(run(['docker', 'ps', '--format', '{{.Names}}']).stdout.decode().splitlines())
    manifest['nonTargets'] = {n: H.container_signature(inspect(n)) for n in names - {t['container'] for t in manifest['targets'].values()}}
    require(manifest['nonTargets'] == plan['nonTargets'], 'fresh_non_target_signature_changed')
    env = environment(read_json(ROOT / 'backend/container-before.json'))
    require(all('\n' not in k + v and '\r' not in k + v for k, v in env.items()), 'runtime_env_file_unsafe')
    env_path = ROOT / 'runtime.env.private'
    env_path.write_text(''.join(k + '=' + v + '\n' for k, v in sorted(env.items())))
    env_path.chmod(0o600)
    candidate_checks(plan, env_path)
    for service in BASES:
        for path in (ROOT / service).iterdir():
            if path.is_file() and path.name not in {'new.compose.json', 'rollback.compose.json'}:
                manifest['privateFiles'][str(path.relative_to(ROOT))] = digest(path.read_bytes())
    manifest['privateFiles']['runtime.env.private'] = digest(env_path.read_bytes())
    save('prepared.json', manifest)
    verify_runtime(manifest, plan, {})
    emit(prepared=True, productionChanged=False, components=2, poolEnabled=False)


def idle_gates(manifest):
    bind_primitives()
    return P.idle_gates(manifest)


def tcp_gate(manifest, progress, *, recovery=False):
    """Same reviewed TCP contract; owner may be baseline, new or rollback."""
    current = inspect('compose-backend-1')
    expected = progress.get('backend', {})
    before = read_json(ROOT / 'backend/container-before.json')
    require(current['Id'] == expected.get('id', before['Id'])
            and current['Image'] == expected.get('image', before['Image']), 'tcp_container_owner_changed')
    if not current['State']['Running']:
        require(recovery and (expected.get('kind') == 'new' or not expected) and H.stopped_process(current), 'stopped_process_proof_unavailable')
        if not expected:
            baseline_stopped_proof('backend', current)
        after = inspect(current['Id'])
        require(H.stopped_process(after) and H.container_signature(after) == H.container_signature(current), 'stopped_process_proof_unavailable')
        save('last-tcp-idle-gate.json', {'passed': True, 'method': 'stoppedProcessProof'})
        return
    identity, namespace = H.running_process_identity(current), H.host_network_namespace(current)
    try:
        response = subprocess.run(['docker', 'exec', '-i', current['Id'], 'python', '-B', '-'],
                                  input=(SUPPORT / TCP_GATE).read_bytes(), capture_output=True, timeout=10)
        value = json.loads(response.stdout)
    except Exception:
        raise GuardError('protected_tcp_gate_unavailable') from None
    fields = {'passed', 'atMs', 'establishedPort8000', 'tablesRead', 'scannedRows', 'scope', 'networkNamespaceSha256'}
    require(response.returncode == 0 and isinstance(value, dict) and set(value) == fields and value['passed'] is True
            and value['scope'] == 'container_tcp8000_established_only', 'protected_tcp_gate_unavailable')
    require(all(type(value[k]) is int and value[k] >= 0 for k in ('atMs', 'establishedPort8000', 'tablesRead', 'scannedRows'))
            and value['tablesRead'] == 2 and value['establishedPort8000'] <= value['scannedRows'] <= 200000
            and 0 <= int(time.time() * 1000) - value['atMs'] <= 10000
            and value['networkNamespaceSha256'] == namespace, 'protected_tcp_gate_unavailable')
    after = inspect(current['Id'])
    require(H.running_process_identity(after) == identity and H.container_signature(after) == H.container_signature(current)
            and H.host_network_namespace(after) == namespace, 'tcp_container_owner_changed')
    save('last-tcp-idle-gate.json', value)
    require(value['establishedPort8000'] == 0, 'protected_user_work_cutover_deferred')


def load_state():
    manifest = read_json(ROOT / 'prepared.json')
    progress = read_json(ROOT / 'progress.json') if (ROOT / 'progress.json').exists() else {}
    bind_primitives()
    P.reconcile_intent(manifest, progress)
    return manifest, progress


def switch(manifest, plan, progress, service, kind):
    check_plan()
    check_files(manifest, plan)
    targets_owned(manifest, progress, recovery=kind == 'rollback')
    idle_gates(manifest)
    tcp_gate(manifest, progress, recovery=kind == 'rollback')
    target = manifest['targets'][service]
    before = inspect(target['container'])
    save('switch-intent.json', {'service': service, 'kind': kind, 'beforeId': before['Id'], 'previousProgress': deepcopy(progress)})
    try:
        run(H.compose_args(target, frozen=True, overlay=target[kind + 'Overlay']) + ['up', '-d', '--no-build', '--no-deps', '--pull', 'never', service], timeout=120)
    finally:
        current = inspect(target['container'])
        if current['Image'] == target[kind + 'Image'] and current['Config']['Labels'].get('com.docker.compose.project.config_files') == ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']]):
            P.record_created_owner(target, kind, before['Id'], current, progress)
            P.runtime_invariant(read_json(ROOT / service / 'container-before.json'), current, target, kind)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        current = inspect(target['container'])
        if current['State']['Running'] and current['RestartCount'] == 0 and (service != 'backend' or current['State'].get('Health', {}).get('Status') == 'healthy'):
            break
        time.sleep(1)
    else:
        raise GuardError('target_health_failed')
    P.runtime_invariant(read_json(ROOT / service / 'container-before.json'), current, target, kind)
    require(inventory(service) == expected_inventory(plan, service, kind), 'released_source_or_static_drift')
    if service == 'backend':
        ips = lambda c: {k: v.get('IPAddress') for k, v in c['NetworkSettings']['Networks'].items()}
        if ips(before) != ips(current):
            for name in ('compose-web-1', 'compose-admin-1'):
                run(['docker', 'exec', name, 'nginx', '-t'])
                run(['docker', 'exec', name, 'nginx', '-s', 'reload'])


def public_checks(plan, progress):
    kind = progress.get('web', {}).get('kind', 'baseline')
    files = expected_inventory(plan, 'web', kind)
    routes = {'/': 'index.html', '/guide': 'guide.html', '/privacy': 'privacy.html', '/terms': 'terms.html',
              '/pricing': 'seo/pricing.html', '/features/realtime-interview': 'seo/realtime-interview.html',
              '/features/ai-interview-assistant': 'seo/ai-interview-assistant.html'}
    routes.update({n: 'index.html' for n in ('/login', '/app/mock-interviews', '/app/resume-optimizer', '/app/interviews/new', '/app/written-exams')})
    routes.update({'/' + n: n for n in ('llms.txt', 'llms-full.txt', 'public-facts.json', 'sitemap.xml', 'offersteady-build.json')})
    routes.update({'/' + n: n for n in set(files) - set(plan['baselines']['web']['inventory'])})
    opener, results = build_opener(ProxyHandler({})), []
    for path, name in routes.items():
        with opener.open(Request('https://mianshiwen.cn' + path + '?release=' + RELEASE,
                                 headers={'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'}), timeout=15) as response:
            data = response.read()
            require(response.status == 200 and digest(data) == files[name], 'public_static_mismatch')
            if path.startswith('/assets/'):
                expected_type = 'javascript' if name.endswith('.js') else 'text/css'
                require(expected_type in response.headers.get('Content-Type', '') and 'immutable' in response.headers.get('Cache-Control', ''), 'public_asset_headers_invalid')
            results.append({'path': path, 'status': 200, 'sha256': digest(data)})
    with opener.open(Request('https://mianshiwen.cn/healthz', headers={'Cache-Control': 'no-cache'}), timeout=15) as response:
        require(response.status == 200 and json.load(response)['data']['status'] == 'ok', 'public_health_failed')
    save('public-verification.json', {'checks': results, 'health': 200, 'kind': kind})


def verify():
    plan = check_plan()
    manifest, progress = load_state()
    verify_runtime(manifest, plan, progress, final=True)
    public_checks(plan, progress)
    emit(verified=True, components=2, poolEnabled=False, nonTargetsUnchanged=True)


def rollback():
    plan = check_plan()
    manifest, progress = load_state()
    check_files(manifest, plan)
    targets_owned(manifest, progress, recovery=True)
    # Compose may have stopped the baseline and failed before creating a new
    # container. Restart only that exact, twice-proven stopped original owner.
    # Its process signature is journaled separately; original financial anchors
    # and frozen container snapshots are never rewritten.
    for service in ('backend', 'web'):
        if service in progress:
            continue
        current = inspect(manifest['targets'][service]['container'])
        if current['State']['Running']:
            continue
        baseline_stopped_proof(service, current)
        check_plan()
        check_files(manifest, plan)
        targets_owned(manifest, progress, recovery=True)
        idle_gates(manifest)
        tcp_gate(manifest, progress, recovery=True)
        try:
            run(['docker', 'start', current['Id']])
        finally:
            after = inspect(current['Id'])
            require((after['Id'], after['Image']) == BASES[service]
                    and P.ownership_signature(after) == P.ownership_signature(current), 'restored_baseline_owner_changed')
            path = ROOT / 'baseline-restorations.json'
            restorations = read_json(path) if path.exists() else {}
            restorations[service] = {'signature': H.container_signature(after)}
            save('baseline-restorations.json', restorations)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            after = inspect(current['Id'])
            if after['State']['Running'] and (service != 'backend' or after['State'].get('Health', {}).get('Status') == 'healthy'):
                break
            time.sleep(1)
        else:
            raise GuardError('baseline_restoration_health_failed')
    for service in ('web', 'backend'):
        if progress.get(service, {}).get('kind') == 'new':
            switch(manifest, plan, progress, service, 'rollback')
    verify_runtime(manifest, plan, progress)
    require(all(e['kind'] == 'rollback' for e in progress.values()), 'rollback_incomplete')
    public_checks(plan, progress)
    save('rollback-result.json', {'restored': True, 'atMs': int(time.time() * 1000)})
    emit(rollbackSucceeded=True)


DRIFT_REASONS = {
    'release_controller_drift', 'candidate_probe_drift', 'input_manifest_drift', 'private_snapshot_drift',
    'production_compose_or_env_drift', 'production_render_drift', 'release_overlay_drift',
    'unrelated_rendered_configuration_change', 'non_target_container_changed', 'non_target_container_set_changed',
    'release_container_owner_changed', 'release_container_context_owner_changed', 'released_container_signature_changed',
    'baseline_container_owner_changed', 'baseline_signature_changed', 'recovery_static_owner_changed',
    'runtime_source_or_static_drift', 'released_source_or_static_drift', 'runtime_nginx_input_tree_changed',
    'original_process_anchor_drift', 'original_process_snapshot_anchor_drift',
    'restored_baseline_owner_changed', 'restored_baseline_process_changed', 'baseline_stopped_process_unproven',
}
DEFER_REASONS = {'protected_user_work_cutover_deferred', 'protected_work_gate_unavailable', 'protected_tcp_gate_unavailable'}


def deploy(*, preflight=False):
    plan = check_plan()
    manifest, progress = load_state()
    require(not (ROOT / 'rollback-result.json').exists(), 'release_was_rolled_back')
    if (ROOT / 'deployed.json').exists():
        verify()
        return emit(alreadyDeployed=True, productionChanged=False)
    verify_runtime(manifest, plan, progress)
    idle_gates(manifest)
    tcp_gate(manifest, progress)
    if preflight:
        return emit(preflightPassed=True, productionChanged=False)
    try:
        for service in ('backend', 'web'):
            if progress.get(service, {}).get('kind') != 'new':
                verify_runtime(manifest, plan, progress)
                switch(manifest, plan, progress, service, 'new')
        verify_runtime(manifest, plan, progress, final=True)
        public_checks(plan, progress)
        save('deployed.json', {'releaseId': RELEASE, 'atMs': int(time.time() * 1000), 'services': list(BASES),
                               'images': {s: manifest['targets'][s]['newImage'] for s in BASES}, 'poolEnabled': False})
        emit(deployed=True, components=2, poolEnabled=False)
    except Exception as exc:
        if isinstance(exc, GuardError) and str(exc) in DRIFT_REASONS | DEFER_REASONS:
            raise
        restored = False
        try:
            rollback()
            restored = True
        except Exception:
            pass
        save('failed-cutover.json', {'failed': True, 'rollbackSucceeded': restored})
        raise GuardError('cutover_failed_rollback_' + ('succeeded' if restored else 'needs_attention')) from None


@contextmanager
def release_lock():
    with (ROOT / 'release.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GuardError('another_release_action_is_running') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'preflight', 'deploy', 'verify', 'rollback'))
    args = parser.parse_args()
    try:
        require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve() == ROOT, 'private_release_directory_missing')
        with release_lock():
            {'prepare': prepare, 'preflight': lambda: deploy(preflight=True), 'deploy': deploy, 'verify': verify, 'rollback': rollback}[args.action]()
    except Exception as exc:
        reason = str(exc) if isinstance(exc, GuardError) and re.fullmatch('[a-z0-9_]+', str(exc)) else 'release_operation_failed_private_diagnostics_only'
        emit(ok=False, reason=reason)
        raise SystemExit(75 if reason == 'protected_user_work_cutover_deferred' else 1) from None


if __name__ == '__main__':
    main()
