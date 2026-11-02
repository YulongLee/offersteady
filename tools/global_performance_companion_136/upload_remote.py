"""Upload one already-verified local Global artifact staged on the Global host."""
from pathlib import Path
import hashlib,json,sys
from remote import Remote

BASE=Path(__file__).resolve().parents[2]/'artifacts/global-performance-companion-20261102'


def main():
    target=sys.argv[1];assert target in {'mac-arm64','mac-x64','windows-x64'}
    meta=json.loads((BASE/(target+'-public-metadata.json')).read_text())
    sha=hashlib.sha256(Path(__file__).with_name('upload_installer.py').read_bytes()).hexdigest()
    code='''import subprocess,json,hashlib,sys
from pathlib import Path
root=Path("/opt/offersteady-global/releases/20261102-global-performance-companion-136-artifacts")
assert hashlib.sha256((root/"upload_installer.py").read_bytes()).hexdigest()==sys.argv[1]
c=json.loads(subprocess.check_output(["docker","inspect","offersteady-global-backend-1"]))[0]
assert c["Id"]=="7bc15c77cef86681d068d6157270f87338d0cab9f1b14c8cddf7d11e83ad7536"
cmd=["docker","run","--rm","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","64","--memory","512m","--network",c["HostConfig"]["NetworkMode"],"--env-file",str(root/"runtime.env.private"),"-e","PYTHONPATH=/app/apps/backend","-v",str(root)+":/release:ro","--workdir","/app/apps/backend","--entrypoint","python",c["Image"],"-B","/release/upload_installer.py","/release/"+sys.argv[2],"/release/"+sys.argv[3]]
r=subprocess.run(cmd,capture_output=True,timeout=600)
if r.returncode:print(json.dumps({"uploaded":False,"exitCode":r.returncode}))
else:print(r.stdout.decode().strip())
'''
    data=Remote().run(['python3','-c',code,sha,target+'-public-metadata.json',meta['fileName']],timeout=630)
    result=json.loads(data);(BASE/(target+'-upload-final-attempt.json')).write_bytes(data)
    assert result.get('objectReadbackVerified'), 'immutable_upload_failed'
    assert all(result[k]==meta[k] for k in ('platform','architecture','version','fileName','fileSizeBytes','sha256'))
    (BASE/(target+'-oss.json')).write_bytes(data);print(json.dumps(result))


if __name__=='__main__':main()
