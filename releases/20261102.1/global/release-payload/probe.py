"""Actual-image, offline Global source/contract probe. Never import app.main."""
from __future__ import annotations
import argparse,asyncio,builtins,copy,hashlib,io,json,os,socket,sys,threading
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline-settings',required=True)
    parser.add_argument('--baseline-schema',required=True)
    parser.add_argument('--rollback',action='store_true')
    args=parser.parse_args()
    before_settings=json.loads(Path(args.baseline_settings).read_text())
    before_schema=json.loads(Path(args.baseline_schema).read_text())
    sys.path.insert(0,'/app/apps/backend')
    counters={'providerCalls':0,'databaseWrites':0,'workersStarted':0}
    def deny_network(*a,**k):
        counters['providerCalls']+=1;raise AssertionError('network_forbidden')
    def deny_database(*a,**k):
        counters['databaseWrites']+=1;raise AssertionError('database_forbidden')
    def deny_worker(*a,**k):
        counters['workersStarted']+=1;raise AssertionError('worker_forbidden')
    socket.socket.connect=deny_network
    socket.create_connection=deny_network
    import psycopg
    psycopg.connect=deny_database
    threading.Thread.start=deny_worker
    opened=builtins.open
    io_opened=io.open
    def checked_open(path,mode='r',*a,**k):
        if any(x in mode for x in 'wax+'):raise AssertionError('file_write_forbidden')
        return opened(path,mode,*a,**k)
    def checked_io_open(path,mode='r',*a,**k):
        if any(x in mode for x in 'wax+'):raise AssertionError('file_write_forbidden')
        return io_opened(path,mode,*a,**k)
    builtins.open=checked_open
    io.open=checked_io_open
    from app.core.config import Settings
    settings=Settings()
    assert settings.model_dump(mode='json')==before_settings,'effective_settings_changed'
    assert settings.product_edition=='global'
    checks=['effective_settings_unchanged']
    from fastapi import FastAPI,Request
    from app.core.responses import ApiEnvelope
    from app.schemas.foundation import HealthResponse
    from app.api.v1 import api_router
    from app.api.admin import admin_router
    from app.api.admin_promotion import admin_promotion_router
    from app.api.admin_global_commerce import admin_global_commerce_router
    from app.api.promotion import public_promotion_router
    app=FastAPI(title=settings.app_name,version=settings.app_version)
    async def healthz(request:Request)->ApiEnvelope[HealthResponse]:
        raise AssertionError('schema_only')
    healthz.__annotations__={'request':Request,'return':ApiEnvelope[HealthResponse]}
    app.add_api_route('/healthz',healthz,methods=['GET'],response_model=ApiEnvelope[HealthResponse])
    for router in (api_router,admin_router,admin_promotion_router,admin_global_commerce_router):
        app.include_router(router,prefix=settings.api_prefix)
    app.include_router(public_promotion_router)
    schema=app.openapi()
    expected=copy.deepcopy(before_schema)
    operation=schema['paths']['/api/v1/screenshot-answer/desktop-devices/{device_id}/capture-requests/next']['get']
    extras=[p for p in operation['parameters'] if p['name'] in ('sessionId','requestId')]
    assert (not extras if args.rollback else len(extras)==2 and all(p['in']=='query' and not p.get('required') for p in extras))
    operation['parameters']=[p for p in operation['parameters'] if p['name'] not in ('sessionId','requestId')]
    if schema!=expected:
        def differences(a,b,path=''):
            if type(a)!=type(b):return [path]
            if isinstance(a,dict):return sum((differences(a.get(k),b.get(k),path+'/'+k) for k in set(a)|set(b)),[])
            if isinstance(a,list):return [path] if a!=b else []
            return [path] if a!=b else []
        print(json.dumps({'contractDifferencePaths':differences(schema,expected)[:20]}))
        raise AssertionError('api_delta_not_limited_to_optional_queries')
    assert 'app.main' not in sys.modules
    checks.append('complete_schema_unchanged' if args.rollback else 'complete_schema_only_two_optional_queries')
    from app.modules import web
    history=json.loads(web._published_desktop_manifest_path().with_name('global_desktop_release_history.json').read_text())
    assert len(history['entries'])==3 and all(e['version']=='1.3.5' for e in history['entries'])
    old_manifest_reader,old_settings_reader=web._published_desktop_manifest,web.get_settings
    try:
        current={'version':1,'entries':[]}
        web._published_desktop_manifest=lambda:current
        for entry in history['entries']:assert web._published_desktop_entry(entry['fileName'])==entry
        assert web._published_desktop_entry('../../unknown') is None
        withdrawn=dict(history['entries'][0],distributionStatus='withdrawn')
        current['entries']=[withdrawn]
        assert web._published_desktop_entry(withdrawn['fileName'])==withdrawn
        assert not web._is_public_desktop_entry(withdrawn)
        current['entries']=[]
        web.get_settings=lambda:SimpleNamespace(product_edition='cn')
        assert web._published_desktop_entry(history['entries'][0]['fileName']) is None
    finally:
        web._published_desktop_manifest,web.get_settings=old_manifest_reader,old_settings_reader
    checks.append('immutable_history_exact_old_bytes_current_priority_global_only')
    if args.rollback:
        assert not any(counters.values()) and 'app.main' not in sys.modules
        print(json.dumps({'passed':True,'checks':checks,**counters,'lifespanStarted':False,'settingsUnchanged':True,'schemaAllowedDelta':True}))
        return
    from app.ports.document_repository import DocumentRecord
    from app.ports.interview_session import SessionBoundDocument
    from app.services.document_repository import InMemoryDocumentRepository
    from app.services.document_service import DocumentService,InMemoryKnowledgeCollectionStore
    from app.services.interview_session_repository import InMemoryInterviewSessionRepository
    from app.services.session_service import SessionService
    owner='synthetic_global_probe_owner'
    class Documents(InMemoryDocumentRepository):
        def __init__(self):super().__init__();self.gets=0;self.lists=0
        def get_by_id(self,key):self.gets+=1;return super().get_by_id(key)
        def list_for_user(self,**k):self.lists+=1;return super().list_for_user(**k)
    repo=Documents()
    docs=DocumentService(storage=SimpleNamespace(),repository=repo,knowledge_store=InMemoryKnowledgeCollectionStore())
    session_repo=InMemoryInterviewSessionRepository()
    sessions=SessionService(settings=settings,repository=session_repo,document_repository=repo)
    records=[]
    for i in range(6):
        records.append(repo.save(DocumentRecord(document_id=f'synthetic-doc-{i}',owner_user_id=owner,document_kind='knowledge',display_name='Synthetic.txt',file_kind='txt',content_type='text/plain',size_bytes=18,object_key=f'synthetic/{i}',status='ready',knowledge_collection_id='synthetic-collection',processing_requested_at_ms=None,deleted_at_ms=None,created_at_ms=100+i,updated_at_ms=100+i,summary='Synthetic summary',document_version_id=f'synthetic-version-{i}',version=1,content_fingerprint='a'*64,index_state='indexed')))
    for i in range(12):
        s=sessions.create_session(user_id=owner,title='Synthetic global read')
        bound=[SessionBoundDocument(document_id=d.document_id,document_kind=d.document_kind,display_name=d.display_name,status=d.status,document_version_id=d.document_version_id,index_state=d.index_state,knowledge_collection_id=d.knowledge_collection_id,summary=d.summary,active=True) for d in records]
        session_repo.save_session(replace(s,material_binding=replace(s.material_binding,knowledge_document_ids=[d.document_id for d in records],bound_documents=bound)))
    old_views=docs.list_documents(user_id=owner)
    old_sessions=sessions.list_sessions(user_id=owner)
    assert repo.gets==6
    repo.gets=repo.lists=0
    views,raw=docs.list_documents_with_records(user_id=owner)
    current=sessions.list_sessions(user_id=owner,document_records=raw)
    assert views==old_views and current==old_sessions and repo.gets==0 and repo.lists==1
    checks.append('request_local_raw_snapshot_six_reads_to_zero_equal_wire')
    # Seed cannot cross owners and never persists across the next read.
    foreign={k:replace(v,owner_user_id='synthetic_other') for k,v in raw.items()}
    repo.gets=0;sessions.list_sessions(user_id=owner,document_records=foreign);assert repo.gets==6
    repo.save(replace(records[0],status='deleted',deleted_at_ms=101))
    _,new_raw=docs.list_documents_with_records(user_id=owner)
    assert records[0].document_id not in new_raw
    new=sessions.list_sessions(user_id=owner,document_records=new_raw)
    assert new[0].material_binding.bound_documents[0].active is False
    checks.extend(['foreign_raw_snapshot_rejected','next_read_observes_deleted_material'])
    # The projection does not refresh/read bound documents and checks owner.
    repo.gets=0
    control=sessions.get_control_state(user_id=owner,session_id=current[0].session_id)
    assert repo.gets==0 and control.session_id==current[0].session_id
    assert set(control.__dataclass_fields__)=={'session_id','owner_user_id','status','session_mode','interview_audio_mode'}
    from app.core.errors import DomainRequestError
    try:sessions.get_control_state(user_id='synthetic_other',session_id=current[0].session_id)
    except DomainRequestError as e:assert e.status_code==403
    else:raise AssertionError('foreign_owner_admitted')
    checks.append('control_projection_five_fields_owner_checked_no_material_reads')
    from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
    calls=[]
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def execute(self,q,p):calls.append((q,p))
        def fetchone(self):return {'session_id':'synthetic-pg','owner_user_id':owner,'status':'live','session_mode':'written','interview_audio_mode':'computer'}
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def cursor(self,**k):return Cursor()
    pg=object.__new__(PostgresInterviewSessionRepository)
    pg._connect=lambda:Connection()
    c=pg.get_control_state('synthetic-pg')
    assert c.session_mode=='written' and len(calls)==1
    query,params=calls[0]
    assert query.strip().startswith('SELECT session_id, owner_user_id, status, session_mode, interview_audio_mode') and 'deleted_at_ms IS NULL' in query and 'json' not in query.lower() and params==('synthetic-pg',)
    checks.append('postgres_projection_single_read_no_full_row_or_write')
    from app.modules import screenshot_answer as module
    from app.ports.screenshot_answer import RemoteScreenshotCaptureRequest
    capture=RemoteScreenshotCaptureRequest(request_id='synthetic-request',session_id='synthetic-current',owner_user_id=owner,device_id='synthetic-device',manual_code='123456',instruction='Synthetic question',status='cancelled',created_at_ms=100,updated_at_ms=100)
    async def control_call(request,method,**kwargs):return method(**kwargs)
    module.run_realtime_control=control_call
    request=Request({'type':'http','headers':[]})
    written=[]
    repository=SimpleNamespace(get_remote_capture_request=lambda **_:capture,list_remote_capture_requests_for_session=lambda **_:[capture])
    service=SimpleNamespace(repository=repository,get_next_remote_capture_request=lambda **_:replace(capture,status='requested',session_id='synthetic-legacy'))
    realtime=SimpleNamespace(get_desktop_pairing_status=lambda **_:{'bound':True,'sessionStatus':'live'},get_desktop_capture_binding=lambda **_:SimpleNamespace(session_id='synthetic-current',owner_user_id=owner,device_id='synthetic-device',manual_code='123456'))
    async def invoke(session_id=None,request_id=None):
        return await module.get_next_remote_capture_request(device_id='synthetic-device',request=request,manual_code='123456',session_id=session_id,request_id=request_id,service=service,realtime=realtime)
    assert asyncio.run(invoke()).data.session_id=='synthetic-legacy'
    assert asyncio.run(invoke('synthetic-current','synthetic-request')).data.status=='cancelled'
    assert asyncio.run(invoke('synthetic-other','synthetic-request')).data is None
    original=capture;capture=replace(capture,owner_user_id='synthetic_other')
    assert asyncio.run(invoke('synthetic-current','synthetic-request')).data is None
    capture=original
    checks.append('scoped_next_terminal_owner_session_and_legacy_contracts')
    assert not any(counters.values()) and 'app.main' not in sys.modules
    print(json.dumps({'passed':True,'checks':checks,**counters,'lifespanStarted':False,'settingsUnchanged':True,'schemaAllowedDelta':True}))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        t=exc.__traceback__
        while t.tb_next:t=t.tb_next
        print(json.dumps({'passed':False,'errorType':type(exc).__name__,'reason':'offline_probe_failed','function':t.tb_frame.f_code.co_name,'line':t.tb_lineno}))
        raise SystemExit(1) from None
