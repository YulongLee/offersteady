"""Server-side guarded candidate preparation. Never switches running services.

Requires a reviewed, exclusively created release directory with local-staging-review
files. Call only after independent review. Outputs aggregates and image IDs only.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/opt/offersteady/releases/20261114-cn-companion-200-1')
CONTEXT = ROOT / 'image-build-context'
IMAGE = 'sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43'
CONTAINER = 'fe11497d82c625b47dc7e5ffcd0ed6463d17dda9259e18db18a81d45f9021a94'
TAG = 'offersteady-cn-backend:companion-200-candidate-20261115-1'
BASELINE_SHA = 'c9aa6e0f9681f29d84adcbe6faac0a726b7354b164f802db0a0ed0f45210c20a'
CONTROLLER_SHA = 'dfeded9c4fe7d97e1b2f3dbbe9e41bfafad4059d44d5a253f16873ccf32cbd1b'
PLAN_SHA = 'd273e5c159d7ab5aa30c47372b2bb4fd2bb2307d6c2b0db5ff2208cf61ea01c7'
COMPOSE_HASHES_SHA = '3391580b22c0d0d3ea53041269d5ef6f574e7da98a74a78bdb42c1e9c358c310'
FILES = {'overlay/apps/backend/app/modules/web.py':'e4865462d344f579db425414fecf06a74378ac6e70df22c74337c3813d26d3a0',
         'overlay/apps/backend/app/desktop_release_manifest.json':'6cb2a0e01afa7c8539a1cccdb1f0d0c8dd1907304ffe71711438ae6b70061340'}
DOCKERFILE = ('FROM '+IMAGE+'\nCOPY overlay/ /app/\n').encode()

class GuardError(RuntimeError): pass

def require(v, reason):
    if not v: raise GuardError(reason)

def sha(data): return hashlib.sha256(data).hexdigest()

def run(args, *, data=None, timeout=60, allowed=(0,)):
    try: p=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
    except Exception: raise GuardError('process_unavailable') from None
    require(p.returncode in allowed, 'process_failed')
    return p

def validate_context(root=CONTEXT):
    require(root.is_dir() and not root.is_symlink(), 'context_root_invalid')
    wanted_files = {'Dockerfile', *FILES}
    wanted_dirs = {'overlay','overlay/apps','overlay/apps/backend','overlay/apps/backend/app','overlay/apps/backend/app/modules'}
    actual_files, actual_dirs = set(), set()
    for p in root.rglob('*'):
        rel=p.relative_to(root).as_posix()
        require(not p.is_symlink(), 'context_symlink_refused')
        if p.is_dir(): actual_dirs.add(rel)
        elif p.is_file():
            require(p.stat().st_nlink == 1 and p.stat().st_mode & 0o777 == 0o644, 'context_file_mode_invalid')
            actual_files.add(rel)
        else: raise GuardError('context_file_type_invalid')
    require(actual_dirs==wanted_dirs and actual_files==wanted_files, 'context_inventory_invalid')
    require((root/'Dockerfile').read_bytes()==DOCKERFILE, 'dockerfile_changed')
    for name,h in FILES.items(): require(sha((root/name).read_bytes())==h, 'context_bytes_changed')

def all_release_locks():
    # Existing per-release locks, plus this release's lock; no universal lock
    # exists, so process detection and identity rechecks are still mandatory.
    handles=[]
    own_locked=False
    for directory in sorted(ROOT.parent.iterdir()):
        if not directory.is_dir() or directory.is_symlink(): continue
        p=directory/'release.lock'
        if not p.exists() and directory != ROOT: continue
        fd=os.open(p,os.O_RDWR | (os.O_CREAT if directory == ROOT else 0) | getattr(os,'O_NOFOLLOW',0),0o600)
        handle=os.fdopen(fd,'r+')
        try: fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            handle.close()
            for old in handles: old.close()
            raise GuardError('concurrent_release_lock') from None
        handles.append(handle)
        if directory == ROOT: own_locked=True
    require(own_locked, 'own_lock_missing')
    return handles

def no_known_concurrency():
    # Counts only known release/build/upload patterns; it is not proof of
    # absolute zero activity by unrelated custom processes.
    me, parent=os.getpid(),os.getppid()
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        if int(p.parent.name) in (me,parent): continue
        try: args=p.read_bytes().split(b'\0')
        except FileNotFoundError: continue
        except Exception: raise GuardError('process_inventory_unavailable') from None
        if not args: continue
        executable=Path(os.fsdecode(args[0])).name
        strings=[os.fsdecode(a) for a in args[1:]]
        suspicious=(executable in ('docker','buildctl','buildkitd') and any(v in ('build','buildx') for v in strings)) or any(
            Path(v).name.startswith(('release_cn_', 'stage_upload_cn_companion_', 'upload_cn_companion_', 'build_cn_companion_')) for v in strings)
        require(not suspicious, 'concurrent_release_process')

def capacity():
    mem={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        a=line.split()
        if a and a[0] in ('MemAvailable:',): mem[a[0][:-1]]=int(a[1])*1024
    require(mem.get('MemAvailable',0)>=2*1024**3, 'host_memory_insufficient')
    disk=os.statvfs('/var/lib/docker'); require(disk.f_bavail*disk.f_frsize>=4*1024**3, 'docker_storage_insufficient')
    backend=json.loads(run(['docker','inspect',CONTAINER]).stdout)[0]
    pid=backend['State']['Pid']; require(type(pid) is int and pid>0,'backend_pid_unavailable')
    lines=Path(f'/proc/{pid}/cgroup').read_text().splitlines()
    cg=next((s.split(':',2)[2] for s in lines if s.startswith('0::')),None)
    require(cg is not None,'cgroup_unavailable')
    root=Path('/sys/fs/cgroup'); p=root.joinpath(cg.lstrip('/'))
    while p!=root:
        require(root in p.parents and not p.is_symlink(),'cgroup_path_invalid')
        try: limit=(p/'memory.max').read_text().strip();used=int((p/'memory.current').read_text())
        except Exception: raise GuardError('cgroup_ancestor_unavailable') from None
        require(limit=='max' or int(limit)-used>=2*1024**3,'cgroup_memory_insufficient')
        p=p.parent

def load_controller():
    f=ROOT/'release_cn_companion_200_backend.py'
    require(f.is_file() and not f.is_symlink(),'controller_missing')
    spec=importlib.util.spec_from_file_location('cn200_candidate_controller',f)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    return m

def preflight(R,plan):
    no_known_concurrency(); capacity()
    current=R.inspect('compose-backend-1')
    baseline=plan['baselines']['backend']
    require((current['Id'],current['Image'])==(CONTAINER,IMAGE), 'backend_owner_changed')
    require(R.H.container_signature(current)=={k:baseline[k] for k in R.H.container_signature(current)},'backend_signature_changed')
    require(current['State']['Running'] and current['State'].get('Health',{}).get('Status')=='healthy','backend_not_healthy')
    require(R.inventory('backend') == baseline['inventory'] == R.inventory('backend',image=IMAGE), 'backend_inventory_changed')
    require(R.inventory('web') == plan['webInventory'],'web_inventory_changed')
    names=set(run(['docker','ps','--format','{{.Names}}']).stdout.decode().splitlines())
    require(names == set(plan['nonTargets']) | {'compose-backend-1'}, 'container_set_changed')
    for name, signature in plan['nonTargets'].items():
        require(R.H.container_signature(R.inspect(name)) == signature, 'non_target_changed')
    hashes=json.loads((ROOT/'compose-hashes.json').read_bytes())
    require(len(hashes)==20 and all(Path(p).is_file() and sha(Path(p).read_bytes())==v for p,v in hashes.items()),'compose_inputs_changed')
    require(R.runtime_contract() == plan['runtimeBefore'],'dependencies_changed')
    require(R.P.settings_sha(R.P.settings('backend'))==baseline['settingsSha256'],'settings_changed')
    R.verify_ancillary_inputs(plan);R.verify_single_writer()
    R.H.ROOT=R.SUPPORT
    try:
        for name in R.GATES:
            data=(R.SUPPORT/name).read_bytes()
            p=run(['docker','exec','-i','-w','/app/apps/backend','-e','OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS='+str(R.FINANCIAL_ANCHOR_MS),CONTAINER,'python','-B','-'],data=data,timeout=25,allowed=(0,75))
            counts=R.H.normalize_gate(name,json.loads(p.stdout))
            require(p.returncode==0 and not R.H.gate_has_read_or_unknown_failure(name,counts) and R.H.gate_is_idle(name,counts),'protected_work_or_unknown')
    finally:R.H.ROOT=R.ROOT
    p=run(['docker','exec','-i','-w','/app/apps/backend',CONTAINER,'python','-B','-'],data=(ROOT/R.ENTITY_GATE).read_bytes(),timeout=25,allowed=(0,75))
    R.validate_entity_gate(json.loads(p.stdout),p.returncode)
    current=R.inspect(CONTAINER);identity=R.H.running_process_identity(current);namespace=R.H.host_network_namespace(current)
    p=run(['docker','exec','-i',CONTAINER,'python','-B','-'],data=(R.SUPPORT/R.TCP_GATE).read_bytes(),timeout=15)
    x=json.loads(p.stdout); fields={'passed','atMs','establishedPort8000','tablesRead','scannedRows','scope','networkNamespaceSha256'}
    require(set(x)==fields and x['passed'] is True and x['establishedPort8000']==0 and x['tablesRead']==2 and x['scope']=='container_tcp8000_established_only' and x['networkNamespaceSha256']==namespace and 0<=int(time.time()*1000)-x['atMs']<=10000,'tcp_gate_failed')
    require(R.H.running_process_identity(R.inspect(CONTAINER))==identity,'backend_owner_changed')
    no_known_concurrency();capacity()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    require(args.execute,'explicit_execute_required')
    require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve()==ROOT,'release_root_invalid')
    raw=(ROOT/'input.template.json').read_bytes()
    require(sha(raw)==PLAN_SHA,'plan_source_changed')
    raw_compose=(ROOT/'compose-hashes.json').read_bytes()
    require(sha(raw_compose)==COMPOSE_HASHES_SHA,'compose_baseline_changed')
    plan=json.loads(raw)
    require(plan['candidates']['backend']['image'] is None and plan['candidateProbe']['resultSha256'] is None,'template_not_unfilled')
    handles=all_release_locks()
    try:
        require(plan['supportFiles'].get('release_cn_companion_200_backend.py')==CONTROLLER_SHA,'controller_source_changed')
        for name,h in plan['supportFiles'].items():
            relative=Path(name)
            require(not relative.is_absolute() and '..' not in relative.parts,'support_path_invalid')
            p=ROOT/relative
            require(all(not parent.is_symlink() for parent in (p,*p.parents) if parent != ROOT.parent),'support_symlink_refused')
            require(p.is_file() and p.stat().st_nlink == 1 and sha(p.read_bytes())==h,'support_source_changed')
        require(sha((ROOT/'candidate-probe.py').read_bytes())==plan['candidateProbe']['scriptSha256'],'probe_source_changed')
        R=load_controller()
        require(set(plan['supportFiles'])==R.support_paths(),'support_scope_invalid')
        validate_context(); preflight(R,plan)
        require(run(['docker','image','inspect',IMAGE]).returncode==0,'baseline_image_missing')
        missing=run(['docker','image','inspect',TAG],allowed=(0,1));require(missing.returncode!=0,'candidate_tag_already_exists')
        validate_context()
        run(['docker','build','--network','none','--pull=false','-t',TAG,str(CONTEXT)],timeout=300)
        validate_context()
        candidate=R.inspect(TAG);base=R.inspect(IMAGE);R.H.verify_image_base(candidate,base)
        require(R.inventory('backend',image=candidate['Id'])==plan['candidates']['backend']['inventory'],'candidate_inventory_changed')
        preflight(R,plan)
        env=R.environment(R.inspect(CONTAINER)); require(all('\n' not in k+v and '\r' not in k+v for k,v in env.items()),'environment_invalid')
        envfile=ROOT/'candidate-probe.env.private';fd=os.open(envfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(fd,'w') as f:f.write(''.join(k+'='+v+'\n' for k,v in sorted(env.items())))
        p=run(['docker','run','--rm','-i','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory','768m','--env-file',str(envfile),'-e','OFFERSTEADY_RELEASE_PROBE_IMAGE='+candidate['Id'],'--workdir','/app/apps/backend','--entrypoint','python',candidate['Id'],'-B','-'],data=(ROOT/'candidate-probe.py').read_bytes(),timeout=90)
        result=json.loads(p.stdout);require(result.get('passed') is True and result.get('image')==candidate['Id'],'candidate_probe_failed')
        preflight(R,plan)
        proof={'candidateImage':candidate['Id'],'derivedFrom':IMAGE,'probe':result,'serviceSwitched':False}
        path=ROOT/'candidate-build-result.json';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(fd,'w') as f:json.dump(proof,f,sort_keys=True);f.write('\n')
        print(json.dumps(proof,sort_keys=True))
    finally:
        for h in handles:h.close()

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'ok':False,'reason':str(e) if isinstance(e,GuardError) else 'preparation_failed','serviceSwitched':False}))
        raise SystemExit(1) from None
