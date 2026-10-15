"""Offline release guards; no Docker, SSH, provider, production DB or publication."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[3]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load_script('release_global_mock_companion')
gate = load_script('global_mock_companion_idle_gate')


def manifest_and_proof():
    entries = []
    for platform, architecture in [('windows', 'x64'), ('macos', 'arm64'), ('macos', 'x64')]:
        file_name = release.INSTALLER_NAMES[(platform, architecture)]
        entries.append(dict(platform=platform, architecture=architecture, version='1.3.5', protocolVersion='2.0',
            distributionStatus='published', developmentOnly=False, fileName=file_name,
            objectKey=f'global-desktop-releases/{platform}/{architecture}/1.3.5/{file_name}',
            fileSizeBytes=100_000_000, sha256='a'*64, signingStatus='verified' if platform == 'macos' else 'unsigned',
            notarized=platform == 'macos'))
    proof = [dict(entry, localVerified=True, objectReadbackVerified=True, contentType=release.INSTALLER_MIME[entry['platform']]) for entry in entries]
    return {'version': 1, 'entries': entries}, {'entries': proof}


def test_release_requires_complete_direct_object_proof_but_not_unadvertised_public_api():
    manifest, proof = manifest_and_proof()
    release.validate_manifest(manifest, proof)
    assert not any('publicReadbackVerified' in row for row in proof['entries'])


@pytest.mark.parametrize('field,value', [
    ('localVerified', False), ('objectReadbackVerified', False), ('sha256', 'b'*64),
    ('fileSizeBytes', 100_000_001), ('objectKey', 'domestic/other'), ('version', '1.3.2'),
    ('contentType', 'text/html'), ('signingStatus', 'verified'), ('notarized', True),
])
def test_incomplete_or_mismatched_windows_proof_rejected(field, value):
    manifest, proof = manifest_and_proof()
    proof['entries'][0][field] = value
    with pytest.raises(release.GuardError):
        release.validate_manifest(manifest, proof)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'domestic_name', 'domestic_object', 'old_version', 'development', 'unsigned_mac', 'unnotarized_mac'])
def test_manifest_scope_and_real_platform_verification_required(change):
    manifest, proof = manifest_and_proof()
    entries = manifest['entries']
    if change == 'missing': entries.pop()
    elif change == 'duplicate': entries[2] = deepcopy(entries[1])
    elif change == 'domestic_name': entries[0]['fileName'] = 'Mianshiwen.exe'
    elif change == 'domestic_object': entries[0]['objectKey'] = 'desktop-releases/windows/x64/1.3.5/other.exe'
    elif change == 'old_version': entries[0]['version'] = '1.3.2'
    elif change == 'development': entries[0]['developmentOnly'] = True
    elif change == 'unsigned_mac': entries[1]['signingStatus'] = 'unsigned'
    elif change == 'unnotarized_mac': entries[1]['notarized'] = False
    with pytest.raises(release.GuardError):
        release.validate_manifest(manifest, proof)


def test_cn_billing_or_deadline_delta_rejected_before_any_read_or_build():
    plan = {'backend': release.BACKEND | {'services/mock_interview_repository.py': '0'*64}}
    with pytest.raises(release.GuardError, match='unexpected'):
        release.check_inputs(plan)


def container():
    return {'Image': 'sha256:old', 'Config': {'Env': ['EDITION=global', 'PRIVATE=synthetic-marker'],
        'Cmd': ['python', 'server'], 'Entrypoint': None, 'WorkingDir': '/app', 'User': '',
        'Labels': {'application-policy': 'preserved', 'com.docker.compose.config-hash': 'old'}},
        'HostConfig': {'PortBindings': {'8000/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '18000'}]},
            'NetworkMode': 'global', 'Binds': [], 'RestartPolicy': {'Name': 'unless-stopped'}, 'Privileged': False},
        'Mounts': []}


def test_container_image_only_cutover_keeps_env_and_full_configuration():
    before, after = container(), container()
    after['Image'] = 'sha256:new'
    after['Config']['Labels']['com.docker.compose.config-hash'] = 'new'
    release.invariant(before, after, 'sha256:new')


@pytest.mark.parametrize('kind', ['env', 'command', 'ports', 'network', 'volume', 'label', 'privileged', 'image'])
def test_configuration_or_domestic_routing_drift_rejected(kind):
    before, after = container(), container()
    after['Image'] = 'sha256:new'
    if kind == 'env': after['Config']['Env'] = ['EDITION=cn']
    elif kind == 'command': after['Config']['Cmd'] = ['different']
    elif kind == 'ports': after['HostConfig']['PortBindings']['8000/tcp'][0]['HostIp'] = '0.0.0.0'
    elif kind == 'network': after['HostConfig']['NetworkMode'] = 'cn'
    elif kind == 'volume': after['Mounts'] = [{'Type': 'volume', 'Source': 'cn-data', 'Destination': '/data'}]
    elif kind == 'label': after['Config']['Labels']['application-policy'] = 'changed'
    elif kind == 'privileged': after['HostConfig']['Privileged'] = True
    elif kind == 'image': after['Image'] = 'sha256:other'
    with pytest.raises(release.GuardError):
        release.invariant(before, after, 'sha256:new')


def test_multiple_compose_and_env_files_keep_order_and_global_project():
    target = dict(composeDirectory='/opt/offersteady-global/releases/old/infra/compose',
        composeFiles=['/old/base.yml', '/old/performance.yml'], envFiles=['/old/private.env'],
        frozenComposeFiles=['/new/compose0', '/new/compose1'], frozenEnvFiles=['/new/env0'])
    args = release.compose_args(target, frozen=True, overlay='/new/image-only.json')
    assert args == ['docker', 'compose', '-p', 'offersteady-global', '--project-directory', target['composeDirectory'],
        '--env-file', '/new/env0', '-f', '/new/compose0', '-f', '/new/compose1', '-f', '/new/image-only.json']
    before = {'services': {'backend': {'image': 'old', 'environment': {'EDITION': 'global'}}, 'admin': {'image': 'stable'}}}
    expected = release.expected_overlay(before, 'backend', 'new')
    assert before['services']['backend']['image'] == 'old'
    assert expected['services']['admin'] == before['services']['admin']
    assert expected['services']['backend'] == {'image': 'new', 'environment': {'EDITION': 'global'}}


def test_wrong_compose_project_rejected():
    with pytest.raises(release.GuardError):
        release.context({'Config': {'Labels': {'com.docker.compose.project': 'compose', 'com.docker.compose.service': 'backend'}}}, 'backend')


def test_idle_failure_never_prints_process_output_or_private_markers(monkeypatch, tmp_path, capsys):
    script = tmp_path / 'synthetic_gate.py'
    script.write_text('print("synthetic-private-marker")')
    monkeypatch.setattr(release.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=75,
        stdout=b'synthetic-private-marker', stderr=b'synthetic-private-marker'))
    with pytest.raises(release.GuardError):
        release.idle_gate({'gateHashes': {str(script): release.digest(script.read_bytes())}})
    assert 'synthetic-private-marker' not in capsys.readouterr().out


def test_changed_gate_rejected_before_any_docker_execution(monkeypatch, tmp_path):
    script = tmp_path / 'gate.py'
    script.write_text('new bytes')
    monkeypatch.setattr(release.subprocess, 'run', Mock(side_effect=AssertionError('must not execute')))
    with pytest.raises(release.GuardError):
        release.idle_gate({'gateHashes': {str(script): release.digest(b'old bytes')}})
    release.subprocess.run.assert_not_called()


@pytest.mark.parametrize('protected', [False, True])
def test_extra_global_gate_is_read_only_and_only_emits_counts(monkeypatch, capsys, protected):
    settings = SimpleNamespace(product_edition='global', database_url='synthetic-only', redis_url='synthetic-only')
    monkeypatch.setattr(gate, 'Settings', lambda: settings)
    executed, connects = [], []
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, query, params=None): executed.append((query, params))
        def fetchone(self): return (0,)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def cursor(self): return Cursor()
    def connect(*args, **kwargs):
        connects.append(kwargs)
        return Connection()
    monkeypatch.setattr(gate.psycopg, 'connect', connect)
    now = 1_800_000_000_000
    monkeypatch.setattr(gate.time, 'time', lambda: now/1000)
    class Redis:
        @staticmethod
        def from_url(*args, **kwargs): return Redis()
        def get(self, key): return '{}'
        def hvals(self, key):
            return [json.dumps({'owner_user_id': 'synthetic-private-marker', 'session_id': 'synthetic-private-marker',
                'lease_expires_at_ms': now+1 if protected else now-1})]
    monkeypatch.setattr(gate, 'Redis', Redis)
    with pytest.raises(SystemExit) as ended:
        gate.main()
    assert ended.value.code == (75 if protected else 0)
    text = capsys.readouterr().out
    assert 'synthetic-private-marker' not in text
    assert json.loads(text)['activeEntityOrLegacyPageLeases'] == int(protected)
    assert 'default_transaction_read_only=on' in connects[0]['options']
    assert all(query.lstrip().startswith('SELECT count(*)') for query, _ in executed)


def test_failure_rollback_rechecks_complete_configuration_and_marks_public_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    release.write_json(tmp_path / 'deployed.json', {'deployed': True})
    targets = [{'service': 'backend'}, {'service': 'web'}]
    events = []
    monkeypatch.setattr(release, 'switch', lambda target, kind: events.append((target['service'], kind)))
    monkeypatch.setattr(release, 'verify_live', lambda *args, **kwargs: events.append(('verification', kwargs['rolled_back'])))
    assert release.rollback({}, {}, targets)
    assert events == [('web', 'rollback'), ('backend', 'rollback'), ('verification', True)]
    assert release.read_json(tmp_path / 'deployed.json') == {'deployed': False, 'rolledBack': True}


def test_failed_rollback_is_not_reported_healthy(monkeypatch, tmp_path):
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    monkeypatch.setattr(release, 'switch', Mock(side_effect=release.GuardError('configuration changed')))
    assert not release.rollback({}, {}, [{'service': 'backend'}])
    assert release.read_json(tmp_path / 'rollback-result.json')['rolledBack'] is False


@pytest.mark.parametrize('changed', ['rendered', 'env', 'compose', 'overlay'])
def test_changed_frozen_context_cannot_execute_cutover(monkeypatch, tmp_path, changed):
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    directory = tmp_path / 'backend'
    directory.mkdir()
    rendered = {'services': {'backend': {'image': 'old', 'environment': {'EDITION': 'global'}}}}
    release.write_json(directory / 'rendered-before.json', rendered)
    release.write_json(directory / 'container-before.json', container())
    env, compose, overlay = directory / 'env.before', directory / 'compose.before', directory / 'image.json'
    env.write_bytes(b'EDITION=global\n')
    compose.write_bytes(b'services: {}\n')
    release.write_json(overlay, {'services': {'backend': {'image': 'new'}}})
    target = dict(service='backend', newTag='new', newImage='sha256:new', renderedSha=release.digest(release.canonical(rendered)),
        composeFiles=['/original/compose'], envFiles=['/original/env'],
        frozenComposeFiles=[str(compose)], frozenEnvFiles=[str(env)],
        sourceHashes={'/original/compose': release.digest(compose.read_bytes()), '/original/env': release.digest(env.read_bytes())},
        newOverlay=str(overlay), newOverlaySha=release.digest(overlay.read_bytes()))
    if changed == 'rendered': release.write_json(directory / 'rendered-before.json', {'services': {}})
    elif changed == 'env': env.write_bytes(b'EDITION=cn\n')
    elif changed == 'compose': compose.write_bytes(b'services: changed\n')
    else: overlay.write_bytes(b'changed')
    monkeypatch.setattr(release, 'inspect', lambda name: {'Id': 'sha256:new'})
    command = Mock(side_effect=AssertionError('must not execute production command'))
    monkeypatch.setattr(release, 'run', command)
    with pytest.raises(release.GuardError):
        release.switch(target, 'new')
    command.assert_not_called()


def deploy_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    plan = {'backendBefore': {}, 'manifestSha': 'synthetic'}
    release.write_json(tmp_path / 'input.json', plan)
    release.write_json(tmp_path / 'installers-verification.json', {})
    manifest = dict(targets=[{'service': 'backend', 'newImage': 'sha256:backend'}], nonTargets={}, models={},
        inputSha=release.digest((tmp_path / 'input.json').read_bytes()),
        installersProofSha=release.digest((tmp_path / 'installers-verification.json').read_bytes()))
    release.write_json(tmp_path / 'prepared.json', manifest)
    release.write_json(tmp_path / 'candidate-verification.json', {'passed': True, 'images': {'backend': 'sha256:backend'}})
    monkeypatch.setattr(release, 'check_inputs', lambda plan: None)
    return plan, manifest


def test_candidate_verification_must_match_exact_immutable_images_before_idle_or_switch(monkeypatch, tmp_path):
    deploy_fixture(tmp_path, monkeypatch)
    release.write_json(tmp_path / 'candidate-verification.json', {'passed': True, 'images': {'backend': 'sha256:other'}})
    verify = Mock(side_effect=AssertionError('must not execute'))
    monkeypatch.setattr(release, 'verify_baseline', verify)
    with pytest.raises(release.GuardError):
        release.deploy()
    verify.assert_not_called()


def test_two_idle_gates_and_final_baseline_check_precede_any_switch(monkeypatch, tmp_path):
    deploy_fixture(tmp_path, monkeypatch)
    events = []
    monkeypatch.setattr(release, 'verify_baseline', lambda *args: events.append('baseline'))
    monkeypatch.setattr(release, 'idle_gate', lambda *args: events.append('idle'))
    monkeypatch.setattr(release, 'switch', lambda *args: events.append('switch'))
    monkeypatch.setattr(release, 'verify_live', lambda *args: events.append('verified'))
    release.deploy()
    assert events == ['baseline', 'idle', 'idle', 'baseline', 'switch', 'verified']


def test_preflight_never_switches_or_advertises_manifest(monkeypatch, tmp_path):
    deploy_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(release, 'verify_baseline', lambda *args: None)
    monkeypatch.setattr(release, 'idle_gate', lambda *args: None)
    switch = Mock(side_effect=AssertionError('must not execute'))
    monkeypatch.setattr(release, 'switch', switch)
    release.deploy(preflight_only=True)
    switch.assert_not_called()
    assert not (tmp_path / 'deployed.json').exists()


def test_partial_switch_failure_rolls_back_only_authorized_touched_components(monkeypatch, tmp_path):
    _, manifest = deploy_fixture(tmp_path, monkeypatch)
    manifest['targets'].append({'service': 'web', 'newImage': 'sha256:web'})
    release.write_json(tmp_path / 'prepared.json', manifest)
    release.write_json(tmp_path / 'candidate-verification.json', {'passed': True,
        'images': {'backend': 'sha256:backend', 'web': 'sha256:web'}})
    monkeypatch.setattr(release, 'verify_baseline', lambda *args: None)
    monkeypatch.setattr(release, 'idle_gate', lambda *args: None)
    events = []
    def switch(target, kind):
        events.append((target['service'], kind))
        if target['service'] == 'web': raise release.GuardError('health failed')
    monkeypatch.setattr(release, 'switch', switch)
    def rollback(manifest, plan, touched):
        events.append(('rollback', [t['service'] for t in touched]))
        return True
    monkeypatch.setattr(release, 'rollback', rollback)
    with pytest.raises(SystemExit) as ended:
        release.deploy()
    assert ended.value.code == 1
    assert events == [('backend', 'new'), ('web', 'new'), ('rollback', ['backend', 'web'])]


def test_candidate_must_append_to_actual_image_layers_not_an_old_future_build():
    base = {'Config': {'Env': ['EDITION=global']}, 'RootFS': {'Layers': ['nginx-base', 'actual-live-assets']}}
    candidate = deepcopy(base)
    candidate['RootFS']['Layers'].append('approved-performance-assets')
    release.verify_image_base(candidate, base)
    candidate['RootFS']['Layers'] = ['nginx-base', 'staged-full-build', 'approved-performance-assets']
    with pytest.raises(release.GuardError):
        release.verify_image_base(candidate, base)


def test_image_overlay_references_immutable_digest_and_never_mutable_tag(monkeypatch, tmp_path):
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    directory = tmp_path / 'backend'
    directory.mkdir()
    before = {'services': {'backend': {'image': 'old-tag'}}}
    release.write_json(directory / 'rendered-before.json', before)
    image = 'sha256:' + 'a'*64
    target = {'service': 'backend'}
    monkeypatch.setattr(release, 'rendered', lambda *a, **kw: release.expected_overlay(before, 'backend', image))
    release.write_overlay(target, 'new', image)
    assert release.read_json(Path(target['newOverlay']))['services']['backend']['image'] == image
    with pytest.raises(release.GuardError):
        release.write_overlay(target, 'new', 'offersteady-global-backend:mutable')


def test_switch_uses_digest_overlay_and_single_service_with_no_build_no_deps_no_pull(monkeypatch, tmp_path):
    monkeypatch.setattr(release, 'ROOT', tmp_path)
    directory = tmp_path / 'backend'
    directory.mkdir()
    before_config = {'services': {'backend': {'image': 'old'}}}
    release.write_json(directory / 'rendered-before.json', before_config)
    before = container()
    release.write_json(directory / 'container-before.json', before)
    image = 'sha256:' + 'a'*64
    after = container()
    after.update(Image=image, State={'Running': True, 'Health': {'Status': 'healthy'}}, RestartCount=0)
    after['Config']['Image'] = image
    overlay = directory / 'image.json'
    release.write_json(overlay, {'services': {'backend': {'image': image}}})
    target = dict(service='backend', container='offersteady-global-backend-1', newTag='mutable-tag', newImage=image,
        composeDirectory='/original/compose', composeFiles=[], envFiles=[], frozenComposeFiles=[], frozenEnvFiles=[], sourceHashes={},
        renderedSha=release.digest(release.canonical(before_config)), newOverlay=str(overlay), newOverlaySha=release.digest(overlay.read_bytes()))
    monkeypatch.setattr(release, 'inspect', lambda name: {'Id': image} if name == 'mutable-tag' else after)
    monkeypatch.setattr(release, 'rendered', lambda *a, **kw: release.expected_overlay(before_config, 'backend', image))
    commands = []
    monkeypatch.setattr(release, 'run', lambda args, **kw: commands.append(args))
    release.switch(target, 'new')
    assert len(commands) == 1
    command = commands[0]
    assert command[-8:] == ['up', '-d', '--no-build', '--no-deps', '--pull', 'never', '--force-recreate', 'backend']
    assert command[-1] == 'backend' and '--remove-orphans' not in command
    assert release.read_json(overlay)['services']['backend']['image'] == image


def test_manual_rollback_rejects_modified_inputs_before_any_switch(monkeypatch, tmp_path):
    _, manifest = deploy_fixture(tmp_path, monkeypatch)
    release.write_json(tmp_path / 'input.json', {'different': 'release'})
    inspect = Mock(side_effect=AssertionError('must not inspect or mutate production'))
    monkeypatch.setattr(release, 'inspect', inspect)
    with pytest.raises(release.GuardError):
        release.manual_rollback()
    inspect.assert_not_called()


def test_manual_rollback_cannot_overwrite_a_later_release(monkeypatch, tmp_path):
    _, manifest = deploy_fixture(tmp_path, monkeypatch)
    base_id, base_image = release.BASES['backend']
    target = dict(manifest['targets'][0], container='offersteady-global-backend-1', beforeId=base_id,
        baseImage=base_image, rollbackImage='sha256:rollback')
    manifest['targets'] = [target]
    release.write_json(tmp_path / 'prepared.json', manifest)
    (tmp_path / 'backend').mkdir()
    release.write_json(tmp_path / 'backend/container-before.json', container())
    monkeypatch.setattr(release, 'inspect', lambda name: {'Image': 'sha256:another-release'})
    rollback = Mock(side_effect=AssertionError('must not switch production'))
    monkeypatch.setattr(release, 'rollback', rollback)
    with pytest.raises(release.GuardError):
        release.manual_rollback()
    rollback.assert_not_called()


@pytest.mark.parametrize('service,extra', [('web', False), ('backend', True)])
def test_runtime_version_exception_never_allows_other_environment_drift(service, extra):
    before = container()
    before['Config']['Env'] += ['OFFERSTEADY_APP_VERSION=actual-version']
    source = {'services': {service: {'environment': {'OFFERSTEADY_APP_VERSION': 'stale-version', 'EDITION': 'global'}}}}
    if extra: source['services'][service]['environment']['EDITION'] = 'cn'
    with pytest.raises(release.GuardError):
        release.runtime_baseline(source, before, service)


def test_runtime_version_override_requires_actual_value_and_does_not_mutate_source():
    before = container()
    source = {'services': {'backend': {'environment': {'OFFERSTEADY_APP_VERSION': 'stale'}}}}
    with pytest.raises(release.GuardError):
        release.runtime_baseline(source, before, 'backend')
    before['Config']['Env'] += ['OFFERSTEADY_APP_VERSION=actual']
    result, needed = release.runtime_baseline(source, before, 'backend')
    assert needed and result['services']['backend']['environment']['OFFERSTEADY_APP_VERSION'] == 'actual'
    assert source['services']['backend']['environment']['OFFERSTEADY_APP_VERSION'] == 'stale'


def test_frozen_version_baseline_is_shared_by_new_and_rollback_image_layers(monkeypatch, tmp_path):
    monkeypatch.setattr(release, 'ROOT', tmp_path / 'new')
    release.ROOT.mkdir()
    old = tmp_path / 'original'
    old.mkdir()
    original_env = old / 'private.env'
    original_env.write_bytes(b'SYNTHETIC_PRIVATE=unchanged\n')
    base_file, prior_overlay = old / 'compose.json', old / 'performance.json'
    source = {'services': {'backend': {'image': 'old-image-tag', 'environment': {
        'EDITION': 'global', 'PRIVATE': 'synthetic-marker', 'OFFERSTEADY_APP_VERSION': 'stale-source-version'}}}}
    base_file.write_bytes(release.canonical(source))
    prior_overlay.write_bytes(release.canonical({'services': {'backend': {'image': 'old-image-tag'}}}))
    before = container()
    before.update(Id='synthetic-before', Image='sha256:'+'b'*64)
    before['Config'].update(Image='old-image-tag')
    before['Config']['Env'].append('OFFERSTEADY_APP_VERSION=actual-runtime-version')
    monkeypatch.setattr(release, 'context', lambda *args: dict(composeDirectory=str(old),
        composeFiles=[str(base_file), str(prior_overlay)], envFiles=[str(original_env)]))
    def render(target, *, frozen=False, overlay=None):
        result = {'services': {}}
        files = target['frozenComposeFiles'] if frozen else target['composeFiles']
        for path in files + ([str(overlay)] if overlay else []):
            for service, config in release.read_json(Path(path))['services'].items():
                merged = result['services'].setdefault(service, {})
                for key, value in config.items():
                    if key == 'environment': merged.setdefault(key, {}).update(value)
                    else: merged[key] = value
        return result
    monkeypatch.setattr(release, 'rendered', render)
    target = release.freeze(before, 'backend')
    assert len(target['frozenComposeFiles']) == 3
    effective = render(target, frozen=True)
    assert effective['services']['backend']['environment']['OFFERSTEADY_APP_VERSION'] == 'actual-runtime-version'
    assert original_env.read_bytes() == b'SYNTHETIC_PRIVATE=unchanged\n'
    assert release.read_json(base_file) == source
    release.verify_frozen_files(target, before)
    for kind, letter in [('new', 'c'), ('rollback', 'd')]:
        image = 'sha256:' + letter*64
        release.write_overlay(target, kind, image)
        final = render(target, frozen=True, overlay=target[kind+'Overlay'])
        assert final == release.expected_overlay(effective, 'backend', image)
        assert final['services']['backend']['environment']['OFFERSTEADY_APP_VERSION'] == 'actual-runtime-version'
    version = Path(target['runtimeVersionOverlay'])
    release.write_json(version, {'services': {'backend': {'environment': {'OFFERSTEADY_APP_VERSION': 'actual-runtime-version',
        'EDITION': 'cn'}}}})
    target['runtimeVersionOverlaySha'] = release.digest(version.read_bytes())
    with pytest.raises(release.GuardError):
        release.verify_frozen_files(target, before)
