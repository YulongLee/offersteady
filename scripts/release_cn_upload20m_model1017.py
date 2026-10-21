"""Pinned CN release: seven model environment keys and one Nginx upload block.

Run only from the authorized server release directory. Private snapshots never
leave the server. No application repository constructors or model calls.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.request import Request, urlopen

ROOT = Path('/opt/offersteady/releases/20261021-cn-upload20m-model1017-1')
SUPPORT = Path(__file__).parent / 'release_support/cn_upload20m_model1017_20261021'
RELEASE = '20261021-cn-upload20m-model1017-1'
MODEL = 'deepseek-v4.1-flash-1017'
BASES = {
    'backend': ('d12beb7086a7ab6b51b31ea55236b4891a8663607a174c996659c7a8c253ddd3', 'sha256:2f2c89359d2268c460dabad38a4f9466e2af5610e730a94ded797586ef4c5e88'),
    'material-worker': ('ee83fe9162a64ec3cfc59d86a3f89c50a6b00bdc9c985e1ea69882f32f14a49c', 'sha256:df6b8500500e955aa2f01c3bc0c5b40dab218296459f4e8341da268bb6b0ee43'),
    'web': ('75986fa2193dca8ef72a35efbd5b7d74dde71767a97a3e1a0b09076857ce5310', 'sha256:011d1f5de69f1208bf8b9c5b9496d4acddcbe090e6c159a0173214eb8efbbee2'),
}
MODEL_KEYS = {
    'backend': ('OFFERSTEADY_CHAT_QWEN_MODEL', 'OFFERSTEADY_CHAT_QUICK_MODEL', 'OFFERSTEADY_CHAT_DETAIL_MODEL', 'OFFERSTEADY_SCREENSHOT_VISION_MODEL'),
    'material-worker': ('OFFERSTEADY_CHAT_QWEN_MODEL', 'OFFERSTEADY_CHAT_QUICK_MODEL', 'OFFERSTEADY_CHAT_DETAIL_MODEL'),
}
SETTINGS_KEYS = {'OFFERSTEADY_CHAT_QWEN_MODEL': 'chat_qwen_model', 'OFFERSTEADY_CHAT_QUICK_MODEL': 'chat_quick_model', 'OFFERSTEADY_CHAT_DETAIL_MODEL': 'chat_detail_model', 'OFFERSTEADY_SCREENSHOT_VISION_MODEL': 'screenshot_vision_model'}
GATES = ('legacy-gates/idle_gate.py', 'legacy-gates/check-idle.py', 'legacy-gates/readiness-idle.py', 'extra_idle_gate.py', 'active_work_gate.py', 'resume_optimizer_idle_gate.py', 'financial_idle_gate.py')
TCP_GATE = 'backend_tcp_idle_gate.py'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Dataclass based patch result resolves its defining module here.
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


H = load_module(SUPPORT / 'base_helpers.py', 'cn_upload20m_release_helpers')
H.ROOT = ROOT
GuardError, require, digest, canonical = H.GuardError, H.require, H.digest, H.canonical
read_json, write_json, run, inspect, environment = H.read_json, H.write_json, H.run, H.inspect, H.environment


def atomic_write_json(path, value):
    data = json.dumps(value, indent=2).encode() + b'\n'
    temporary = path.with_name('.' + path.name + '.' + str(os.getpid()) + '.' + str(time.time_ns()) + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


write_json = H.write_json = atomic_write_json


def save(name, value):
    write_json(ROOT / name, value)


def emit(**value):
    print(json.dumps(value, separators=(',', ':')), flush=True)


def expected_overrides():
    return {service: {key: MODEL for key in keys} for service, keys in MODEL_KEYS.items()}


def expected_environment(before, service, kind):
    value = dict(environment(before))
    if kind == 'new':
        value.update(expected_overrides().get(service, {}))
    return value


def expected_render(before, service, image, kind):
    expected = deepcopy(before)
    expected['services'][service]['image'] = image
    if kind == 'new' and service in MODEL_KEYS:
        expected['services'][service].setdefault('environment', {}).update(expected_overrides()[service])
    return expected


def check_plan():
    plan = read_json(ROOT / 'input.json')
    required = {'releaseId', 'baselines', 'modelOverrides', 'nginxBeforeSha256', 'nginxAfterSha256', 'nginxCandidate', 'openapiBefore', 'supportFiles'}
    require(required <= set(plan) <= required | {'nonTargets'}, 'input_fields_changed')
    require(plan['releaseId'] == RELEASE and plan['modelOverrides'] == expected_overrides(), 'model_scope_changed')
    require(set(plan['baselines']) == set(BASES), 'component_scope_changed')
    for service, (container_id, image) in BASES.items():
        item = plan['baselines'][service]
        require(item['id'] == container_id and item['image'] == image and isinstance(item['inventory'], dict) and item['inventory'], 'baseline_scope_changed')
        if service in MODEL_KEYS:
            require(bool(re.fullmatch('[0-9a-f]{64}', item['settingsSha256'])), 'settings_baseline_missing')
    require(plan['nginxCandidate'] == 'nginx/default.conf', 'nginx_payload_path_changed')
    for key in ('nginxBeforeSha256', 'nginxAfterSha256'):
        require(bool(re.fullmatch('[0-9a-f]{64}', plan[key])), 'nginx_hash_invalid')
    require(digest((ROOT / plan['nginxCandidate']).read_bytes()) == plan['nginxAfterSha256'], 'nginx_payload_drift')
    prefix = 'release_support/cn_upload20m_model1017_20261021/'
    support = {Path(__file__).name, 'patch_cn_upload_proxy_20m.py', prefix + 'base_helpers.py', *(prefix + path for path in (*GATES, TCP_GATE))}
    require(set(plan['supportFiles']) == support, 'release_support_scope_changed')
    for relative, checksum in plan['supportFiles'].items():
        path = ROOT / relative
        require(not path.is_symlink() and path.is_file() and digest(path.read_bytes()) == checksum, 'release_support_drift')
    return plan


def inventory(service, *, image=None):
    if service == 'web':
        args = ['sh', '-c', 'cd /usr/share/nginx/html && find . -type f -exec sha256sum {} +']
        command = ['docker', 'run', '--rm', '--read-only', '--network', 'none', '--entrypoint', 'sh', image, '-c', args[-1]] if image else ['docker', 'exec', 'compose-web-1', *args]
        result = {}
        for line in run(command).stdout.decode().splitlines():
            checksum, path = line.split(None, 1)
            require(re.fullmatch('[0-9a-f]{64}', checksum) and path.startswith('./'), 'public_inventory_invalid')
            result[path[2:]] = checksum
        return result
    code = "from pathlib import Path;import hashlib,json;r=Path('/app');files=[p for f in ('apps/backend/app','ai/prompts','apps/backend/migrations') for p in (r/f).rglob('*')]+[r/'apps/backend/pyproject.toml'];print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='.desktop-release-manifest.lock'}))"
    command = ['docker', 'run', '--rm', '--read-only', '--network', 'none', '--entrypoint', 'python', image, '-B', '-c', code] if image else ['docker', 'exec', 'compose-' + service + '-1', 'python', '-B', '-c', code]
    return json.loads(run(command).stdout)


def settings(service):
    code = "from app.core.config import Settings;import json;s=Settings(_env_file=None);assert s.product_edition=='cn' and s.environment=='production';print(json.dumps(s.model_dump(mode='json'),sort_keys=True,separators=(',',':')))"
    return json.loads(run(['docker', 'exec', '-w', '/app/apps/backend', 'compose-' + service + '-1', 'python', '-B', '-c', code]).stdout)


def nginx_inputs(*, image=None):
    code = "for root in /etc/nginx /docker-entrypoint.sh /docker-entrypoint.d; do if [ -e \"$root\" ]; then find \"$root\" -type f -exec sha256sum {} +; find \"$root\" -type l -exec sh -c 'for item do printf \"LINK|%s|%s\\n\" \"$item\" \"$(readlink \"$item\")\"; done' sh {} +; fi; done"
    command = ['docker', 'run', '--rm', '--read-only', '--network', 'none', '--entrypoint', 'sh', image, '-c', code] if image else ['docker', 'exec', 'compose-web-1', 'sh', '-c', code]
    result = {}
    for line in run(command).stdout.decode().splitlines():
        if line.startswith('LINK|'):
            _, path, destination = line.split('|')
            value = 'link:' + destination
        else:
            checksum, path = line.split(None, 1)
            require(bool(re.fullmatch('[0-9a-f]{64}', checksum)), 'nginx_input_inventory_invalid')
            value = 'sha256:' + checksum
        require(path.startswith(('/etc/nginx/', '/docker-entrypoint.d/')) or path == '/docker-entrypoint.sh', 'nginx_input_inventory_outside_scope')
        require(path not in result, 'nginx_input_inventory_duplicate')
        result[path] = value
    require('/etc/nginx/nginx.conf' in result and '/etc/nginx/conf.d/default.conf' in result, 'nginx_input_inventory_incomplete')
    return result


def settings_sha(value):
    # Matches the existing model probe's ensure_ascii=False canonical encoding.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def schema():
    code = "from urllib.request import urlopen;import json;print(json.dumps(json.load(urlopen('http://127.0.0.1:8000/openapi.json',timeout=10)),sort_keys=True,separators=(',',':')))"
    return json.loads(run(['docker', 'exec', 'compose-backend-1', 'python', '-B', '-c', code]).stdout)


def check_schema(actual, expected):
    paths = actual['paths']
    required_paths = expected['paths']
    require((paths == required_paths if isinstance(required_paths, dict) else sorted(paths) == sorted(required_paths)), 'existing_api_paths_changed')
    require(digest(canonical(actual)) == expected['schemaSha256'], 'complete_api_schema_changed')


def network_configuration(container):
    return {name: {key: value.get(key) for key in ('IPAMConfig', 'Links', 'DriverOpts', 'GwPriority')} | {
        'Aliases': sorted(alias for alias in value.get('Aliases') or [] if alias not in (container['Id'], container['Id'][:12]))}
        for name, value in container['NetworkSettings']['Networks'].items()}


def ownership_signature(container):
    """Immutable ownership/configuration; excludes process/endpoint lifecycle."""
    return {'id': container['Id'], 'image': container['Image'],
        'configSha256': digest(canonical(container['Config'])),
        'hostConfigSha256': digest(canonical(container['HostConfig'])),
        'mountsSha256': digest(canonical(H.canonical_mounts(container['Mounts']))),
        'networkConfigurationSha256': digest(canonical(network_configuration(container)))}


def assert_context_owner(current, target, kind):
    labels = current['Config']['Labels']
    require(current['Image'] == target[kind + 'Image'] and
        labels.get('com.docker.compose.project') == 'compose' and
        labels.get('com.docker.compose.service') == target['service'] and
        labels.get('com.docker.compose.project.config_files') == ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']]) and
        labels.get('com.docker.compose.project.environment_file') == ','.join(target['frozenEnvFiles']) and
        labels.get('com.docker.compose.project.working_dir') == target['composeDirectory'], 'release_container_context_owner_changed')


def record_created_owner(target, kind, previous_id, current, progress):
    """Journal our newly created container before validating its behavior.

    A bad environment or health result must remain recoverable. Complete frozen
    Compose ownership and expected image prove creation; invariant checks then
    decide acceptance. This does not authorize replacing an unrelated container.
    """
    require(current['Id'] != previous_id, 'new_container_creation_not_proven')
    assert_context_owner(current, target, kind)
    progress[target['service']] = {'id': current['Id'], 'image': current['Image'], 'kind': kind,
        'signature': H.container_signature(current), 'ownershipSignature': ownership_signature(current),
        'recordedState': {key: current['State'].get(key) for key in ('Running', 'StartedAt', 'Pid', 'Status')},
        'recordedRestartCount': current['RestartCount']}
    save('progress.json', progress)


def recovery_process_proof(current, entry):
    require(entry['kind'] == 'new' and ownership_signature(current) == entry['ownershipSignature'], 'recovery_static_owner_changed')
    if not current['State']['Running']:
        require(H.stopped_process(current), 'stopped_process_proof_unavailable')
        after = inspect(current['Id'])
        require(H.stopped_process(after) and H.container_signature(current) == H.container_signature(after)
            and ownership_signature(after) == entry['ownershipSignature'], 'stopped_process_proof_unavailable')
        save('last-recovery-process-proof.json', {'method': 'stoppedProcessProof', 'observations': 2, 'sameOwnedCandidate': True})
        return
    require(type(current['RestartCount']) is int and current['RestartCount'] > entry['recordedRestartCount'], 'unexpected_running_process_change')
    identity = H.running_process_identity(current)
    after = inspect(current['Id'])
    require(H.running_process_identity(after) == identity and H.container_signature(current) == H.container_signature(after)
        and ownership_signature(after) == entry['ownershipSignature'], 'restarted_process_proof_unavailable')
    save('last-recovery-process-proof.json', {'method': 'stableRestartedOwnedCandidate', 'observations': 2, 'sameOwnedCandidate': True})


def targets_owned(manifest, progress, *, recovery=False):
    for service, target in manifest['targets'].items():
        current = inspect(target['container'])
        entry = progress.get(service)
        if entry:
            require(current['Id'] == entry['id'] and current['Image'] == entry['image'], 'release_container_owner_changed')
            assert_context_owner(current, target, entry['kind'])
            same = {k: v for k, v in H.container_signature(current).items() if k != 'health'} == {k: v for k, v in entry['signature'].items() if k != 'health'}
            if not same and recovery:
                recovery_process_proof(current, entry)
            else:
                require(same, 'released_container_signature_changed')
        else:
            require((current['Id'], current['Image']) == BASES[service], 'baseline_container_owner_changed')
            before = read_json(ROOT / service / 'container-before.json')
            require({k: v for k, v in H.container_signature(current).items() if k != 'health'} == {k: v for k, v in H.container_signature(before).items() if k != 'health'}, 'baseline_signature_changed')


def check_non_targets(manifest):
    actual_names = set(run(['docker', 'ps', '--format', '{{.Names}}']).stdout.decode().splitlines()) - {target['container'] for target in manifest['targets'].values()}
    require(actual_names == set(manifest['nonTargets']), 'non_target_container_set_changed')
    for name, signature in manifest['nonTargets'].items():
        current = H.container_signature(inspect(name))
        require({k: v for k, v in current.items() if k != 'health'} == {k: v for k, v in signature.items() if k != 'health'}, 'non_target_container_changed')


def check_files(manifest, plan):
    require(digest((ROOT / 'input.json').read_bytes()) == manifest['inputSha256'], 'input_manifest_drift')
    for relative, checksum in manifest['privateFiles'].items():
        require(digest((ROOT / relative).read_bytes()) == checksum, 'private_snapshot_drift')
    for target in manifest['targets'].values():
        before = read_json(ROOT / target['service'] / 'container-before.json')
        H.verify_frozen_files(target, before)
        for source, checksum in target['sourceHashes'].items():
            require(digest(Path(source).read_bytes()) == checksum, 'production_compose_or_env_drift')
        require(digest(H.canonical(H.rendered(target))) == target['sourceRenderedSha'], 'production_render_drift')
        for kind in ('new', 'rollback'):
            overlay = ROOT / target['service'] / (kind + '.compose.json')
            require(digest(overlay.read_bytes()) == target[kind + 'OverlaySha256'], 'release_overlay_drift')
            expected = expected_render(read_json(ROOT / target['service'] / 'rendered-before.json'), target['service'], target[kind + 'Image'], kind)
            require(H.rendered(target, frozen=True, overlay=overlay) == expected, 'unrelated_rendered_configuration_change')
    check_non_targets(manifest)


def runtime_invariant(before, after, target, kind):
    service = target['service']
    require(after['Image'] == target[kind + 'Image'], 'runtime_image_changed')
    require(environment(after) == expected_environment(before, service, kind), 'runtime_environment_changed')
    for key in set(before['Config']) | set(after['Config']):
        if key not in ('Image', 'Hostname', 'Labels', 'Env'):
            require(before['Config'].get(key) == after['Config'].get(key), 'application_configuration_changed')
    hostname = after['Id'][:12] if before['Config']['Hostname'] == before['Id'][:12] else before['Config']['Hostname']
    require(after['Config']['Hostname'] == hostname, 'container_hostname_changed')
    labels = lambda value: {k: v for k, v in value['Config'].get('Labels', {}).items() if not k.startswith('com.docker.compose.')}
    require(labels(before) == labels(after) and before['HostConfig'] == after['HostConfig'] and H.canonical_mounts(before['Mounts']) == H.canonical_mounts(after['Mounts']), 'host_mount_or_label_changed')
    old_networks, new_networks = before['NetworkSettings']['Networks'], after['NetworkSettings']['Networks']
    require(set(old_networks) == set(new_networks), 'target_network_set_changed')
    for name, old in old_networks.items():
        new = new_networks[name]
        for key in ('IPAMConfig', 'Links', 'DriverOpts', 'GwPriority'):
            require(old.get(key) == new.get(key), 'target_network_configuration_changed')
        aliases = lambda c, n: sorted(a for a in n.get('Aliases') or [] if a not in (c['Id'], c['Id'][:12]))
        require(aliases(before, old) == aliases(after, new), 'target_network_aliases_changed')
    labels = after['Config']['Labels']
    require(labels.get('com.docker.compose.project') == 'compose' and labels.get('com.docker.compose.service') == service and labels.get('com.docker.compose.project.config_files') == ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']]) and labels.get('com.docker.compose.project.environment_file') == ','.join(target['frozenEnvFiles']) and labels.get('com.docker.compose.project.working_dir') == target['composeDirectory'], 'released_compose_owner_changed')


def verify_runtime(manifest, plan, progress, *, final=False):
    targets_owned(manifest, progress)
    check_files(manifest, plan)
    for service, target in manifest['targets'].items():
        kind = progress.get(service, {}).get('kind', 'rollback')
        current = inspect(target['container'])
        require(current['State']['Running'] and current['RestartCount'] == 0, 'target_not_running')
        if service == 'backend':
            require(current['State'].get('Health', {}).get('Status') == 'healthy', 'backend_unhealthy')
        if service in progress:
            runtime_invariant(read_json(ROOT / service / 'container-before.json'), current, target, kind)
        require(inventory(service) == plan['baselines'][service]['inventory'], 'runtime_source_or_static_drift')
        if service in MODEL_KEYS:
            baseline = read_json(ROOT / service / 'settings-before.private.json')
            if kind == 'new':
                baseline.update({SETTINGS_KEYS[key]: value for key, value in expected_overrides()[service].items()})
            require(settings(service) == baseline, 'effective_settings_drift')
        if final:
            require(kind == 'new', 'partial_release_not_complete')
    nginx = H.read_container('compose-web-1', '/etc/nginx/conf.d/default.conf')
    expected = plan['nginxAfterSha256'] if progress.get('web', {}).get('kind') == 'new' else plan['nginxBeforeSha256']
    require(digest(nginx) == expected, 'runtime_nginx_drift')
    expected_inputs = dict(manifest['nginxInputsBefore'])
    expected_inputs['/etc/nginx/conf.d/default.conf'] = 'sha256:' + expected
    require(nginx_inputs() == expected_inputs, 'runtime_nginx_input_tree_changed')
    check_schema(schema(), plan['openapiBefore'])


def prepare():
    plan = check_plan()
    require(not (ROOT / 'prepared.json').exists(), 'already_prepared')
    patch = load_module(Path(__file__).parent / 'patch_cn_upload_proxy_20m.py', 'cn_upload20m_precise_patch')
    original = H.read_container('compose-web-1', '/etc/nginx/conf.d/default.conf')
    result = patch.patch_config(original, expected_sha256=plan['nginxBeforeSha256'])
    require(result.content == (ROOT / plan['nginxCandidate']).read_bytes(), 'nginx_candidate_not_precise_patch')
    check_schema(schema(), plan['openapiBefore'])
    manifest = {'inputSha256': digest((ROOT / 'input.json').read_bytes()), 'targets': {}, 'nonTargets': {}, 'privateFiles': {}}
    actual_inputs = nginx_inputs()
    base_inputs = nginx_inputs(image=BASES['web'][1])
    require(actual_inputs == base_inputs, 'nginx_writable_input_tree_differs_from_image')
    manifest['nginxInputsBefore'] = actual_inputs
    names = set(run(['docker', 'ps', '--format', '{{.Names}}']).stdout.decode().splitlines())
    for service, (container_id, image) in BASES.items():
        current = inspect('compose-' + service + '-1')
        require((current['Id'], current['Image']) == (container_id, image), 'fresh_runtime_baseline_changed')
        signature = H.container_signature(current)
        require(all(plan['baselines'][service].get(key) == value for key, value in signature.items()), 'fresh_runtime_signature_changed')
        require(current['State']['Running'] and current['RestartCount'] == 0, 'baseline_unhealthy')
        require(inventory(service) == plan['baselines'][service]['inventory'] == inventory(service, image=image), 'writable_layer_or_source_baseline_drift')
        if service == 'backend':
            require(current['State'].get('Health', {}).get('Status') == 'healthy', 'baseline_unhealthy')
        target = H.freeze(current, service)
        target.update(newImage=image, rollbackImage=image)
        if service in MODEL_KEYS:
            require(all(key in environment(current) for key in MODEL_KEYS[service]), 'model_environment_key_missing')
            value = settings(service)
            require(settings_sha(value) == plan['baselines'][service]['settingsSha256'], 'settings_baseline_drift')
            save(service + '/settings-before.private.json', value)
        if service == 'web':
            save('web/nginx-before-sha.json', {'sha256': digest(original)})
            (ROOT / 'web/nginx-before.conf').write_bytes(original)
            (ROOT / 'web/nginx-before.conf').chmod(0o600)
            build = ROOT / 'web/build'
            build.mkdir(mode=0o700)
            tag = 'offersteady-cn-web-baseline:upload20m-model1017-20261021'
            run(['docker', 'tag', image, tag])
            (build / 'default.conf').write_bytes(result.content)
            (build / 'default.conf').chmod(0o644)
            (build / 'Dockerfile').write_text('FROM ' + tag + '\nCOPY default.conf /etc/nginx/conf.d/default.conf\n')
            tag = 'offersteady-cn-web:upload20m-model1017-20261021-1'
            run(['docker', 'build', '--network=none', '--pull=false', '-t', tag, str(build)], timeout=90)
            candidate = inspect(tag)
            H.verify_image_base(candidate, inspect(image))
            target['newImage'] = candidate['Id']
            require(inventory('web', image=target['newImage']) == plan['baselines']['web']['inventory'], 'candidate_public_static_changed')
            require(digest(run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--entrypoint', 'cat', target['newImage'], '/etc/nginx/conf.d/default.conf']).stdout) == plan['nginxAfterSha256'], 'candidate_nginx_mismatch')
            expected_inputs = dict(actual_inputs)
            expected_inputs['/etc/nginx/conf.d/default.conf'] = 'sha256:' + plan['nginxAfterSha256']
            require(nginx_inputs(image=target['newImage']) == expected_inputs, 'candidate_nginx_input_tree_changed')
            # Resolve configured static upstream names to a loopback QA sink;
            # nginx -t does no request forwarding and has no network access.
            text = result.content.decode('utf-8')
            hosts = set(re.findall(r'proxy_pass\s+https?://([A-Za-z0-9_.-]+)', text))
            hosts.update(re.findall(r'^\s*server\s+([A-Za-z0-9_.-]+):[0-9]+', text, re.M))
            qa = ['docker', 'run', '--rm', '--network', 'none', '--read-only', '--tmpfs', '/var/cache/nginx', '--tmpfs', '/var/run']
            for host in sorted(hosts):
                require(bool(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', host)), 'nginx_check_host_invalid')
                qa.extend(['--add-host', host + ':127.0.0.1'])
            run([*qa, '--entrypoint', 'nginx', target['newImage'], '-t'])
        for kind in ('new', 'rollback'):
            overlay = ROOT / service / (kind + '.compose.json')
            value = {'services': {service: {'image': target[kind + 'Image']}}}
            if kind == 'new' and service in MODEL_KEYS:
                value['services'][service]['environment'] = expected_overrides()[service]
            write_json(overlay, value)
            target[kind + 'Overlay'] = str(overlay)
            target[kind + 'OverlaySha256'] = digest(overlay.read_bytes())
            require(H.rendered(target, frozen=True, overlay=overlay) == expected_render(read_json(ROOT / service / 'rendered-before.json'), service, target[kind + 'Image'], kind), 'unrelated_rendered_configuration_change')
        manifest['targets'][service] = target
    for name in names - {target['container'] for target in manifest['targets'].values()}:
        manifest['nonTargets'][name] = H.container_signature(inspect(name))
    if 'nonTargets' in plan:
        require(manifest['nonTargets'] == plan['nonTargets'], 'fresh_non_target_signature_changed')
    before = read_json(ROOT / 'backend/container-before.json')
    env = environment(before)
    require(all('\n' not in key + value and '\r' not in key + value for key, value in env.items()), 'runtime_env_file_unsafe')
    (ROOT / 'runtime.env.private').write_text(''.join(key + '=' + value + '\n' for key, value in sorted(env.items())))
    (ROOT / 'runtime.env.private').chmod(0o600)
    for service in BASES:
        for path in (ROOT / service).iterdir():
            if path.is_file() and path.name not in {'new.compose.json', 'rollback.compose.json'}:
                manifest['privateFiles'][str(path.relative_to(ROOT))] = digest(path.read_bytes())
    manifest['privateFiles']['runtime.env.private'] = digest((ROOT / 'runtime.env.private').read_bytes())
    save('prepared.json', manifest)
    verify_runtime(manifest, plan, {})
    emit(prepared=True, productionChanged=False, components=3, modelEnvironmentKeys=7, webStaticFiles=len(plan['baselines']['web']['inventory']))


def gate_command(manifest):
    before = read_json(ROOT / 'backend/container-before.json')
    network = before['HostConfig']['NetworkMode']
    require(isinstance(network, str) and re.fullmatch('[A-Za-z0-9_.-]+', network) and network not in {'host', 'none'}, 'gate_network_invalid')
    return ['docker', 'run', '--rm', '-i', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '64', '--memory', '512m', '--network', network, '--env-file', str(ROOT / 'runtime.env.private'), '--workdir', '/app/apps/backend', '--entrypoint', 'python', BASES['backend'][1], '-B', '-']


def idle_gates(manifest):
    records = []
    for path in GATES:
        try:
            response = subprocess.run(gate_command(manifest), input=(SUPPORT / path).read_bytes(), capture_output=True, timeout=25)
            H.ROOT = SUPPORT
            counts = H.normalize_gate(path, json.loads(response.stdout))
            unknown = H.gate_has_read_or_unknown_failure(path, counts)
            idle = H.gate_is_idle(path, counts)
        except Exception:
            raise GuardError('protected_work_gate_unavailable') from None
        finally:
            H.ROOT = ROOT
        records.append({'gate': path, 'exitCode': response.returncode, 'counts': counts})
        save('last-idle-gates.json', records)
        require(not unknown and (response.returncode == 0 or not idle), 'protected_work_gate_unavailable')
        require(response.returncode == 0 and idle, 'protected_user_work_cutover_deferred')
    return records


def tcp_gate(manifest, progress, *, recovery=False):
    current = inspect('compose-backend-1')
    before = read_json(ROOT / 'backend/container-before.json')
    expected = progress.get('backend', {}).get('id', before['Id'])
    require(current['Id'] == expected and current['Image'] == BASES['backend'][1], 'tcp_container_owner_changed')
    if not current['State']['Running']:
        require(recovery and 'backend' in progress and H.stopped_process(current), 'stopped_process_proof_unavailable')
        after = inspect(current['Id'])
        require(H.stopped_process(after) and H.container_signature(current) == H.container_signature(after), 'stopped_process_proof_unavailable')
        save('last-tcp-idle-gate.json', {'passed': True, 'method': 'stoppedProcessProof'})
        return
    identity = H.running_process_identity(current)
    namespace = H.host_network_namespace(current)
    try:
        response = subprocess.run(['docker', 'exec', '-i', current['Id'], 'python', '-B', '-'], input=(SUPPORT / TCP_GATE).read_bytes(), capture_output=True, timeout=10)
        value = json.loads(response.stdout)
    except Exception:
        raise GuardError('protected_tcp_gate_unavailable') from None
    require(response.returncode == 0 and isinstance(value, dict) and set(value) == {'passed', 'atMs', 'establishedPort8000', 'tablesRead', 'scannedRows', 'scope', 'networkNamespaceSha256'} and value['passed'] is True and value['scope'] == 'container_tcp8000_established_only', 'protected_tcp_gate_unavailable')
    require(all(type(value[k]) is int and value[k] >= 0 for k in ('atMs', 'establishedPort8000', 'tablesRead', 'scannedRows')) and value['tablesRead'] == 2 and value['establishedPort8000'] <= value['scannedRows'] <= 200000 and 0 <= int(time.time() * 1000) - value['atMs'] <= 10000 and value['networkNamespaceSha256'] == namespace, 'protected_tcp_gate_unavailable')
    after = inspect(current['Id'])
    require(H.running_process_identity(after) == identity and H.container_signature(current) == H.container_signature(after) and H.host_network_namespace(after) == namespace, 'tcp_container_owner_changed')
    save('last-tcp-idle-gate.json', value)
    require(value['establishedPort8000'] == 0, 'protected_user_work_cutover_deferred')


def reconcile_intent(manifest, progress):
    path = ROOT / 'switch-intent.json'
    if not path.exists():
        return
    intent = read_json(path)
    if progress != intent['previousProgress']:
        return
    service, kind = intent['service'], intent['kind']
    require(service in BASES and kind in {'new', 'rollback'}, 'switch_intent_invalid')
    target = manifest['targets'][service]
    current = inspect(target['container'])
    if current['Image'] == target[kind + 'Image'] and current['Config']['Labels'].get('com.docker.compose.project.config_files') == ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']]):
        record_created_owner(target, kind, intent['beforeId'], current, progress)


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
            record_created_owner(target, kind, before['Id'], current, progress)
            runtime_invariant(read_json(ROOT / service / 'container-before.json'), current, target, kind)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        current = inspect(target['container'])
        if current['State']['Running'] and current['RestartCount'] == 0 and (service != 'backend' or current['State'].get('Health', {}).get('Status') == 'healthy'):
            break
        time.sleep(1)
    else:
        raise GuardError('target_health_failed')
    runtime_invariant(read_json(ROOT / service / 'container-before.json'), current, target, kind)
    require(inventory(service) == plan['baselines'][service]['inventory'], 'released_source_or_static_drift')
    if service == 'backend':
        ips = lambda item: {key: value.get('IPAddress') for key, value in item['NetworkSettings']['Networks'].items()}
        if ips(before) != ips(current):
            for name in ('compose-web-1', 'compose-admin-1'):
                run(['docker', 'exec', name, 'nginx', '-t'])
                run(['docker', 'exec', name, 'nginx', '-s', 'reload'])


def public_checks(plan):
    for path in ('/healthz', '/login', '/app/mock-interviews', '/app/resume-optimizer', '/app/interviews/new', '/app/written-exams'):
        with urlopen(Request('https://mianshiwen.cn' + path, headers={'Cache-Control': 'no-cache'}), timeout=12) as response:
            require(response.status == 200, 'public_route_unavailable')
            data = response.read()
            if path == '/healthz':
                require(json.loads(data)['data']['status'] == 'ok', 'public_health_failed')
            else:
                require(digest(data) == plan['baselines']['web']['inventory']['index.html'], 'public_html_changed')
    return {'passed': True, 'routes': 6}


def verify():
    plan, manifest = check_plan(), read_json(ROOT / 'prepared.json')
    progress = read_json(ROOT / 'progress.json') if (ROOT / 'progress.json').exists() else {}
    reconcile_intent(manifest, progress)
    verify_runtime(manifest, plan, progress, final=True)
    public_checks(plan)
    emit(verified=True, components=3, modelEnvironmentKeys=7, fileLimitMiB=20, nginxProxyLimit='21m', sourcesAndWebStaticUnchanged=True, nonTargetsUnchanged=True)


def rollback():
    plan, manifest = check_plan(), read_json(ROOT / 'prepared.json')
    progress = read_json(ROOT / 'progress.json') if (ROOT / 'progress.json').exists() else {}
    reconcile_intent(manifest, progress)
    for service in ('web', 'material-worker', 'backend'):
        if progress.get(service, {}).get('kind') == 'new':
            switch(manifest, plan, progress, service, 'rollback')
    verify_runtime(manifest, plan, progress)
    require(all(entry['kind'] == 'rollback' for entry in progress.values()), 'rollback_incomplete')
    public_checks(plan)
    save('rollback-result.json', {'restored': True, 'atMs': int(time.time() * 1000)})
    emit(rollbackSucceeded=True)


def deploy(*, preflight=False):
    plan, manifest = check_plan(), read_json(ROOT / 'prepared.json')
    progress = read_json(ROOT / 'progress.json') if (ROOT / 'progress.json').exists() else {}
    reconcile_intent(manifest, progress)
    require(not (ROOT / 'rollback-result.json').exists(), 'release_was_rolled_back')
    if (ROOT / 'deployed.json').exists():
        verify()
        emit(alreadyDeployed=True)
        return
    verify_runtime(manifest, plan, progress)
    idle_gates(manifest)
    tcp_gate(manifest, progress)
    if preflight:
        emit(preflightPassed=True, productionChanged=False)
        return
    # Every component repeats all gates immediately before its sole mutation.
    # Gates reduce the observation window; they are not an admission fence.
    try:
        for service in ('material-worker', 'backend', 'web'):
            if progress.get(service, {}).get('kind') != 'new':
                verify_runtime(manifest, plan, progress)
                switch(manifest, plan, progress, service, 'new')
        verify_runtime(manifest, plan, progress, final=True)
        public_checks(plan)
        save('deployed.json', {'deployed': True, 'atMs': int(time.time() * 1000), 'services': list(BASES), 'models': expected_overrides(), 'webImage': manifest['targets']['web']['newImage']})
        emit(deployed=True, components=3, modelEnvironmentKeys=7, fileLimitMiB=20, nginxProxyLimit='21m', existingSourcesAndStaticUnchanged=True)
    except Exception as exc:
        if isinstance(exc, GuardError) and str(exc) in {'protected_user_work_cutover_deferred', 'protected_work_gate_unavailable', 'protected_tcp_gate_unavailable'}:
            raise
        if isinstance(exc, GuardError) and str(exc) in {
            'runtime_source_or_static_drift', 'released_source_or_static_drift', 'runtime_nginx_input_tree_changed',
            'runtime_nginx_drift', 'input_manifest_drift', 'private_snapshot_drift', 'release_support_drift',
            'production_compose_or_env_drift', 'production_render_drift', 'release_overlay_drift',
            'unrelated_rendered_configuration_change', 'non_target_container_changed', 'non_target_container_set_changed',
            'release_container_owner_changed', 'release_container_context_owner_changed',
            'released_container_signature_changed', 'recovery_static_owner_changed'}:
            # Unrelated drift is not permission to overwrite somebody else's
            # work. Keep known progress and stop for an ownership audit.
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
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'preflight', 'deploy', 'verify', 'rollback'))
    action = parser.parse_args().action
    try:
        require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve() == ROOT, 'private_release_directory_missing')
        with release_lock():
            {'prepare': prepare, 'preflight': lambda: deploy(preflight=True), 'deploy': deploy, 'verify': verify, 'rollback': rollback}[action]()
    except Exception as exc:
        reason = str(exc) if isinstance(exc, GuardError) and re.fullmatch('[a-z0-9_]+', str(exc)) else 'release_operation_failed_private_diagnostics_only'
        emit(ok=False, reason=reason)
        raise SystemExit(75 if reason == 'protected_user_work_cutover_deferred' else 1) from None


if __name__ == '__main__':
    main()
