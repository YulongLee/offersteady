"""Noninteractive Global host operations; provider errors remain private."""
from pathlib import Path
import shlex
import subprocess


class Remote:
    def run(self,args,*,data=None,timeout=60):
        ssh=['ssh','-i',str(Path.home()/'.ssh/id_ed25519_oneshowtools_server'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=yes','root@47.84.65.103']
        r=subprocess.run(ssh+[shlex.join(args)],input=data,capture_output=True,timeout=timeout)
        if r.returncode:raise RuntimeError('global_remote_operation_failed_'+str(r.returncode))
        return r.stdout

    def put(self,path,data):
        code='from pathlib import Path;import sys,os;p=Path(sys.argv[1]);f=p.open("xb");f.write(sys.stdin.buffer.read());f.flush();os.fsync(f.fileno());f.close();os.chmod(p,0o644)'
        return self.run(['python3','-c',code,path],data=data)
