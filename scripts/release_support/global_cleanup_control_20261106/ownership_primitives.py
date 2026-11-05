"""Exact reviewed Global model1017 helper functions, no deployment entrypoints.

Functions are AST-extracted from the executed 20261022 Global controller.
The new controller supplies ROOT/BASES and reviewed policies explicitly.
"""
from copy import deepcopy
import io,json,os,re,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
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

def write_env(path, values):
    require(all(isinstance(key,str) and isinstance(value,str) and '\n' not in key+value and '\r' not in key+value for key,value in values.items()), 'runtime_env_file_unsafe')
    path.write_text(''.join(key+'='+value+'\n' for key,value in sorted(values.items())))
    path.chmod(0o600)

def stopped_source_inventory(current):
    """Hash only four source scopes without starting or exporting the container."""
    result={}
    for scope in ('apps/backend/app','ai/prompts','apps/backend/migrations','apps/backend/pyproject.toml'):
        response=run(['docker','cp',current['Id']+':/app/'+scope,'-'],timeout=30)
        require(len(response.stdout) <= 100*1024*1024, 'stopped_source_archive_too_large')
        root=PurePosixPath(scope).name
        with tarfile.open(fileobj=io.BytesIO(response.stdout),mode='r:*') as archive:
            for member in archive:
                name=PurePosixPath(member.name)
                require(not name.is_absolute() and '..' not in name.parts
                    and name.parts and name.parts[0] == root, 'stopped_source_archive_scope_changed')
                if '__pycache__' in name.parts or name.suffix == '.pyc' or name.name == '.desktop-release-manifest.lock':
                    continue
                if member.isdir():
                    continue
                require(member.isfile() and 0 <= member.size <= 20*1024*1024, 'stopped_source_archive_entry_invalid')
                relative=str(PurePosixPath(scope).parent/name)
                require(relative not in result, 'stopped_source_archive_duplicate')
                data=archive.extractfile(member).read()
                require(len(data) == member.size, 'stopped_source_archive_truncated')
                result[relative]=digest(data)
    return result

def inventory(service, *, image=None):
    if service == 'web':
        args = ['sh', '-c', 'cd /usr/share/nginx/html && find . -type f -exec sha256sum {} +']
        command = ['docker', 'run', '--rm', '--read-only', '--network', 'none', '--entrypoint', 'sh', image, '-c', args[-1]] if image else ['docker', 'exec', PROJECT + '-web-1', *args]
        result = {}
        for line in run(command).stdout.decode().splitlines():
            checksum, path = line.split(None, 1)
            require(re.fullmatch('[0-9a-f]{64}', checksum) and path.startswith('./'), 'public_inventory_invalid')
            result[path[2:]] = checksum
        return result
    code = "from pathlib import Path;import hashlib,json;r=Path('/app');files=[p for f in ('apps/backend/app','ai/prompts','apps/backend/migrations') for p in (r/f).rglob('*')]+[r/'apps/backend/pyproject.toml'];print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='.desktop-release-manifest.lock'}))"
    command = ['docker', 'run', '--rm', '--read-only', '--network', 'none', '--entrypoint', 'python', image, '-B', '-c', code] if image else ['docker', 'exec', PROJECT + '-' + service + '-1', 'python', '-B', '-c', code]
    return json.loads(run(command).stdout)

def settings(service):
    code = "from app.core.config import Settings;import json;s=Settings(_env_file=None);assert s.product_edition=='global' and s.environment=='production';print(json.dumps(s.model_dump(mode='json'),sort_keys=True,separators=(',',':')))"
    return json.loads(run(['docker', 'exec', '-w', '/app/apps/backend', PROJECT + '-' + service + '-1', 'python', '-B', '-c', code]).stdout)

def nginx_inputs(*, image=None, container=None):
    code = "for root in /etc/nginx /docker-entrypoint.sh /docker-entrypoint.d; do if [ -e \"$root\" ]; then find \"$root\" -type f -exec sha256sum {} +; find \"$root\" -type l -exec sh -c 'for item do printf \"LINK|%s|%s\\n\" \"$item\" \"$(readlink \"$item\")\"; done' sh {} +; fi; done"
    command = ['docker', 'run', '--rm', '--read-only', '--network', 'none', '--entrypoint', 'sh', image, '-c', code] if image else ['docker', 'exec', container or PROJECT + '-web-1', 'sh', '-c', code]
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
    # Same canonical encoding as the fresh Global baseline, including ASCII escapes.
    return digest(canonical(value))

def schema():
    code = "from urllib.request import urlopen;import json;print(json.dumps(json.load(urlopen('http://127.0.0.1:8000/openapi.json',timeout=10)),sort_keys=True,separators=(',',':')))"
    return json.loads(run(['docker', 'exec', PROJECT + '-backend-1', 'python', '-B', '-c', code]).stdout)

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
        labels.get('com.docker.compose.project') == PROJECT and
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

def runtime_invariant(before, after, target, kind):
    service = target['service']
    require(service in BASES, 'runtime_component_outside_scope')
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
    require(labels.get('com.docker.compose.project') == PROJECT and labels.get('com.docker.compose.service') == service and labels.get('com.docker.compose.project.config_files') == ','.join(target['frozenComposeFiles'] + [target[kind + 'Overlay']]) and labels.get('com.docker.compose.project.environment_file') == ','.join(target['frozenEnvFiles']) and labels.get('com.docker.compose.project.working_dir') == target['composeDirectory'], 'released_compose_owner_changed')

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
    targets_owned(manifest,progress,recovery=recovery)
    current = inspect(PROJECT + '-backend-1')
    before = read_json(ROOT / 'backend/container-before.json')
    expected = progress.get('backend', {}).get('id', before['Id'])
    expected_image = progress.get('backend', {}).get('image', BASES['backend'][1])
    require(current['Id'] == expected and current['Image'] == expected_image, 'tcp_container_owner_changed')
    if not current['State']['Running']:
        require(recovery and 'backend' in progress and H.stopped_process(current), 'stopped_process_proof_unavailable')
        after = inspect(current['Id'])
        require(H.stopped_process(after) and H.container_signature(current) == H.container_signature(after), 'stopped_process_proof_unavailable')
        targets_owned(manifest,progress,recovery=recovery)
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
    targets_owned(manifest,progress,recovery=recovery)
    save('last-tcp-idle-gate.json', value)
    require(value['establishedPort8000'] == 0, 'protected_user_work_cutover_deferred')
