"""Stage and conditionally publish exactly three frozen CN installers, serially.

Explicit --execute is required. Failed/unknown results stop immediately; no
automatic retry, deletion, manifest update, output of credentials, or restart.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'artifacts/cn-companion-2.0.0-live-preflight/desktop_release_manifest.2.0.0.hidden-history.json'
PACKAGE_DIR = Path('/Users/liyulong/.codex/worktrees/companion-floating-2-0-0/offersteady/artifacts/cn-companion-2.0.0-candidate-r2')
UPLOADER = ROOT / 'scripts/upload_cn_companion_200_object.py'
MANIFEST_SHA = '6cb2a0e01afa7c8539a1cccdb1f0d0c8dd1907304ffe71711438ae6b70061340'
UPLOADER_SHA = 'f0225c3e8a810aafc0c3b91eeaac96f3a07b311d51a39d4591e57eb2b5116984'
REMOTE_DIR = '/tmp/offersteady-cn200-20261114-stage-1'
CONTAINER = 'fe11497d82c625b47dc7e5ffcd0ed6463d17dda9259e18db18a81d45f9021a94'
ITEMS = [
    ('macos', 'arm64', 136608975, '99eeea79ef001e37c1347e8c87493291177973db83ded048f33421966904bbad'),
    ('macos', 'x64', 142139062, '8cdfbf524ce8abf0763a7e28c8d647781405deb5f0574412624f4f857527b27f'),
    ('windows', 'x64', 102182232, '2ca70baa786662c176d2a3d78831e5c1029a1369dfd68e15d799dbb5346a8af8'),
]

# No shell, no symlink traversal, no replacement; unknown/partial stages are
# deliberately left for inspection and never resumed automatically.
REMOTE_STAGE = r'''
import hashlib,json,os,sys
from pathlib import Path
d=Path(sys.argv[1]); name=sys.argv[2]; meta=json.loads(sys.argv[3]); expected=meta['sha256']; size=meta['fileSizeBytes']
if name!=Path(name).name: raise SystemExit(1)
dfd=os.open(d,os.O_RDONLY|os.O_DIRECTORY|getattr(os,'O_NOFOLLOW',0))
flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0)
fd=os.open(name,flags,0o600,dir_fd=dfd); n=0; h=hashlib.sha256()
with os.fdopen(fd,'wb') as f:
 while True:
  b=sys.stdin.buffer.read(1048576)
  if not b: break
  n+=len(b)
  if n>size: raise SystemExit(1)
  h.update(b);f.write(b)
 f.flush();os.fsync(f.fileno())
if n!=size or h.hexdigest()!=expected: raise SystemExit(1)
fd=os.open(name+'.json',flags,0o600,dir_fd=dfd)
with os.fdopen(fd,'wb') as f: f.write(json.dumps(meta,sort_keys=True).encode()); f.flush();os.fsync(f.fileno())
os.fsync(dfd);os.close(dfd)
print(json.dumps({'staged':True,'size':n,'sha256':h.hexdigest()}))
'''
REMOTE_CAPACITY = r'''
import json,os,sys
from pathlib import Path
required=int(sys.argv[1]); values={}
for line in Path('/proc/meminfo').read_text().splitlines():
 p=line.split()
 if p and p[0] in ('MemAvailable:','SwapTotal:'): values[p[0][:-1]]=int(p[1])*1024
if 'MemAvailable' not in values: raise SystemExit(1)
v=os.statvfs('/tmp'); disk=v.f_bavail*v.f_frsize
root=Path('/sys/fs/cgroup')
groups=Path('/proc/self/cgroup').read_text().splitlines()
if (root/'memory.max').is_file():
 if '0::/' not in groups: raise SystemExit(1)
 limit=(root/'memory.max').read_text().strip(); current=int((root/'memory.current').read_text().strip()); remaining=None if limit=='max' else int(limit)-current
elif (root/'memory/memory.limit_in_bytes').is_file():
 if not any(line.split(':',2)[1].split(',').count('memory') and line.split(':',2)[2]=='/' for line in groups if line.count(':')==2): raise SystemExit(1)
 limit=int((root/'memory/memory.limit_in_bytes').read_text().strip()); current=int((root/'memory/memory.usage_in_bytes').read_text().strip()); remaining=None if limit>=2**60 else limit-current
else: raise SystemExit(1)
ok=values['MemAvailable']>=1536*1024*1024 and (remaining is None or remaining>=1536*1024*1024) and disk>=required+1024*1024*1024
print(json.dumps({'ok':ok,'hostAvailable':values['MemAvailable'],'containerRemaining':remaining,'diskAvailable':disk}))
if not ok: raise SystemExit(1)
'''
REMOTE_MKDIR = "import os,sys;os.mkdir(sys.argv[1],0o700)"

# Evaluate every non-root cgroup on the host, not merely the namespace root
# visible in the container. The root cgroup need not expose memory.max.
HOST_ANCESTORS = r'''
import json,subprocess,sys
from pathlib import Path
container=sys.argv[1]
proc=subprocess.run(['docker','inspect','--format','{{.Id}} {{.State.Pid}} {{.State.Running}}',container],capture_output=True,text=True,timeout=10,check=True)
parts=proc.stdout.strip().split()
if len(parts)!=3 or parts[0]!=container or parts[2]!='true' or not parts[1].isdigit() or int(parts[1])<=0: raise SystemExit(1)
lines=Path('/proc/'+parts[1]+'/cgroup').read_text().splitlines()
groups=[line[3:] for line in lines if line.startswith('0::')]
if len(groups)!=1: raise SystemExit(1)
relative=Path(groups[0])
if not relative.is_absolute() or '..' in relative.parts: raise SystemExit(1)
root=Path('/sys/fs/cgroup'); current=root.joinpath(*relative.parts[1:]); count=0
while current != root:
 maximum=(current/'memory.max').read_text().strip()
 if maximum!='max':
  remaining=int(maximum)-int((current/'memory.current').read_text().strip())
  if remaining < 1536*1024*1024: raise SystemExit(1)
 count+=1;current=current.parent
again=subprocess.run(['docker','inspect','--format','{{.Id}} {{.State.Pid}} {{.State.Running}}',container],capture_output=True,text=True,timeout=10,check=True)
if again.stdout.strip()!=proc.stdout.strip(): raise SystemExit(1)
print(json.dumps({'ok':True,'checkedAncestors':count}))
'''


class GuardError(RuntimeError): pass


def digest(data): return hashlib.sha256(data).hexdigest()


def frozen_inputs():
    manifest_bytes = MANIFEST.read_bytes()
    source = UPLOADER.read_bytes()
    if digest(manifest_bytes) != MANIFEST_SHA or digest(source) != UPLOADER_SHA:
        raise GuardError('frozen_inputs_changed')
    manifest = json.loads(manifest_bytes)
    rows = manifest.get('entries')
    if not isinstance(rows, list) or len(rows) != 6: raise GuardError('manifest_shape_changed')
    result = []
    for platform, arch, size, checksum in ITEMS:
        matches = [e for e in rows if (e.get('platform'), e.get('architecture'), e.get('version')) == (platform, arch, '2.0.0')]
        if len(matches) != 1: raise GuardError('target_invalid')
        row = matches[0]
        name = (f'OfferSteady-Companion-2.0.0-macOS-{arch}.dmg' if platform == 'macos' else 'OfferSteady-Companion-Setup-2.0.0-Windows-x64.exe')
        if row.get('fileName') != name or row.get('fileSizeBytes') != size or row.get('sha256') != checksum:
            raise GuardError('target_drift')
        path = PACKAGE_DIR / name
        if path.is_symlink() or not path.is_file(): raise GuardError('source_invalid')
        result.append((row, path))
    return result, source


def remote(args, *, data=None, timeout=600):
    ssh = ['ssh', '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-i', str(Path.home()/'.ssh/id_ed25519_oneshowtools_server'), '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes', os.environ['OFFERSTEADY_CN_SSH_TARGET']]
    result = subprocess.run([*ssh, shlex.join(args)], input=data, capture_output=True, timeout=timeout)
    if result.returncode != 0: raise GuardError('remote_operation_failed_or_unknown')
    return result.stdout


def run(executor=remote):
    inputs, source = frozen_inputs()
    prefix = ['docker','exec','-i','-w','/app/apps/backend',CONTAINER,'python','-B','-c']
    # Fail before creating a directory if the first artifact cannot safely stage.
    if json.loads(executor(['python3','-c',HOST_ANCESTORS,CONTAINER])).get('ok') is not True:
        raise GuardError('ancestor_capacity_unavailable')
    if json.loads(executor(prefix+[REMOTE_CAPACITY,str(inputs[0][0]['fileSizeBytes'])])).get('ok') is not True:
        raise GuardError('capacity_unavailable')
    executor(prefix+[REMOTE_MKDIR,REMOTE_DIR])
    reports = []
    for row, path in inputs:
        if json.loads(executor(['python3','-c',HOST_ANCESTORS,CONTAINER])).get('ok') is not True:
            raise GuardError('ancestor_capacity_unavailable')
        if json.loads(executor(prefix+[REMOTE_CAPACITY,str(row['fileSizeBytes'])])).get('ok') is not True:
            raise GuardError('capacity_unavailable')
        fd = os.open(path, os.O_RDONLY | getattr(os,'O_NOFOLLOW',0))
        with os.fdopen(fd,'rb') as f: payload = f.read(row['fileSizeBytes']+1)
        if len(payload) != row['fileSizeBytes'] or digest(payload) != row['sha256']:
            raise GuardError('local_artifact_changed')
        name = row['fileName']
        staged = json.loads(executor(prefix+[REMOTE_STAGE,REMOTE_DIR,name,json.dumps(row)],data=payload))
        if staged != {'staged':True,'size':row['fileSizeBytes'],'sha256':row['sha256']}:
            raise GuardError('staging_unverified')
        del payload
        out = executor(prefix+[source.decode(),f'{REMOTE_DIR}/{name}.json',f'{REMOTE_DIR}/{name}'])
        report = json.loads(out)
        if not isinstance(report,dict) or report.get('objectReadbackVerified') is not True or report.get('sha256') != row['sha256'] or report.get('fileSizeBytes') != row['fileSizeBytes'] or report.get('objectKey') != row['objectKey']:
            raise GuardError('upload_or_readback_unverified')
        reports.append({'platform':row['platform'],'architecture':row['architecture'],'sha256':row['sha256'],'verified':True})
    return reports


if __name__ == '__main__':
    if sys.argv[1:] != ['--execute']:
        print('No remote actions: explicit --execute required')
        raise SystemExit(0)
    try:
        print(json.dumps({'objects':run(),'publicManifestChanged':False}))
    except Exception as exc:
        print(json.dumps({'ok':False,'errorType':type(exc).__name__,'reason':'stage_or_upload_stopped_inspect_before_retry'}))
        raise SystemExit(1)
