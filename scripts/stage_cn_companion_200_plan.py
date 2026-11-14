"""Exclusively stage actual candidate input/probe receipt; no prepare or cutover."""
from __future__ import annotations
import argparse,base64,hashlib,json,os
from pathlib import Path
import shlex,subprocess
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'artifacts/cn-companion-2.0.0-live-preflight/local-staging-review'
REMOTE='/opt/offersteady/releases/20261114-cn-companion-200-1'
INPUT_SHA='3cefcfd258034a55c46c3554a654900625972dbc7f49c7fe9fd633615f1c0ab1'
PROBE_SHA='07c5a408f25a93d456710340cd84a8bddecd6a788b11b281a748871b0e8e88e8'
IMAGE='sha256:4c1b3c60ba2366bce93831cc0684aab703935388f8b38a6d1a95444f9d96b25e'
class GuardError(RuntimeError):pass

def require(v,msg):
 if not v:raise GuardError(msg)
def sha(v):return hashlib.sha256(v).hexdigest()

def payload():
 a=(LOCAL/'input.json').read_bytes();b=(LOCAL/'candidate-probe-result.json').read_bytes();require(sha(a)==INPUT_SHA and sha(b)==PROBE_SHA,'local_plan_changed')
 p=json.loads(a);q=json.loads(b);require(p['candidates']['backend']['image']==IMAGE and p['candidateProbe']['resultSha256']==PROBE_SHA and q['image']==IMAGE and q['passed'] is True,'local_proof_invalid')
 return {'input.json':a,'candidate-probe-result.json':b}

REMOTE_SCRIPT=r'''
import base64,fcntl,hashlib,json,os,subprocess,sys
from pathlib import Path
p=json.loads(sys.stdin.buffer.read());root=Path('/opt/offersteady/releases/20261114-cn-companion-200-1')
if root.is_symlink() or root.resolve()!=root or not root.is_dir():raise SystemExit(1)
fd=os.open(root/'release.lock',os.O_RDWR|getattr(os,'O_NOFOLLOW',0));lock=os.fdopen(fd,'r+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
proof=json.loads((root/'candidate-build-result.json').read_bytes());files=p['files']
if set(files)!={'input.json','candidate-probe-result.json'} or proof.get('serviceSwitched') is not False:raise SystemExit(1)
raw={name:base64.b64decode(v['data'],validate=True) for name,v in files.items()}
for name,b in raw.items():
 if hashlib.sha256(b).hexdigest()!=files[name]['sha256']:raise SystemExit(1)
plan=json.loads(raw['input.json']);candidate=json.loads(raw['candidate-probe-result.json'])
if candidate!=proof['probe'] or plan['candidates']['backend']['image']!=proof['candidateImage'] or plan['candidateProbe']['resultSha256']!=hashlib.sha256(raw['candidate-probe-result.json']).hexdigest():raise SystemExit(1)
backend=json.loads(subprocess.check_output(['docker','inspect','compose-backend-1']))[0]
if backend['Id']!='fe11497d82c625b47dc7e5ffcd0ed6463d17dda9259e18db18a81d45f9021a94' or backend['Image']!='sha256:58d39c035650ba6619bd5783b6e344a49e1a10eadad962ee9a7aa9638a5e7e43' or not backend['State']['Running']:raise SystemExit(1)
image=json.loads(subprocess.check_output(['docker','image','inspect',proof['candidateImage']]))[0]
if image['Id']!=proof['candidateImage']:raise SystemExit(1)
for name in files:
 if (root/name).exists() or (root/name).is_symlink():raise SystemExit(1)
for name,b in raw.items():
 fd=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
for name in files:
 if hashlib.sha256((root/name).read_bytes()).hexdigest()!=files[name]['sha256']:raise SystemExit(1)
print(json.dumps({'staged':True,'files':2,'serviceSwitched':False}));lock.close()
'''

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');a=parser.parse_args();require(a.execute,'explicit_execute_required');files=payload();data={'files':{n:{'data':base64.b64encode(v).decode(),'sha256':sha(v)} for n,v in files.items()}}
 ssh=['ssh','-o','IdentitiesOnly=yes','-o','BatchMode=yes','-i',str(Path.home()/'.ssh/id_ed25519_oneshowtools_server'),'-o','ConnectTimeout=10','-o','StrictHostKeyChecking=yes',os.environ['OFFERSTEADY_CN_SSH_TARGET']];p=subprocess.run(ssh+[shlex.join(['python3','-c',REMOTE_SCRIPT])],input=json.dumps(data).encode(),capture_output=True,timeout=30);require(p.returncode==0,'remote_plan_staging_failed_unknown_state');x=json.loads(p.stdout);require(x=={'staged':True,'files':2,'serviceSwitched':False},'remote_plan_receipt_invalid');print(json.dumps(x))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'ok':False,'reason':str(e) if isinstance(e,GuardError) else 'plan_staging_failed_unknown_state'}));raise SystemExit(1) from None
