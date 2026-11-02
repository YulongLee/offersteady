"""Synthetic controller regressions; no Docker/SSH/network/model/database."""
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
from types import SimpleNamespace

import pytest


@pytest.fixture
def release(tmp_path,monkeypatch):
    path=Path(__file__).with_name('release_global_performance_companion_136.py')
    spec=importlib.util.spec_from_file_location('perf136_controller_test',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    monkeypatch.setattr(m,'ROOT',tmp_path)
    monkeypatch.setattr(m,'run',lambda *a,**k:pytest.fail('unexpected external command'))
    monkeypatch.setattr(m,'inspect',lambda *a,**k:pytest.fail('unexpected Docker inspect'))
    monkeypatch.setattr(m,'urlopen',lambda *a,**k:pytest.fail('unexpected public request'))
    monkeypatch.setattr(m.H,'run',lambda *a,**k:pytest.fail('unexpected helper command'))
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('unexpected subprocess'))
    m.bind_primitives()
    return m


def h(value):return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def plan(release):
    m=release;root=m.ROOT
    old={p:h('old '+p) for p in sorted(m.BACKEND_FILES|{m.MANIFEST})}
    old.update({f'apps/backend/app/synthetic_{i}.py':h(str(i)) for i in range(302-len(old))})
    new={**old,**{p:h('new '+p) for p in m.BACKEND_FILES},m.HISTORY:h('history')}
    rollback={**old,m.HISTORY:h('history'),'apps/backend/app/modules/web.py':h('compat web')}
    manifest={'version':1,'generatedAtMs':123456789,'entries':[]};proofs=[]
    for platform,arch in sorted(m.TARGETS):
        name=('OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe' if platform=='windows' else f'OfferSteady-Companion-Global-1.3.6-macOS-{arch}.dmg')
        entry={'id':platform+arch,'platform':platform,'architecture':arch,'version':'1.3.6','protocolVersion':'2.0',
               'fileName':name,'fileSizeBytes':1000,'sha256':h(name),'objectKey':f'global-desktop-releases/{platform}/{arch}/1.3.6/{name}',
               'distributionStatus':'published','developmentOnly':False,'publishedAtMs':manifest['generatedAtMs'],
               'signingStatus':'verified' if platform=='macos' else 'unsigned','notarized':platform=='macos',
               'minimumOs':'macOS 14.2+' if platform=='macos' else 'Windows 10 22H2+'}
        manifest['entries'].append(entry)
        proofs.append({k:entry[k] for k in ('platform','architecture','version','fileName','fileSizeBytes','sha256','objectKey')}|
                      {'objectReadbackVerified':True,'contentType':'application/x-apple-diskimage' if platform=='macos' else 'application/vnd.microsoft.portable-executable'})
    p=root/'input/global_desktop_release_manifest.json';p.parent.mkdir();p.write_text(json.dumps(manifest))
    new[m.MANIFEST]=rollback[m.MANIFEST]=m.digest(p.read_bytes())
    before_schema={'openapi':'3.1.0','paths':{m.NEXT_PATH:{'get':{'parameters':[{'in':'path','name':'device_id','required':True}],'responses':{'200':{}}}},'/existing':{'get':{}}},'components':{'schemas':{'Existing':{'type':'string'}}}}
    after_schema=deepcopy(before_schema)
    after_schema['paths'][m.NEXT_PATH]['get']['parameters'] += [{'in':'query','name':name,'required':False,'schema':{'anyOf':[{'type':'string'},{'type':'null'}]}} for name in ('sessionId','requestId')]
    schema_refs={}
    for key,value in [('openapiBefore',before_schema),('openapiAfter',after_schema)]:
        f=root/'input'/f'{key}.json';f.write_text(json.dumps(value))
        schema_refs[key]={'path':str(f.relative_to(root)),'schemaSha256':m.digest(m.canonical(value)),'pathCount':len(value['paths'])}
    web={'index.html':h('index'),'login.html':h('login'),'offersteady-global-build.json':h('build')}
    web.update({f'assets/existing{i}.js':h(str(i)) for i in range(235-len(web))})
    web_new={**web,'index.html':h('new index'),'offersteady-global-build.json':h('new build'),'assets/main-new.js':h('newjs')}
    support={}
    for name in {'controller.py','base_helpers.py','ownership_primitives.py','probe.py',*m.GATES,m.TCP_GATE}:
        f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('synthetic '+name);support[name]=m.digest(f.read_bytes())
    b={}
    for service,(cid,image) in m.BASES.items():
        b[service]={'id':cid,'image':image,'startedAt':'2026-10-21T17:40:06.734602223Z',
                    'signature':{'id':cid,'image':image,'startedAt':'2026-10-21T17:40:06.734602223Z'},
                    'inventory':old if service=='backend' else web,'settingsSha256':h('settings'),'settingsFields':1,'nginxSha256':h('nginx')}
    value={'releaseId':m.RELEASE,'baselines':b,'candidates':{
        'backend':{'image':'sha256:'+h('newbackend'),'rollbackImage':'sha256:'+h('rollbackbackend'),'inventory':new,'rollbackInventory':rollback},
        'web':{'image':'sha256:'+h('newweb'),'rollbackImage':'sha256:'+h('rollbackweb'),'inventory':web_new,'rollbackInventory':{**web,'assets/main-new.js':h('newjs')}}},
        'allowedBackend':{p:new[p] for p in m.BACKEND_FILES|{m.MANIFEST,m.HISTORY}},
        'allowedWebChanged':['index.html','offersteady-global-build.json'],
        'globalManifest':{'path':'input/global_desktop_release_manifest.json','sha256':new[m.MANIFEST]},
        'objectsReadback':proofs,'supportFiles':support,'publicRoutes':{'/':'index.html','/login':'index.html'},
        'nonTargets':{n:(deepcopy(m.LEGACY_STOPPED_SIGNATURE) if n==m.LEGACY_STOPPED_NAME else {'image':'sha256:'+h(n)})
                      for n in m.EXPECTED_NAMES-{m.PROJECT+'-'+s+'-1' for s in m.BASES}},**schema_refs}
    (root/'input.json').write_text(json.dumps(value));return value


def write_plan(m,plan):
    (m.ROOT/'input.json').write_text(json.dumps(plan))


def test_valid_plan_without_external_calls(release,plan):
    assert release.check_plan()==plan


@pytest.mark.parametrize('field,value',[
    ('id','f'*64),('image','sha256:'+'f'*64),('imageReference','unknown:latest'),
    ('running',True),('restartCount',1),('startedAt','2026-11-02T00:00:00Z'),
    ('configSha256','f'*64),('hostConfigSha256','f'*64),('mountsSha256','f'*64),
    ('networkSettingsSha256','f'*64),('networks',['unknown']),('health','healthy'),
])
def test_historical_stopped_input_signature_is_exact(release,plan,field,value):
    plan['nonTargets'][release.LEGACY_STOPPED_NAME][field]=value
    write_plan(release,plan)
    with pytest.raises(release.GuardError,match='historical_stopped_baseline_changed'):
        release.check_plan()


def non_target_fixture(m,plan,monkeypatch,*,extra=None,change=None):
    names=set(m.EXPECTED_NAMES)
    if extra:names.add(extra)
    monkeypatch.setattr(m,'run',lambda *a,**k:SimpleNamespace(stdout=('\n'.join(sorted(names))+'\n').encode()))
    signatures=deepcopy(plan['nonTargets'])
    if change:signatures[m.LEGACY_STOPPED_NAME].update(change)
    inspected=[]
    def inspect(name):
        inspected.append(name);return signatures[name]
    monkeypatch.setattr(m,'inspect',inspect)
    monkeypatch.setattr(m.H,'container_signature',lambda value:deepcopy(value))
    return {'nonTargets':deepcopy(plan['nonTargets']),'nonTargetNginx':{}},inspected


def test_all_six_nontargets_including_exact_stopped_are_read_only(release,plan,monkeypatch):
    manifest,inspected=non_target_fixture(release,plan,monkeypatch)
    release.check_non_targets(manifest)
    assert len(inspected)==6 and set(inspected)==set(plan['nonTargets'])


@pytest.mark.parametrize('change',[
    {'running':True},{'id':'f'*64},{'restartCount':1},{'health':'healthy'},
    {'configSha256':'f'*64},{'networkSettingsSha256':'f'*64},
])
def test_historical_stopped_runtime_drift_stops(release,plan,monkeypatch,change):
    manifest,_=non_target_fixture(release,plan,monkeypatch,change=change)
    with pytest.raises(release.GuardError,match='historical_stopped_container_changed'):
        release.check_non_targets(manifest)


def test_unknown_ninth_container_is_not_ignored(release,plan,monkeypatch):
    manifest,inspected=non_target_fixture(release,plan,monkeypatch,extra='unknown-stopped-builder')
    with pytest.raises(release.GuardError,match='non_target_container_set_changed'):
        release.check_non_targets(manifest)
    assert inspected==[]


def test_stopped_container_cannot_be_dropped_from_prepared_manifest(release,plan,monkeypatch):
    manifest,_=non_target_fixture(release,plan,monkeypatch)
    manifest['nonTargets'].pop(release.LEGACY_STOPPED_NAME)
    with pytest.raises(release.GuardError,match='non_target_manifest_set_changed'):
        release.check_non_targets(manifest)


def test_changed_stopped_container_blocks_prepare_before_freeze(release,plan,monkeypatch):
    non_target_fixture(release,plan,monkeypatch,change={'running':True})
    monkeypatch.setattr(release.H,'freeze',lambda *a,**k:pytest.fail('must not freeze changed stopped baseline'))
    with pytest.raises(release.GuardError,match='historical_stopped_container_changed'):
        release.prepare()
    assert not (release.ROOT/'prepared.json').exists()


@pytest.mark.parametrize('mutation',[
    lambda m,p:p.update(releaseId='wrong'),
    lambda m,p:p['baselines'].update(worker={}),
    lambda m,p:p['baselines']['backend'].update(id='0'*64),
    lambda m,p:p['baselines']['backend'].pop('signature'),
    lambda m,p:p['candidates']['backend'].update(image='latest'),
    lambda m,p:p['allowedBackend'].pop(next(iter(m.BACKEND_FILES))),
    lambda m,p:p['candidates']['backend']['inventory'].update({'apps/backend/app/private.py':h('unknown')}),
    lambda m,p:p['candidates']['backend']['inventory'].pop(m.HISTORY),
    lambda m,p:p['candidates']['backend']['rollbackInventory'].update({'apps/backend/app/services/session_service.py':h('wrong rollback')}),
    lambda m,p:p['candidates']['web']['inventory'].pop('assets/existing1.js'),
    lambda m,p:p['candidates']['web']['inventory'].update({'assets/existing1.js':h('changed old JS')}),
    lambda m,p:p['candidates']['web']['inventory'].update({'assets/new.css':h('unapproved css')}),
    lambda m,p:p['candidates']['web']['rollbackInventory'].update({'index.html':h('new index')}),
    lambda m,p:p['objectsReadback'].pop(),
    lambda m,p:p['objectsReadback'][0].update(objectReadbackVerified=False),
    lambda m,p:p['objectsReadback'][0].update(sha256=h('wrong')),
    lambda m,p:p['objectsReadback'][0].update(contentType='application/zip'),
    lambda m,p:p['publicRoutes'].update({'https://evil.invalid/':'index.html'}),
    lambda m,p:p['nonTargets'].pop(next(iter(p['nonTargets']))),
    lambda m,p:p['supportFiles'].pop('ownership_primitives.py'),
])
def test_scope_and_proof_drift_rejected(release,plan,mutation):
    mutation(release,plan);write_plan(release,plan)
    with pytest.raises(release.GuardError):release.check_plan()


@pytest.mark.parametrize('field,value',[
    ('version','1.3.5'),('protocolVersion','1.0'),('objectKey','desktop-releases/forbidden'),
    ('fileName','CN-or-local.dmg'),('fileSizeBytes',True),('fileSizeBytes',0),
    ('signingStatus','local-development'),('notarized',False),('developmentOnly',True),
    ('distributionStatus','internal'),('artifactPath','/private/path'),('minimumOs','different')])
def test_manifest_invalid_fields(release,plan,field,value):
    f=release.ROOT/plan['globalManifest']['path'];m=json.loads(f.read_text());m['entries'][0][field]=value
    with pytest.raises(release.GuardError):release.validate_manifest(m,plan['objectsReadback'])


@pytest.mark.parametrize('case',['extra_path','response','component','required','duplicate','wrong_name'])
def test_schema_rejects_nonoptional_or_other_changes(release,plan,case):
    before=json.loads((release.ROOT/plan['openapiBefore']['path']).read_text());after=json.loads((release.ROOT/plan['openapiAfter']['path']).read_text())
    if case=='extra_path':after['paths']['/extra']={}
    if case=='response':after['paths'][release.NEXT_PATH]['get']['responses']['403']={}
    if case=='component':after['components']['schemas']['Extra']={}
    if case=='required':after['paths'][release.NEXT_PATH]['get']['parameters'][-1]['required']=True
    if case=='duplicate':after['paths'][release.NEXT_PATH]['get']['parameters'].append(after['paths'][release.NEXT_PATH]['get']['parameters'][-1])
    if case=='wrong_name':after['paths'][release.NEXT_PATH]['get']['parameters'][-1]['name']='another'
    with pytest.raises(release.GuardError):release.check_schema_delta(before,after)


def test_support_content_drift_rejected(release,plan):
    (release.ROOT/'ownership_primitives.py').write_text('changed')
    with pytest.raises(release.GuardError,match='support_drift'):release.check_plan()


def test_relative_file_symlink_escape(release,tmp_path):
    outside=tmp_path.parent/(tmp_path.name+'outside');outside.write_text('synthetic')
    (tmp_path/'linked').symlink_to(outside)
    for value in ('../outside','/etc/passwd','linked'):
        with pytest.raises(release.GuardError):release.relative_file(value)


def container(m,service='backend',*,kind='baseline',running=True):
    cid,image=m.BASES[service]
    return {'Id':cid,'Image':image,'Config':{'Image':image,'Hostname':cid[:12],'Env':['SAFE=synthetic'],'Labels':{}},
            'HostConfig':{'NetworkMode':'synthetic-network'},'Mounts':[{'Type':'volume','Destination':'/b','Source':'synthetic-b','RW':True},{'Type':'bind','Destination':'/a','Source':'synthetic-a','RW':False}],
            'NetworkSettings':{'Networks':{'synthetic-network':{'Aliases':['synthetic',cid[:12]],'IPAddress':'172.20.0.2'}}},
            'RestartCount':0,'State':{'Running':running,'StartedAt':'2026-10-21T17:40:06Z','Pid':123 if running else 0,'Status':'running' if running else 'exited','Restarting':False,'Dead':False,'Paused':False,'Health':{'Status':'healthy'}}}


def test_mount_order_is_canonical_but_every_field_remains(release):
    c=container(release);reversed_c=deepcopy(c);reversed_c['Mounts'].reverse()
    assert release.H.container_signature(c)==release.H.container_signature(reversed_c)
    assert release.P.ownership_signature(c)==release.P.ownership_signature(reversed_c)
    for key,value in [('RW',False),('Source','different'),('Destination','/different'),('Type','tmpfs'),('Propagation','rshared')]:
        changed=deepcopy(c);changed['Mounts'][0][key]=value
        assert release.P.ownership_signature(changed)!=release.P.ownership_signature(c)
    for change in ('duplicate','delete'):
        changed=deepcopy(c);changed['Mounts']=[c['Mounts'][0],c['Mounts'][0]] if change=='duplicate' else [c['Mounts'][0]]
        assert release.P.ownership_signature(changed)!=release.P.ownership_signature(c)


def test_gate_uses_original_financial_anchor_and_not_current_start(release,monkeypatch):
    c=container(release);c['State']['StartedAt']='2099-01-01T00:00:00Z'
    monkeypatch.setattr(release,'read_json',lambda p:c)
    args=release.gate_command({'financialAnchorMs':release.FINANCIAL_ANCHOR_MS})
    assert 'OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=1792604406734' in args
    assert release.BASES['backend'][1] in args and '--network' in args
    with pytest.raises(release.GuardError):release.gate_command({'financialAnchorMs':1})


@pytest.mark.parametrize('bad',['unknown','unhealthy','source'])
def test_switch_stops_before_mutation_when_guards_fail(release,monkeypatch,bad):
    monkeypatch.setattr(release,'check_plan',lambda:None)
    monkeypatch.setattr(release,'check_files',lambda *a:None)
    def guard(*a,**k):raise release.GuardError(bad)
    monkeypatch.setattr(release,'verify_sources',guard)
    monkeypatch.setattr(release,'idle_gates',lambda *a:pytest.fail('gates must not bypass source failure'))
    with pytest.raises(release.GuardError,match=bad):release.switch({}, {}, {}, 'backend','new')


def test_busy_gate_blocks_switch_without_compose(release,monkeypatch):
    monkeypatch.setattr(release,'check_plan',lambda:None);monkeypatch.setattr(release,'check_files',lambda *a:None)
    monkeypatch.setattr(release,'verify_sources',lambda *a,**k:None)
    monkeypatch.setattr(release,'idle_gates',lambda *a:(_ for _ in ()).throw(release.GuardError('protected_user_work_cutover_deferred')))
    with pytest.raises(release.GuardError,match='deferred'):release.switch({}, {}, {}, 'backend','new')


def test_deployed_rerun_verifies_without_switch(release,monkeypatch):
    (release.ROOT/'deployed.json').write_text('{}');calls=[]
    monkeypatch.setattr(release,'check_plan',lambda:{})
    monkeypatch.setattr(release,'read_json',lambda p:{})
    monkeypatch.setattr(release,'progress_state',lambda:{})
    monkeypatch.setattr(release,'reconcile_intent',lambda *a:None)
    monkeypatch.setattr(release,'verify',lambda:calls.append('verify'))
    monkeypatch.setattr(release,'emit',lambda **k:calls.append(k))
    release.deploy();assert calls==['verify',{'alreadyDeployed':True,'productionChanged':False}]


def test_completed_lost_receipt_does_not_restart(release,monkeypatch):
    progress={s:{'kind':'new'} for s in release.BASES};calls=[]
    monkeypatch.setattr(release,'check_plan',lambda:{})
    monkeypatch.setattr(release,'read_json',lambda p:{})
    monkeypatch.setattr(release,'progress_state',lambda:progress)
    monkeypatch.setattr(release,'reconcile_intent',lambda *a:None)
    monkeypatch.setattr(release,'verify_runtime',lambda *a,**k:calls.append('verified'))
    monkeypatch.setattr(release,'public_checks',lambda *a:calls.append('public'))
    monkeypatch.setattr(release,'save',lambda *a:calls.append('saved'))
    monkeypatch.setattr(release,'emit',lambda **k:None)
    release.deploy();assert calls==['verified','public','saved']


@pytest.mark.parametrize('reason',['runtime_source_drift','production_compose_or_env_drift','release_container_owner_changed','protected_work_gate_unavailable','protected_user_work_cutover_deferred'])
def test_unknown_or_busy_failure_never_auto_rolls_back(release,monkeypatch,reason):
    monkeypatch.setattr(release,'check_plan',lambda:{})
    monkeypatch.setattr(release,'read_json',lambda p:{})
    monkeypatch.setattr(release,'progress_state',lambda:{})
    monkeypatch.setattr(release,'reconcile_intent',lambda *a:None)
    monkeypatch.setattr(release,'verify_runtime',lambda *a,**k:None)
    monkeypatch.setattr(release,'idle_gates',lambda *a:None);monkeypatch.setattr(release,'tcp_gate',lambda *a:None)
    monkeypatch.setattr(release,'switch',lambda *a:(_ for _ in ()).throw(release.GuardError(reason)))
    monkeypatch.setattr(release,'rollback',lambda:pytest.fail('must not roll back drift or busy state'))
    with pytest.raises(release.GuardError,match=reason):release.deploy()


def test_stopped_baseline_proof_requires_same_owned_container_twice(release,monkeypatch):
    before=container(release);now=container(release,running=False)
    monkeypatch.setattr(release,'read_json',lambda p:before)
    monkeypatch.setattr(release,'inspect',lambda n:now)
    release.baseline_stopped_proof('backend',now)
    changed=deepcopy(now);changed['Config']['Env']=['CHANGED=true']
    with pytest.raises(release.GuardError):release.baseline_stopped_proof('backend',changed)
    again=deepcopy(now);again['State']['Running']=True
    monkeypatch.setattr(release,'inspect',lambda n:again)
    with pytest.raises(release.GuardError):release.baseline_stopped_proof('backend',now)


def test_tcp_stopped_baseline_requires_proof(release,monkeypatch):
    c=container(release,running=False);calls=[]
    monkeypatch.setattr(release,'inspect',lambda n:c)
    monkeypatch.setattr(release,'baseline_stopped_proof',lambda *a:calls.append('proof'))
    monkeypatch.setattr(release,'save',lambda *a:None)
    release.tcp_gate({}, {}, recovery=True);assert calls==['proof']


def test_reconcile_only_adopts_known_intent_context(release,monkeypatch):
    target={'container':'synthetic','newImage':'sha256:'+h('new'),'frozenComposeFiles':['/old'],'newOverlay':'/new'}
    intent={'previousProgress':{},'service':'backend','kind':'new','beforeId':'old'}
    (release.ROOT/'switch-intent.json').write_text(json.dumps(intent));calls=[]
    now={'Image':target['newImage'],'Config':{'Labels':{'com.docker.compose.project.config_files':'/old,/new'}}}
    monkeypatch.setattr(release,'inspect',lambda n:now)
    monkeypatch.setattr(release.P,'record_created_owner',lambda *a:calls.append('adopt'))
    release.reconcile_intent({'targets':{'backend':target}},{});assert calls==['adopt']
    now['Config']['Labels']['com.docker.compose.project.config_files']='/foreign'
    release.reconcile_intent({'targets':{'backend':target}},{});assert calls==['adopt']


def test_no_historical_mutation_entrypoints_in_helper(release):
    for name in ('prepare','deploy','rollback','switch','verify'):
        assert not hasattr(release.P,name)


def test_health_failure_recovery_is_not_implicit_on_guard_drift(release,monkeypatch):
    calls=[]
    monkeypatch.setattr(release,'check_plan',lambda:{})
    monkeypatch.setattr(release,'read_json',lambda p:{})
    monkeypatch.setattr(release,'progress_state',lambda:{})
    monkeypatch.setattr(release,'reconcile_intent',lambda *a:None)
    monkeypatch.setattr(release,'verify_runtime',lambda *a,**k:None)
    monkeypatch.setattr(release,'idle_gates',lambda *a:None);monkeypatch.setattr(release,'tcp_gate',lambda *a:None)
    monkeypatch.setattr(release,'switch',lambda *a:(_ for _ in ()).throw(release.GuardError('target_health_failed')))
    monkeypatch.setattr(release,'rollback',lambda:calls.append('guarded rollback'))
    monkeypatch.setattr(release,'save',lambda *a:None)
    with pytest.raises(release.GuardError,match='cutover_failed_rollback_succeeded'):release.deploy()
    assert calls==['guarded rollback']


@pytest.mark.parametrize('rollback',[False,True])
def test_actual_candidate_probe_contract_and_isolation_flags(release,plan,monkeypatch,rollback):
    (release.SUPPORT/'probe.py').is_file()  # probe bytes may be staged separately; read is mocked below
    monkeypatch.setattr(Path,'read_bytes',lambda self:b'synthetic probe')
    report={'passed':True,'checks':['synthetic_check'],'providerCalls':0,'databaseWrites':0,'workersStarted':0,
            'lifespanStarted':False,'settingsUnchanged':True,'schemaAllowedDelta':True}
    commands=[];saved=[]
    def fake_run(args,**kwargs):commands.append(args);return SimpleNamespace(stdout=json.dumps(report).encode())
    monkeypatch.setattr(release,'run',fake_run);monkeypatch.setattr(release,'save',lambda *a:saved.append(a))
    target={'newImage':'sha256:'+h('new'),'rollbackImage':'sha256:'+h('rollback')}
    release.candidate_probe(target,plan,rollback=rollback)
    command=commands[0]
    assert command[command.index('--network')+1]=='none' and '--read-only' in command and '--cap-drop' in command
    assert '--env-file' in command and 'ALL' in command and ('--rollback' in command)==rollback
    assert target['rollbackImage' if rollback else 'newImage'] in command
    assert saved[0][0]=='backend/offline-probe-'+('rollback' if rollback else 'new')+'.json'


@pytest.mark.parametrize('key,value',[('providerCalls',1),('databaseWrites',1),('workersStarted',1),
                                     ('lifespanStarted',True),('settingsUnchanged',False),('schemaAllowedDelta',False),
                                     ('checks',['raw supplier response']),('extraPrivateField','secret')])
def test_probe_rejects_mutation_or_unapproved_output(release,plan,monkeypatch,key,value):
    monkeypatch.setattr(Path,'read_bytes',lambda self:b'synthetic probe')
    report={'passed':True,'checks':['synthetic_check'],'providerCalls':0,'databaseWrites':0,'workersStarted':0,
            'lifespanStarted':False,'settingsUnchanged':True,'schemaAllowedDelta':True};report[key]=value
    monkeypatch.setattr(release,'run',lambda *a,**k:SimpleNamespace(stdout=json.dumps(report).encode()))
    with pytest.raises(release.GuardError,match='offline_probe'):release.candidate_probe({'newImage':'sha256:'+h('new')},plan)


@pytest.mark.parametrize('failure',['busy','unknown','stale','bad_shape','read_failure'])
def test_seven_gate_contracts_fail_closed(release,monkeypatch,failure):
    before=container(release);monkeypatch.setattr(release,'read_json',lambda p:before)
    seen=[]
    def fake_run(args,**kwargs):
        path=release.GATES[len(seen)];seen.append(path)
        old_root=release.H.ROOT;release.H.ROOT=release.SUPPORT
        try:protected,informational=release.H.gate_contract(path)
        finally:release.H.ROOT=old_root
        counts=dict.fromkeys(protected|informational,0)
        if 'atMs' in counts:counts['atMs']=int(release.time.time()*1000)
        status=0
        if failure=='busy' and len(seen)==1:counts['liveInterviews']=1;status=75
        if failure=='stale' and len(seen)==1:counts['atMs']=1
        if failure=='bad_shape' and len(seen)==1:counts['unexpected']=0
        if failure=='read_failure' and path=='global_financial_idle_gate.py':counts['financialReadFailures']=1;status=75
        if failure=='unknown' and path=='global_financial_idle_gate.py':counts['unknownCommerceStates']=1;status=75
        return SimpleNamespace(stdout=json.dumps(counts).encode(),returncode=status)
    monkeypatch.setattr(release.subprocess,'run',fake_run);monkeypatch.setattr(release,'save',lambda *a:None)
    with pytest.raises(release.GuardError,match='deferred' if failure=='busy' else 'unavailable'):
        release.idle_gates({'financialAnchorMs':release.FINANCIAL_ANCHOR_MS})
    assert len(seen)==(1 if failure in ('busy','stale','bad_shape') else 7)


def test_all_seven_gates_run_with_original_anchor(release,monkeypatch):
    monkeypatch.setattr(release,'read_json',lambda p:container(release));seen=[]
    def fake_run(args,**kwargs):
        path=release.GATES[len(seen)];seen.append(path)
        assert 'OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=1792604406734' in args
        old_root=release.H.ROOT;release.H.ROOT=release.SUPPORT
        try:protected,info=release.H.gate_contract(path)
        finally:release.H.ROOT=old_root
        counts=dict.fromkeys(protected|info,0)
        if 'atMs' in counts:counts['atMs']=int(release.time.time()*1000)
        return SimpleNamespace(stdout=json.dumps(counts).encode(),returncode=0)
    monkeypatch.setattr(release.subprocess,'run',fake_run);monkeypatch.setattr(release,'save',lambda *a:None)
    assert len(release.idle_gates({'financialAnchorMs':release.FINANCIAL_ANCHOR_MS}))==7
    assert seen==list(release.GATES)


def test_actual_switch_lost_response_records_created_owner_once(release,monkeypatch):
    before=container(release);now=deepcopy(before);now['Id']='c'*64;now['Image']='sha256:'+h('new');now['Config']['Image']=now['Image'];now['Config']['Hostname']=now['Id'][:12]
    now['NetworkSettings']['Networks']['synthetic-network']['Aliases']=['synthetic',now['Id'][:12]]
    target={'container':'synthetic','service':'backend','newImage':now['Image'],'newOverlay':'/new',
            'frozenComposeFiles':['/frozen'],'frozenEnvFiles':['/env'],'composeDirectory':'/directory'}
    now['Config']['Labels']={'com.docker.compose.project':release.PROJECT,'com.docker.compose.service':'backend',
        'com.docker.compose.project.config_files':'/frozen,/new','com.docker.compose.project.environment_file':'/env',
        'com.docker.compose.project.working_dir':'/directory'}
    seq=iter([before,now]);monkeypatch.setattr(release,'inspect',lambda n:next(seq));calls=[]
    for name in ('check_plan','check_files','verify_sources','idle_gates','tcp_gate','targets_owned'):
        monkeypatch.setattr(release,name,lambda *a,**k:None)
    monkeypatch.setattr(release.H,'compose_args',lambda *a,**k:['docker','compose'])
    monkeypatch.setattr(release,'save',lambda *a:None);release.P.save=release.save
    (release.ROOT/'backend').mkdir();(release.ROOT/'backend/container-before.json').write_text(json.dumps(before))
    def timeout(args,**kwargs):calls.append(args);raise subprocess.TimeoutExpired('synthetic compose',120)
    monkeypatch.setattr(release,'run',timeout)
    progress={}
    with pytest.raises(subprocess.TimeoutExpired):release.switch({'targets':{'backend':target}},{},progress,'backend','new')
    assert progress['backend']['id']==now['Id'] and progress['backend']['kind']=='new' and len(calls)==1


def test_proxy_refresh_only_known_static_upstreams_after_gates(release,monkeypatch):
    calls=[]
    for name in ('check_plan','check_files','verify_sources','check_non_targets','targets_owned'):
        monkeypatch.setattr(release,name,lambda *a,**k:None)
    monkeypatch.setattr(release,'idle_gates',lambda *a:calls.append('idle'))
    monkeypatch.setattr(release,'tcp_gate',lambda *a:calls.append('tcp'))
    monkeypatch.setattr(release,'run',lambda a,**k:calls.append(a));monkeypatch.setattr(release,'save',lambda *a:None)
    manifest={'proxyStaticBackendUpstreams':{release.PROJECT+'-web-1':True,release.PROJECT+'-admin-1':False}}
    release.refresh_static_proxies(manifest,{},{});assert calls[:2]==['idle','tcp']
    assert calls[2:]==[['docker','exec',release.PROJECT+'-web-1','nginx','-t'],['docker','exec',release.PROJECT+'-web-1','nginx','-s','reload']]
    manifest['proxyStaticBackendUpstreams']={'unrelated':True}
    with pytest.raises(release.GuardError):release.refresh_static_proxies(manifest,{}, {})


def test_proxy_refresh_does_nothing_when_gates_busy(release,monkeypatch):
    for name in ('check_plan','check_files','verify_sources'):
        monkeypatch.setattr(release,name,lambda *a,**k:None)
    monkeypatch.setattr(release,'idle_gates',lambda *a:(_ for _ in ()).throw(release.GuardError('protected_user_work_cutover_deferred')))
    with pytest.raises(release.GuardError):release.refresh_static_proxies({}, {}, {})


@pytest.mark.parametrize('kind',['baseline','new','rollback'])
def test_partial_backend_recovery_does_not_require_unpublished_web_assets(release,plan,monkeypatch,kind):
    plan['publicRoutes']['/assets/main-new.js']='assets/main-new.js'
    data={'index.html':b'synthetic HTML','assets/main-new.js':b'synthetic JS'}
    files={name:hashlib.sha256(value).hexdigest() for name,value in data.items()}
    plan['baselines']['web']['inventory']={'index.html':files['index.html']}
    plan['candidates']['web']['inventory']=files;plan['candidates']['web']['rollbackInventory']=files
    seen=[]
    class Response(io.BytesIO):
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):self.close()
    def opened(request,**kwargs):
        url=request if isinstance(request,str) else request.full_url;seen.append(url)
        if url.endswith('/healthz'):return Response(b'{"data":{"status":"ok"}}')
        return Response(data['assets/main-new.js' if url.endswith('.js') else 'index.html'])
    monkeypatch.setattr(release,'urlopen',opened)
    progress={'backend':{'kind':'rollback'}}
    if kind!='baseline':progress['web']={'kind':kind}
    release.public_checks(plan,progress)
    assert any(url.endswith('/assets/main-new.js') for url in seen)==(kind!='baseline')
