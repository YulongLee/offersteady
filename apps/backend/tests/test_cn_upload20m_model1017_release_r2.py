"""Synthetic regression tests for bounded CN production release guards."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'scripts/release_cn_upload20m_model1017_v2.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def release():
    return load(SCRIPT, 'test_cn_upload20m_release_r2')


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
        'HostConfig': {'NetworkMode': 'compose_default', 'ReadonlyRootfs': False},
        'Mounts': [], 'RestartCount': 0,
        'State': {'Running':True,'StartedAt':'2026-10-21T12:00:00Z','Pid':100,
                  'Status':'running','Restarting':False,'Dead':False,'Paused':False},
        'NetworkSettings': {'Networks': {'compose_default': {
            'Aliases': [service, 'compose-'+service+'-1', 'a'*12], 'IPAMConfig': None,
            'Links': None, 'DriverOpts': None, 'GwPriority': 0}}}}


def target(service='backend'):
    return {'service':service,'newImage':'sha256:'+'1'*64,'rollbackImage':'sha256:'+'1'*64,
        'frozenComposeFiles':['/release/'+service+'/compose.before'],
        'frozenEnvFiles':['/release/'+service+'/env.before'],
        'newOverlay':'/release/'+service+'/new.compose.json',
        'rollbackOverlay':'/release/'+service+'/rollback.compose.json',
        'composeDirectory':'/original/'+service,'container':'compose-'+service+'-1'}


def after(release, original, item, kind='new'):
    value=deepcopy(original)
    value['Id']='b'*64
    value['Config']['Hostname']='b'*12
    value['Config']['Env']=[key+'='+v for key,v in release.expected_environment(original,item['service'],kind).items()]
    value['Config']['Labels'].update({'com.docker.compose.project':'compose',
        'com.docker.compose.service':item['service'],
        'com.docker.compose.project.config_files':','.join(item['frozenComposeFiles']+[item[kind+'Overlay']]),
        'com.docker.compose.project.environment_file':','.join(item['frozenEnvFiles']),
        'com.docker.compose.project.working_dir':item['composeDirectory']})
    value['NetworkSettings']['Networks']['compose_default']['Aliases']=[item['service'],'compose-'+item['service']+'-1','b'*12]
    return value


@pytest.mark.parametrize('service,count',[('backend',4),('material-worker',3),('web',0)])
def test_only_the_approved_model_keys_change(release, service, count):
    original=before(service)
    changed=release.expected_environment(original,service,'new')
    old=release.environment(original)
    assert sum(changed[k]!=old[k] for k in changed)==count
    assert changed['UNCHANGED_SECRET']==old['UNCHANGED_SECRET']
    assert changed['FEATURE_FLAG']==old['FEATURE_FLAG']
    assert release.expected_environment(original,service,'rollback')==old


@pytest.mark.parametrize('service',['backend','material-worker','web'])
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


@pytest.mark.parametrize('service',['backend','material-worker','web'])
def test_runtime_accepts_only_model_scope_and_expected_owner(release,service):
    original,item=before(service),target(service)
    release.runtime_invariant(original,after(release,original,item),item,'new')


@pytest.mark.parametrize('mutation,reason',[
    ('secret','runtime_environment_changed'),('flag','runtime_environment_changed'),
    ('host','host_mount_or_label_changed'),('mount','host_mount_or_label_changed'),
    ('command','application_configuration_changed'),('image','runtime_image_changed'),
    ('compose','released_compose_owner_changed'),('network','target_network_aliases_changed')])
def test_runtime_refuses_unrelated_drift(release,mutation,reason):
    original,item=before(),target()
    changed=after(release,original,item)
    if mutation=='secret':changed['Config']['Env'].append('NEW_SECRET=unexpected')
    elif mutation=='flag':changed['Config']['Env']=[x.replace('FEATURE_FLAG=unchanged','FEATURE_FLAG=changed') for x in changed['Config']['Env']]
    elif mutation=='host':changed['HostConfig']['ReadonlyRootfs']=True
    elif mutation=='mount':changed['Mounts']=[{'Destination':'/unexpected'}]
    elif mutation=='command':changed['Config']['Cmd']=['different']
    elif mutation=='image':changed['Image']='sha256:'+'2'*64
    elif mutation=='compose':changed['Config']['Labels']['com.docker.compose.service']='another-service'
    elif mutation=='network':changed['NetworkSettings']['Networks']['compose_default']['Aliases'].append('unexpected')
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


class Rows:
    def __init__(self,rows):self.rows=iter(rows)
    def __enter__(self):return self
    def __exit__(self,*args):return None
    def execute(self,*args):
        self.next=next(self.rows)
        return self
    def fetchone(self):return self.next


@pytest.mark.parametrize('status_active,claimed,usage_reserved,blocked',[
    (0,0,0,False),(0,1,0,True),(1,0,0,True),(0,0,1,True)])
def test_optimizer_protects_claims_and_reserved_charges_including_terminal_rows(release,status_active,claimed,usage_reserved,blocked):
    gate=load(release.SUPPORT/'resume_optimizer_idle_gate.py','test_cn_optimizer_release_gate')
    rows=[('cn_resume_optimizer_jobs','cn_resume_optimizer_usage'),(gate.MIGRATION_SHA,),
          (status_active,0),(claimed,),(usage_reserved,0)]
    counts=gate.collect_counts(SimpleNamespace(database_url='synthetic'),connect=lambda *a,**k:Rows(rows))
    assert bool(any(counts.values())) is blocked
    assert counts['resumeOptimizerEffectiveClaims']==claimed


def test_unknown_optimizer_schema_fails_closed(release):
    gate=load(release.SUPPORT/'resume_optimizer_idle_gate.py','test_cn_optimizer_unknown_gate')
    counts=gate.collect_counts(SimpleNamespace(database_url='synthetic'),connect=lambda *a,**k:Rows([(None,'cn_resume_optimizer_usage'),None]))
    assert counts['resumeOptimizerReadFailures']==1


@pytest.mark.parametrize('usage,index,blocked',[(0,0,False),(1,0,True),(0,1,True)])
def test_financial_gate_protects_unfinished_reservations(release,usage,index,blocked):
    gate=load(release.SUPPORT/'financial_idle_gate.py','test_cn_financial_release_gate')
    counts=gate.collect_counts(SimpleNamespace(database_url='synthetic',billing_usage_reservation_ttl_seconds=60),now_ms=1000000,
        orphan_before_process_ms=900000,connect=lambda *a,**k:Rows([(usage,0,0),(index,0),(0,0),(0,)]))
    assert bool(any(counts.values())) is blocked


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
    candidate['NetworkSettings']['Networks']['compose_default']['IPAddress']=''
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


def test_required_optimizer_schema_missing_is_not_empty_work(release):
    gate=load(release.SUPPORT/'resume_optimizer_idle_gate.py','test_cn_optimizer_missing_gate')
    counts=gate.collect_counts(SimpleNamespace(database_url='synthetic'),connect=lambda *a,**k:Rows([(None,None),None]))
    assert counts['resumeOptimizerReadFailures']==1


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
    container['Config']['Image']='compose-material-worker'
    monkeypatch.setattr(release.H,'inspect',lambda name:{'Id':container['Image']})
    release.H.assert_rendered_image(source,container,'material-worker')
    monkeypatch.setattr(release.H,'inspect',lambda name:{'Id':'sha256:'+'2'*64})
    with pytest.raises(release.GuardError,match='implicit_compose_image_tag_drift'):
        release.H.assert_rendered_image(source,container,'material-worker')


@pytest.mark.parametrize('reason,auto_recover',[
    ('runtime_environment_changed',True),('target_health_failed',True),
    ('released_source_or_static_drift',False),('runtime_nginx_input_tree_changed',False),
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


@pytest.mark.parametrize('interrupted',[False,True])
def test_real_controller_recovery_after_bad_candidate_or_interrupted_owner_journal(release,monkeypatch,tmp_path,interrupted):
    """Exercise the real switch/reconcile/rollback/verify control flow offline."""
    import socket
    original,item=before(),target()
    original['State']['Health']={'Status':'healthy'}
    world={'current':deepcopy(original),'checks':[]}
    source={'synthetic-runtime-input':'1'*64}
    nginx=b'synthetic unchanged nginx'
    schema_value={'paths':{'/api/v1/synthetic':{}}}
    plan={'baselines':{'backend':{'inventory':source}},'nginxBeforeSha256':release.digest(nginx),
        'nginxAfterSha256':release.digest(b'new'),'openapiBefore':{'paths':schema_value['paths'],
        'schemaSha256':release.digest(release.canonical(schema_value))}}
    manifest={'targets':{'backend':item},'nginxInputsBefore':{
        '/etc/nginx/conf.d/default.conf':'sha256:'+release.digest(nginx)},'nonTargets':{},'privateFiles':{}}
    def candidate(kind):
        value=after(release,original,item,kind)
        value['Id']=('b' if kind=='new' else 'c')*64
        value['Config']['Hostname']=value['Id'][:12]
        value['NetworkSettings']['Networks']['compose_default']['Aliases']=['backend','compose-backend-1',value['Id'][:12]]
        if kind=='new':value['Config']['Env'].append('UNEXPECTED=synthetic-rejection')
        return value
    def simulated_compose(args,**kwargs):
        assert args[:2]==['docker','compose']
        world['current']=candidate('rollback' if item['rollbackOverlay'] in args else 'new')
        return SimpleNamespace(stdout=b'')
    def settings_value(service):
        return {key:release.environment(world['current'])[env] for env,key in release.SETTINGS_KEYS.items()}
    baseline={key:release.environment(original)[env] for env,key in release.SETTINGS_KEYS.items()}
    monkeypatch.setattr(release,'ROOT',tmp_path)
    monkeypatch.setattr(release.H,'ROOT',tmp_path)
    (tmp_path/'backend').mkdir()
    release.save('backend/container-before.json',original)
    release.save('backend/settings-before.private.json',baseline)
    release.save('prepared.json',manifest)
    monkeypatch.setattr(release,'check_plan',lambda:plan)
    monkeypatch.setattr(release,'check_files',lambda *args:None)
    monkeypatch.setattr(release,'inspect',lambda name:deepcopy(world['current']))
    monkeypatch.setattr(release,'idle_gates',lambda *args:world['checks'].append(('all-work-gates',None)))
    monkeypatch.setattr(release,'tcp_gate',lambda *args,**kwargs:world['checks'].append(('tcp',kwargs.get('recovery'))))
    monkeypatch.setattr(release,'run',simulated_compose)
    monkeypatch.setattr(release,'inventory',lambda *args,**kwargs:source)
    monkeypatch.setattr(release,'settings',settings_value)
    monkeypatch.setattr(release,'schema',lambda:schema_value)
    monkeypatch.setattr(release,'nginx_inputs',lambda **kwargs:manifest['nginxInputsBefore'])
    monkeypatch.setattr(release.H,'read_container',lambda *args:nginx)
    monkeypatch.setattr(release,'BASES',{'backend':(original['Id'],original['Image'])})
    monkeypatch.setattr(release,'public_checks',lambda *args:world['checks'].append(('publicAcceptance',None)))
    def forbidden(*args,**kwargs):pytest.fail('network forbidden in synthetic recovery test')
    monkeypatch.setattr(socket,'socket',forbidden)
    if interrupted:
        release.save('switch-intent.json',{'service':'backend','kind':'new','beforeId':original['Id'],'previousProgress':{}})
        world['current']=candidate('new')
    else:
        with pytest.raises(release.GuardError,match='^runtime_environment_changed$'):
            release.switch(manifest,plan,{},'backend','new')
        assert json.loads((tmp_path/'progress.json').read_text())['backend']['id']=='b'*64
    release.rollback()
    progress=json.loads((tmp_path/'progress.json').read_text())
    assert progress['backend']['kind']=='rollback' and progress['backend']['id']=='c'*64
    assert release.environment(world['current'])==release.environment(original)
    assert ('tcp',True) in world['checks']
    assert ('all-work-gates',None) in world['checks']
    assert ('publicAcceptance',None) in world['checks']


@pytest.mark.parametrize('kind,status,created,birth,ttl,active,info,unknown',[
    ('answer','reserved',4_999_999,5_000_000,1800,0,1,0),
    ('answer','reserved',5_000_000,5_000_000,1800,1,0,0),
    ('answer','reserved',8_200_000,9_000_000,1800,1,0,0),
    ('answer','reserved',8_199_999,9_000_000,1800,0,1,0),
    ('answer','reserved',9_940_000,9_999_999,1,1,0,0),
    ('answer','reserved',9_939_999,9_999_999,1,0,1,0),
    ('answer','reserved',0,5_000_000,1800,1,0,0),
    ('answer','reserved',-1,5_000_000,1800,1,0,0),
    ('answer','reserved',None,5_000_000,1800,1,0,0),
    ('answer','reserved',10_000_001,5_000_000,1800,1,0,0),
    ('web_answer','reserved',1,5_000_000,1800,1,0,0),
    ('screenshot_answer','reserved',1,5_000_000,1800,1,0,0),
    ('realtime_minute','reserved',1,5_000_000,1800,1,0,0),
    ('written_exam_entry','reserved',1,5_000_000,1800,1,0,0),
    ('unrecognized','reserved',1,5_000_000,1800,1,0,0),
    ('answer','unknown-status',1,5_000_000,1800,0,0,1),
    ('answer',None,1,5_000_000,1800,0,0,1),
    ('answer','settled',1,5_000_000,1800,0,0,0),
])
def test_exact_financial_sql_distinguishes_orphan_inventory_without_writes(release,kind,status,created,birth,ttl,active,info,unknown):
    import sqlite3
    gate=load(release.SUPPORT/'financial_idle_gate.py','test_cn_financial_r2_predicate')
    connection=sqlite3.connect(':memory:')
    connection.executescript('CREATE TABLE billing_usage_reservations (status TEXT,usage_kind TEXT,created_at_ms INTEGER); CREATE TABLE billing_index_reservations(status TEXT); CREATE TABLE billing_checkout_orders(status TEXT,expires_at_ms INTEGER); CREATE TABLE billing_payment_callback_events(completed_at_ms INTEGER,last_received_at_ms INTEGER);')
    connection.execute('INSERT INTO billing_usage_reservations VALUES (?,?,?)',(status,kind,created))
    previous_changes=connection.total_changes
    class ReadOnlyAdapter:
        def __enter__(self):return self
        def __exit__(self,*args):return None
        def execute(self,sql,args=()):return connection.execute(sql.replace('%s','?'),args)
    try:
        counts=gate.collect_counts(SimpleNamespace(database_url='synthetic',billing_usage_reservation_ttl_seconds=ttl),
            now_ms=10_000_000,orphan_before_process_ms=birth,connect=lambda *a,**k:ReadOnlyAdapter())
        assert counts['financialReadFailures']==0
        assert counts['unfinishedUsageReservations']==active
        assert counts['historicalOrphanAnswerReservations']==info
        assert counts['unknownUsageReservationStates']==unknown
        assert connection.total_changes==previous_changes
    finally:connection.close()


@pytest.mark.parametrize('birth',[None,0,-1,True,'5000000',10_000_001])
def test_financial_orphan_context_missing_or_invalid_fails_closed(release,birth):
    gate=load(release.SUPPORT/'financial_idle_gate.py','test_cn_financial_r2_missing_context')
    counts=gate.collect_counts(SimpleNamespace(database_url='synthetic',billing_usage_reservation_ttl_seconds=1800),
        now_ms=10_000_000,orphan_before_process_ms=birth,connect=lambda *args,**kwargs:pytest.fail('invalid context queried data'))
    assert counts['financialReadFailures']==1


def test_financial_information_is_explicit_and_does_not_disable_other_protection(release):
    old=release.H.ROOT
    release.H.ROOT=release.SUPPORT
    try:
        protected,informational=release.H.gate_contract('financial_idle_gate.py')
        assert informational=={'historicalOrphanAnswerReservations'}
        counts={key:0 for key in protected|informational}
        counts['historicalOrphanAnswerReservations']=22
        assert release.H.gate_is_idle('financial_idle_gate.py',counts)
        release.H.normalize_gate('financial_idle_gate.py',counts)
        counts['unfinishedIndexReservations']=1
        assert not release.H.gate_is_idle('financial_idle_gate.py',counts)
        with pytest.raises(release.GuardError):
            release.H.normalize_gate('financial_idle_gate.py',counts|{'unrecognizedInfo':22})
    finally:release.H.ROOT=old


def test_original_backend_anchor_is_fixed_to_fresh_baseline_and_frozen_snapshot(release):
    value='2026-10-18T22:35:38.555217206Z'
    assert release.docker_started_at_ms(value)==1792362938555
    baseline={'startedAt':value}
    context=release.expected_orphan_context(baseline)
    plan={'baselines':{'backend':baseline},'orphanAnswerContext':context}
    manifest={'orphanAnswerContext':deepcopy(context)}
    snapshot={'Id':release.BASES['backend'][0],'State':{'StartedAt':value}}
    release.verify_orphan_context(plan,manifest,snapshot)
    manifest['orphanAnswerContext']['baselineBackendStartedAt']='2026-10-19T22:35:38.555217206Z'
    with pytest.raises(release.GuardError,match='original_process_anchor_drift'):
        release.verify_orphan_context(plan,manifest,snapshot)
    manifest['orphanAnswerContext']=deepcopy(context)
    snapshot['State']['StartedAt']='2026-10-19T22:35:38.555217206Z'
    with pytest.raises(release.GuardError,match='original_process_snapshot_anchor_drift'):
        release.verify_orphan_context(plan,manifest,snapshot)
