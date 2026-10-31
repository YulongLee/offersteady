"""Pinned CN Web-only release; private state stays on the deployment host."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path('/opt/offersteady/releases/20261027-cn-search-content-1')
SUPPORT = Path(__file__).parent/'release_support/cn_upload20m_model1017_20261021_r2'
RELEASE = 'cn-search-content-20261027.1'
WEB = 'compose-web-1'
ALLOW_EXISTING_PREPARATION_PAGE = False
PREPARATION_EXCEPTION_APPLIED = False
BASE_IMAGE = 'sha256:407376001c127de09cbb93d6bd9ee5f30dcace2693eb0c60e51c22e27cc49c1f'
BASE_ID = '0ffcf7f58e310ad667d2ade0dc8d57af7a74b609e46244bf96541972f016a1a9'
GATES = ('legacy-gates/idle_gate.py','legacy-gates/check-idle.py','legacy-gates/readiness-idle.py',
         'extra_idle_gate.py','active_work_gate.py','resume_optimizer_idle_gate.py','financial_idle_gate.py')
spec = importlib.util.spec_from_file_location('cn_search_release_helpers', SUPPORT/'base_helpers.py')
H = importlib.util.module_from_spec(spec); sys.modules[spec.name] = H; spec.loader.exec_module(H)
H.ROOT = ROOT
GuardError, require, digest, canonical = H.GuardError, H.require, H.digest, H.canonical
run, inspect, environment, read_json = H.run, H.inspect, H.environment, H.read_json


def save(name, value):
    path=ROOT/name; temporary=path.with_name('.'+path.name+'.'+str(os.getpid())+'.tmp')
    with temporary.open('x') as handle:
        json.dump(value,handle,sort_keys=True,indent=2); handle.write('\n');handle.flush();os.fsync(handle.fileno())
    temporary.chmod(0o600);os.replace(temporary,path)


def inventory_files(directory):
    require(directory.is_dir() and not directory.is_symlink(),'payload_directory_invalid')
    result={}
    for path in directory.rglob('*'):
        require(not path.is_symlink(),'payload_symlink_rejected')
        if path.is_file():result[path.relative_to(directory).as_posix()]=digest(path.read_bytes())
    return result


def inventory(*, image=None, unprivileged=False):
    command=['sh','-c','cd /usr/share/nginx/html && find . -type f -exec sha256sum {} +']
    require(not unprivileged or image is not None,'inventory_probe_scope_invalid')
    args=['docker','run','--rm','--read-only','--network','none',*(['--user','nginx'] if unprivileged else []),'--entrypoint',command[0],image,*command[1:]] if image else ['docker','exec',WEB,*command]
    result={}
    for line in run(args,timeout=45).stdout.decode().splitlines():
        checksum,path=line.split(None,1); require(re.fullmatch('[a-f0-9]{64}',checksum) and path.startswith('./'),'inventory_invalid')
        result[path[2:]]=checksum
    return result


def nginx_sha(*, image=None):
    command=['cat','/etc/nginx/conf.d/default.conf']
    args=['docker','run','--rm','--read-only','--network','none','--entrypoint',command[0],image,*command[1:]] if image else ['docker','exec',WEB,*command]
    return digest(run(args).stdout)


def checked_plan():
    p=read_json(ROOT/'input.json')
    required={'releaseId','baseline','candidateManifestSha256','supportFiles','pricingSha256'}
    require(required<=set(p)<=required|{'authorization'} and p['releaseId']==RELEASE,'input_scope_invalid')
    validate_authorization(p)
    b=p['baseline'];require(b['web']['id']==BASE_ID and b['web']['image']==BASE_IMAGE and len(b['inventory'])==328,'baseline_scope_invalid')
    expected={'release_cn_search_content.py',*(('release_support/cn_upload20m_model1017_20261021_r2/'+name) for name in ('base_helpers.py',*GATES))}
    require(set(p['supportFiles'])==expected,'support_scope_invalid')
    for relative,checksum in p['supportFiles'].items():
        path=ROOT/relative;require(path.is_file() and not path.is_symlink() and digest(path.read_bytes())==checksum,'release_controller_drift')
    require(digest((ROOT/'pricing.json').read_bytes())==p['pricingSha256'],'pricing_payload_drift')
    path=ROOT/'candidate/release-manifest.json'
    require(digest(path.read_bytes())==p['candidateManifestSha256'],'candidate_manifest_drift')
    m=read_json(path);require(m['releaseId']==RELEASE and m['baseWebImage']==BASE_IMAGE and m['packageReady'] is True,'candidate_scope_invalid')
    require(inventory_files(ROOT/'candidate/html')==m['inventory'],'candidate_static_drift')
    require(digest((ROOT/'candidate/nginx/default.conf').read_bytes())==m['nginx']['afterSha256'] and m['nginx']['beforeSha256']==b['nginxSha256'],'candidate_nginx_drift')
    allowed={'index.html','guide.html','privacy.html','terms.html','offersteady-build.json','sitemap.xml','llms.txt','llms-full.txt','public-facts.json','seo/pricing.html','seo/realtime-interview.html','seo/ai-interview-assistant.html'}
    require(set(m['inventory'])==set(b['inventory'])|set(m['newModules']) and len(m['newModules'])==11,'new_asset_scope_invalid')
    for name,checksum in b['inventory'].items():
        require(m['inventory'][name]==checksum or name in allowed,'unapproved_original_changed')
    for name,item in m['newModules'].items():
        require(re.fullmatch(r'assets/[A-Za-z0-9_-]+-[a-f0-9]{8}\.js',name) and item['sha256']==m['inventory'][name] and name not in b['inventory'],'new_asset_invalid')
    check_pricing_binding(p,m)
    return p,m


RATE_KEYS=('catalogVersion','answerPoints','screenshotAnswerPoints','writtenExamPoints','realtimeMinutePoints','knowledgeIndexMinimumPoints','knowledgeIndexPointsPer1000Tokens')

def normalized_pricing(envelope):
    billing=envelope.get('data',{}).get('billing',{});catalog=[]
    integer=lambda value,minimum=0:type(value) is int and value>=minimum
    require(type(billing.get('catalog')) is list and type(billing.get('rates')) is dict,'public_catalog_invalid')
    for p in billing['catalog']:
        if p.get('published') is not True:continue
        require(type(p.get('id')) is str and bool(re.fullmatch('[a-z0-9-]+',p['id'])) and type(p.get('displayName')) is str and bool(p['displayName'].strip()) and integer(p.get('priceCents'),1) and integer(p.get('catalogVersion'),1) and p.get('kind') in {'time_pass','points_pack'},'public_catalog_invalid')
        item={k:p[k] for k in ('id','displayName','kind','priceCents','catalogVersion')}
        if p['kind']=='time_pass':
            require(integer(p.get('durationDays'),1) and integer(p.get('knowledgeIndexAllowance')),'public_catalog_invalid')
            item.update(durationDays=p['durationDays'],knowledgeIndexAllowance=p['knowledgeIndexAllowance'])
        else:
            require(integer(p.get('points'),1),'public_catalog_invalid');item['points']=p['points']
        catalog.append(item)
    rates={key:billing['rates'].get(key) for key in RATE_KEYS}
    require(catalog and len({p['id'] for p in catalog})==len(catalog) and all(integer(value,1) for value in rates.values()) and all(p['catalogVersion']<=rates['catalogVersion'] for p in catalog),'public_catalog_invalid')
    return {'catalog':sorted(catalog,key=lambda p:p['id']),'rates':rates}


def pricing_fingerprint(value):
    return digest(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode())


def check_pricing_binding(p,m):
    require(digest((ROOT/'pricing.json').read_bytes())==p['pricingSha256'],'pricing_payload_drift')
    expected=read_json(ROOT/'pricing.json')
    require(set(expected)=={'catalog','rates'},'pricing_payload_invalid')
    normalized=normalized_pricing({'data':{'billing':{'catalog':[{**item,'published':True} for item in expected['catalog']],'rates':expected['rates']}}})
    require(expected==normalized and pricing_fingerprint(normalized)==m['pricing']['fingerprint'],'pricing_fingerprint_mismatch')
    require(digest((ROOT/'candidate/html/seo/pricing.html').read_bytes())==m['pricing']['htmlSha256'],'pricing_html_drift')
    return normalized


def fresh_pricing(p,m):
    expected=check_pricing_binding(p,m)
    try:
        request=Request('https://mianshiwen.cn/api/v1/web/state',headers={'Accept':'application/json','Cache-Control':'no-cache','Accept-Encoding':'identity'})
        with build_opener(ProxyHandler({})).open(request,timeout=20) as response:
            require(response.status==200,'public_catalog_unavailable');actual=normalized_pricing(json.load(response))
    except GuardError:raise
    except Exception:raise GuardError('public_catalog_unavailable') from None
    require(actual==expected and pricing_fingerprint(actual)==m['pricing']['fingerprint'],'public_catalog_changed')


def validate_authorization(p):
    allowed={'allowExistingPreparationPage':True,'scope':'one-existing-preparation-page'}
    auth=p.get('authorization',{})
    require(auth=={} or auth==allowed,'release_authorization_scope_invalid')
    require(not ALLOW_EXISTING_PREPARATION_PAGE or auth==allowed,'explicit_preparation_authorization_missing')


def action_authorization(p):
    return {'inputAuthorization':p.get('authorization',{}),'explicitAllowExistingPreparationPage':ALLOW_EXISTING_PREPARATION_PAGE,'preparationOnlyExceptionApplied':PREPARATION_EXCEPTION_APPLIED}


def preparation_only_exception(name,counts,code,unknown,protected):
    return (ALLOW_EXISTING_PREPARATION_PAGE and name=='extra_idle_gate.py' and code==75 and not unknown
            and counts.get('preparationPageLeases')==1
            and all(counts.get(key)==0 for key in protected if key!='preparationPageLeases'))


def simple_signature(c):
    return {'id':c['Id'],'image':c['Image'],'restarts':c['RestartCount'],'started':c['State']['StartedAt']}


def check_observed(p):
    before=inspect(WEB);b=p['baseline']
    require(before['Id']==BASE_ID and before['Image']==BASE_IMAGE and before['State']['StartedAt']==b['web']['started'],'baseline_owner_changed')
    require(digest(json.dumps(sorted(before['Config']['Env'])).encode())==b['web']['environmentSha256'],'baseline_environment_changed')
    require(inventory()==b['inventory'] and nginx_sha()==b['nginxSha256'],'baseline_files_changed')
    names=set(run(['docker','ps','--format','{{.Names}}']).stdout.decode().splitlines())
    require(names=={WEB,*b['nonTargets']},'container_set_changed')
    for name,value in b['nonTargets'].items():require(simple_signature(inspect(name))==value,'non_target_changed')
    return before


def check_non_targets(state):
    names=set(run(['docker','ps','--format','{{.Names}}']).stdout.decode().splitlines())
    require(names=={WEB,*state['nonTargets']},'container_set_changed')
    for name,value in state['nonTargets'].items():
        current=H.container_signature(inspect(name))
        require({k:v for k,v in current.items() if k!='health'}=={k:v for k,v in value.items() if k!='health'},'non_target_changed')


def started_ms(value):
    return int(datetime.fromisoformat(re.sub(r'(\.\d{6})\d+',r'\1',value).replace('Z','+00:00')).timestamp()*1000)


def gates(p):
    global PREPARATION_EXCEPTION_APPLIED
    validate_authorization(p)
    backend=p['baseline']['nonTargets']['compose-backend-1']; current=inspect('compose-backend-1')
    require(simple_signature(current)==backend,'gate_backend_owner_changed')
    anchor=started_ms(current['State']['StartedAt']);records=[]
    for name in GATES:
        try:
            args=['docker','exec','-i','-e','OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS='+str(anchor),'-w','/app/apps/backend',current['Id'],'python','-B','-']
            result=subprocess.run(args,input=(SUPPORT/name).read_bytes(),capture_output=True,timeout=30)
            H.ROOT=SUPPORT;counts=H.normalize_gate(name,json.loads(result.stdout))
            unknown=H.gate_has_read_or_unknown_failure(name,counts);idle=H.gate_is_idle(name,counts)
            protected,_=H.gate_contract(name)
            exception=preparation_only_exception(name,counts,result.returncode,unknown,protected)
        except Exception:raise GuardError('protected_work_gate_unavailable') from None
        finally:H.ROOT=ROOT
        PREPARATION_EXCEPTION_APPLIED=PREPARATION_EXCEPTION_APPLIED or exception
        records.append({'gate':name,'exitCode':result.returncode,'counts':counts,'preparationOnlyExceptionApplied':exception,'authorization':action_authorization(p)});save('last-idle-gates.json',records)
        require(not unknown and (result.returncode==0 or not idle),'protected_work_gate_unavailable')
        require((result.returncode==0 and idle) or exception,'protected_user_work_cutover_deferred')
    require(simple_signature(inspect('compose-backend-1'))==backend,'gate_backend_owner_changed')
    return records


def runtime_invariant(before,after,image):
    require(after['Image']==image and environment(after)==environment(before),'runtime_image_or_environment_changed')
    for key in set(before['Config'])|set(after['Config']):
        if key not in ('Image','Hostname','Labels','Env'):require(before['Config'].get(key)==after['Config'].get(key),'runtime_configuration_changed')
    hostname=after['Id'][:12] if before['Config']['Hostname']==before['Id'][:12] else before['Config']['Hostname']
    labels=lambda c:{k:v for k,v in c['Config'].get('Labels',{}).items() if not k.startswith('com.docker.compose.')}
    require(after['Config']['Hostname']==hostname and labels(before)==labels(after),'runtime_labels_changed')
    require(before['HostConfig']==after['HostConfig'] and H.canonical_mounts(before['Mounts'])==H.canonical_mounts(after['Mounts']),'runtime_host_or_mounts_changed')
    old,new=before['NetworkSettings']['Networks'],after['NetworkSettings']['Networks'];require(set(old)==set(new),'runtime_network_set_changed')
    for name in old:
        for key in ('IPAMConfig','Links','DriverOpts','GwPriority'):require(old[name].get(key)==new[name].get(key),'runtime_network_config_changed')
        aliases=lambda c,n:sorted(a for a in n.get('Aliases') or [] if a not in (c['Id'],c['Id'][:12]))
        require(aliases(before,old[name])==aliases(after,new[name]),'runtime_network_aliases_changed')


def frozen_checks(state,p):
    require(state['inputSha256']==digest((ROOT/'input.json').read_bytes()),'input_drift')
    for relative,checksum in state['privateFiles'].items():require(digest((ROOT/relative).read_bytes())==checksum,'private_snapshot_drift')
    target=state['target']; before=read_json(ROOT/'web/container-before.json');H.verify_frozen_files(target,before)
    for name,checksum in target['sourceHashes'].items():require(digest(Path(name).read_bytes())==checksum,'production_compose_or_env_drift')
    require(digest(canonical(H.rendered(target)))==target['sourceRenderedSha'],'production_render_drift')
    for kind in ('new','rollback'):
        image=state[kind+'Image'];overlay=ROOT/'web'/f'{kind}.compose.json'
        expected=H.expected_overlay(read_json(ROOT/'web/rendered-before.json'),'web',image)
        require(H.rendered(target,frozen=True,overlay=overlay)==expected,'unrelated_rendered_change')
    check_non_targets(state)


def owned_labels(current,target,kind):
    labels=current['Config']['Labels']
    require(labels.get('com.docker.compose.project')=='compose' and labels.get('com.docker.compose.service')=='web' and labels.get('com.docker.compose.project.config_files')==','.join(target['frozenComposeFiles']+[str(ROOT/'web'/f'{kind}.compose.json')]) and labels.get('com.docker.compose.project.environment_file')==','.join(target['frozenEnvFiles']) and labels.get('com.docker.compose.project.working_dir')==target['composeDirectory'],'released_compose_owner_changed')


def current_kind(state):
    current=inspect(WEB);progress=read_json(ROOT/'progress.json') if (ROOT/'progress.json').exists() else None
    if progress is None:
        require(current['Id']==BASE_ID and current['Image']==BASE_IMAGE,'baseline_owner_changed');return 'baseline',current
    signature=H.container_signature(current)
    require(signature==progress['signature'] and current['Id']==progress['id'] and current['Image']==progress['image'],'released_owner_changed')
    kind=progress['kind'];owned_labels(current,state['target'],kind)
    return kind,current


def verify_runtime(state,p,m,*,kind=None):
    frozen_checks(state,p); actual,current=current_kind(state)
    if kind is not None:require(actual==kind,'unexpected_deployment_state')
    require(current['State']['Running'] and current['RestartCount']==0,'web_not_running')
    expected_image=BASE_IMAGE if actual=='baseline' else state[actual+'Image']
    runtime_invariant(read_json(ROOT/'web/container-before.json'),current,expected_image)
    files=m['inventory'] if actual=='new' else p['baseline']['inventory']|({n:v['sha256'] for n,v in m['newModules'].items()} if actual=='rollback' else {})
    require(inventory()==files,'runtime_static_drift')
    require(nginx_sha()==(m['nginx']['afterSha256'] if actual=='new' else p['baseline']['nginxSha256']),'runtime_nginx_drift')
    return actual


def prepare():
    p,m=checked_plan()
    if (ROOT/'prepared.private.json').exists():
        state=read_json(ROOT/'prepared.private.json');verify_runtime(state,p,m);return emit(prepared=True,alreadyPrepared=True,productionChanged=False)
    before=check_observed(p);fresh_pricing(p,m);gates(p)
    require(not (ROOT/'web').exists(),'partial_preparation_requires_review')
    target=H.freeze(before,'web'); non_targets={name:H.container_signature(inspect(name)) for name in p['baseline']['nonTargets']}
    base=inspect(BASE_IMAGE)
    require(inventory(image=BASE_IMAGE)==p['baseline']['inventory'] and nginx_sha(image=BASE_IMAGE)==p['baseline']['nginxSha256'],'image_baseline_differs_runtime')
    baseline_tag='offersteady-cn-web-baseline:search-content-20261027'
    run(['docker','tag',BASE_IMAGE,baseline_tag]);require(inspect(baseline_tag)['Id']==BASE_IMAGE,'local_baseline_tag_drift')
    images={}
    for kind in ('new','rollback'):
        context=ROOT/'candidate' if kind=='new' else ROOT/'rollback-public'
        if kind=='rollback':
            (context/'assets').mkdir(parents=True,exist_ok=False)
            for name in m['newModules']:shutil.copy2(ROOT/'candidate/html'/name,context/name)
        dockerfile=ROOT/f'{kind}.Dockerfile'
        dockerfile.write_text('FROM '+baseline_tag+'\n'+('COPY html/ /usr/share/nginx/html/\nCOPY nginx/default.conf /etc/nginx/conf.d/default.conf\n' if kind=='new' else 'COPY assets/ /usr/share/nginx/html/assets/\n'))
        tag='offersteady-cn-web:search-content-20261027-'+kind
        run(['docker','build','--network','none','--pull=false','-f',str(dockerfile),'-t',tag,str(context)],timeout=240)
        image=inspect(tag);H.verify_image_base(image,base);images[kind+'Image']=image['Id']
        expected=m['inventory'] if kind=='new' else p['baseline']['inventory']|{n:v['sha256'] for n,v in m['newModules'].items()}
        require(inventory(image=image['Id'])==expected,'candidate_image_inventory_mismatch')
        require(inventory(image=image['Id'],unprivileged=True)==expected,'candidate_public_files_not_readable')
        require(nginx_sha(image=image['Id'])==(m['nginx']['afterSha256'] if kind=='new' else p['baseline']['nginxSha256']),'candidate_image_nginx_mismatch')
        run(['docker','run','--rm','--read-only','--tmpfs','/var/cache/nginx','--tmpfs','/var/run','--network','none','--add-host','backend:127.0.0.1','--entrypoint','nginx',image['Id'],'-t'])
        H.write_json(ROOT/'web'/f'{kind}.compose.json',{'services':{'web':{'image':image['Id']}}})
    private={str(path.relative_to(ROOT)):digest(path.read_bytes()) for path in (ROOT/'web').rglob('*') if path.is_file()}
    state={'authorization':action_authorization(p),'inputSha256':digest((ROOT/'input.json').read_bytes()),'target':target,'privateFiles':private,'nonTargets':non_targets,**images}
    save('prepared.private.json',state);verify_runtime(state,p,m,kind='baseline')
    emit(prepared=True,productionChanged=False,newWebImage=images['newImage'],rollbackWebImage=images['rollbackImage'])


def switch(state,kind):
    _,before=current_kind(state);target=state['target'];image=state[kind+'Image'];overlay=ROOT/'web'/f'{kind}.compose.json'
    save('switch-intent.json',{'beforeId':before['Id'],'targetKind':kind,'targetImage':image})
    try:run(H.compose_args(target,frozen=True,overlay=overlay)+['up','-d','--no-build','--no-deps','--pull','never','web'],timeout=120)
    finally:
        current=inspect(WEB)
        if current['Id']!=before['Id'] and current['Image']==image:
            owned_labels(current,target,kind)
            save('progress.json',{'kind':kind,'id':current['Id'],'image':image,'signature':H.container_signature(current)})
            runtime_invariant(read_json(ROOT/'web/container-before.json'),current,image)
    require(inspect(WEB)['State']['Running'],'web_not_running')


def public_checks(p,m,kind):
    files=m['inventory'] if kind=='new' else p['baseline']['inventory']|({n:v['sha256'] for n,v in m['newModules'].items()} if kind=='rollback' else {})
    routes={'/':'index.html','/guide':'guide.html','/terms':'terms.html','/privacy':'privacy.html','/pricing':'seo/pricing.html','/features/realtime-interview':'seo/realtime-interview.html','/features/ai-interview-assistant':'seo/ai-interview-assistant.html',**{path:'index.html' for path in ('/login','/app/mock-interviews','/app/resume-optimizer','/app/written-exams')}}
    routes.update({'/'+name:name for name in ('llms.txt','llms-full.txt','public-facts.json','offersteady-build.json','sitemap.xml',*(m['newModules'] if kind!='baseline' else {}))})
    opener=build_opener(ProxyHandler({}));results=[]
    for path,name in routes.items():
        request=Request('https://mianshiwen.cn'+path+'?release='+RELEASE,headers={'Cache-Control':'no-cache','Accept-Encoding':'identity'})
        with opener.open(request,timeout=15) as response:
            data=response.read();require(response.status==200 and digest(data)==files[name],'public_static_mismatch')
            if path.startswith('/assets/'):
                require('javascript' in response.headers.get('Content-Type','') and 'immutable' in response.headers.get('Cache-Control',''),'public_asset_headers_invalid')
            results.append({'path':path,'status':200,'sha256':digest(data)})
    with opener.open('https://mianshiwen.cn/healthz',timeout=10) as response:require(response.status==200,'public_health_failed')
    save('public-verification.json',{'kind':kind,'checks':results,'health':200})


def restore_after_failure(state,p,m):
    restored=False
    try:
        checked_plan();kind,current=current_kind(state);frozen_checks(state,p)
        if kind=='baseline':
            runtime_invariant(read_json(ROOT/'web/container-before.json'),current,BASE_IMAGE)
            if not current['State']['Running']:
                require(current['Id']==BASE_ID and H.stopped_process(current),'baseline_stopped_process_unproven')
                gates(p);run(['docker','start',BASE_ID])
            verify_runtime(state,p,m,kind='baseline');public_checks(p,m,'baseline');restored=True
        elif kind=='new':
            gates(p);switch(state,'rollback');verify_runtime(state,p,m,kind='rollback');public_checks(p,m,'rollback');restored=True
    except Exception:pass
    save('failed-cutover.json',{'failed':True,'rollbackSucceeded':restored,'authorization':action_authorization(p)})
    raise GuardError('cutover_failed_rollback_'+('succeeded' if restored else 'needs_attention')) from None


def emit(**value):
    value.update(explicitAllowExistingPreparationPage=ALLOW_EXISTING_PREPARATION_PAGE,preparationOnlyExceptionApplied=PREPARATION_EXCEPTION_APPLIED)
    print(json.dumps(value,separators=(',',':')),flush=True)


def verify():
    p,m=checked_plan();state=read_json(ROOT/'prepared.private.json');kind=verify_runtime(state,p,m)
    require(kind in {'new','rollback'},'not_deployed');public_checks(p,m,kind);emit(verified=True,kind=kind,productionChanged=False)


def deploy(*,preflight=False):
    p,m=checked_plan();state=read_json(ROOT/'prepared.private.json');kind=verify_runtime(state,p,m)
    if (ROOT/'deployed.json').exists():
        require(kind=='new','completed_release_owner_changed');public_checks(p,m,kind);return emit(deployed=True,alreadyDeployed=True,productionChanged=False)
    if kind=='new':
        try:
            public_checks(p,m,kind)
        except Exception:restore_after_failure(state,p,m)
        save('deployed.json',{'releaseId':RELEASE,'deployed':True,'webImage':state['newImage'],'atMs':int(time.time()*1000),'authorization':action_authorization(p)});return emit(deployed=True,recoveredOwnedSwitch=True,productionChanged=False)
    require(kind=='baseline','rollback_state_requires_review');gates(p);verify_runtime(state,p,m,kind='baseline')
    if preflight:
        fresh_pricing(p,m);return emit(preflightPassed=True,productionChanged=False)
    gates(p);verify_runtime(state,p,m,kind='baseline');fresh_pricing(p,m)
    try:
        switch(state,'new');verify_runtime(state,p,m,kind='new');public_checks(p,m,'new')
        save('deployed.json',{'releaseId':RELEASE,'deployed':True,'webImage':state['newImage'],'atMs':int(time.time()*1000),'authorization':action_authorization(p)})
        emit(deployed=True,webOnly=True,webImage=state['newImage'])
    except Exception:restore_after_failure(state,p,m)



@contextmanager
def release_lock():
    with (ROOT/'release.lock').open('a') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise GuardError('another_release_action_is_running') from None
        try:yield
        finally:fcntl.flock(handle,fcntl.LOCK_UN)


def main():
    global ALLOW_EXISTING_PREPARATION_PAGE
    os.umask(0o077);parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','preflight','deploy','verify'));parser.add_argument('--allow-existing-preparation-page',action='store_true');args=parser.parse_args();action=args.action
    ALLOW_EXISTING_PREPARATION_PAGE=args.allow_existing_preparation_page
    try:
        require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve()==ROOT,'private_release_directory_missing')
        with release_lock():{'prepare':prepare,'preflight':lambda:deploy(preflight=True),'deploy':deploy,'verify':verify}[action]()
    except Exception as exc:
        reason=str(exc) if isinstance(exc,GuardError) and re.fullmatch('[a-z0-9_]+',str(exc)) else 'release_operation_failed_private_diagnostics_only'
        emit(ok=False,reason=reason);raise SystemExit(75 if reason=='protected_user_work_cutover_deferred' else 1) from None


if __name__=='__main__':main()
