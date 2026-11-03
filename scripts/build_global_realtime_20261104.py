"""Apply the reviewed CN delta to exact Global public inputs, never the root build."""
from pathlib import Path
import ast, difflib, hashlib, json, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'artifacts/global-realtime-blocking-20261104'
CN=ROOT/'artifacts/cn-realtime-shared-local-20261103/baseline'
SCOPE=json.loads((ROOT/'artifacts/cn-realtime-shared-local-20261103/final-source-scope.json').read_text())['changedOrAddedRuntimeFiles']

def adapted_delta(before,after):
    a,b=before.splitlines(keepends=True),after.splitlines(keepends=True)
    output=[]
    for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        part=b[k:l]
        if tag!='equal':
            part=[s.replace('product_edition == "cn"','product_edition == "global"')
                   .replace('"product_edition", None) == "cn"','"product_edition", None) == "global"')
                   .replace('"product_edition", None) != "cn"','"product_edition", None) != "global"')
                   .replace('product_edition != "cn"','product_edition != "global"') for s in part]
        output.extend(part)
    return ''.join(output)

def main():
    dest=E/'candidate-initial'
    assert not dest.exists(),'candidate_exists'
    baseline=json.loads((E/'baseline-public.json').read_text())['backend']['inventory']
    for n,h in baseline.items():
        data=(E/'baseline'/n).read_bytes();assert hashlib.sha256(data).hexdigest()==h
    shutil.copytree(E/'baseline',dest)
    work=E/'merge-inputs';work.mkdir(exist_ok=False)
    conflicts=[]
    for f in SCOPE:
        current=(ROOT/f).read_text();p=dest/f
        if not (CN/f).exists():
            data=current.replace('product_edition != "cn"','product_edition != "global"')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data);continue
        previous=(CN/f).read_text()
        adapted=adapted_delta(previous,current)
        their=work/(Path(f).name+'.cn-delta');their.write_text(adapted)
        result=subprocess.run(['git','merge-file','-p',str(p),str(CN/f),str(their)],capture_output=True)
        assert result.returncode in (0,1,2,3),result.stderr
        p.write_bytes(result.stdout)
        if result.returncode:conflicts.append(f)
    (E/'initial-merge.json').write_text(json.dumps({'scope':SCOPE,'conflicts':conflicts},indent=2)+'\n')
    print(json.dumps({'files':len(SCOPE),'conflicts':conflicts}))

def resolve_reviewed_conflicts():
    """Keep Global-specific contexts and add only reviewed nodes."""
    import re
    dest=E/'candidate-initial'
    for relative in json.loads((E/'initial-merge.json').read_text())['conflicts']:
        path=dest/relative;s=path.read_text()
        s=re.sub(r'^<<<<<<< [^\n]*\n(.*?)^=======\n.*?^>>>>>>> [^\n]*\n',lambda m:m.group(1),s,flags=re.M|re.S)
        if relative.endswith('/main.py'):
            s=s.replace('from app.middleware.request_context import RequestContextMiddleware\n',
                        'from app.middleware.request_context import RequestContextMiddleware\nfrom app.platform.cn_realtime_lifespan import with_cn_realtime_lifespan\n')
            s=s.replace('version=settings.app_version, lifespan=lifespan)',
                        'version=settings.app_version, lifespan=with_cn_realtime_lifespan(lifespan, settings))')
        elif relative.endswith('/modules/realtime_speech.py'):
            s=s.replace('from app.services.realtime_control_executor import run_realtime_control\n',
                        'from app.services.realtime_control_executor import run_realtime_control\nfrom app.services.cn_realtime_io_executor import run_cn_realtime_io, drain_cn_realtime_cleanup\n')
            # Global already treats these errors as terminal. Retain that
            # branch, while moving its synchronous disconnect to lifecycle.
            s=s.replace('                        service.disconnect_publisher(token=token)\n',
                        '                        await _disconnect_voice_publisher(websocket, service, token=token)\n')
        else:
            s=s.replace('    def save_frame_receipt(self, receipt):\n',
                        '    def save_frame_receipt(self, receipt):\n        if self._cn_entity_mode(): return self._cn_saved("receipt", receipt)\n')
            s=s.replace('        """Remove ended-session realtime state while retaining review transcripts."""\n',
                        '        """Remove ended-session realtime state while retaining review transcripts."""\n        cleared = self._cn_controls.call("clear", session_id) if self._cn_entity_mode() else 0\n')
            needle='        resources["cleared_publishers"] = max(resources["cleared_publishers"], len(publisher_ids))\n'
            s=s.replace(needle,'        if self._cn_entity_mode():\n            with self._runtime_lock:\n                for key in [key for key, item in self.candidates.items() if item.session_id == session_id]:\n                    self.candidates.pop(key, None)\n            resources["cleared_candidates"] = int(cleared)\n'+needle)
            s=s.replace('"面试会话已结束，不能继续更新实时状态。"',
                        '"The interview session has ended; realtime state can no longer be updated."')
        path.write_text(s);ast.parse(s)
    for p in dest.rglob('*.py'):ast.parse(p.read_text())
    service=dest/'apps/backend/app/services/realtime_speech_service.py'
    s=service.read_text()
    s=s.replace('        self._session_cleanup_locks: dict[str, threading.Lock] = {}\n',
                '        self._session_cleanup_locks: dict[str, threading.Lock] = {}\n        self._session_cleanup_lock_users: dict[str, int] = {}\n')
    cn_text=(ROOT/'apps/backend/app/services/realtime_speech_service.py').read_text()
    cn_lines=cn_text.splitlines(True)
    functions={n.name:n for n in ast.walk(ast.parse(cn_text)) if isinstance(n,ast.FunctionDef)}
    helpers=''.join(''.join(cn_lines[functions[name].lineno-1:functions[name].end_lineno])+'\n\n' for name in ('_acquire_session_cleanup_lock','_release_session_cleanup_lock'))
    s=s.replace('    def _touch_session_activity(',helpers+'    def _touch_session_activity(',1)
    start='        with self._session_activity_lock:\n            cleanup_lock = self._session_cleanup_locks.setdefault(session_id, threading.Lock())\n        with cleanup_lock:\n'
    assert s.count(start)==1
    before,rest=s.split(start,1)
    body,after=rest.split('\n    def reconcile_idle_session(',1)
    s=before+'        cleanup_lock = self._acquire_session_cleanup_lock(session_id)\n        try:\n            with cleanup_lock:\n'+''.join('    '+line if line.strip() else line for line in body.splitlines(True))+'        finally:\n            self._release_session_cleanup_lock(session_id, cleanup_lock)\n\n    def reconcile_idle_session('+after
    pop='                getattr(self, "_session_cleanup_locks", {}).pop(session_id, None)\n'
    assert s.count(pop)==1
    s=s.replace(pop,'                if not getattr(self, "_session_cleanup_lock_users", {}).get(session_id):\n    '+pop)
    # Supersede keeps its original Global event/body, but uses the same lock
    # identity as capture and explicit end while closing each old session.
    begin='        for conflict in conflicts:\n            self.session_service.end_session(user_id=user_id, session_id=conflict.session_id)\n'
    assert s.count(begin)==1
    before,rest=s.split(begin,1)
    body,after=rest.split('        self._invalidate_control_query_cache()\n        return sorted(conflict_ids)',1)
    first='            self.session_service.end_session(user_id=user_id, session_id=conflict.session_id)\n'
    body=body.replace('            self._reset_realtime_session(session_id=conflict.session_id, retired=True)\n',
                      '            self._reset_realtime_session(session_id=conflict.session_id, retired=True)\n            self.repository.clear_session_runtime(session_id=conflict.session_id, preserve_transcripts=True)\n')
    s=before+'        for conflict in conflicts:\n            cleanup_lock = self._acquire_session_cleanup_lock(conflict.session_id)\n            try:\n                with cleanup_lock:\n'+''.join('        '+line if line.strip() else line for line in (first+body).splitlines(True))+'            finally:\n                self._release_session_cleanup_lock(conflict.session_id, cleanup_lock)\n        self._invalidate_control_query_cache()\n        return sorted(conflict_ids)'+after
    ast.parse(s);service.write_text(s)
    actual={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()}
    baseline=json.loads((E/'baseline-public.json').read_text())['backend']['inventory']
    changed={n:h for n,h in actual.items() if baseline.get(n)!=h}
    assert set(changed)==set(SCOPE)
    (E/'candidate-manifest.json').write_text(json.dumps(actual,indent=2,sort_keys=True)+'\n')
    (E/'allowed-delta.json').write_text(json.dumps(changed,indent=2,sort_keys=True)+'\n')
    diff=''.join(''.join(difflib.unified_diff((E/'baseline'/n).read_text().splitlines(True) if (E/'baseline'/n).exists() else [],(dest/n).read_text().splitlines(True),fromfile='baseline/'+n,tofile='candidate/'+n)) for n in sorted(changed))
    (E/'candidate.diff').write_text(diff)
    print(json.dumps({'inputs':len(actual),'changed':len(changed),'unchanged':len(actual)-len(changed),'compiled':True}))

if __name__=='__main__':
    import sys
    resolve_reviewed_conflicts() if '--resolve' in sys.argv else main()
