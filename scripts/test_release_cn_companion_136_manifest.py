"""Synthetic 1.3.6 publication checks. No network, SSH, Docker or user data."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import threading

import pytest


@pytest.fixture
def release(monkeypatch):
    path = Path(__file__).with_name('release_cn_companion_136_manifest.py')
    spec = importlib.util.spec_from_file_location('cn_companion_136', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: pytest.fail('external operation forbidden'))
    return module


@pytest.fixture
def payload(release):
    entries = []
    for platform, architecture in sorted(release.TARGETS):
        filename = (f'OfferSteady-Companion-1.3.6-macOS-{architecture}.dmg' if platform == 'macos'
                    else 'OfferSteady-Companion-Setup-1.3.6-Windows-x64.exe')
        entries.append({'id': f'synthetic-{platform}-{architecture}', 'platform': platform,
            'architecture': architecture, 'version': '1.3.6', 'protocolVersion': '2.0',
            'distributionStatus': 'published', 'developmentOnly': False, 'fileSizeBytes': 123456,
            'sha256': release.digest(filename.encode()), 'publishedAtMs': 1234, 'fileName': filename,
            'objectKey': f'desktop-releases/{platform}/{architecture}/1.3.6/{filename}',
            'minimumOs': 'macOS 14.2+' if platform == 'macos' else 'Windows 10 22H2+',
            'signingStatus': 'verified' if platform == 'macos' else 'unsigned',
            'notarized': platform == 'macos', 'capabilities': {'microphone': True, 'systemAudio': True}})
    return {'version': 1, 'generatedAtMs': 1234, 'entries': entries}


@pytest.mark.parametrize('key,value', [('version','1.3.5'), ('protocolVersion','1'),
    ('distributionStatus','internal'), ('developmentOnly',True), ('fileSizeBytes',0),
    ('fileSizeBytes',True), ('sha256','0'*64), ('sha256','invalid'), ('publishedAtMs',True),
    ('objectKey','global-desktop-releases/forbidden'), ('fileName','Local-r3.zip'),
    ('artifactPath','/private/forbidden'), ('platform',{})])
def test_invalid_metadata_rejected(release, payload, key, value):
    payload['entries'][0][key] = value
    with pytest.raises(release.GuardError):
        release.validate_manifest(payload)


def test_complete_truthful_three_platform_manifest(release, payload):
    release.validate_manifest(payload)
    with pytest.raises(release.GuardError):
        release.validate_manifest({**payload, 'entries': payload['entries'][:2]})
    for row in payload['entries']:
        changed = deepcopy(payload)
        next(e for e in changed['entries'] if e['id'] == row['id'])['notarized'] = not row['notarized']
        with pytest.raises(release.GuardError):
            release.validate_manifest(changed)


@pytest.fixture
def files(release, payload, tmp_path, monkeypatch):
    root = tmp_path / 'root'
    target = root / 'apps/backend/app' / release.MANIFEST_NAME
    target.parent.mkdir(parents=True)
    old = b'{"syntheticOnly":true}\n'
    new = (json.dumps(payload) + '\n').encode()
    target.write_bytes(old)
    pending = target.with_name('.pending')
    pending.write_bytes(new)
    hashes = {}
    for relative in ['apps/backend/app/services/other.py', 'ai/prompts/synthetic.md']:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('synthetic ' + relative).encode())
        hashes[relative] = release.digest(path.read_bytes())
    monkeypatch.setattr(release, 'OLD_MANIFEST_SHA', release.digest(old))
    return {'path':target, 'pending':pending, 'expected_old_sha':release.digest(old),
            'expected_new_sha':release.digest(new), 'source_hashes':hashes}


def test_atomic_source_and_permissions_and_exact_rollback(release, files):
    old = files['path'].read_bytes()
    files['pending'].chmod(0o600)
    release.atomic_switch(**files)
    assert release.digest(files['path'].read_bytes()) == files['expected_new_sha']
    assert files['path'].stat().st_mode & 0o777 == 0o644
    files['pending'].write_bytes(old)
    release.atomic_switch(**{**files, 'expected_old_sha':files['expected_new_sha'],
        'expected_new_sha':files['expected_old_sha'], 'restore_baseline':True})
    assert files['path'].read_bytes() == old


@pytest.mark.parametrize('drift', ['runtime','candidate','non_business_source','symlink','directory','path_traversal'])
def test_atomic_drift_cannot_truncate_public_file(release, files, drift):
    if drift == 'runtime': files['path'].write_bytes(b'synthetic concurrent release')
    elif drift == 'candidate': files['pending'].write_bytes(b'partial')
    elif drift == 'non_business_source':
        (files['path'].parents[3] / 'ai/prompts/synthetic.md').write_bytes(b'changed')
    elif drift == 'symlink':
        data = files['pending'].read_bytes(); other = files['pending'].with_name('other')
        other.write_bytes(data); files['pending'].unlink(); files['pending'].symlink_to(other)
    elif drift == 'directory':
        other = files['path'].parent / 'other'; other.mkdir()
        files['pending'] = files['pending'].rename(other / 'pending')
    else: files['source_hashes']['../outside'] = 'f'*64
    before = files['path'].read_bytes()
    with pytest.raises(release.GuardError): release.atomic_switch(**files)
    assert files['path'].read_bytes() == before


def test_competing_atomic_switches_have_one_winner(release, files):
    second = files['pending'].with_name('.pending2'); second.write_bytes(files['pending'].read_bytes())
    barrier = threading.Barrier(2)
    def switch(p):
        barrier.wait(timeout=3)
        try: release.atomic_switch(**{**files, 'pending':p}); return 'published'
        except release.GuardError: return 'stale'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(switch,[files['pending'],second])) == ['published','stale']


def test_actual_container_cas_code_matches_local_guards(release, files, monkeypatch):
    args = {key:str(value) if isinstance(value,Path) else value for key,value in files.items()}
    monkeypatch.setattr(release.sys,'argv',['guard',json.dumps(args)])
    exec(release.portable_atomic_source(),{})
    assert release.digest(files['path'].read_bytes()) == files['expected_new_sha']


COMPOSE_FILES = {*(f"/opt/offersteady/releases/20261101-cn-mock-1/backend/compose-{i}.before" for i in range(14)),
                 "/opt/offersteady/releases/20261101-cn-mock-1/backend/new.compose.json"}


def synthetic_record(row):
    return {'Name':'/'+row['name'], 'Id':row['id'], 'Image':row['image'],
        'Config':{'Image':row['imageName'],'Env':['SYNTHETIC_NOT_A_SECRET=value'],
                  'Labels':{'com.docker.compose.project.config_files':','.join(sorted(COMPOSE_FILES))}}, 'HostConfig':{},
        'State':{'StartedAt':row['startedAt'],'Running':True,'Health':{'Status':'healthy'}},
        'RestartCount':row['restartCount'],'Mounts':[]}


@pytest.fixture
def plan(release, payload, tmp_path, monkeypatch):
    old = b'{"syntheticOnly":true}\n'
    monkeypatch.setattr(release,'OLD_MANIFEST_SHA',release.digest(old))
    baseline = tmp_path/'baseline'; baseline.mkdir()
    hashes = {filename:release.digest(filename.encode()) for filename in release.BUSINESS_FILES}
    hashes[release.BUSINESS_FILES[1]] = release.HEARTBEAT_SHA
    hashes[release.MANIFEST_NAME] = release.digest(old)
    inputs = {'apps/backend/app/'+path:value for path,value in hashes.items()}
    inputs['apps/backend/app/modules/screenshot_answer.py'] = release.digest(b'synthetic screenshot module')
    inputs.update({f'ai/prompts/synthetic-{index}.md':release.digest(str(index).encode()) for index in range(226)})
    data = (json.dumps(inputs,sort_keys=True)+'\n').encode()
    monkeypatch.setattr(release,'BASE_INPUTS_SHA',release.digest(data))
    rows = []
    for index,name in enumerate(sorted(release.EXPECTED_NAMES),1):
        row = {'name':name,'id':f'{index:064x}',
            'image':release.BASE_IMAGE if name == release.BACKEND_NAME else f'sha256:{index:064x}',
            'imageName':release.BASE_IMAGE if name == release.BACKEND_NAME else name,
            'startedAt':'2026-11-01T00:00:00Z','restartCount':0,'mounts':[]}
        row['runtimeConfigSha256'] = release.runtime_config_sha(synthetic_record(row))
        rows.append(row)
    summary = {'components':rows,'backendFileHashes':hashes,
        'backendComposeFiles':{path:release.digest(path.encode()) for path in COMPOSE_FILES}}
    (baseline/'desktop_release_manifest.before.json').write_bytes(old)
    (baseline/'component-summary.before.json').write_text(json.dumps(summary))
    (baseline/'backend-runtime-manifest.before.json').write_bytes(data)
    manifest = tmp_path/'manifest.json'; manifest.write_text(json.dumps(payload))
    return release.load_plan(manifest,baseline,release.DEFAULT_RELEASE_DIR)


class FakeRemote:
    def __init__(self,release,plan):
        self.release,self.plan = release,plan
        self.calls,self.writes,self.tags = [],{}, {release.PRESERVED_TAG:release.PRESERVED_TAG_IMAGE}
        self.manifest_sha = release.OLD_MANIFEST_SHA
        self.base = {'Id':release.BASE_IMAGE,'RootFS':{'Layers':['base-layer']},'Config':{'Cmd':['synthetic']}}
        self.candidate = {'Id':'sha256:'+'c'*64,'RootFS':{'Layers':['base-layer','manifest-layer']},'Config':deepcopy(self.base['Config'])}
        self.lose_switch_response = False
        self.lose_rollback_response = False
        self.before_switch_error = False
        self.nonbusiness_drift = False
    def inspect_containers(self,names):
        return [synthetic_record(row) for row in self.plan['summary']['components']]
    def image(self,name,*,missing_ok=False):
        value = name if name == self.release.BASE_IMAGE else self.tags.get(name)
        if value is None:
            if missing_ok:return None
            raise self.release.GuardError('synthetic image missing')
        if value == self.release.BASE_IMAGE:return deepcopy(self.base)
        if value == self.release.PRESERVED_TAG_IMAGE:return {'Id':value}
        return deepcopy({**self.candidate,'Id':value})
    def hashes(self,name,files,*,candidate=False):
        values = {**self.plan['inputs'],self.release.MANIFEST_INPUT:self.plan['newManifestSha'] if candidate else self.manifest_sha}
        if self.nonbusiness_drift: values['apps/backend/app/modules/screenshot_answer.py'] = 'f'*64
        return {key:values[key] for key in files}
    def host_hashes(self,paths):
        return {path:self.plan['summary']['backendComposeFiles'][path] for path in paths}
    def put_exclusive(self,path,data):
        assert path not in self.writes
        self.writes[path] = data
    def read_public_file(self,path,*,missing_ok=False):
        if path not in self.writes and not missing_ok:raise self.release.GuardError('synthetic staged missing')
        return self.writes.get(path)
    def manifest_mode(self,image):return 0o644
    def run(self,argv,**kwargs):
        self.calls.append(argv)
        if argv[:2] == ['docker','tag']:
            self.tags[argv[3]] = argv[2]
        elif argv[:2] == ['docker','build']:
            self.tags[self.release.NEW_TAG] = self.candidate['Id']
        elif argv[:3] == ['docker','exec',self.release.BACKEND_NAME] and 'atomic_switch(**p)' in argv[-2]:
            args = json.loads(argv[-1])
            assert self.manifest_sha == args['expected_old_sha']
            assert len(args['source_hashes']) == 231
            if self.before_switch_error: raise self.release.GuardError('synthetic CAS unavailable')
            self.manifest_sha = args['expected_new_sha']
            if self.lose_switch_response and not args['restore_baseline']:
                self.lose_switch_response = False
                raise self.release.GuardError('synthetic lost SSH after switch')
            if self.lose_rollback_response and args['restore_baseline']:
                self.lose_rollback_response = False
                raise self.release.GuardError('synthetic lost SSH after rollback')


def test_dry_run_is_read_only(release,plan,monkeypatch,capsys):
    remote = FakeRemote(release,plan)
    monkeypatch.setattr(release,'Remote',lambda:remote);monkeypatch.setattr(release,'load_plan',lambda *a:plan)
    assert release.main(['--manifest','synthetic','--baseline-dir','synthetic']) == 0
    assert json.loads(capsys.readouterr().out)['dryRun']
    assert not remote.calls and not remote.writes


def test_apply_only_metadata_preserves_legacy_tag_and_restarts_nothing(release,plan):
    remote = FakeRemote(release,plan);report=release.apply(remote,plan)
    assert remote.manifest_sha == plan['newManifestSha']
    assert remote.tags[release.PRESERVED_TAG] == release.PRESERVED_TAG_IMAGE
    assert report['containersRestarted'] is False and report['runtimeInputCount'] == 232
    assert remote.writes[f'{release.DEFAULT_RELEASE_DIR}/Dockerfile'] == release.build_dockerfile()
    assert json.loads(remote.writes[f'{release.DEFAULT_RELEASE_DIR}/backend-image.compose.json']) == {'services':{'backend':{'image':remote.candidate['Id']}}}
    assert all(not any(word in call for word in ('restart','compose','push','--force-recreate')) for call in remote.calls)
    assert all(call[3] != release.PRESERVED_TAG for call in remote.calls if call[:2] == ['docker','tag'])
    assert all(path.startswith(release.DEFAULT_RELEASE_DIR+'/') for path in remote.writes)


def test_published_verification_and_reapply_do_not_write(release,plan):
    remote=FakeRemote(release,plan);release.apply(remote,plan)
    old_calls,old_writes=deepcopy(remote.calls),deepcopy(remote.writes)
    assert release.verify_published(remote,plan)['verifiedPublished']
    assert release.apply(remote,plan)['verifiedPublished']
    assert old_calls == remote.calls and old_writes == remote.writes


def test_verify_published_handles_lost_receipt_without_restarting(release,plan):
    remote=FakeRemote(release,plan);release.apply(remote,plan)
    remote.writes.pop(f'{release.DEFAULT_RELEASE_DIR}/deployed.json')
    before = deepcopy(remote.writes)
    assert release.verify_published(remote,plan)['deployedRecordPresent'] is False
    assert release.apply(remote,plan)['verifiedPublished']
    assert remote.writes == before


def test_lost_switch_receipt_restores_exact_old_manifest(release,plan):
    remote=FakeRemote(release,plan);remote.lose_switch_response=True
    with pytest.raises(release.GuardError,match='lost SSH'):release.apply(remote,plan)
    assert remote.manifest_sha == release.OLD_MANIFEST_SHA
    assert remote.tags[release.PRESERVED_TAG] == release.PRESERVED_TAG_IMAGE
    assert f'{release.DEFAULT_RELEASE_DIR}/deployed.json' not in remote.writes


def test_explicit_rollback_is_exact_and_survives_lost_response(release,plan):
    remote=FakeRemote(release,plan);release.apply(remote,plan);remote.lose_rollback_response=True
    assert release.rollback(remote,plan)['rolledBack']
    assert remote.manifest_sha == release.OLD_MANIFEST_SHA
    assert remote.tags[release.PRESERVED_TAG] == release.PRESERVED_TAG_IMAGE


def test_failed_cas_keeps_old_manifest(release,plan):
    remote=FakeRemote(release,plan);remote.before_switch_error=True
    with pytest.raises(release.GuardError,match='CAS unavailable'):release.apply(remote,plan)
    assert remote.manifest_sha == release.OLD_MANIFEST_SHA


@pytest.mark.parametrize('drift',['layer','config','non_business_source','mode','rollback'])
def test_candidate_refuses_any_additional_changes(release,plan,drift):
    remote=FakeRemote(release,plan);remote.tags[release.ROLLBACK_TAG]=release.BASE_IMAGE
    candidate=deepcopy(remote.candidate)
    if drift == 'layer':candidate['RootFS']['Layers'].insert(1,'source-layer')
    elif drift == 'config':candidate['Config']['Cmd']=['forbidden']
    elif drift == 'non_business_source':remote.nonbusiness_drift=True
    elif drift == 'mode':remote.manifest_mode=lambda image:0o600
    else:remote.tags[release.ROLLBACK_TAG]=candidate['Id']
    with pytest.raises(release.GuardError):release.verify_candidate(remote,plan,candidate)


@pytest.mark.parametrize('drift',['manifest','non_business_source','legacy_tag','rollback_tag','runtime_config','frozen_compose'])
def test_initial_drift_prevents_staging(release,plan,drift):
    remote=FakeRemote(release,plan)
    if drift == 'manifest':remote.manifest_sha='f'*64
    elif drift == 'non_business_source':remote.nonbusiness_drift=True
    elif drift == 'legacy_tag':remote.tags[release.PRESERVED_TAG]=remote.candidate['Id']
    elif drift == 'rollback_tag':remote.tags[release.ROLLBACK_TAG]=remote.candidate['Id']
    elif drift == 'frozen_compose':remote.host_hashes=lambda paths: {path:'f'*64 for path in paths}
    else:
        original=remote.inspect_containers
        def changed(names):
            records=original(names);records[0]['Config']['Env']=['SYNTHETIC_DRIFT=true'];return records
        remote.inspect_containers=changed
    with pytest.raises(release.GuardError):release.apply(remote,plan)
    assert not remote.calls and not remote.writes


@pytest.mark.parametrize('field,value',[('Id','replaced'),('Image','other-image'),('RestartCount',1)])
def test_component_lifecycle_drift_rejected(release,plan,field,value):
    remote=FakeRemote(release,plan);records=remote.inspect_containers([]);records[0][field]=value
    with pytest.raises(release.GuardError):release.verify_components(plan['summary']['components'],records)


@pytest.mark.parametrize('field',['inputs','old_manifest','heartbeat','image','runtime_config','component_count'])
def test_saved_baseline_tampering_rejected(release,plan,field):
    baseline=plan['baselineDir'];summary_path=baseline/'component-summary.before.json'
    summary=json.loads(summary_path.read_bytes())
    if field == 'inputs':(baseline/'backend-runtime-manifest.before.json').write_text('{}')
    elif field == 'old_manifest':(baseline/'desktop_release_manifest.before.json').write_text('{}')
    elif field == 'heartbeat':summary['backendFileHashes'][release.BUSINESS_FILES[1]]='f'*64
    elif field == 'image':next(r for r in summary['components'] if r['name'] == release.BACKEND_NAME)['imageName']='compose-backend'
    elif field == 'runtime_config':summary['components'][0].pop('runtimeConfigSha256')
    else:summary['components'].pop()
    summary_path.write_text(json.dumps(summary))
    with pytest.raises(release.GuardError):release.load_plan(baseline.parent/'manifest.json',baseline,release.DEFAULT_RELEASE_DIR)


def seed_staged(release,plan,*,candidate=False):
    remote=FakeRemote(release,plan);remote.tags[release.ROLLBACK_TAG]=release.BASE_IMAGE
    remote.writes={f'{release.DEFAULT_RELEASE_DIR}/{name}':data for name,data in release.staged_contents(plan).items()}
    remote.writes[f'{release.DEFAULT_RELEASE_DIR}/Dockerfile']=release.build_dockerfile()
    if candidate:remote.tags[release.NEW_TAG]=remote.candidate['Id']
    return remote


@pytest.mark.parametrize('filename',['desktop_release_manifest.before.json','component-summary.before.json',
    'backend-runtime-manifest.before.json','desktop_release_manifest.json','Dockerfile'])
def test_resume_staged_refuses_altered_materials_before_writes(release,plan,filename):
    remote=seed_staged(release,plan);remote.writes[f'{release.DEFAULT_RELEASE_DIR}/{filename}']=b'drift'
    before=deepcopy(remote.writes)
    with pytest.raises(release.GuardError,match='staged'):release.apply(remote,plan,resume_staged=True)
    assert remote.writes == before and not remote.calls


@pytest.mark.parametrize('candidate',[False,True])
def test_resume_staged_preserves_exact_candidate_and_legacy_tag(release,plan,candidate):
    remote=seed_staged(release,plan,candidate=candidate)
    assert release.apply(remote,plan,resume_staged=True)['containersRestarted'] is False
    assert remote.manifest_sha == plan['newManifestSha']
    assert remote.tags[release.PRESERVED_TAG] == release.PRESERVED_TAG_IMAGE
    assert len([c for c in remote.calls if c[:2] == ['docker','build']]) == (0 if candidate else 1)


@pytest.mark.parametrize('filename',['candidate-image.json','backend-image.compose.json','deployed.json'])
def test_published_verification_refuses_unknown_durable_state(release,plan,filename):
    remote=FakeRemote(release,plan);release.apply(remote,plan)
    remote.writes[f'{release.DEFAULT_RELEASE_DIR}/{filename}']=b'drift'
    before=deepcopy(remote.writes);calls=deepcopy(remote.calls)
    with pytest.raises(release.GuardError):release.verify_published(remote,plan)
    with pytest.raises(release.GuardError):release.rollback(remote,plan)
    assert remote.writes == before and remote.calls == calls


@pytest.mark.parametrize('value',['/opt/offersteady/current','/opt/offersteady/releases/../current',
    '/opt/offersteady-global/releases/20261102-cn-companion-136-1','/tmp/$(touch forbidden)'])
def test_unreviewed_directory_is_rejected(release,value):
    with pytest.raises(release.GuardError):release.validate_release_directory(value)



def test_rollback_repeat_is_read_only_after_exact_baseline_restore(release,plan):
    remote=FakeRemote(release,plan);release.apply(remote,plan);release.rollback(remote,plan)
    calls,writes=deepcopy(remote.calls),deepcopy(remote.writes)
    assert release.rollback(remote,plan)['verifiedRolledBack']
    assert remote.calls == calls and remote.writes == writes


def test_drift_during_build_is_rechecked_before_public_switch(release,plan):
    remote=FakeRemote(release,plan);original=remote.run
    def run(argv,**kwargs):
        result=original(argv,**kwargs)
        if argv[:2] == ['docker','build']:remote.nonbusiness_drift=True
        return result
    remote.run=run
    with pytest.raises(release.GuardError,match='complete runtime'):
        release.apply(remote,plan)
    assert remote.manifest_sha == release.OLD_MANIFEST_SHA
    assert not any(call[:2] == ['docker','cp'] for call in remote.calls)


def test_published_cli_and_rollback_cli_use_reviewed_operations(release,plan,monkeypatch,capsys):
    remote=FakeRemote(release,plan);release.apply(remote,plan)
    monkeypatch.setattr(release,'Remote',lambda:remote);monkeypatch.setattr(release,'load_plan',lambda *a:plan)
    calls,writes=deepcopy(remote.calls),deepcopy(remote.writes)
    assert release.main(['--manifest','synthetic','--baseline-dir','synthetic','--verify-published']) == 0
    assert json.loads(capsys.readouterr().out)['verifiedPublished']
    assert remote.calls == calls and remote.writes == writes
    assert release.main(['--manifest','synthetic','--baseline-dir','synthetic','--rollback']) == 0
    assert json.loads(capsys.readouterr().out)['rolledBack']


@pytest.mark.parametrize('arguments', [['--verify-published','--apply'],['--rollback','--apply'],['--resume-staged']])
def test_contradictory_cli_actions_cannot_write(release,plan,monkeypatch,arguments):
    remote=FakeRemote(release,plan)
    monkeypatch.setattr(release,'Remote',lambda:remote);monkeypatch.setattr(release,'load_plan',lambda *a:plan)
    with pytest.raises(SystemExit):
        release.main(['--manifest','synthetic','--baseline-dir','synthetic',*arguments])
    assert remote.calls == [] and remote.writes == {}



def two_mount_record():
    return {'Config':{'Image':'synthetic-image','Env':['SYNTHETIC_NOT_A_SECRET=value']},
            'HostConfig':{'ReadonlyRootfs':False},
            'Mounts':[{'Type':'volume','Source':'/synthetic/volume','Destination':'/data',
                       'RW':True,'Driver':'local','Mode':'z','Propagation':''},
                      {'Type':'bind','Source':'/synthetic/init','Destination':'/init',
                       'RW':False,'Mode':'ro','Propagation':'rprivate'}]}


def test_docker_two_mount_order_is_compatible_with_original_whole_digest(release):
    record=two_mount_record();expected=release.runtime_config_sha(record)
    swapped={**record,'Mounts':list(reversed(record['Mounts']))}
    assert release.runtime_config_sha(swapped) != expected
    assert release.runtime_config_matches(record,expected)
    assert release.runtime_config_matches(swapped,expected)
    # The old frozen digest and the record have not been rewritten.
    assert expected == release.runtime_config_sha(record)


@pytest.mark.parametrize('field,value',[('Source','/synthetic/changed'),('Destination','/changed'),
    ('RW',False),('Type','bind'),('Driver','other'),('Mode','ro'),('Propagation','private')])
def test_mount_order_compatibility_still_rejects_every_changed_mount_field(release,field,value):
    record=two_mount_record();expected=release.runtime_config_sha(record)
    changed=deepcopy(record);changed['Mounts'][0][field]=value
    changed['Mounts'].reverse()
    assert not release.runtime_config_matches(changed,expected)


@pytest.mark.parametrize('field',['Config','HostConfig','add_mount','remove_mount','duplicate_mount'])
def test_mount_order_compatibility_does_not_ignore_actual_configuration_changes(release,field):
    record=two_mount_record();expected=release.runtime_config_sha(record);changed=deepcopy(record)
    if field == 'Config':changed['Config']['Env']=['SYNTHETIC_CHANGED=true']
    elif field == 'HostConfig':changed['HostConfig']['ReadonlyRootfs']=True
    elif field == 'add_mount':changed['Mounts'].append(deepcopy(changed['Mounts'][0]))
    elif field == 'remove_mount':changed['Mounts'].pop()
    else:changed['Mounts'][1]=deepcopy(changed['Mounts'][0])
    changed['Mounts'].reverse()
    assert not release.runtime_config_matches(changed,expected)


def test_verify_components_accepts_only_mount_order_and_preserves_frozen_evidence(release,plan):
    baseline=deepcopy(plan['summary']['components']);remote=FakeRemote(release,plan)
    records=remote.inspect_containers([]);row=records[0]
    row['Mounts']=two_mount_record()['Mounts']
    baseline[0]['runtimeConfigSha256']=release.runtime_config_sha(row)
    frozen=deepcopy(baseline)
    row['Mounts'].reverse()
    release.verify_components(baseline,records)
    assert baseline == frozen
    row['Mounts'][0]['Source']='/synthetic/other'
    with pytest.raises(release.GuardError,match='configuration drift'):
        release.verify_components(baseline,records)
    assert baseline == frozen
