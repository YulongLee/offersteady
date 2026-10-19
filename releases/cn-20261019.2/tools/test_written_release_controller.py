"""Synthetic release/controller tests: no SSH, Docker, model or real gates."""
from pathlib import Path
import copy
import importlib.util
import json
from itertools import permutations
from types import SimpleNamespace
import time

import pytest

HERE=Path(__file__).parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


m=load('template_release',HERE/'payload/release_cn_written_multi_screen.py')
tcp=load('template_tcp',HERE/'payload/backend_tcp_idle_gate.py')


def put(root,path,value):
    target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(value if type(value) is bytes else json.dumps(value).encode())
    return m.digest(target.read_bytes())


@pytest.fixture
def seeded(tmp_path,monkeypatch):
    import shutil
    source=HERE/'payload'
    shutil.copytree(source,tmp_path,dirs_exist_ok=True)
    monkeypatch.setattr(m,'ROOT',tmp_path)
    plan=json.loads((tmp_path/'input.json').read_bytes()) if (tmp_path/'input.json').exists() else {'gates':sorted(m.GATES),'supportFiles':{r:m.digest((tmp_path/r).read_bytes()) for r in [*m.GATES,m.TCP_GATE]}}
    def flush():put(tmp_path,'input.json',plan)
    return tmp_path,plan,flush








@pytest.mark.parametrize('gate',sorted(m.GATES))
def test_every_original_protected_field_still_defers(seeded,gate):
    fields,info=m.gate_contract(gate);counts=dict.fromkeys(fields|info,0)
    assert m.gate_is_idle(gate,counts)
    for name in fields:assert not m.gate_is_idle(gate,counts|{name:1})


def test_gate_uses_the_actual_parent_not_an_inherited_old_default(seeded,monkeypatch):
    root,plan,_=seeded;put(root,'backend/container-before.json',{'HostConfig':{'NetworkMode':'compose_default'}})
    assert m.baseline_command({})[-3:]==[m.BASE_IMAGE,'-B','-']
    assert m.BASE_IMAGE=='sha256:f6dbe8fd498f1f965bf8ba611d666e7ea49475ac1a7bf01b547ed79e8c6bbfaa'
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=b'not-json'))
    with pytest.raises(m.GuardError,match='protected_work_gate_unavailable'):m.idle_gates({},plan)


@pytest.fixture
def flow(seeded,monkeypatch):
    root,plan,_=seeded;manifest={'targets':[{'service':'backend','newImage':'candidate'},{'service':'web','newImage':'webcandidate'}]}
    put(root,'prepared.json',manifest);events=[]
    monkeypatch.setattr(m,'check_inputs',lambda:plan)
    monkeypatch.setattr(m,'reconcile_intent',lambda *a:None)
    monkeypatch.setattr(m,'verify_current',lambda *a,**k:events.append('verify'))
    monkeypatch.setattr(m,'idle_gates',lambda *a:events.append('seven-gates'))
    monkeypatch.setattr(m,'tcp_idle_guard',lambda *a,**k:events.append('tcp'))
    monkeypatch.setattr(m,'public_checks',lambda:[])
    def switch(manifest,target,kind,progress):
        events.append('switch-'+target['service']+'-'+kind);progress[target['service']]={'kind':kind}
    monkeypatch.setattr(m,'switch',switch)
    return root,manifest,events


def test_preflight_only_verifies_all_gates_and_actual_backend_tcp(flow):
    root,_,events=flow;m._deploy(preflight=True)
    assert events==['verify','seven-gates','tcp'] and not (root/'deployed.json').exists()


def test_dual_target_deploy_repeats_all_seven_gates_before_each_switch(flow):
    _,_,events=flow;m._deploy()
    assert events==['verify','seven-gates','tcp','verify','seven-gates','switch-backend-new','verify','seven-gates','switch-web-new','verify']


def test_deployed_marker_is_verified_without_a_second_restart(flow):
    root,_,events=flow;put(root,'deployed.json',{'deployed':True});m._deploy()
    assert events==['verify']


@pytest.mark.parametrize('reason',['protected_user_work_cutover_deferred','protected_work_gate_unavailable','protected_tcp_gate_unavailable'])
def test_busy_or_unknown_protection_never_switches_or_recovers(flow,monkeypatch,reason):
    root,_,events=flow;put(root,'progress.json',{})
    def fail(*a):raise m.GuardError(reason)
    monkeypatch.setattr(m,'idle_gates',fail);monkeypatch.setattr(m,'rollback',lambda:events.append('rollback'))
    with pytest.raises(m.GuardError):m.deploy()
    assert events==['verify']


def test_generic_command_failure_with_progress_does_not_auto_rollback(flow,monkeypatch):
    root,_,events=flow;put(root,'progress.json',{'backend':{'kind':'new'}})
    def fail(**kwargs):raise m.subprocess.CalledProcessError(1,['synthetic'])
    monkeypatch.setattr(m,'_deploy',fail);monkeypatch.setattr(m,'rollback',lambda:events.append('rollback'))
    with pytest.raises(m.subprocess.CalledProcessError):m.deploy()
    assert events==[] and m.read_json(root/'cutover-failure.json')['automaticRecoveryAttempted'] is False


def test_known_health_failure_attempts_only_the_guarded_recovery(flow,monkeypatch):
    root,_,events=flow;put(root,'progress.json',{'backend':{'kind':'new'}})
    def fail(**kwargs):raise m.GuardError('target_health_failed')
    monkeypatch.setattr(m,'_deploy',fail);monkeypatch.setattr(m,'rollback',lambda:events.append('rollback'))
    with pytest.raises(m.GuardError):m.deploy()
    assert events==['rollback']


def test_rollback_rechecks_exact_ownership_and_all_seven_gates(flow,monkeypatch):
    root,_,events=flow;put(root,'progress.json',{'backend':{'kind':'new'}})
    monkeypatch.setattr(m,'verify_files',lambda *a:events.append('files'))
    monkeypatch.setattr(m,'assert_owned',lambda *a,**k:events.append('owned'))
    m.rollback()
    assert events==['files','owned','owned','seven-gates','switch-backend-rollback','verify']


@pytest.mark.parametrize('kind',['new','rollback'])
@pytest.mark.parametrize('busy',[False,True])
def test_switch_reads_tcp_immediately_before_the_only_backend_recreation(seeded,monkeypatch,kind,busy):
    root,_,_=seeded;events=[];before=container();after=copy.deepcopy(before)
    target={'service':'backend','container':'compose-backend-1','newImage':'candidate','rollbackImage':'old',
            'newOverlay':'o','rollbackOverlay':'r','frozenComposeFiles':['f'],'frozenEnvFiles':['e'],'composeDirectory':'/synthetic'}
    after['Image']=target[kind+'Image'];after['Config']['Labels']['com.docker.compose.project.config_files']='f,'+target[kind+'Overlay']
    after['State']['Health']={'Status':'healthy'}
    put(root,'backend/container-before.json',before)
    monkeypatch.setattr(m,'check_inputs',lambda:{})
    monkeypatch.setattr(m,'verify_files',lambda *a:None)
    monkeypatch.setattr(m,'assert_owned',lambda *a,**k:None)
    monkeypatch.setattr(m,'runtime_invariant',lambda *a:None)
    monkeypatch.setattr(m,'inspect',lambda *a:copy.deepcopy(after if 'up' in events else before))
    def tcp(*args,**kwargs):
        events.append('tcp-recovery' if kwargs['recovery'] else 'tcp-live')
        if busy:raise m.GuardError('protected_user_work_cutover_deferred')
    def run(args,**kwargs):
        assert args[-1]=='backend' and '--no-build' in args and '--no-deps' in args and args[-3:-1]==['--pull','never']
        events.append('up');return SimpleNamespace(stdout=b'')
    monkeypatch.setattr(m,'tcp_idle_guard',tcp);monkeypatch.setattr(m,'run',run)
    if busy:
        with pytest.raises(m.GuardError):m.switch({'targets':[target]},target,kind,{})
        assert events==['tcp-recovery' if kind=='rollback' else 'tcp-live']
    else:
        m.switch({'targets':[target]},target,kind,{})
        assert events==['tcp-recovery' if kind=='rollback' else 'tcp-live','up']


HEADER='sl local_address rem_address st tx_queue rx_queue tr tm_when retrnsmt uid timeout inode\n'


def row(local_port='1F40',state='01',*,ipv6=False,remote_port='01BB'):
    address='0'*32 if ipv6 else '0100007F'
    return f'0: {address}:{local_port} {address}:{remote_port} {state} 00000000:00000000 00:00000000 00000000 1000 0 12345 1\n'


def test_tcp_counts_only_local_8000_established_ipv4_and_ipv6():
    assert tcp.count_established(HEADER+row()+row(state='0A')+row(state='06')+row(local_port='01BB',remote_port='1F40'),ipv6=False)==(1,4)
    assert tcp.count_established(HEADER.replace('rem_address','remote_address')+row(ipv6=True),ipv6=True)==(1,1)
    assert tcp.count_established(HEADER,ipv6=False)==(0,0)


def test_tcp_script_binds_exec_and_init_netns_before_and_after_reading_both_tables(monkeypatch):
    seen=[]
    def readlink(path):
        seen.append(str(path));return Path('net:[12345]')
    monkeypatch.setattr(Path,'readlink',readlink)
    monkeypatch.setattr(Path,'read_text',lambda path,**k:HEADER)
    result=tcp.main()
    assert result['networkNamespaceSha256']==m.digest(b'net:[12345]') and result['tablesRead']==2
    assert seen==['/proc/self/ns/net','/proc/1/ns/net']*2
    assert 'net:[' not in json.dumps(result)


@pytest.mark.parametrize('change',['different_init','malformed','unreadable','changed_after_tables'])
def test_tcp_script_stops_on_unknown_mismatched_or_drifting_netns(monkeypatch,change):
    seen=[]
    def readlink(path):
        seen.append(str(path))
        if change=='unreadable':raise PermissionError('private-namespace')
        if change=='malformed':return Path('unknown')
        if change=='different_init' and str(path)=='/proc/1/ns/net':return Path('net:[67890]')
        return Path('net:[67890]' if change=='changed_after_tables' and len(seen)>2 else 'net:[12345]')
    monkeypatch.setattr(Path,'readlink',readlink)
    monkeypatch.setattr(Path,'read_text',lambda path,**k:HEADER)
    with pytest.raises((tcp.TCPTableError,PermissionError)):tcp.main()


@pytest.mark.parametrize('table,ipv6',[
    ('',False),('unknown header\n',False),(HEADER+'garbage\n',False),(HEADER+row(state='FF'),False),
    (HEADER+row(state='00'),False),(HEADER+row(local_port='unknown'),False),(HEADER+row(ipv6=True),False),
    (HEADER+row(),True),(HEADER+row().replace('0100007F','SYNTHETIC_PRIVATE'),False),
])
def test_malformed_or_unknown_tcp_tables_fail_without_echoing_rows(table,ipv6):
    with pytest.raises(tcp.TCPTableError) as error:tcp.count_established(table,ipv6=ipv6)
    assert str(error.value)==''


def test_tcp_read_failure_is_fixed_and_does_not_print_private_error(monkeypatch,capsys):
    source=(HERE/'payload/backend_tcp_idle_gate.py').read_text()
    def unavailable(*a,**k):raise PermissionError('synthetic-private-address')
    monkeypatch.setattr(Path,'read_text',unavailable)
    with pytest.raises(SystemExit):exec(compile(source,'tcp-test','exec'),{'__name__':'__main__'})
    output=capsys.readouterr().out
    assert json.loads(output)=={'passed':False,'reason':'tcp_read_or_parse_failed'} and 'synthetic-private' not in output


def container():
    identity='a'*64
    return {'Id':identity,'Image':'candidate','Config':{'Image':'candidate','Hostname':identity[:12],'Env':['VALUE=unchanged'],
        'Labels':{'com.docker.compose.project':'compose','com.docker.compose.service':'backend',
        'com.docker.compose.project.config_files':'f,o','com.docker.compose.project.working_dir':'/synthetic',
        'com.docker.compose.project.environment_file':'e'}},'HostConfig':{},'Mounts':[],
        'State':{'StartedAt':'synthetic-start','Running':True,'Pid':123,'Status':'running','Restarting':False,'Dead':False,'Paused':False},
        'RestartCount':0,'NetworkSettings':{'Networks':{'synthetic':{'Aliases':['backend',identity[:12]],'IPAddress':'192.0.2.1'}}}}


@pytest.fixture
def tcp_flow(seeded,monkeypatch):
    root,plan,_=seeded;current=container()
    target={'service':'backend','container':'compose-backend-1','newImage':'candidate','newOverlay':'o',
            'frozenComposeFiles':['f'],'frozenEnvFiles':['e'],'composeDirectory':'/synthetic'}
    manifest={'targets':[target]}
    progress={'backend':{'id':current['Id'],'image':current['Image'],'kind':'new','signature':m.container_signature(current)}}
    monkeypatch.setattr(m,'inspect',lambda *a:copy.deepcopy(current))
    monkeypatch.setattr(m,'host_network_namespace',lambda *a:m.digest(b'net:[12345]'))
    return root,plan,manifest,progress,current


def tcp_output(count=0):
    return {'passed':True,'atMs':int(time.time()*1000),'establishedPort8000':count,'tablesRead':2,
            'scannedRows':max(1,count),'scope':'container_tcp8000_established_only',
            'networkNamespaceSha256':m.digest(b'net:[12345]')}


@pytest.mark.parametrize('count',[0,1])
def test_tcp_guard_executes_in_the_actual_owned_backend_id_and_preserves_idle_keepalives(tcp_flow,monkeypatch,count):
    _,plan,manifest,progress,current=tcp_flow;calls=[]
    def run(args,**kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0,stdout=json.dumps(tcp_output(count)).encode())
    monkeypatch.setattr(m.subprocess,'run',run)
    if count:
        with pytest.raises(m.GuardError,match='protected_user_work_cutover_deferred'):m.tcp_idle_guard(manifest,plan,progress)
    else:assert m.tcp_idle_guard(manifest,plan,progress)['establishedPort8000']==0
    assert calls[0]==['docker','exec','-i',current['Id'],'python','-B','-']


@pytest.mark.parametrize('change',['readfail','exit','missing','extra','bool','negative','stale','future','wrong_scope','netns'])
def test_tcp_unknown_unreadable_or_stale_state_stops(tcp_flow,monkeypatch,change):
    _,plan,manifest,progress,_=tcp_flow;value=tcp_output();code=0
    if change=='readfail':value={'passed':False,'reason':'tcp_read_or_parse_failed'}
    elif change=='exit':code=2
    elif change=='missing':value.pop('tablesRead')
    elif change=='extra':value['private']='must not pass'
    elif change=='bool':value['establishedPort8000']=False
    elif change=='negative':value['scannedRows']=-1
    elif change=='stale':value['atMs']-=20000
    elif change=='future':value['atMs']+=20000
    elif change=='wrong_scope':value['scope']='different'
    elif change=='netns':value['networkNamespaceSha256']=m.digest(b'net:[67890]')
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=code,stdout=json.dumps(value).encode()))
    with pytest.raises(m.GuardError,match='protected_tcp_gate_unavailable'):m.tcp_idle_guard(manifest,plan,progress)


@pytest.mark.parametrize('field,value',[('Pid',0),('Pid',-1),('Pid',True),('Status','restarting'),('Restarting',True),('Dead',True),('Paused',True),('StartedAt','')])
def test_running_tcp_refuses_unknown_process_identity_before_exec(tcp_flow,monkeypatch,field,value):
    _,plan,manifest,progress,current=tcp_flow;current['State'][field]=value
    monkeypatch.setattr(m,'assert_owned',lambda *a,**k:None)
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('invalid process must not execute probe'))
    with pytest.raises(m.GuardError):m.tcp_idle_guard(manifest,plan,progress)


@pytest.mark.parametrize('change',['Pid','StartedAt','Restarting','Dead','Paused','netns'])
def test_running_tcp_requires_same_process_and_host_netns_after_exec(tcp_flow,monkeypatch,change):
    _,plan,manifest,progress,current=tcp_flow;changed=False
    monkeypatch.setattr(m,'assert_owned',lambda *a,**k:None)
    def run(*args,**kwargs):
        nonlocal changed
        changed=True
        if change!='netns':current['State'][change]=456 if change=='Pid' else ('changed' if change=='StartedAt' else True)
        return SimpleNamespace(returncode=0,stdout=json.dumps(tcp_output()).encode())
    monkeypatch.setattr(m.subprocess,'run',run)
    monkeypatch.setattr(m,'host_network_namespace',lambda *a:m.digest(b'net:[67890]' if change=='netns' and changed else b'net:[12345]'))
    with pytest.raises(m.GuardError):m.tcp_idle_guard(manifest,plan,progress)


@pytest.mark.parametrize('change',['valid','unreadable','missing','malformed'])
def test_host_netns_reads_exact_inspected_init_pid_and_fails_closed(monkeypatch,change):
    seen=[]
    def readlink(path):
        seen.append(str(path))
        if change=='unreadable':raise PermissionError('private-namespace')
        if change=='missing':raise FileNotFoundError('private-namespace')
        return Path('unknown' if change=='malformed' else 'net:[12345]')
    monkeypatch.setattr(Path,'readlink',readlink)
    if change=='valid':assert m.host_network_namespace(container())==m.digest(b'net:[12345]')
    else:
        with pytest.raises(m.GuardError,match='protected_tcp_gate_unavailable'):m.host_network_namespace(container())
    assert seen==['/proc/123/ns/net']


def test_owned_exited_candidate_has_explicit_stopped_proof_only_for_recovery(tcp_flow,monkeypatch):
    _,plan,manifest,progress,current=tcp_flow
    current['State'].update(Running=False,Pid=0,Status='exited')
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:pytest.fail('stopped proof must not pretend to read sockets'))
    with pytest.raises(m.GuardError):m.tcp_idle_guard(manifest,plan,progress)
    result=m.tcp_idle_guard(manifest,plan,progress,recovery=True)
    assert result['method']=='stoppedProcessProof' and result['observations']==2 and 'establishedPort8000' not in result


@pytest.mark.parametrize('field,value',[('Restarting',True),('Dead',True),('Paused',True),('Pid',4),('Status','created'),('StartedAt','changed')])
def test_stopped_recovery_rejects_unknown_restarting_or_drifting_process_state(tcp_flow,monkeypatch,field,value):
    _,plan,manifest,progress,current=tcp_flow
    current['State'].update(Running=False,Pid=0,Status='exited');current['State'][field]=value
    with pytest.raises(m.GuardError):m.tcp_idle_guard(manifest,plan,progress,recovery=True)


def test_stopped_proof_rejects_a_change_between_its_two_snapshots(tcp_flow,monkeypatch):
    _,plan,manifest,progress,current=tcp_flow;current['State'].update(Running=False,Pid=0,Status='exited')
    calls=[]
    def inspect(*args):
        calls.append(args);result=copy.deepcopy(current)
        if len(calls)>=3:result['State']['StartedAt']='changed-after-first-proof'
        return result
    monkeypatch.setattr(m,'inspect',inspect)
    with pytest.raises(m.GuardError):m.tcp_idle_guard(manifest,plan,progress,recovery=True)


def test_image_overlay_is_two_targets_only_and_changes_no_environment():
    original={'services':{'backend':{'image':'old','environment':{'VALUE':'unchanged'}},'web':{'image':'untouched'}}}
    assert m.expected_config(original,{'service':'backend','newImage':'new'},'new')=={'services':{'backend':{'image':'new','environment':{'VALUE':'unchanged'}},'web':{'image':'untouched'}}}
    assert m.expected_config(original,{'service':'web','newImage':'new'},'new')=={'services':{'backend':{'image':'old','environment':{'VALUE':'unchanged'}},'web':{'image':'new'}}}
    with pytest.raises(m.GuardError):m.expected_config(original,{'service':'admin','newImage':'new'},'new')


def test_full_mount_multiset_preserves_unknown_fields_and_duplicate_count():
    mounts=[{'Type':'bind','Destination':'/a','RW':True,'future':['a','b']},{'Type':'volume','Destination':'/b','RW':False}]
    for order in permutations(mounts):assert m.canonical_mounts(list(order))==m.canonical_mounts(mounts)
    assert m.canonical_mounts(mounts+[mounts[0]])!=m.canonical_mounts(mounts)
    changed=copy.deepcopy(mounts);changed[0]['future'].reverse()
    assert m.canonical_mounts(changed)!=m.canonical_mounts(mounts)














def test_all_untouched_protection_functions_are_byte_ast_identical():
    import ast
    old=HERE/'fixtures/release_cn_resume_rollback.py'
    def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
    before=functions(old);after=functions(Path(m.__file__))
    changed={name for name in before if name in after and before[name]!=after[name]}
    assert changed=={'expected_config','write_overlay','verify_non_targets','verify_files','check_inputs','prepare','verify_current','probe','_deploy','inspect_release','verify','public_checks','tcp_idle_guard','switch','deploy'}
    assert set(before)-set(after)=={'validate_service_delta'}
    assert {'gate_contract','normalize_gate','gate_is_idle','gate_has_read_or_unknown_failure','idle_gates','host_network_namespace','running_process_identity','assert_owned','runtime_invariant','release_lock','freeze','reconcile_intent','rollback'}<=set(before)-changed


def test_build_is_copy_only_and_has_no_migration_dependency_env_or_nginx_mutation():
    import inspect
    source=inspect.getsource(m.prepare)
    assert 'COPY input/' in source and "'--network=none','--pull=false'" in source
    for forbidden in ('migrate(', 'pip install', 'wheels', 'FLAG', 'nginxFile'):
        assert forbidden not in source
    assert "'newTag'" in source and "('backend','web')" in source


@pytest.mark.parametrize('service',['backend','web'])
@pytest.mark.parametrize('kind',['new','rollback'])
def test_each_component_switch_keeps_tcp_check_and_fixed_no_deps_flags(seeded,monkeypatch,service,kind):
    root,_,_=seeded;events=[];before=container();after=copy.deepcopy(before)
    target={'service':service,'container':'compose-'+service+'-1','newImage':'candidate','rollbackImage':'old',
            'newOverlay':'o','rollbackOverlay':'r','frozenComposeFiles':['f'],'frozenEnvFiles':['e'],'composeDirectory':'/synthetic'}
    after['Image']=target[kind+'Image'];after['Config']['Labels']['com.docker.compose.service']=service
    after['Config']['Labels']['com.docker.compose.project.config_files']='f,'+target[kind+'Overlay']
    after['State']['Health']={'Status':'healthy'}
    put(root,service+'/container-before.json',before)
    monkeypatch.setattr(m,'check_inputs',lambda:{})
    monkeypatch.setattr(m,'verify_files',lambda *a:None)
    monkeypatch.setattr(m,'assert_owned',lambda *a,**k:None)
    monkeypatch.setattr(m,'runtime_invariant',lambda *a:None)
    monkeypatch.setattr(m,'inspect',lambda *a:copy.deepcopy(after if 'up' in events else before))
    def tcp(*args,**kwargs):events.append(('tcp',kwargs['recovery']))
    def run(args,**kwargs):
        assert args[-1]==service and '--no-build' in args and '--no-deps' in args and args[-3:-1]==['--pull','never']
        events.append('up');return SimpleNamespace(stdout=b'')
    monkeypatch.setattr(m,'tcp_idle_guard',tcp);monkeypatch.setattr(m,'run',run)
    m.switch({'targets':[target]},target,kind,{})
    assert events==[('tcp',kind=='rollback' and service=='backend'),'up']


def test_web_only_failure_does_not_enable_backend_stopped_proof(seeded,monkeypatch):
    root,plan,_=seeded;current=container()
    # Put Web first intentionally: TCP must select Backend by name, not by index.
    backend={'service':'backend','container':'compose-backend-1','newImage':'candidate','newOverlay':'o',
             'frozenComposeFiles':['f'],'frozenEnvFiles':['e'],'composeDirectory':'/synthetic'}
    manifest={'targets':[{'service':'web','newImage':'web'},backend]}
    progress={'backend':{'id':current['Id'],'image':current['Image'],'kind':'new','signature':m.container_signature(current)}}
    monkeypatch.setattr(m,'inspect',lambda *a:copy.deepcopy(current))
    monkeypatch.setattr(m,'host_network_namespace',lambda *a:m.digest(b'net:[12345]'))
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=json.dumps(tcp_output()).encode()))
    assert m.tcp_idle_guard(manifest,plan,progress)['establishedPort8000']==0


def test_container_set_check_permits_only_owned_targets_to_be_temporarily_stopped(monkeypatch):
    non=container();non['Id']='b'*64
    manifest={'nonTargets':{'compose-admin-1':m.container_signature(non)},'sharedTags':{}}
    monkeypatch.setattr(m,'inspect',lambda *a:non)
    monkeypatch.setattr(m,'run',lambda *a,**k:SimpleNamespace(stdout=b'compose-admin-1\n'))
    m.verify_non_targets(manifest)
    monkeypatch.setattr(m,'run',lambda *a,**k:SimpleNamespace(stdout=b'compose-admin-1\nforeign\n'))
    with pytest.raises(m.GuardError,match='running_container_set_changed'):m.verify_non_targets(manifest)
    monkeypatch.setattr(m,'run',lambda *a,**k:SimpleNamespace(stdout=b'compose-backend-1\n'))
    with pytest.raises(m.GuardError,match='running_container_set_changed'):m.verify_non_targets(manifest)


def test_complete_fixed_incremental_plan_is_valid(seeded):
    root,plan,_=seeded
    assert m.check_inputs()==plan
    assert len(plan['files'])==6 and len(plan['webFiles'])==17 and len(plan['beforeInventory'])==230
    assert len(plan['webBefore']|plan['webFiles'])==328 and len(plan['openapiAfter']['paths'])==203


@pytest.mark.parametrize('change',['extra','before','schema','settings','webBefore','nonTargets','gates','fields','tcp','support','symlink','authorization','source','public_mode','immutable','unapproved_backend','web_scope','expected_probe','scope','baseline'])
def test_incremental_scope_payload_schema_and_authorization_drift_never_accepted(seeded,change):
    root,p,flush=seeded
    if change=='extra':p['providerCalls']=1
    elif change=='before':p['beforeInventory'].pop(next(iter(p['beforeInventory'])))
    elif change=='schema':p['openapiAfter']['paths'].pop(next(iter(p['openapiAfter']['paths'])))
    elif change=='settings':p['configBeforeSha']='0'*64
    elif change=='webBefore':p['webBefore']['index.html']='0'*64
    elif change=='nonTargets':p['nonTargets'].pop(next(iter(p['nonTargets'])))
    elif change=='gates':p['gates']=p['gates'][:-1]
    elif change=='fields':p['gateFields'][p['gates'][0]]=[]
    elif change=='tcp':p['tcpGate']='none'
    elif change=='support':p['supportFiles']['unknown.py']='0'*64
    elif change=='symlink':
        file=root/'authorization.json';raw=file.read_bytes();file.unlink();(root/'synthetic-target').write_bytes(raw);file.symlink_to(root/'synthetic-target')
    elif change=='authorization':(root/'authorization.json').write_text('{}')
    elif change=='source':(root/'input'/next(iter(p['files']))).write_text('unapproved source')
    elif change=='public_mode':(root/'web-input/index.html').chmod(0o600)
    elif change=='immutable':p['webFiles']['assets/unknown-old.js']='0'*64
    elif change=='unapproved_backend':p['files']['apps/backend/app/deps.py']='0'*64
    elif change=='web_scope':p['webFiles']['nginx.conf']='0'*64
    elif change=='expected_probe':p['probeExpected']['passed']=False
    elif change=='scope':p['verified']['providerCallsByReleaseControllerAndOfflineProbe']=1
    elif change=='baseline':(root/'baseline.json').write_text('{}')
    flush()
    with pytest.raises(m.GuardError):m.check_inputs()



def test_r2_only_adapts_original_r1_public_verification_authorization_and_unique_tags():
    import ast
    old=HERE/'fixtures/r1-payload/release_cn_written_multi_screen.py'
    def functions(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
    before=functions(old);after=functions(Path(m.__file__))
    assert {n for n in before if before[n]!=after[n]}=={'public_checks','check_inputs','prepare'}
    assert set(after)-set(before)=={'public_static_route'}
    for service in ('backend','web'):
        assert m.BASES[service][0]!=load('r1compare',old).BASES[service][0]


def test_r2_backend_web_and_probe_payloads_are_byte_identical_to_tested_r1(seeded):
    root,plan,_=seeded
    old=HERE/'fixtures/r1-payload'
    before=json.loads((old/'input.json').read_bytes())
    assert plan['files']==before['files'] and plan['webFiles']==before['webFiles']
    for folder,mapping in [('input',plan['files']),('web-input',plan['webFiles'])]:
        for name,checksum in mapping.items():assert m.digest((old/folder/name).read_bytes())==m.digest((root/folder/name).read_bytes())==checksum
    assert (old/'probe/offline-probe.py').read_bytes()==(root/'probe/offline-probe.py').read_bytes()


def test_r2_actual_routing_diagnosis_is_frozen_and_required(seeded):
    root,plan,flush=seeded
    assert m.digest((root/'public-route-diagnosis.json').read_bytes())==plan['publicRouteDiagnosisSha256']
    (root/'public-route-diagnosis.json').write_text('{}')
    with pytest.raises(m.GuardError):m.check_inputs()


def test_r2_embedded_public_logic_equals_standalone_tested_version():
    import ast
    standalone=Path(__file__).parent/'public-checks-fixed.py'
    tree=ast.parse(standalone.read_text())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='public_checks')
    transformed=ast.get_source_segment(standalone.read_text(),function).replace('def public_checks(m):','def public_checks():').replace('m.','')
    actual=next(n for n in ast.parse(Path(m.__file__).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='public_checks')
    assert ast.dump(ast.parse(transformed).body[0],include_attributes=False)==ast.dump(actual,include_attributes=False)
