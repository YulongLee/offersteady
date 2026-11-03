"""Pinned CN Backend-only fixed-binding lookup repair release; never alter protected work.

Reuse the reviewed mock-release ownership, frozen Compose, seven work gates,
TCP gate and recovery proofs. Only this release's scope and Backend lifecycle
are selected below. Private configuration and diagnostics stay on the server.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path('/opt/offersteady/releases/20261104-cn-pinned-binding-1')
RELEASE = 'cn-pinned-binding-20261104.1'
BASES = {'backend': ('7849b16dc46c45c97e70b62d40391a7458c1819f37bdad58f873159936571e8d', 'sha256:dc8f3bb3aa95b6615686226c95612d7b3973860d2b2da0dd391a316134266b9b')}
ROLLBACK_IMAGE = 'sha256:dc8f3bb3aa95b6615686226c95612d7b3973860d2b2da0dd391a316134266b9b'
BASELINE_RUNTIME_SHA256 = '31d4ce4c3d625d010d9cd38efea52c9a9199217dfb2968d31ee2c08826a21f1c'
BASELINE_IMAGE_SHA256 = BASELINE_RUNTIME_SHA256
ANCILLARY_INPUTS = {'packages/protocol/src/material-upload-formats.json': 'e6607164d21950319ab2b6179d38ed6cf771715a2663c18db704af612907ac2f'}
ENTITY_GATE = 'release_support/cn_realtime_shared_20261104/cn_entity_idle_gate.py'
MANIFEST_PATH = 'apps/backend/app/desktop_release_manifest.json'
MANIFEST_SHA256 = 'd7b106a6497bce873d67c2c81b045fab520aaa7382296978a8f6a04056e10927'
APPROVED_BACKEND_SHA256 = {'apps/backend/app/services/cn_realtime_entity_state.py': '23a7ba15c30ac651a2859b1391ca563b8799f85f1e73145cc546d8833c7b8f05', 'apps/backend/app/services/realtime_speech_service.py': '4e1a297f9b82da241a189767d16196718ade539ce1448ce5fdd56f6682aec118', 'apps/backend/app/services/redis_realtime_speech_repository.py': '78543dcb51f42015ecab45c209990fde79663e82b11d20c0c45e73d2f95e6fb7'}
ADDED_PATHS = set()
SUPPORT = Path(__file__).parent / 'release_support/cn_upload20m_model1017_20261021_r2'

_spec = importlib.util.spec_from_file_location('cn_pinned_binding_reviewed_controller', Path(__file__).with_name('release_cn_mock.py'))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
P, H = M.P, M.H
GuardError, require, digest, canonical = M.GuardError, M.require, M.digest, M.canonical
read_json, run, inspect, environment = M.read_json, M.run, M.inspect, M.environment
write_json = M.write_json
GATES, TCP_GATE, FINANCIAL_ANCHOR_MS = M.GATES, M.TCP_GATE, M.FINANCIAL_ANCHOR_MS
_bind_reviewed_primitives = M.bind_primitives
_reviewed_idle_gates = M.idle_gates
_reviewed_tcp_gate = M.tcp_gate
_idle_authorization = None


def bind_primitives():
    M.ROOT, M.RELEASE, M.BASES, M.SUPPORT = ROOT, RELEASE, BASES, SUPPORT
    _bind_reviewed_primitives()
    M.check_plan = check_plan
    M.expected_inventory = expected_inventory
    M.expected_settings = expected_settings
    M.idle_gates = idle_gates
    M.tcp_gate = tcp_gate


def save(name, value):
    write_json(ROOT / name, value)


def emit(**value):
    print(json.dumps(value, separators=(',', ':')), flush=True)


def inventory(service, *, image=None):
    bind_primitives()
    return M.inventory(service, image=image)


def expected_inventory(plan, service, kind):
    require(service == 'backend' and kind in {'baseline', 'new', 'rollback'}, 'unexpected_target_or_kind')
    return plan['candidates']['backend']['inventory'] if kind == 'new' else plan['baselines']['backend']['inventory']


def expected_settings(before, kind):
    require(len(before) == 344 and before.get('product_edition') == 'cn'
            and before.get('environment') == 'production'
            and before.get('cn_hot_database_pool_enabled') is False, 'settings_contract_changed')
    return dict(before)


def support_paths():
    prefix = 'release_support/cn_upload20m_model1017_20261021_r2/'
    return {Path(__file__).name, 'release_cn_mock.py', 'release_cn_upload20m_model1017_v2.py',
            prefix + 'base_helpers.py', *(prefix + n for n in (*GATES, TCP_GATE)), ENTITY_GATE}


def check_candidate_scope(plan):
    require(set(plan['baselines']) == {'backend'} and set(plan['candidates']) == {'backend', 'backendRollback'}, 'candidate_components_changed')
    baseline = plan['baselines']['backend']
    old, image_old = baseline['inventory'], baseline['imageInventory']
    require(len(old) == len(image_old) == 237 and digest(canonical(old)) == BASELINE_RUNTIME_SHA256
            and digest(canonical(image_old)) == BASELINE_IMAGE_SHA256, 'baseline_source_manifest_changed')
    require(old.get(MANIFEST_PATH) == MANIFEST_SHA256 and set(old) == set(image_old)
            and old == image_old, 'baseline_hot_manifest_contract_changed')
    for candidate in plan['candidates'].values():
        require(set(candidate) == {'image', 'inventory', 'settingsSha256'}
                and re.fullmatch(r'sha256:[0-9a-f]{64}', candidate['image'])
                and isinstance(candidate['inventory'], dict)
                and candidate['settingsSha256'] == baseline['settingsSha256'], 'candidate_manifest_invalid')
    candidate = plan['candidates']['backend']
    require(set(candidate['inventory']) == set(old) | ADDED_PATHS
            and len(candidate['inventory']) == 237, 'backend_input_set_changed')
    require(all(candidate['inventory'][n] == sha or n in APPROVED_BACKEND_SHA256 for n, sha in old.items()), 'unapproved_backend_input_changed')
    require(all(candidate['inventory'].get(n) == sha for n, sha in APPROVED_BACKEND_SHA256.items()), 'unreviewed_pinned_binding_source')
    rollback = plan['candidates']['backendRollback']
    require(rollback['image'] == ROLLBACK_IMAGE and rollback['inventory'] == old, 'rollback_hot_manifest_not_preserved')
    require(candidate['image'] not in {BASES['backend'][1], ROLLBACK_IMAGE}, 'candidate_image_not_incremental')


def check_plan():
    bind_primitives()
    plan = read_json(ROOT / 'input.json')
    fields = {'releaseId', 'baselines', 'candidates', 'openapiBefore', 'nginxInputs', 'supportFiles', 'webInventory', 'runtimeBefore',
              'orphanAnswerContext', 'nonTargets', 'candidateProbe', 'financialAnchorMs', 'ancillaryInputs'}
    require(set(plan) == fields and plan['releaseId'] == RELEASE and set(plan['baselines']) == {'backend'}, 'input_scope_invalid')
    require(type(plan['financialAnchorMs']) is int and plan['financialAnchorMs'] == FINANCIAL_ANCHOR_MS, 'financial_anchor_invalid')
    baseline = plan['baselines']['backend']
    require((baseline['id'], baseline['image']) == BASES['backend'], 'baseline_scope_invalid')
    require(re.fullmatch('[0-9a-f]{64}', baseline['settingsSha256']), 'settings_hash_missing')
    require(plan['orphanAnswerContext'] == P.expected_orphan_context(baseline), 'original_process_anchor_drift')
    require(isinstance(plan['openapiBefore']['paths'], (list, dict)) and len(plan['openapiBefore']['paths']) == 203
            and re.fullmatch('[0-9a-f]{64}', plan['openapiBefore']['schemaSha256']), 'schema_contract_changed')
    require(isinstance(plan['nonTargets'], dict) and len(plan['nonTargets']) == 7
            and 'compose-web-1' in plan['nonTargets'] and 'compose-backend-1' not in plan['nonTargets'], 'non_target_scope_changed')
    require(isinstance(plan['webInventory'], dict) and len(plan['webInventory']) == 366
            and {'index.html', 'guide.html', 'privacy.html', 'terms.html', 'offersteady-build.json'} <= set(plan['webInventory'])
            and all(re.fullmatch('[0-9a-f]{64}', value) for value in plan['webInventory'].values()), 'web_inventory_invalid')
    require(set(plan['runtimeBefore']) == {'python', 'distributions'} and plan['runtimeBefore']['python'] == '3.13.15'
            and isinstance(plan['runtimeBefore']['distributions'], dict) and len(plan['runtimeBefore']['distributions']) == 44,
            'runtime_dependency_contract_changed')
    require(set(plan['supportFiles']) == support_paths(), 'support_scope_invalid')
    for relative, sha in plan['supportFiles'].items():
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == sha, 'release_controller_drift')
    require(set(plan['candidateProbe']) == {'scriptSha256', 'resultSha256'}, 'probe_contract_invalid')
    for name, key in (('candidate-probe.py', 'scriptSha256'), ('candidate-probe-result.json', 'resultSha256')):
        path = ROOT / name
        require(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == plan['candidateProbe'][key], 'candidate_probe_drift')
    result = read_json(ROOT / 'candidate-probe-result.json')
    require(result.get('passed') is True and result.get('image') == plan['candidates']['backend']['image'], 'candidate_probe_failed')
    require(isinstance(plan['nginxInputs'], dict) and '/etc/nginx/nginx.conf' in plan['nginxInputs']
            and '/etc/nginx/conf.d/default.conf' in plan['nginxInputs'], 'nginx_input_inventory_missing')
    require(plan['ancillaryInputs'] == ANCILLARY_INPUTS, 'ancillary_inputs_contract_changed')
    check_candidate_scope(plan)
    return plan


def check_files(manifest, plan):
    bind_primitives()
    return M.check_files(manifest, plan)


def verify_runtime(manifest, plan, progress, *, final=False, recovery=False):
    bind_primitives()
    require(set(manifest['targets']) == {'backend'} and set(progress) <= {'backend'}, 'unexpected_target_or_progress')
    M.verify_runtime(manifest, plan, progress, final=final, recovery=recovery)
    require(inventory('web') == plan['webInventory'], 'non_target_web_files_changed')
    require(runtime_contract() == plan['runtimeBefore'], 'runtime_dependencies_changed')
    verify_ancillary_inputs(plan)
    verify_single_writer()


def runtime_contract():
    code = "import importlib.metadata,json,platform;print(json.dumps({'python':platform.python_version(),'distributions':{d.metadata['Name'].lower().replace('_','-'):d.version for d in importlib.metadata.distributions()}},sort_keys=True,separators=(',',':')))"
    return json.loads(run(['docker', 'exec', 'compose-backend-1', 'python', '-B', '-c', code]).stdout)


def candidate_checks(plan, runtime_env_path):
    bind_primitives()
    baseline = inspect(BASES['backend'][1])
    for key in ('backend', 'backendRollback'):
        candidate = plan['candidates'][key]
        H.verify_image_base(inspect(candidate['image']), baseline)
        require(inventory('backend', image=candidate['image']) == candidate['inventory'], 'candidate_image_inventory_drift')
        verify_ancillary_inputs(plan, image=candidate['image'])
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
        idle_gates(manifest)
        tcp_gate(manifest, progress)
        return emit(prepared=True, alreadyPrepared=True, productionChanged=False)
    require(not (ROOT / 'backend').exists(), 'partial_preparation_requires_review')
    P.check_schema(P.schema(), plan['openapiBefore'])
    require(P.nginx_inputs() == plan['nginxInputs'], 'baseline_nginx_inputs_drift')
    current = inspect('compose-backend-1')
    baseline = plan['baselines']['backend']
    require((current['Id'], current['Image']) == BASES['backend'], 'fresh_runtime_baseline_changed')
    require(all(baseline.get(k) == v for k, v in H.container_signature(current).items()), 'fresh_runtime_signature_changed')
    require(current['State']['Running'] and current['RestartCount'] == 0
            and current['State'].get('Health', {}).get('Status') == 'healthy', 'baseline_unhealthy')
    require(inventory('backend') == baseline['inventory']
            and inventory('backend', image=BASES['backend'][1]) == baseline['imageInventory'], 'baseline_source_or_static_drift')
    require(inventory('web') == plan['webInventory'], 'non_target_web_files_changed')
    require(runtime_contract() == plan['runtimeBefore'], 'runtime_dependencies_changed')
    verify_ancillary_inputs(plan)
    verify_single_writer()
    manifest = {'inputSha256': digest((ROOT / 'input.json').read_bytes()), 'targets': {}, 'privateFiles': {},
                'nonTargets': {}, 'orphanAnswerContext': deepcopy(plan['orphanAnswerContext'])}
    target = H.freeze(current, 'backend')
    target['newImage'] = plan['candidates']['backend']['image']
    target['rollbackImage'] = plan['candidates']['backendRollback']['image']
    before = expected_settings(P.settings('backend'), 'baseline')
    require(P.settings_sha(before) == baseline['settingsSha256'], 'baseline_settings_drift')
    save('backend/settings-before.private.json', before)
    for kind in ('new', 'rollback'):
        path = ROOT / 'backend' / (kind + '.compose.json')
        write_json(path, {'services': {'backend': {'image': target[kind + 'Image']}}})
        target[kind + 'Overlay'], target[kind + 'OverlaySha256'] = str(path), digest(path.read_bytes())
        require(H.rendered(target, frozen=True, overlay=path) == H.expected_overlay(
            read_json(ROOT / 'backend/rendered-before.json'), 'backend', target[kind + 'Image']), 'unrelated_rendered_configuration_change')
    manifest['targets']['backend'] = target
    names = set(run(['docker', 'ps', '--format', '{{.Names}}']).stdout.decode().splitlines())
    manifest['nonTargets'] = {n: H.container_signature(inspect(n)) for n in names - {target['container']}}
    require(manifest['nonTargets'] == plan['nonTargets'], 'fresh_non_target_signature_changed')
    env = environment(read_json(ROOT / 'backend/container-before.json'))
    require(all('\n' not in k + v and '\r' not in k + v for k, v in env.items()), 'runtime_env_file_unsafe')
    env_path = ROOT / 'runtime.env.private'
    env_path.write_text(''.join(k + '=' + v + '\n' for k, v in sorted(env.items())))
    env_path.chmod(0o600)
    candidate_checks(plan, env_path)
    for path in (ROOT / 'backend').iterdir():
        if path.is_file() and path.name not in {'new.compose.json', 'rollback.compose.json'}:
            manifest['privateFiles'][str(path.relative_to(ROOT))] = digest(path.read_bytes())
    manifest['privateFiles']['runtime.env.private'] = digest(env_path.read_bytes())
    save('prepared.json', manifest)
    verify_runtime(manifest, plan, {})
    idle_gates(manifest)
    tcp_gate(manifest, {})
    emit(prepared=True, productionChanged=False, components=1, poolEnabled=False)


def idle_gates(manifest):
    bind_primitives()
    verify_single_writer()
    records = _reviewed_idle_gates(manifest)
    entity_idle_gate(manifest)
    return records


def tcp_gate(manifest, progress, *, recovery=False):
    # This release has no residual-connection exception. Both normal cutover
    # and every recovery require the original strict zero-TCP proof.
    bind_primitives()
    return _reviewed_tcp_gate(manifest, progress, recovery=recovery)


def load_state():
    bind_primitives()
    return M.load_state()


def switch(manifest, plan, progress, service, kind):
    bind_primitives()
    require(service == 'backend' and kind in {'new', 'rollback'}, 'unexpected_target_or_kind')
    return M.switch(manifest, plan, progress, service, kind)


def public_checks(plan, progress):
    opener = build_opener(ProxyHandler({}))
    files = plan['webInventory']
    routes = {'/': 'index.html', '/guide': 'guide.html', '/privacy': 'privacy.html', '/terms': 'terms.html',
              '/pricing': 'seo/pricing.html', '/features/ai-interview-assistant': 'seo/ai-interview-assistant.html'}
    routes.update({path: 'index.html' for path in ('/login', '/app/mock-interviews', '/app/resume-optimizer', '/app/interviews/new', '/app/written-exams')})
    routes.update({'/' + path: path for path in ('llms.txt', 'llms-full.txt', 'public-facts.json', 'sitemap.xml', 'offersteady-build.json')})
    results = []
    for path, name in routes.items():
        with opener.open(Request('https://mianshiwen.cn' + path + '?release=' + RELEASE,
                                 headers={'Cache-Control': 'no-cache', 'Accept-Encoding': 'identity'}), timeout=15) as response:
            data = response.read()
            require(response.status == 200 and digest(data) == files[name], 'public_static_mismatch')
            results.append({'path': path, 'status': 200, 'sha256': digest(data)})
    with opener.open(Request('https://mianshiwen.cn/healthz', headers={'Cache-Control': 'no-cache'}), timeout=15) as response:
        require(response.status == 200 and json.load(response)['data']['status'] == 'ok', 'public_health_failed')
    kind = progress.get('backend', {}).get('kind', 'baseline')
    save('public-verification.json', {'health': 200, 'checks': results, 'kind': kind})


def verify():
    plan = check_plan()
    manifest, progress = load_state()
    verify_runtime(manifest, plan, progress, final=True)
    public_checks(plan, progress)
    emit(verified=True, components=1, poolEnabled=False, inputs=237, settings=344, schemaPaths=203, nonTargetsUnchanged=True)


def rollback():
    plan = check_plan()
    manifest, progress = load_state()
    check_files(manifest, plan)
    M.targets_owned(manifest, progress, recovery=True)
    if 'backend' not in progress:
        current = inspect(manifest['targets']['backend']['container'])
        if not current['State']['Running']:
            M.baseline_stopped_proof('backend', current)
            check_plan()
            check_files(manifest, plan)
            M.targets_owned(manifest, progress, recovery=True)
            idle_gates(manifest)
            tcp_gate(manifest, progress, recovery=True)
            try:
                run(['docker', 'start', current['Id']])
            finally:
                after = inspect(current['Id'])
                require((after['Id'], after['Image']) == BASES['backend']
                        and P.ownership_signature(after) == P.ownership_signature(current), 'restored_baseline_owner_changed')
                save('baseline-restorations.json', {'backend': {'signature': H.container_signature(after)}})
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                after = inspect(current['Id'])
                if after['State']['Running'] and after['State'].get('Health', {}).get('Status') == 'healthy':
                    break
                time.sleep(1)
            else:
                raise GuardError('baseline_restoration_health_failed')
    if progress.get('backend', {}).get('kind') == 'new':
        switch(manifest, plan, progress, 'backend', 'rollback')
    verify_runtime(manifest, plan, progress)
    require(all(e['kind'] == 'rollback' for e in progress.values()), 'rollback_incomplete')
    public_checks(plan, progress)
    save('rollback-result.json', {'restored': True, 'atMs': int(time.time() * 1000), 'manifestPreserved': True})
    emit(rollbackSucceeded=True)


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
        if progress.get('backend', {}).get('kind') != 'new':
            verify_runtime(manifest, plan, progress)
            switch(manifest, plan, progress, 'backend', 'new')
        verify_runtime(manifest, plan, progress, final=True)
        public_checks(plan, progress)
        save('deployed.json', {'releaseId': RELEASE, 'atMs': int(time.time() * 1000), 'services': ['backend'],
                               'images': {'backend': manifest['targets']['backend']['newImage']}, 'poolEnabled': False})
        emit(deployed=True, components=1, poolEnabled=False)
    except Exception as exc:
        # Unknown states and all drift/read failures stop. Only an understood
        # health/Compose failure enters the reviewed ownership-limited recovery;
        # recovery itself repeats all guards and never bypasses active work.
        recoverable = (isinstance(exc, GuardError) and str(exc) == 'target_health_failed') or isinstance(
            exc, (subprocess.CalledProcessError, subprocess.TimeoutExpired))
        if not recoverable:
            raise
        restored = False
        try:
            rollback()
            restored = True
        except Exception:
            pass
        save('failed-cutover.json', {'failed': True, 'rollbackSucceeded': restored})
        raise GuardError('cutover_failed_rollback_' + ('succeeded' if restored else 'needs_attention')) from None


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'preflight', 'deploy', 'verify', 'rollback'))
    args = parser.parse_args()
    try:
        require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve() == ROOT, 'private_release_directory_missing')
        bind_primitives()
        with M.release_lock():
            {'prepare': prepare, 'preflight': lambda: deploy(preflight=True), 'deploy': deploy, 'verify': verify, 'rollback': rollback}[args.action]()
    except Exception as exc:
        reason = str(exc) if isinstance(exc, GuardError) and re.fullmatch('[a-z0-9_]+', str(exc)) else 'release_operation_failed_private_diagnostics_only'
        emit(ok=False, reason=reason)
        raise SystemExit(75 if reason == 'protected_user_work_cutover_deferred' else 1) from None



def verify_ancillary_inputs(plan, *, image=None):
    require(plan['ancillaryInputs'] == ANCILLARY_INPUTS, 'ancillary_inputs_contract_changed')
    for relative, checksum in ANCILLARY_INPUTS.items():
        data = M.read_image_file(image, '/app/' + relative) if image else H.read_container('compose-backend-1', '/app/' + relative)
        require(digest(data) == checksum, 'ancillary_input_drift')


def verify_single_writer():
    current = inspect('compose-backend-1')
    names = run(['docker', 'ps', '--filter', 'label=com.docker.compose.service=backend', '--format', '{{.Names}}']).stdout.decode().splitlines()
    require(names == (['compose-backend-1'] if current['State']['Running'] else []), 'single_backend_container_unproven')
    entrypoint, arguments = current['Config'].get('Entrypoint') or [], current['Config'].get('Cmd') or []
    require(type(entrypoint) is list and type(arguments) is list,
            'single_writer_command_unproven')
    command = entrypoint + arguments
    require(command and all(type(value) is str and value for value in command), 'single_writer_command_unproven')
    executable = Path(command[0]).name
    if executable == 'uvicorn':
        server_command = command
    elif re.fullmatch(r'python(?:[0-9]+(?:\.[0-9]+)*)?', executable) and command[1:3] == ['-m', 'uvicorn']:
        # The actual fixed Backend image starts the module with python -m;
        # accept this exact form without admitting shells or wrapper scripts.
        server_command = command[2:]
    else:
        raise GuardError('single_writer_command_unproven')
    require(len(server_command) >= 2 and server_command[1] == 'app.main:app'
            and '--reload' not in server_command, 'single_writer_command_unproven')
    env = environment(current)
    workers = env.get('WEB_CONCURRENCY', '1')
    for i, value in enumerate(server_command):
        if value == '--workers':
            require(i + 1 < len(server_command), 'single_writer_command_unproven')
            workers = server_command[i + 1]
        elif value.startswith('--workers='):
            workers = value.split('=', 1)[1]
    require(str(workers) == '1' and not env.get('GUNICORN_CMD_ARGS'), 'single_writer_config_unproven')
    if not current['State']['Running']:
        require(H.stopped_process(current), 'single_writer_stopped_process_unproven')
        return
    code = """from pathlib import Path
import json
rows=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        rows.append(path.read_bytes().split(bytes([0])))
    except (FileNotFoundError, ProcessLookupError):
        continue

def server(args):
    if not args:
        return False
    name=args[0].split(b'/')[-1]
    if name in (b'uvicorn',b'gunicorn'):
        return True
    if not name.startswith(b'python'):
        return False
    return (b'--multiprocessing-fork' in args or len(args)>1 and args[1].split(b'/')[-1] in (b'uvicorn',b'gunicorn')
            or len(args)>2 and args[1]==b'-m' and args[2] in (b'uvicorn',b'gunicorn',b'multiprocessing.spawn'))
print(json.dumps({'serverProcesses':sum(server(args) for args in rows)}))
"""
    try:
        value = json.loads(run(['docker', 'exec', current['Id'], 'python', '-B', '-c', code]).stdout)
    except Exception:
        raise GuardError('single_writer_process_read_failed') from None
    require(isinstance(value, dict) and set(value) == {'serverProcesses'}
            and type(value['serverProcesses']) is int and value['serverProcesses'] == 1, 'single_writer_process_count_unproven')
    after = inspect(current['Id'])
    require(H.container_signature(after) == H.container_signature(current), 'single_writer_owner_changed')


def entity_idle_gate(manifest):
    # This standalone read-only gate understands the new namespace even when
    # executed with the baseline image. It must never instantiate a writer repo.
    try:
        response = subprocess.run(P.gate_command(manifest), input=(ROOT / ENTITY_GATE).read_bytes(), capture_output=True, timeout=25)
        value = json.loads(response.stdout)
    except Exception:
        raise GuardError('protected_entity_gate_unavailable') from None
    # Exact numeric contract is supplied by the independently reviewed gate.
    validate_entity_gate(value, response.returncode)


def validate_entity_gate(value, returncode):
    protected = {'activeCnBindings', 'activeCnCandidates', 'pendingCnCandidateClaims', 'recentCnEntityWrites',
                 'unknownCnSessionStates', 'invalidCnEntityMetadata', 'cnEntityReadFailures',
                 'cnEntityScanLimitExceeded', 'cnEntityMutationDetected'}
    informational = {'cnBoundBindings', 'cnStaleBindings', 'cnRetiredBindings', 'cnCandidates',
                     'cnRetiredCandidates', 'cnHistoricalEntities', 'scannedCnEntityRecords'}
    require(isinstance(value, dict) and set(value) == protected | informational | {'atMs'}
            and all(type(v) is int and v >= 0 for v in value.values())
            and 0 <= int(time.time() * 1000) - value['atMs'] <= 10000
            and returncode in {0, 75}, 'protected_entity_gate_unavailable')
    save('last-entity-idle-gate.json', value)
    unknown = {'unknownCnSessionStates', 'invalidCnEntityMetadata', 'cnEntityReadFailures', 'cnEntityScanLimitExceeded'}
    require(not any(value[k] for k in unknown), 'protected_entity_gate_unavailable')
    busy = any(value[k] for k in protected)
    require((returncode == 75) == bool(busy), 'protected_entity_gate_unavailable')
    require(not busy, 'protected_user_work_cutover_deferred')


bind_primitives()

if __name__ == '__main__':
    main()
