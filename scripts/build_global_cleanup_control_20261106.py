"""Apply explicit reviewed nodes to the exact Global source; never build root CN."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'artifacts/global-cleanup-control-20261106'
CN=ROOT/'artifacts/cn-cleanup-control-local-20261104'
PREFIX='apps/backend/app/'


def methods(source):
    lines=source.splitlines(True)
    return {n.name:''.join(lines[n.lineno-1:n.end_lineno]) for n in ast.walk(ast.parse(source))
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}


def replace_once(source,old,new):
    assert source.count(old)==1,old[:110]
    return source.replace(old,new,1)


def replace_method(source,name,value):
    return replace_once(source,methods(source)[name],value)


def adapted(source):
    return source.replace('product_edition == "cn"','product_edition == "global"').replace(
        '"product_edition", None) == "cn"','"product_edition", None) == "global"').replace(
        '"product_edition", None) != "cn"','"product_edition", None) != "global"')


def main():
    baseline=json.loads((E/'baseline-manifest.json').read_text())
    cn_old=json.loads((CN/'baseline-manifest.json').read_text())
    cm=json.loads((CN/'candidate-manifest.json').read_text())
    approved=cm['changed']+cm['added']
    for n,h in baseline.items():assert hashlib.sha256((E/'baseline'/n).read_bytes()).hexdigest()==h,n
    dest=E/'candidate';assert not dest.exists();shutil.copytree(E/'baseline',dest)
    for name in ('services/cn_realtime_entity_state.py','services/cn_realtime_io_executor.py'):
        p=PREFIX+name;assert baseline[p]==cn_old[p]
        (dest/p).write_bytes((CN/'candidate'/p).read_bytes())
    p=PREFIX+'services/cn_provider_close_executor.py';assert p not in baseline
    (dest/p).write_bytes((CN/'candidate'/p).read_bytes())

    p=PREFIX+'modules/realtime_speech.py';s=(dest/p).read_text()
    for operation in ('publisher_prepare','publisher_create'):
        s=replace_once(s,'lane="lifecycle", operation_name="'+operation+'"',
                       'lane="preparation", operation_name="'+operation+'"')
    (dest/p).write_text(s)

    p=PREFIX+'services/redis_realtime_speech_repository.py';s=(dest/p).read_text()
    start=methods(s)['_overlay_cn_control_entities']
    s=replace_method(s,'_overlay_cn_control_entities',replace_once(start,
        '        self.candidates = {x.candidate_id: x for x in store.all_records("candidate")}\n',
        '        store.seed_owner_indexes()\n        self.candidates = {x.candidate_id: x for x in store.all_records("candidate")}\n'))
    cn=methods((CN/'candidate'/p).read_text())
    for n in ('list_account_desktop_devices','list_session_desktop_bindings_for_user'):
        s=replace_method(s,n,cn[n])
    (dest/p).write_text(s)

    p=PREFIX+'services/dashscope_realtime_asr_gateway.py';s=(dest/p).read_text()
    cn=methods((CN/'candidate'/p).read_text())
    s=replace_once(s,'from app.services.realtime_speech_service import NonRetryableAsrError, RetryableAsrError\n',
        'from app.services.realtime_speech_service import NonRetryableAsrError, RetryableAsrError\nfrom app.services.cn_provider_close_executor import CnProviderCloseExecutor\n')
    s=replace_once(s,'        self._partial_listener: Callable[[AudioFrame, TranscriptResult], None] | None = None\n',
        '        self._partial_listener: Callable[[AudioFrame, TranscriptResult], None] | None = None\n        self._deferred_closes = CnProviderCloseExecutor(logger) if settings.product_edition == "global" else None\n')
    s=replace_method(s,'close_all_sessions',cn['close_all_sessions'])
    helpers='\n'.join(cn[n] for n in ('drain_deferred_closes','close_session_deferred','close_source_deferred',
        '_close_source_deferred','_close_detached','_detach_source_session','_mark_detached'))
    # Global already exposes closure_failures. Preserve that counter while the
    # new bounded executor records fixed privacy-safe failure evidence.
    old=cn['_close_detached']
    new='''    def _close_detached(self, session: _SourceRealtimeSession) -> None:
        def physical_close():
            try:
                session.connection.close()
            except Exception:
                with self._source_sessions_lock:
                    self._closure_failures[session.source_kind] = self._closure_failures.get(session.source_kind, 0) + 1
                raise
        if self._deferred_closes is None:
            try:
                physical_close()
            except Exception:
                pass
        else:
            self._deferred_closes.close(physical_close)
'''
    helpers=replace_once(helpers,old,new)
    marker=methods(s)['close_source'];s=replace_once(s,marker,helpers+'\n'+marker)
    (dest/p).write_text(s)

    p=PREFIX+'services/realtime_speech_service.py';s=(dest/p).read_text()
    cn=methods((CN/'candidate'/p).read_text())
    helpers='\n'.join(adapted(cn[n]) for n in ('_close_asr_session','_read_performance_ack_access',
        '_retire_session_id','_unretire_session_id'))
    marker=methods(s)['_session_is_retired'];s=replace_once(s,marker,helpers+'\n'+marker)
    old=methods(s)['terminate_session_for_admin']
    block=cn['terminate_session_for_admin'].split('                binding_read =',1)[1].split('                for binding in bindings:',1)[0]
    new=replace_once(old,'                for binding in self.repository.list_session_desktop_bindings_for_user(user_id=user_id):',
        adapted('                binding_read ='+block)+'                for binding in bindings:')
    s=replace_method(s,'terminate_session_for_admin',new)
    for name in ('_pause_for_insufficient_realtime_balance','_control_capture'):
        old=methods(s)[name]
        new=replace_once(old,'self.asr_gateway.close_session(session_id=session_id)',
            'self._close_asr_session(session_id=session_id)')
        s=replace_method(s,name,new)
    s=replace_method(s,'_cleanup_source_resources',adapted(cn['_cleanup_source_resources']))
    old=methods(s)['_reset_realtime_session']
    new=replace_once(old,'        if retired:\n            self._stop_realtime_metering(session_id=session_id)\n',
        '        if retired:\n            self._retire_session_id(session_id)\n            self._stop_realtime_metering(session_id=session_id)\n        else:\n            self._unretire_session_id(session_id)\n')
    first=new.index('            if retired:',new.index('        with self._frame_worker_lock:'))
    last=new.index('            queues = [',first)
    new=new[:first]+new[last:]
    new=replace_once(new,'int(self.asr_gateway.close_session(session_id=session_id))',
        'self._close_asr_session(session_id=session_id)')
    s=replace_method(s,'_reset_realtime_session',new)
    old=methods(s)['_verify_performance_ack_session'];assert old.count('self.session_service.get_session(')==2
    s=replace_method(s,'_verify_performance_ack_session',old.replace('self.session_service.get_session(',
        'self._read_performance_ack_access('))
    old=methods(s)['acknowledge_runtime_timing'];lines=old.splitlines(True)
    expr=next(n for n in ast.walk(ast.parse(old.replace('    def ','def ',1))) if isinstance(n,ast.Expr)
              and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='log_event')
    log=''.join(lines[expr.lineno-1:expr.end_lineno])
    new=replace_once(old,log,'        if getattr(self.settings, "product_edition", None) != "global" or self.logger.isEnabledFor(logging.DEBUG):\n'+''.join('    '+line for line in log.splitlines(True)))
    s=replace_method(s,'acknowledge_runtime_timing',new)
    (dest/p).write_text(s)

    allowed={
        'modules/realtime_speech.py':{'create_publisher'},
        'services/redis_realtime_speech_repository.py':{'_overlay_cn_control_entities','list_account_desktop_devices','list_session_desktop_bindings_for_user'},
        'services/dashscope_realtime_asr_gateway.py':{'__init__','close_all_sessions','drain_deferred_closes','close_session_deferred','close_source_deferred','_close_source_deferred','_close_detached','_detach_source_session','_mark_detached','physical_close'},
        'services/realtime_speech_service.py':{'_pause_for_insufficient_realtime_balance','terminate_session_for_admin','_control_capture','_cleanup_source_resources','_reset_realtime_session','_verify_performance_ack_session','acknowledge_runtime_timing','_close_asr_session','_read_performance_ack_access','_retire_session_id','_unretire_session_id'},
    }
    reviews={}
    for name,scope in allowed.items():
        p=PREFIX+name
        node_map=lambda x:{n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(x)) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        a=node_map((E/'baseline'/p).read_text());b=node_map((dest/p).read_text())
        changed={n for n in a.keys()|b.keys() if a.get(n)!=b.get(n)}
        assert changed<=scope,(name,changed-scope)
        reviews[p]={'changedOrAddedFunctions':sorted(changed),'otherFunctionAstsUnchanged':True}
    files={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()}
    delta={n:h for n,h in files.items() if baseline.get(n)!=h}
    assert set(delta)==set(approved) and len(files)==308 and sum(files[n]==h for n,h in baseline.items())==301
    for p in (dest/'apps/backend/app').rglob('*.py'):
        if not p.name.startswith('._'):compile(p.read_bytes(),str(p),'exec')
    (E/'candidate-manifest.json').write_text(json.dumps(files,indent=2,sort_keys=True)+'\n')
    (E/'allowed-delta.json').write_text(json.dumps(delta,indent=2,sort_keys=True)+'\n')
    (E/'source-review.json').write_text(json.dumps(reviews,indent=2)+'\n')
    diff=''.join(''.join(difflib.unified_diff((E/'baseline'/n).read_text().splitlines(True) if n in baseline else [],
        (dest/n).read_text().splitlines(True),fromfile='baseline/'+n,tofile='candidate/'+n)) for n in sorted(delta))
    (E/'candidate.diff').write_text(diff)
    print(json.dumps({'candidateInputs':308,'changedOrAdded':7,'unchangedInputs':301,'sourceNodesReviewed':True}))


if __name__=='__main__':main()
