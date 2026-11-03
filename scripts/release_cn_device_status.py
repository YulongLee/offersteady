"""Pinned CN Backend-only device-status release; never alter protected work.

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

ROOT = Path('/opt/offersteady/releases/20261103-cn-device-status-1')
RELEASE = 'cn-device-status-20261103.1'
BASES = {'backend': (
    'edd16865e5d5c0b1e57f33a696faf28cdffc340846db65e70150bb77a418a4dd',
    'sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a',
)}
ROLLBACK_IMAGE = 'sha256:15824dc57cdaaa817d171f11e3750cc84919750259a595c4741b042bbb2129ab'
BASELINE_RUNTIME_SHA256 = '3cddfb1e35fc03594f2632761758521ac0286932ae7d06635225a6d190cf605d'
BASELINE_IMAGE_SHA256 = '4706b7a4e2540809c0a1aa1e3c0a5a51abc68fa99998cdf87ffffb86d2cb0c93'
MANIFEST_PATH = 'apps/backend/app/desktop_release_manifest.json'
MANIFEST_SHA256 = 'd7b106a6497bce873d67c2c81b045fab520aaa7382296978a8f6a04056e10927'
APPROVED_BACKEND_SHA256 = {
    'apps/backend/app/modules/realtime_speech.py': '46ab0ef117da378ff87760ac36656bb752f9bec40a0ece2aa02e6da43a941eaa',
    'apps/backend/app/platform/cn_device_status_timing.py': '502d1578b076f326a3409d32804bdff20e3ceca4f4cfff5133dfa668efee0a99',
    'apps/backend/app/services/postgres_interview_session_repository.py': '611260aaee7571d818e7771e166ea48c48b0d8d68b21ed6efd537a0244d542f9',
    'apps/backend/app/services/realtime_speech_service.py': 'f853a7ba011e5c720dd79bb7dece0ec7578aa5f27a6b5b9e144df3ce8e3cc5bb',
}
TIMING_PATH = 'apps/backend/app/platform/cn_device_status_timing.py'
SUPPORT = Path(__file__).parent / 'release_support/cn_upload20m_model1017_20261021_r2'

_spec = importlib.util.spec_from_file_location('cn_device_status_reviewed_controller', Path(__file__).with_name('release_cn_mock.py'))
M = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = M
_spec.loader.exec_module(M)
P, H = M.P, M.H
GuardError, require, digest, canonical = M.GuardError, M.require, M.digest, M.canonical
read_json, run, inspect, environment = M.read_json, M.run, M.inspect, M.environment
write_json = M.write_json
GATES, TCP_GATE, FINANCIAL_ANCHOR_MS = M.GATES, M.TCP_GATE, M.FINANCIAL_ANCHOR_MS
_bind_reviewed_primitives = M.bind_primitives


def bind_primitives():
    M.ROOT, M.RELEASE, M.BASES, M.SUPPORT = ROOT, RELEASE, BASES, SUPPORT
    _bind_reviewed_primitives()
    M.check_plan = check_plan
    M.expected_inventory = expected_inventory
    M.expected_settings = expected_settings


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
            prefix + 'base_helpers.py', *(prefix + n for n in (*GATES, TCP_GATE))}


def check_candidate_scope(plan):
    require(set(plan['baselines']) == {'backend'} and set(plan['candidates']) == {'backend', 'backendRollback'}, 'candidate_components_changed')
    baseline = plan['baselines']['backend']
    old, image_old = baseline['inventory'], baseline['imageInventory']
    require(len(old) == len(image_old) == 232 and digest(canonical(old)) == BASELINE_RUNTIME_SHA256
            and digest(canonical(image_old)) == BASELINE_IMAGE_SHA256, 'baseline_source_manifest_changed')
    require(old.get(MANIFEST_PATH) == MANIFEST_SHA256 and set(old) == set(image_old)
            and {n for n in old if old[n] != image_old[n]} == {MANIFEST_PATH}, 'baseline_hot_manifest_contract_changed')
    for candidate in plan['candidates'].values():
        require(set(candidate) == {'image', 'inventory', 'settingsSha256'}
                and re.fullmatch(r'sha256:[0-9a-f]{64}', candidate['image'])
                and isinstance(candidate['inventory'], dict)
                and candidate['settingsSha256'] == baseline['settingsSha256'], 'candidate_manifest_invalid')
    candidate = plan['candidates']['backend']
    require(set(candidate['inventory']) == set(old) | {TIMING_PATH}
            and len(candidate['inventory']) == 233, 'backend_input_set_changed')
    require(all(candidate['inventory'][n] == sha or n in APPROVED_BACKEND_SHA256 for n, sha in old.items()), 'unapproved_backend_input_changed')
    require(all(candidate['inventory'].get(n) == sha for n, sha in APPROVED_BACKEND_SHA256.items()), 'unreviewed_device_status_source')
    rollback = plan['candidates']['backendRollback']
    require(rollback['image'] == ROLLBACK_IMAGE and rollback['inventory'] == old, 'rollback_hot_manifest_not_preserved')
    require(candidate['image'] not in {BASES['backend'][1], ROLLBACK_IMAGE}, 'candidate_image_not_incremental')


def check_plan():
    bind_primitives()
    plan = read_json(ROOT / 'input.json')
    fields = {'releaseId', 'baselines', 'candidates', 'openapiBefore', 'nginxInputs', 'supportFiles', 'webInventory', 'runtimeBefore',
              'orphanAnswerContext', 'nonTargets', 'candidateProbe', 'financialAnchorMs'}
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
    emit(prepared=True, productionChanged=False, components=1, poolEnabled=False)


def idle_gates(manifest):
    bind_primitives()
    return M.idle_gates(manifest)


def tcp_gate(manifest, progress, *, recovery=False):
    bind_primitives()
    return M.tcp_gate(manifest, progress, recovery=recovery)


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
    emit(verified=True, components=1, poolEnabled=False, inputs=233, settings=344, schemaPaths=203, nonTargetsUnchanged=True)


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


bind_primitives()

if __name__ == '__main__':
    main()
