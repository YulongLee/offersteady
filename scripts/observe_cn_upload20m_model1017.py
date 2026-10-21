"""Server-only post-release aggregate observation; never export raw logs."""
import argparse
import datetime
import json
import re
import subprocess
import time

parser=argparse.ArgumentParser()
parser.add_argument('--since-ms',required=True,type=int)
args=parser.parse_args()
now=int(time.time()*1000)
assert 0<=now-args.since_ms<=3600000
since=datetime.datetime.fromtimestamp(args.since_ms/1000,datetime.timezone.utc).isoformat()
until=datetime.datetime.fromtimestamp(now/1000,datetime.timezone.utc).isoformat()
records=[]
for name in ('compose-backend-1','compose-material-worker-1','compose-web-1'):
    d=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    p=subprocess.run(['docker','logs','--timestamps','--since',since,'--until',until,'--tail','4000',name],capture_output=True,text=True,timeout=20)
    assert p.returncode==0
    lines=(p.stdout+'\n'+p.stderr).splitlines()
    errors=sum(bool(re.search(r'"level"\s*:\s*"(?:ERROR|CRITICAL)"|\bERROR:|\[error\]|\[crit\]|\[alert\]|\[emerg\]',line)) for line in lines)
    tracebacks=sum('Traceback (most recent call last)' in line for line in lines)
    server_errors=sum(bool(re.search(r'"[A-Z]+ [^" ]+ HTTP/[0-9.]+"\s+5\d\d\b',line)) for line in lines)
    records.append({'component':name,'image':d['Image'],'running':d['State']['Running'],'health':d['State'].get('Health',{}).get('Status'),'restartCount':d['RestartCount'],'linesRead':len(lines),'tailLimitReached':len(lines)>=4000,'errorLines':errors,'tracebacks':tracebacks,'http5xx':server_errors})
print(json.dumps({'readOnly':True,'fromMs':args.since_ms,'toMs':now,'durationSeconds':round((now-args.since_ms)/1000,1),'records':records,'rawLogsExported':False,'identifiersExported':False}))
