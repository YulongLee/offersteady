"""Run one frozen Global release action, exporting only controller JSON output."""
from pathlib import Path
import hashlib,json,sys
from remote import Remote

BASE=Path(__file__).resolve().parents[2]/'artifacts/global-performance-companion-20261102'


def main():
    action=sys.argv[1];assert action in {'prepare','preflight','deploy','verify','rollback'}
    payload=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else BASE/'payload'
    expected={p.relative_to(payload).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in payload.rglob('*') if p.is_file()}
    assert len(expected)==16 and 'input.json' in expected and 'controller.py' in expected
    code='''from pathlib import Path
import json,sys,hashlib,subprocess
root=Path("/opt/offersteady-global/releases/20261102-global-performance-companion-136-1");expected=json.loads(sys.argv[1]);action=sys.argv[2]
assert action in ("prepare","preflight","deploy","verify","rollback") and root.is_dir() and not root.is_symlink()
for n,h in expected.items():
 p=root/n;assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==h
r=subprocess.run(["python3",str(root/"controller.py"),action],cwd=root,capture_output=True,timeout=900)
(root/(action+".stdout.private")).write_bytes(r.stdout);(root/(action+".stderr.private")).write_bytes(r.stderr)
rows=[]
for line in r.stdout.decode("utf8",errors="replace").splitlines():
 try:
  obj=json.loads(line)
  if isinstance(obj,dict):rows.append(obj)
 except Exception:pass
print(json.dumps({"action":action,"exitCode":r.returncode,"results":rows,"allPayloadHashesVerified":True}))
'''
    data=Remote().run(['python3','-c',code,json.dumps(expected),action],timeout=930)
    result=json.loads(data);(BASE/(action+'-result.json')).write_bytes(data);print(json.dumps(result))
    if result['exitCode']:raise SystemExit(result['exitCode'])


if __name__=='__main__':main()
