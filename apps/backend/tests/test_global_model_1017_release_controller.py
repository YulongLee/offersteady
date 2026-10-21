"""Synthetic regression tests for bounded Global model/summary production release guards."""
from copy import deepcopy
import importlib.util
import json
import io
import tarfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'scripts/global_model_1017_release/controller.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def release():
    return load(SCRIPT, 'test_global_model1017_release')


def before(service='backend'):
    env = {'UNCHANGED_SECRET': 'synthetic-value', 'FEATURE_FLAG': 'unchanged',
           'OFFERSTEADY_CHAT_QWEN_MODEL': 'deepseek-v4.1-flash',
           'OFFERSTEADY_CHAT_QUICK_MODEL': 'deepseek-v4.1-flash',
           'OFFERSTEADY_CHAT_DETAIL_MODEL': 'deepseek-v4.1-flash',
           'OFFERSTEADY_SCREENSHOT_VISION_MODEL': 'qwen3.6-flash'}
    return {'Id': 'a'*64, 'Image': 'sha256:'+'1'*64, 'Config': {
        'Env': [key+'='+value for key,value in env.items()], 'Hostname': 'a'*12,
        'Image': 'original-runtime-tag', 'Cmd': ['unchanged'], 'User': '',
        'Labels': {'preserved': 'value', 'com.docker.compose.service': service}},
        'HostConfig': {'NetworkMode': 'offersteady-global_default', 'ReadonlyRootfs': False},
        'Mounts': [], 'RestartCount': 0,
        'State': {'Running':True,'StartedAt':'2026-10-21T12:00:00Z','Pid':100,
                  'Status':'running','Restarting':False,'Dead':False,'Paused':False},
        'NetworkSettings': {'Networks': {'offersteady-global_default': {
            'Aliases': [service, 'offersteady-global-'+service+'-1', 'a'*12], 'IPAMConfig': None,
            'Links': None, 'DriverOpts': None, 'GwPriority': 0}}}}


def target(service='backend'):
    return {'service':service,'newImage':'sha256:'+'1'*64,'rollbackImage':'sha256:'+'1'*64,
        'frozenComposeFiles':['/release/'+service+'/compose.before'],
        'frozenEnvFiles':['/release/'+service+'/env.before'],
        'newOverlay':'/release/'+service+'/new.compose.json',
        'rollbackOverlay':'/release/'+service+'/rollback.compose.json',
        'composeDirectory':'/original/'+service,'container':'offersteady-global-'+service+'-1'}


def after(release, original, item, kind='new'):
    value=deepcopy(original)
    value['Id']='b'*64
    value['Config']['Hostname']='b'*12
    value['Config']['Env']=[key+'='+v for key,v in release.expected_environment(original,item['service'],kind).items()]
    value['Config']['Labels'].update({'com.docker.compose.project':'offersteady-global',
        'com.docker.compose.service':item['service'],
        'com.docker.compose.project.config_files':','.join(item['frozenComposeFiles']+[item[kind+'Overlay']]),
        'com.docker.compose.project.environment_file':','.join(item['frozenEnvFiles']),
        'com.docker.compose.project.working_dir':item['composeDirectory']})
    value['NetworkSettings']['Networks']['offersteady-global_default']['Aliases']=[item['service'],'offersteady-global-'+item['service']+'-1','b'*12]
    return value


@pytest.mark.parametrize('service,count',[('backend',4),('material-worker',1),('web',0)])
def test_only_the_approved_model_keys_change(release, service, count):
    original=before(service)
    changed=release.expected_environment(original,service,'new')
    old=release.environment(original)
    assert sum(changed[k]!=old[k] for k in changed)==count
    assert changed['UNCHANGED_SECRET']==old['UNCHANGED_SECRET']
    assert changed['FEATURE_FLAG']==old['FEATURE_FLAG']
    assert release.expected_environment(original,service,'rollback')==old


@pytest.mark.parametrize('service',['backend','material-worker'])
def test_overlay_keeps_independent_compose_context_and_unrelated_services(release,service):
    source={'services':{'backend':{'environment':{'UNCHANGED_SECRET':'synthetic'}},
        'material-worker':{'environment':{'WORKER_ONLY':'present'}},
        'web':{'build':{'context':'original'},'volumes':['original']}},'networks':{'original':{}}}
    frozen=deepcopy(source)
    expected=release.expected_render(source,service,'sha256:'+'1'*64,'new')
    assert source==frozen
    assert expected['networks']==source['networks']
    for key in source['services']:
        if key!=service:assert expected['services'][key]==source['services'][key]


@pytest.mark.parametrize('service',['backend','material-worker'])
def test_runtime_accepts_only_model_scope_and_expected_owner(release,service):
    original,item=before(service),target(service)
    release.runtime_invariant(original,after(release,original,item),item,'new')


@pytest.mark.parametrize('mutation,reason',[
    ('secret','runtime_environment_changed'),('flag','runtime_environment_changed'),
    ('host','host_mount_or_label_changed'),('mount','host_mount_or_label_changed'),
    ('command','application_configuration_changed'),('image','runtime_image_changed'),
    ('offersteady-global','released_compose_owner_changed'),('network','target_network_aliases_changed')])
def test_runtime_refuses_unrelated_drift(release,mutation,reason):
    original,item=before(),target()
    changed=after(release,original,item)
    if mutation=='secret':changed['Config']['Env'].append('NEW_SECRET=unexpected')
    elif mutation=='flag':changed['Config']['Env']=[x.replace('FEATURE_FLAG=unchanged','FEATURE_FLAG=changed') for x in changed['Config']['Env']]
    elif mutation=='host':changed['HostConfig']['ReadonlyRootfs']=True
    elif mutation=='mount':changed['Mounts']=[{'Destination':'/unexpected'}]
    elif mutation=='command':changed['Config']['Cmd']=['different']
    elif mutation=='image':changed['Image']='sha256:'+'2'*64
    elif mutation=='offersteady-global':changed['Config']['Labels']['com.docker.compose.service']='another-service'
    elif mutation=='network':changed['NetworkSettings']['Networks']['offersteady-global_default']['Aliases'].append('unexpected')
    with pytest.raises(release.GuardError,match='^'+reason+'$'):
        release.runtime_invariant(original,changed,item,'new')


def test_schema_hash_uses_original_ascii_canonical_contract(release):
    value={'paths':{'/api/v1/test':{'description':'合成测试'}}}
    expected={'paths':['/api/v1/test'],'schemaSha256':release.digest(release.canonical(value))}
    release.check_schema(value,expected)
    with pytest.raises(release.GuardError,match='existing_api_paths_changed'):
        release.check_schema({'paths':{}},expected)


def test_inventory_preserves_migration_and_dependency_inputs(release,monkeypatch,tmp_path):
    import subprocess
    import sys
    paths=['apps/backend/app/synthetic.py','ai/prompts/synthetic.md',
           'apps/backend/migrations/versions/0001_synthetic.sql','apps/backend/pyproject.toml']
    for relative in paths:
        file=tmp_path/relative
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text('synthetic fixture')
    def local_inventory(command):
        code=command[-1].replace("Path('/app')",'Path('+repr(str(tmp_path))+')')
        return subprocess.run([sys.executable,'-c',code],capture_output=True,check=True)
    monkeypatch.setattr(release,'run',local_inventory)
    result=release.inventory('backend')
    assert set(result)==set(paths)


def test_gate_rejects_unknown_fields_even_when_all_known_counts_are_zero(release):
    old=release.H.ROOT
    release.H.ROOT=release.SUPPORT
    try:
        fields,info=release.H.gate_contract('resume_optimizer_idle_gate.py')
        counts={key:0 for key in fields|info}
        assert release.H.gate_is_idle('resume_optimizer_idle_gate.py',counts)
        with pytest.raises(release.GuardError,match='invalid_gate_aggregate'):
            release.H.normalize_gate('resume_optimizer_idle_gate.py',counts|{'unexpected':0})
        counts['resumeOptimizerEffectiveClaims']=1
        assert not release.H.gate_is_idle('resume_optimizer_idle_gate.py',counts)
    finally:release.H.ROOT=old


def test_switch_never_changes_container_after_busy_gate(release,monkeypatch):
    calls=[]
    monkeypatch.setattr(release,'check_plan',lambda:{} )
    monkeypatch.setattr(release,'check_files',lambda *args:calls.append('files'))
    monkeypatch.setattr(release,'targets_owned',lambda *args,**kwargs:calls.append('owner'))
    def busy(*args):
        calls.append('busy')
        raise release.GuardError('protected_user_work_cutover_deferred')
    monkeypatch.setattr(release,'idle_gates',busy)
    monkeypatch.setattr(release,'run',lambda *args,**kwargs:pytest.fail('production mutation reached'))
    with pytest.raises(release.GuardError,match='protected_user_work_cutover_deferred'):
        release.switch({'targets':{}},{},{},'backend','new')
    assert calls==['files','owner','busy']


def test_switch_never_changes_container_after_tcp_activity(release,monkeypatch):
    monkeypatch.setattr(release,'check_plan',lambda:{} )
    monkeypatch.setattr(release,'check_files',lambda *args:None)
    monkeypatch.setattr(release,'targets_owned',lambda *args,**kwargs:None)
    monkeypatch.setattr(release,'idle_gates',lambda *args:None)
    def busy(*args,**kwargs):raise release.GuardError('protected_user_work_cutover_deferred')
    monkeypatch.setattr(release,'tcp_gate',busy)
    monkeypatch.setattr(release,'run',lambda *args,**kwargs:pytest.fail('production mutation reached'))
    with pytest.raises(release.GuardError,match='protected_user_work_cutover_deferred'):
        release.switch({'targets':{}},{},{},'web','new')


def test_effective_settings_checks_do_not_bootstrap_app_or_business_repositories():
    source=SCRIPT.read_text()
    assert 'from app.deps' not in source
    assert 'app.main' not in source
    assert 'Settings(_env_file=None)' in source
    assert 'schema_migrations' not in source
    assert 'terminate' not in source
    assert 'kill' not in source


def test_created_owner_is_journaled_before_failed_configuration_acceptance(release,monkeypatch):
    original,item=before(),target()
    candidate=after(release,original,item)
    candidate['Config']['Env'].append('UNEXPECTED=bad-candidate')
    progress={}
    saved=[]
    monkeypatch.setattr(release,'save',lambda name,value:saved.append((name,deepcopy(value))))
    release.record_created_owner(item,'new',original['Id'],candidate,progress)
    assert saved[0][0]=='progress.json'
    assert progress['backend']['id']==candidate['Id']
    assert progress['backend']['ownershipSignature']==release.ownership_signature(candidate)
    with pytest.raises(release.GuardError,match='runtime_environment_changed'):
        release.runtime_invariant(original,candidate,item,'new')


@pytest.mark.parametrize('change',['wrong-project','wrong-env-files','same-id','wrong-image'])
def test_unknown_creation_never_gains_recovery_ownership(release,monkeypatch,change):
    original,item=before(),target()
    candidate=after(release,original,item)
    if change=='wrong-project':candidate['Config']['Labels']['com.docker.compose.project']='other'
    elif change=='wrong-env-files':candidate['Config']['Labels']['com.docker.compose.project.environment_file']='/other/.env'
    elif change=='same-id':candidate['Id']=original['Id']
    elif change=='wrong-image':candidate['Image']='sha256:'+'2'*64
    monkeypatch.setattr(release,'save',lambda *args:pytest.fail('unproven owner recorded'))
    with pytest.raises(release.GuardError):
        release.record_created_owner(item,'new',original['Id'],candidate,{})


def recorded(release,original,item,monkeypatch):
    candidate=after(release,original,item)
    monkeypatch.setattr(release,'save',lambda *args:None)
    progress={}
    release.record_created_owner(item,'new',original['Id'],candidate,progress)
    return candidate,progress


def test_owned_candidate_that_exits_has_recovery_only_stopped_process_proof(release,monkeypatch):
    original,item=before(),target()
    candidate,progress=recorded(release,original,item,monkeypatch)
    candidate['State'].update(Running=False,Pid=0,Status='exited')
    candidate['NetworkSettings']['Networks']['offersteady-global_default']['IPAddress']=''
    monkeypatch.setattr(release,'inspect',lambda name:deepcopy(candidate))
    manifest={'targets':{'backend':item}}
    with pytest.raises(release.GuardError,match='released_container_signature_changed'):
        release.targets_owned(manifest,progress)
    release.targets_owned(manifest,progress,recovery=True)


@pytest.mark.parametrize('change',['config','mount','external-id','live-restart-without-proof'])
def test_recovery_never_ignores_unrelated_drift(release,monkeypatch,change):
    original,item=before(),target()
    candidate,progress=recorded(release,original,item,monkeypatch)
    if change=='config':candidate['Config']['Cmd']=['outside-change']
    elif change=='mount':candidate['Mounts']=[{'Destination':'/outside'}]
    elif change=='external-id':candidate['Id']='c'*64
    else:candidate['State']['StartedAt']='2026-10-21T13:00:00Z'
    monkeypatch.setattr(release,'inspect',lambda name:deepcopy(candidate))
    with pytest.raises(release.GuardError):
        release.targets_owned({'targets':{'backend':item}},progress,recovery=True)


def test_atomic_journal_write_keeps_previous_json_if_replace_fails(release,tmp_path,monkeypatch):
    path=tmp_path/'progress.json'
    path.write_text('{"previous":true}\n')
    def failed(*args):raise OSError('synthetic interruption before atomic replace')
    monkeypatch.setattr(release.os,'replace',failed)
    with pytest.raises(OSError):release.atomic_write_json(path,{'next':True})
    assert json.loads(path.read_text())=={'previous':True}
    assert sorted(file.name for file in tmp_path.iterdir())==['progress.json']


def test_implicit_worker_image_accepts_only_pinned_original_tag(release,monkeypatch):
    source={'services':{'material-worker':{'build':{'context':'original'}}}}
    container=before('material-worker')
    container['Config']['Image']='offersteady-global-material-worker'
    monkeypatch.setattr(release.H,'inspect',lambda name:{'Id':container['Image']})
    release.H.assert_rendered_image(source,container,'material-worker')
    monkeypatch.setattr(release.H,'inspect',lambda name:{'Id':'sha256:'+'2'*64})
    with pytest.raises(release.GuardError,match='implicit_compose_image_tag_drift'):
        release.H.assert_rendered_image(source,container,'material-worker')


@pytest.mark.parametrize('reason,auto_recover',[
    ('runtime_environment_changed',True),('target_health_failed',True),
    ('released_source_drift',False),('non_target_nginx_input_tree_changed',False),
    ('non_target_container_changed',False),('protected_user_work_cutover_deferred',False)])
def test_cutover_failure_distinguishes_owned_failure_from_external_drift(release,monkeypatch,tmp_path,reason,auto_recover):
    monkeypatch.setattr(release,'ROOT',tmp_path)
    monkeypatch.setattr(release,'check_plan',lambda:{})
    monkeypatch.setattr(release,'read_json',lambda path:{})
    monkeypatch.setattr(release,'reconcile_intent',lambda *args:None)
    monkeypatch.setattr(release,'verify_runtime',lambda *args,**kwargs:None)
    monkeypatch.setattr(release,'idle_gates',lambda *args:None)
    monkeypatch.setattr(release,'tcp_gate',lambda *args:None)
    monkeypatch.setattr(release,'save',lambda *args:None)
    def fail_switch(*args,**kwargs):raise release.GuardError(reason)
    monkeypatch.setattr(release,'switch',fail_switch)
    recovered=[]
    monkeypatch.setattr(release,'rollback',lambda:recovered.append(True))
    expected='cutover_failed_rollback_succeeded' if auto_recover else reason
    with pytest.raises(release.GuardError,match='^'+expected+'$'):
        release.deploy()
    assert bool(recovered) is auto_recover


def source_tar(scope, files, *, special=None):
    output=io.BytesIO()
    parent=Path(scope).parent
    with tarfile.open(fileobj=output,mode='w') as archive:
        for path,data in files.items():
            if path == scope or path.startswith(scope+'/'):
                member=tarfile.TarInfo(str(Path(path).relative_to(parent)))
                member.size=len(data)
                archive.addfile(member,io.BytesIO(data))
        if special:
            member=tarfile.TarInfo(special)
            member.type=tarfile.SYMTYPE
            member.linkname='/outside'
            archive.addfile(member)
    return output.getvalue()


@pytest.mark.parametrize('tamper',[None,'changed','extra','symlink','escape'])
def test_stopped_inventory_reads_all_four_exact_source_scopes_without_starting(release,monkeypatch,tamper):
    scopes=('apps/backend/app','ai/prompts','apps/backend/migrations','apps/backend/pyproject.toml')
    files={'apps/backend/app/a.py':b'synthetic python','ai/prompts/a.md':b'synthetic prompt',
        'apps/backend/migrations/0001.sql':b'synthetic migration','apps/backend/pyproject.toml':b'synthetic dependencies'}
    expected={key:release.digest(value) for key,value in files.items()}
    if tamper=='changed':files['apps/backend/app/a.py']=b'different'
    if tamper=='extra':files['apps/backend/app/extra.py']=b'extra'
    calls=[]
    def docker_copy(command,**kwargs):
        assert command[:2]==['docker','cp'] and command[-1]=='-'
        calls.append(command)
        scope=command[2].split(':/app/',1)[1]
        special=('app/symlink' if tamper=='symlink' else '../escape') if scope==scopes[0] and tamper in {'symlink','escape'} else None
        return SimpleNamespace(stdout=source_tar(scope,files,special=special))
    monkeypatch.setattr(release,'run',docker_copy)
    if tamper in {'symlink','escape'}:
        with pytest.raises(release.GuardError):
            release.stopped_source_inventory({'Id':'synthetic-stopped'})
    else:
        actual=release.stopped_source_inventory({'Id':'synthetic-stopped'})
        assert (actual==expected) is (tamper is None)
        assert len(calls)==4


def test_tcp_gate_rejects_same_id_host_config_change_before_any_probe(release,monkeypatch,tmp_path):
    original,item=before(),target()
    candidate,progress=recorded(release,original,item,monkeypatch)
    candidate['HostConfig']['ReadonlyRootfs']=True
    monkeypatch.setattr(release,'inspect',lambda name:deepcopy(candidate))
    monkeypatch.setattr(release.subprocess,'run',lambda *args,**kwargs:pytest.fail('TCP probe must not accept changed static owner'))
    with pytest.raises(release.GuardError,match='released_container_signature_changed'):
        release.tcp_gate({'targets':{'backend':item}},progress)


@pytest.mark.parametrize('stopped_service',['material-worker','backend'])
@pytest.mark.parametrize('tamper_source',[False,True])
def test_full_rollback_of_stopped_owned_candidate_hashes_real_tar_and_restores_worker_first(
        release,monkeypatch,tmp_path,stopped_service,tamper_source):
    """Real ownership/source/TCP/switch/rollback flow over a synthetic Docker transport."""
    services=('backend','material-worker')
    originals,targets,current,files,baseline_settings={},{},{},{},{}
    source={'apps/backend/app/services/document_processing.py':b'old synthetic source',
        'ai/prompts/a.md':b'synthetic prompt','apps/backend/migrations/0001.sql':b'synthetic migration',
        'apps/backend/pyproject.toml':b'synthetic dependencies'}
    new_source=source|{release.PATCH_PATH:b'new synthetic source'}
    plan={'baselines':{},'sourceOverlays':{},'openapiBefore':{}}
    monkeypatch.setattr(release,'ROOT',tmp_path)
    monkeypatch.setattr(release.H,'ROOT',tmp_path)
    progress={}
    for index,service in enumerate(services):
        original=before(service)
        original['Id']=('a' if index==0 else 'd')*64
        original['Image']='sha256:'+str(index+1)*64
        original['Config']['Hostname']=original['Id'][:12]
        original['NetworkSettings']['Networks']['offersteady-global_default'].update(
            Aliases=[service,'offersteady-global-'+service+'-1',original['Id'][:12]],IPAddress='10.0.0.'+str(index+2))
        if service=='backend':original['State']['Health']={'Status':'healthy'}
        item=target(service)
        item.update(newImage='sha256:'+str(index+3)*64,rollbackImage=original['Image'],
                    beforeId=original['Id'],baseImage=original['Image'])
        value=after(release,original,item)
        value['Id']=('b' if index==0 else 'e')*64
        value['Image']=item['newImage']
        value['Config']['Hostname']=value['Id'][:12]
        value['NetworkSettings']['Networks']['offersteady-global_default']['Aliases']=[service,item['container'],value['Id'][:12]]
        originals[service],targets[service],current[service]=original,item,value
        files[service]=dict(new_source)
        baseline_settings[service]={release.SETTINGS_KEYS[key]:release.environment(original)[key] for key in release.MODEL_KEYS[service]}
        plan['baselines'][service]={'inventory':{key:release.digest(data) for key,data in source.items()}}
        plan['sourceOverlays'][service]={'afterSha256':release.digest(new_source[release.PATCH_PATH])}
        (tmp_path/service).mkdir()
        release.save(service+'/container-before.json',original)
        release.save(service+'/settings-before.private.json',baseline_settings[service])
        release.record_created_owner(item,'new',original['Id'],value,progress)
    stopped=current[stopped_service]
    stopped['State'].update(Running=False,Pid=0,Status='exited')
    stopped['NetworkSettings']['Networks']['offersteady-global_default']['IPAddress']=''
    if tamper_source:files[stopped_service][release.PATCH_PATH]=b'outside writable-layer change'
    proxies={}
    for service in ('web','admin'):
        value=before(service)
        value['Id']=(service[0]*64)
        proxies['offersteady-global-'+service+'-1']=value
    trees={'/etc/nginx/nginx.conf':'sha256:'+release.digest(b'nginx'),
        '/etc/nginx/conf.d/default.conf':'sha256:'+release.digest(b'config')}
    static={'index.html':release.digest(b'html')}
    manifest={'targets':targets,'nonTargets':{name:release.H.container_signature(value) for name,value in proxies.items()},
        'proxyInputTrees':{name:trees for name in proxies},'webStaticBefore':static,
        'proxyStaticBackendUpstreams':{name:True for name in proxies}}
    api={'paths':{'/api/v1/synthetic':{}}}
    plan['openapiBefore']={'paths':list(api['paths']),'schemaSha256':release.digest(release.canonical(api))}
    release.save('prepared.json',manifest)
    operations=[]
    def inspect(name):
        for service,value in current.items():
            if name in (value['Id'],targets[service]['container']):return deepcopy(value)
        if name in proxies:return deepcopy(proxies[name])
        pytest.fail('unknown synthetic inspect target')
    def run(command,**kwargs):
        if command[:2]==['docker','compose']:
            service=command[-1]
            assert targets[service]['rollbackOverlay'] in command
            assert '--no-build' in command and '--no-deps' in command and '--pull' in command and 'never' in command
            operations.append(('restore',service))
            value=after(release,originals[service],targets[service],'rollback')
            value['Id']=('c' if service=='backend' else 'f')*64
            value['Image']=targets[service]['rollbackImage']
            value['Config']['Hostname']=value['Id'][:12]
            value['NetworkSettings']['Networks']['offersteady-global_default'].update(
                Aliases=[service,targets[service]['container'],value['Id'][:12]],IPAddress='10.0.0.99' if service=='backend' else '10.0.0.3')
            current[service]=value
            files[service]=dict(source)
            return SimpleNamespace(stdout=b'')
        if command[:2]==['docker','cp']:
            value=inspect(command[2].split(':/app/',1)[0])
            service=next(key for key,value0 in current.items() if value0['Id']==value['Id'])
            assert value['State']['Running'] is False
            operations.append(('source-tar',service))
            return SimpleNamespace(stdout=source_tar(command[2].split(':/app/',1)[1],files[service]))
        if command[:3]==['docker','ps','-a']:
            return SimpleNamespace(stdout=('\n'.join([*proxies,*[item['container'] for item in targets.values()]])+'\n').encode())
        assert command[:2]==['docker','exec']
        name=command[4] if command[2:4]==['-w','/app/apps/backend'] else command[2]
        if name in proxies:
            if command[3:]==['nginx','-t']:operations.append(('nginx-test',name));return SimpleNamespace(stdout=b'')
            if command[3:]==['nginx','-s','reload']:operations.append(('nginx-reload',name));return SimpleNamespace(stdout=b'')
            if 'find .' in command[-1]:return SimpleNamespace(stdout=(static['index.html']+'  ./index.html\n').encode())
            return SimpleNamespace(stdout=('\n'.join(value.removeprefix('sha256:')+'  '+key for key,value in trees.items())+'\n').encode())
        service=next(key for key,item in targets.items() if name in (item['container'],current[key]['Id']))
        assert current[service]['State']['Running'], 'stopped source collection must not use docker exec'
        if 'Settings(_env_file=None)' in command[-1]:
            value=dict(baseline_settings[service])
            if current[service]['Image']==targets[service]['newImage']:
                value.update({release.SETTINGS_KEYS[key]:release.MODEL for key in release.MODEL_KEYS[service]})
            return SimpleNamespace(stdout=json.dumps(value).encode())
        if 'openapi.json' in command[-1]:return SimpleNamespace(stdout=json.dumps(api).encode())
        return SimpleNamespace(stdout=json.dumps({key:release.digest(data) for key,data in files[service].items()}).encode())
    namespace=release.digest(b'synthetic network namespace')
    def tcp_probe(*args,**kwargs):
        operations.append(('tcp',None))
        return SimpleNamespace(returncode=0,stdout=json.dumps({'passed':True,'atMs':int(time.time()*1000),
            'establishedPort8000':0,'tablesRead':2,'scannedRows':0,'scope':'container_tcp8000_established_only',
            'networkNamespaceSha256':namespace}).encode())
    monkeypatch.setattr(release,'BASES',{key:(value['Id'],value['Image']) for key,value in originals.items()})
    monkeypatch.setattr(release,'inspect',inspect)
    monkeypatch.setattr(release,'run',run)
    monkeypatch.setattr(release,'check_plan',lambda:plan)
    monkeypatch.setattr(release,'check_files',lambda *args:release.check_non_targets(manifest))
    monkeypatch.setattr(release,'idle_gates',lambda *args:operations.append(('all-seven-gates',None)))
    monkeypatch.setattr(release,'public_checks',lambda *args:operations.append(('public',None)))
    monkeypatch.setattr(release.H,'host_network_namespace',lambda *args:namespace)
    monkeypatch.setattr(release.subprocess,'run',tcp_probe)
    if tamper_source:
        with pytest.raises(release.GuardError,match='runtime_source_drift'):
            release.rollback()
        assert not [operation for operation in operations if operation[0]=='restore']
        return
    release.rollback()
    assert [entry for entry in operations if entry[0]=='restore']==[('restore','material-worker'),('restore','backend')]
    assert sum(entry==('source-tar',stopped_service) for entry in operations)>=4
    assert len([entry for entry in operations if entry[0]=='nginx-reload'])==2
    assert all(current[key]['Image']==originals[key]['Image'] for key in services)
    assert json.loads((tmp_path/'rollback-result.json').read_text())['restored'] is True
