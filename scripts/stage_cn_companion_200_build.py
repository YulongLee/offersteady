"""Exclusively stage the reviewed candidate build context; never build/switch."""
from __future__ import annotations
import argparse,base64,hashlib,json,os
from pathlib import Path
import shlex,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'artifacts/cn-companion-2.0.0-live-preflight/local-staging-review'
REMOTE='/opt/offersteady/releases/20261114-cn-companion-200-1'
PLAN_SHA='d273e5c159d7ab5aa30c47372b2bb4fd2bb2307d6c2b0db5ff2208cf61ea01c7'
BUILD_SHA='191094fb3b2a0d9f6a7e8adabcf0f4aa88df9838f67d473403aed75f9c626667'
COMPOSE_SHA='3391580b22c0d0d3ea53041269d5ef6f574e7da98a74a78bdb42c1e9c358c310'
class GuardError(RuntimeError):pass

def require(v,msg):
 if not v:raise GuardError(msg)
def sha(v):return hashlib.sha256(v).hexdigest()

def payload():
 raw=(LOCAL/'input.template.json').read_bytes();require(sha(raw)==PLAN_SHA,'plan_changed');plan=json.loads(raw)
 require(plan['candidates']['backend']['image'] is None and plan['candidateProbe']['resultSha256'] is None,'plan_already_filled')
 files={}
 for name,h in plan['supportFiles'].items():
  p=LOCAL/name;require(p.is_file() and not p.is_symlink() and sha(p.read_bytes())==h,'support_changed');files[name]=(p.read_bytes(),0o600)
 for name,h in [('candidate-probe.py',plan['candidateProbe']['scriptSha256']),('compose-hashes.json',COMPOSE_SHA),('input.template.json',PLAN_SHA)]:
  p=LOCAL/name;require(p.is_file() and not p.is_symlink() and sha(p.read_bytes())==h,'input_changed');files[name]=(p.read_bytes(),0o600)
 b=(ROOT/'scripts/build_cn_companion_200_candidate.py').read_bytes();require(sha(b)==BUILD_SHA,'build_script_changed');files['build_cn_companion_200_candidate.py']=(b,0o600)
 ctx=LOCAL/'image-build-context'; expected={'Dockerfile','overlay/apps/backend/app/modules/web.py','overlay/apps/backend/app/desktop_release_manifest.json'}
 require({p.relative_to(ctx).as_posix() for p in ctx.rglob('*') if p.is_file()}==expected,'context_changed')
 for p in ctx.rglob('*'):require(not p.is_symlink(),'context_symlink')
 for name in expected:
  path=ctx/name;files['image-build-context/'+name]=(path.read_bytes(),0o644)
 require(files['image-build-context/Dockerfile'][0]==b'FROM sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43\nCOPY overlay/ /app/\n','dockerfile_changed')
 for relative,key in [('overlay/apps/backend/app/modules/web.py','apps/backend/app/modules/web.py'),('overlay/apps/backend/app/desktop_release_manifest.json','apps/backend/app/desktop_release_manifest.json')]:
  require(sha(files['image-build-context/'+relative][0])==plan['candidates']['backend']['inventory'][key],'overlay_changed')
 return files

REMOTE_SCRIPT=r'''
import base64,hashlib,json,os,sys
from pathlib import Path
p=json.loads(sys.stdin.buffer.read());root=Path(p['root']);files=p['files'];parent=root.parent
if str(root)!='/opt/offersteady/releases/20261114-cn-companion-200-1' or parent.is_symlink() or parent.resolve()!=parent:raise SystemExit(1)
os.mkdir(root,0o700)
for name,item in sorted(files.items()):
 rel=Path(name)
 if rel.is_absolute() or '..' in rel.parts:raise SystemExit(1)
 dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 if any(p.is_symlink() for p in (dest.parent,*dest.parent.parents) if p!=parent.parent):raise SystemExit(1)
 b=base64.b64decode(item['data'],validate=True)
 if hashlib.sha256(b).hexdigest()!=item['sha256']:raise SystemExit(1)
 fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),item['mode'])
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.chmod(dest,item['mode'])
actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
if actual!=set(files) or any(p.is_symlink() for p in root.rglob('*')):raise SystemExit(1)
for name,item in files.items():
 q=root/name
 if not q.is_file() or q.stat().st_nlink!=1 or q.stat().st_mode&0o777!=item['mode'] or hashlib.sha256(q.read_bytes()).hexdigest()!=item['sha256']:raise SystemExit(1)
print(json.dumps({'staged':True,'files':len(files),'serviceSwitched':False}))
'''

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 require(args.execute,'explicit_execute_required');files=payload()
 data={'root':REMOTE,'files':{n:{'data':base64.b64encode(v).decode(),'sha256':sha(v),'mode':m} for n,(v,m) in files.items()}}
 ssh=['ssh','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-i',str(Path.home()/'.ssh/id_ed25519_oneshowtools_server'),'-o','ConnectTimeout=10','-o','StrictHostKeyChecking=yes',os.environ['OFFERSTEADY_CN_SSH_TARGET']]
 command=['python3','-c',REMOTE_SCRIPT];p=subprocess.run(ssh+[shlex.join(command)],input=json.dumps(data).encode(),capture_output=True,timeout=120)
 require(p.returncode==0,'remote_staging_failed_unknown_state'); result=json.loads(p.stdout);require(result=={'staged':True,'files':len(files),'serviceSwitched':False},'remote_staging_receipt_invalid');print(json.dumps(result))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'ok':False,'reason':str(e) if isinstance(e,GuardError) else 'staging_failed_unknown_state'}));raise SystemExit(1) from None
