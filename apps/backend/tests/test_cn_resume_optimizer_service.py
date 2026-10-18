"""CN HTTP wire, privacy, editing, deletion, runtime and independent material save."""
import asyncio
from dataclasses import replace
import json
import logging
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
import pytest
from pydantic import ValidationError

from app.core.errors import DomainRequestError
from app.schemas.cn_resume_optimizer import CreateResumeOptimization
from app.services.cn_resume_optimizer_provider import ResumeProviderError,validate_resume_review
from app.services.cn_resume_optimizer_service import CNResumeOptimizerRuntime, SAFE_ERRORS, public_job
from app.services.cn_resume_optimizer_diagnostics import failure_diagnostic, error_message_for_diagnostic
from app.services.document_processing import DocumentProcessingService
from app.services.document_parser import DocumentParserService,ProcessingTaskParserStatusReporter
from app.services.document_processing_repository import PostgresProcessingTaskRepository
from app.services.document_processing_adapters import (MineruDocumentParserAdapter,MarkdownNormalizerAdapter,MarkdownCleanerAdapter,
    MarkdownChunkSplitterAdapter,ChunkMetadataBuilderAdapter,SyntheticEmbeddingAdapter,InMemoryPgvectorStore)
from app.services.embedding_pipeline import EmbeddingPipelineService,ProcessingTaskEmbeddingStatusReporter
from app.services.cn_resume_optimizer_repository import quota_day
from cn_resume_optimizer_test_support import review_payload,harness,ensure_synthetic_database,member,creation,complete,seed_document,api,NOW,RESUME,QUOTE,JD


@pytest.mark.parametrize('operation',['get','cancel','delete','edit','export','save'])
def test_foreign_job_operations_do_not_expose_or_change_data(harness,operation):
    h=harness;job=h.service.create('owner',creation(h))
    actions={'get':lambda:h.service.get('other',job['jobId']),'cancel':lambda:h.service.cancel('other',job['jobId']),
        'delete':lambda:h.service.delete('other',job['jobId']),'edit':lambda:h.service.update_draft('other',job['jobId'],revision=1,markdown='稿件'),
        'export':lambda:h.service.export('other',job['jobId'],revision=1,format='docx',facts_confirmed=True),
        'save':lambda:h.service.save_as('other',job['jobId'],revision=1,facts_confirmed=True)}
    with pytest.raises(DomainRequestError) as exc:actions[operation]()
    assert exc.value.status_code==404 and h.service.get('owner',job['jobId'])['status']=='queued'
    assert h.billing.state_for_user(user_id='owner').balance==100


@pytest.mark.parametrize('mutation',['foreign','version','deleted','processing','wrongkind','empty','oversized','markup'])
def test_bad_source_before_charge_and_provider(harness,mutation):
    h=harness
    if mutation in ('foreign','wrongkind'):
        from psycopg import sql
        field='owner_user_id' if mutation=='foreign' else 'document_kind'
        value='other' if mutation=='foreign' else 'knowledge'
        with h.repo.connect() as c:
            for table in ('material_documents','material_document_versions'):
                c.execute(sql.SQL('UPDATE {} SET {}=%s WHERE document_id=%s').format(sql.Identifier(table),sql.Identifier(field)),(value,h.source.document_id))
    elif mutation in ('version','deleted','processing'):
        updates={'version':{'document_version_id':'new-version','object_key':'new-object'},'deleted':{'status':'deleted','deleted_at_ms':NOW},'processing':{'status':'processing'}}[mutation]
        h.documents.save(replace(h.source,**updates))
    else:
        text={'empty':'','oversized':'a'*40001,'markup':'<script>private()</script>'}[mutation]
        h.storage.save_object_bytes(object_key=h.source_key,payload=text.encode(),content_type='text/markdown')
    with pytest.raises(DomainRequestError) as exc:h.service.create('owner',creation(h))
    assert exc.value.error_code=='resume_optimizer_'+('source_markup_unsupported' if mutation=='markup' else 'source_unavailable')
    assert h.billing.state_for_user(user_id='owner').balance==200 and h.service.provider.calls==0


@pytest.mark.parametrize('value',[True,False,'100',100.0,1,99])
def test_points_quote_is_strict_before_wallet(value,harness):
    h=harness;raw=creation(h).model_dump(by_alias=True);raw['quotedPoints']=value
    with pytest.raises(ValidationError):CreateResumeOptimization(**raw)
    assert h.billing.state_for_user(user_id='owner').balance==200


@pytest.mark.parametrize('value',['true',1,100,None])
def test_points_confirmation_is_strict_bool(value,harness):
    h=harness;raw=creation(h).model_dump(by_alias=True);raw['confirmPointsCharge']=value
    with pytest.raises(ValidationError):CreateResumeOptimization(**raw)


def test_edit_export_and_independent_save_no_additional_fee_after_membership_expiry(harness):
    h=harness;member(h,ends=NOW+2)
    job=complete(h,h.service.create('owner',creation(h)))
    h.now[0]=NOW+60_000
    changed=h.service.update_draft('owner',job['jobId'],revision=job['revision'],markdown=job['draftMarkdown']+'\n用户确认的补充信息。')
    assert changed['initialDraftMarkdown']==job['initialDraftMarkdown'] and changed['revision']==job['revision']+1
    for fmt,signature in [('docx',b'PK'),('pdf',b'%PDF-')]:
        data,mime,name=h.service.export('owner',job['jobId'],revision=changed['revision'],format=fmt,facts_confirmed=True)
        assert data.startswith(signature) and name=='优化后简历.'+fmt
    saved=h.service.save_as('owner',job['jobId'],revision=changed['revision'],facts_confirmed=True)
    replay=h.service.save_as('owner',job['jobId'],revision=changed['revision'],facts_confirmed=True)
    assert saved.document_id==replay.document_id!=h.source.document_id
    assert h.documents.get_by_id(h.source.document_id).document_version_id==h.source.document_version_id
    assert h.billing.state_for_user(user_id='owner').balance==200
    h.service.delete('owner',job['jobId'])
    assert h.documents.get_by_id(saved.document_id).status=='processing_requested'


def test_save_processing_ready_uses_normal_path_without_second_wallet_charge(harness):
    h=harness
    tasks=PostgresProcessingTaskRepository(h.settings)
    logger=logging.getLogger("synthetic-cn-resume-processing")
    parser=DocumentParserService(settings=h.settings,logger=logger,object_storage=h.storage,
        binary_parser=MineruDocumentParserAdapter(h.settings),markdown_normalizer=MarkdownNormalizerAdapter(),
        status_reporter=ProcessingTaskParserStatusReporter(settings=h.settings,logger=logger,task_repository=tasks))
    embedding=EmbeddingPipelineService(settings=h.settings,logger=logger,cleaner=MarkdownCleanerAdapter(),
        splitter=MarkdownChunkSplitterAdapter(),metadata_builder=ChunkMetadataBuilderAdapter(),
        embedding=SyntheticEmbeddingAdapter(h.settings),vector_store=InMemoryPgvectorStore(),
        status_reporter=ProcessingTaskEmbeddingStatusReporter(settings=h.settings,logger=logger,task_repository=tasks),artifact_storage=h.storage)
    processing=DocumentProcessingService(settings=h.settings,logger=logger,document_repository=h.documents,task_repository=tasks,
        parser_service=parser,embedding_pipeline=embedding,billing_service=h.billing)
    h.document_service.processing_service=processing
    job=complete(h,h.service.create('owner',creation(h)))
    before=h.billing.state_payload(h.billing.state_for_user(user_id='owner'))
    saved=h.service.save_as('owner',job['jobId'],revision=job['revision'],facts_confirmed=True)
    task=tasks.get_task('task-'+saved.document_version_id)
    assert task is not None
    processing.process_task(task.task_id)
    ready=h.documents.get_by_id(saved.document_id)
    assert ready.status=='ready' and ready.document_kind=='resume'
    after=h.billing.state_payload(h.billing.state_for_user(user_id='owner'))
    assert after['balance']==before['balance']==100
    assert [(r['kind'],r['points']) for r in after['ledger']]==[(r['kind'],r['points']) for r in before['ledger']]
    with h.repo.connect() as c:
        assert c.execute("SELECT count(*) FROM billing_index_reservations WHERE user_id='owner'").fetchone()['count']==0
    assert h.documents.get_by_id(h.source.document_id).document_version_id==h.source.document_version_id


def test_revision_and_fact_confirmation_guards_before_export_or_save(harness,monkeypatch):
    h=harness;job=complete(h,h.service.create('owner',creation(h)))
    h.service.exporter=lambda *_:pytest.fail('render must not run')
    for action in [lambda:h.service.export('owner',job['jobId'],revision=1,format='pdf',facts_confirmed=True),
                   lambda:h.service.export('owner',job['jobId'],revision=job['revision'],format='pdf',facts_confirmed=False),
                   lambda:h.service.save_as('owner',job['jobId'],revision=job['revision'],facts_confirmed=False),
                   lambda:h.service.update_draft('owner',job['jobId'],revision=1,markdown='过期稿')]:
        with pytest.raises(DomainRequestError):action()
    assert h.billing.state_for_user(user_id='owner').balance==100


def test_source_delete_racing_export_purges_and_blocks_response_no_completed_refund(harness):
    h=harness;job=complete(h,h.service.create('owner',creation(h)))
    def renderer(*_):
        h.document_service.delete_document(user_id='owner',document_id=h.source.document_id)
        return b'private body','application/pdf','synthetic.pdf'
    h.service.exporter=renderer
    with pytest.raises(DomainRequestError):h.service.export('owner',job['jobId'],revision=job['revision'],format='pdf',facts_confirmed=True)
    with h.repo.connect() as c:
        row=c.execute('SELECT payload FROM cn_resume_optimizer_jobs').fetchone()
        assert row['payload']=={}
    assert h.billing.state_for_user(user_id='owner').balance==100


def test_explicit_delete_purges_derived_content_and_keeps_minimal_billing(harness):
    h=harness;job=h.service.create('owner',creation(h,jdText=JD))
    h.service.delete('owner',job['jobId'])
    with h.repo.connect() as c:
        row=c.execute('SELECT payload,status,deleted_at_ms FROM cn_resume_optimizer_jobs').fetchone()
        assert row['payload']=={} and row['status']=='cancelled' and row['deleted_at_ms'] is not None
    assert h.billing.state_for_user(user_id='owner').balance==200


def test_private_http_wire_quote_charge_cancel_refund_and_unauth_errors(harness,monkeypatch,tmp_path):
    h=harness;client=api(h,monkeypatch)
    snapshot={'synthetic':True,'providerCalls':0,'edition':'cn','responses':[]}
    def record(label,response):
        assert response.headers['cache-control']=='private, no-store'
        snapshot['responses'].append({'label':label,'status':response.status_code,'body':response.json()})
        return response.json()
    record('points-capabilities',client.get('/api/v1/resume-optimizer/capabilities'))
    raw=creation(h).model_dump(by_alias=True)
    snapshot['pointsCreateRequest']=raw
    created=record('points-create',client.post('/api/v1/resume-optimizer/jobs',json=raw))['data']
    record('points-replay',client.post('/api/v1/resume-optimizer/jobs',json=raw))
    record('points-cancel',client.post('/api/v1/resume-optimizer/jobs/'+created['jobId']+'/cancel'))
    snapshot['billingAfterRefund']=h.billing.state_payload(h.billing.state_for_user(user_id='owner'))
    member(h)
    cap=record('free-capabilities',client.get('/api/v1/resume-optimizer/capabilities'))['data']
    raw=creation(h,key='free').model_dump(by_alias=True);snapshot['freeCreateRequest']=raw
    free=record('free-create',client.post('/api/v1/resume-optimizer/jobs',json=raw))['data']
    complete(h,free)
    assert cap['dailyLimit']==3 and cap['dailyRemaining']==3
    for index in range(2):
        complete(h,h.service.create('owner',creation(h,key=f'exhaust-free-{index}')))
    stale={**raw,'idempotencyKey':'stale-free'}
    assert client.post('/api/v1/resume-optimizer/jobs',json=stale).status_code==409
    record('quote-changed',client.post('/api/v1/resume-optimizer/jobs',json=stale))
    # Remove only synthetic balance, never real provider work.
    with h.repo.connect() as c:c.execute("INSERT INTO points_redemption_ledger VALUES('synthetic-adjust','owner','admin_adjustment',-200,%s,'synthetic-adjust','合成余额不足')",(NOW,))
    record('insufficient-balance',client.post('/api/v1/resume-optimizer/jobs',json=creation(h,key='insufficient').model_dump(by_alias=True)))
    denied=api(h,monkeypatch,auth=False).get('/api/v1/resume-optimizer/capabilities')
    assert denied.status_code==401;record('unauthenticated',denied)
    snapshot['providerCalls']=h.service.provider.calls
    target=Path(os.environ['CN_RESUME_OPTIMIZER_WIRE_OUT']) if os.environ.get('CN_RESUME_OPTIMIZER_WIRE_OUT') else tmp_path/'http-wire-snapshot.json'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
    assert snapshot['providerCalls']==0


def test_disabled_and_wrong_region_do_not_create_model_repository_or_work(harness,monkeypatch):
    h=harness;client=api(h,monkeypatch)
    h.service.settings=h.settings.model_copy(update={'product_edition':'global'})
    monkeypatch.setattr('app.modules.cn_resume_optimizer.cn_resume_optimizer_service',lambda:pytest.fail('disabled route must not construct service'))
    response=client.get('/api/v1/resume-optimizer/capabilities')
    assert response.status_code==200 and response.json()['data']['enabled'] is False
    assert response.json()['data']['dailyLimit']==3 and h.service.capabilities('owner')['dailyLimit']==3
    assert response.headers['cache-control']=='private, no-store'


def test_runtime_independent_provider_completion_and_cancel_refund(harness):
    h=harness
    async def run():
        runtime=CNResumeOptimizerRuntime(h.service)
        await runtime.start()
        try:
            job=h.service.create('owner',creation(h))
            for _ in range(100):
                result=await runtime.db(h.service.get,'owner',job['jobId'])
                if result['status']=='completed':break
                await asyncio.sleep(.01)
            assert result['status']=='completed' and result['billingStatus']=='settled' and h.service.provider.calls==1
            entered=asyncio.Event()
            class Slow:
                async def generate(self,**kwargs):entered.set();await asyncio.sleep(60)
            h.service.provider=Slow()
            nextjob=h.service.create('owner',creation(h,key='cancel-running'))
            await asyncio.wait_for(entered.wait(),2)
            await runtime.db(h.service.cancel,'owner',nextjob['jobId'])
            for _ in range(100):
                if runtime.active_job_id is None:break
                await asyncio.sleep(.01)
            cancelled=h.service.get('owner',nextjob['jobId'])
            assert cancelled['status']=='cancelled' and cancelled['billingStatus']=='released'
            assert h.billing.state_for_user(user_id='owner').balance==100
        finally:await runtime.shutdown()
    asyncio.run(run())


@pytest.mark.parametrize('member_free',[False,True])
def test_diagnosed_failure_persists_with_exactly_once_original_payment_release(harness,member_free):
    h=harness
    if member_free:member(h)
    request=creation(h);job=h.service.create('owner',request);claim=h.repo.claim(now_ms=NOW)
    diagnostic=failure_diagnostic('evidence_quote_missing')
    finish=dict(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=NOW+1,error='invalid_output',diagnostic=diagnostic)
    assert h.repo.finish(**finish) is True
    assert h.repo.finish(**finish) is False
    result=h.service.get('owner',job['jobId'])
    assert result['status']=='failed' and result['billingStatus']=='released'
    assert result['errorCode']=='invalid_output'
    assert result['errorMessage']==error_message_for_diagnostic(diagnostic)+'本次积分或免费次数已退还。'
    assert 'failureDiagnostic' not in result and 'diagnostic' not in result
    assert result['review'] is None and result['draftMarkdown'] is None
    assert h.service.create('owner',request)['jobId']==job['jobId']
    assert h.billing.state_for_user(user_id='owner').balance==200
    with h.repo.connect() as c:
        assert c.execute('SELECT payload FROM cn_resume_optimizer_jobs').fetchone()['payload']['failureDiagnostic']==diagnostic
        entries=c.execute("SELECT points FROM points_redemption_ledger WHERE kind LIKE 'resume_optimizer_%%' ORDER BY points").fetchall()
    assert [r['points'] for r in entries]==([] if member_free else [-100,100])
    if member_free:assert h.service.capabilities('owner')['dailyRemaining']==3


@pytest.mark.parametrize('diagnostic',[
    {'stage':'evidence','reason':'evidence_quote_missing','private':'SYNTHETIC-PRIVATE-DIAGNOSTIC'},
    {'stage':'SYNTHETIC-PRIVATE-DIAGNOSTIC','reason':'evidence_quote_missing'},
    {'stage':'facts','reason':'SYNTHETIC-PRIVATE-DIAGNOSTIC'},
    'SYNTHETIC-PRIVATE-DIAGNOSTIC',None])
def test_invalid_failure_diagnostics_are_discarded_and_legacy_message_is_preserved(harness,diagnostic):
    h=harness;job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    assert h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=NOW+1,error='invalid_output',diagnostic=diagnostic)
    result=h.service.get('owner',job['jobId'])
    assert result['errorMessage']==SAFE_ERRORS['invalid_output']
    with h.repo.connect() as c:payload=c.execute('SELECT payload FROM cn_resume_optimizer_jobs').fetchone()['payload']
    assert 'failureDiagnostic' not in payload
    assert 'SYNTHETIC-PRIVATE-DIAGNOSTIC' not in json.dumps(payload)+json.dumps(result)
    assert h.billing.state_for_user(user_id='owner').balance==200


@pytest.mark.parametrize('terminal',['cancel','delete','source'])
def test_late_diagnosed_failure_cannot_overwrite_cancellation_or_deleted_payload(harness,terminal):
    h=harness;job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    if terminal=='cancel':h.service.cancel('owner',job['jobId'])
    elif terminal=='delete':h.service.delete('owner',job['jobId'])
    else:h.document_service.delete_document(user_id='owner',document_id=h.source.document_id)
    assert h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=NOW+1,error='invalid_output',diagnostic=failure_diagnostic('evidence_quote_missing')) is False
    with h.repo.connect() as c:row=c.execute('SELECT status,payload FROM cn_resume_optimizer_jobs').fetchone()
    assert row['status']=='cancelled' and 'failureDiagnostic' not in row['payload']
    if terminal!='cancel':assert row['payload']=={}
    assert h.billing.state_for_user(user_id='owner').balance==200


def test_expired_claim_uses_interruption_diagnostic_instead_of_provider_cause(harness):
    h=harness;job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    assert h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=NOW+h.repo.lease_ms+1,error='invalid_output',diagnostic=failure_diagnostic('evidence_quote_missing'))
    row=h.repo.get(user_id='owner',job_id=job['jobId'],now_ms=NOW+h.repo.lease_ms+1)
    assert row['error_code']=='interrupted' and row['payload']['failureDiagnostic']==failure_diagnostic('runtime_interrupted')
    assert h.billing.state_for_user(user_id='owner').balance==200


def test_specific_public_failure_message_refund_claim_depends_on_released_state(harness):
    h=harness;job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=NOW+1,error='invalid_output',diagnostic=failure_diagnostic('evidence_quote_missing'))
    row=h.repo.get(user_id='owner',job_id=job['jobId'],now_ms=NOW+1)
    assert '已退还' in public_job(row)['errorMessage']
    assert '已退还' not in public_job({**row,'allowance_status':'reserved'})['errorMessage']


def test_diagnosed_failure_http_detail_and_list_keep_internal_payload_private(harness,monkeypatch):
    h=harness;job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    diagnostic=failure_diagnostic('fact_numbers_changed')
    h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=NOW+1,error='invalid_output',diagnostic=diagnostic)
    client=api(h,monkeypatch)
    detail=client.get('/api/v1/resume-optimizer/jobs/'+job['jobId'])
    listing=client.get('/api/v1/resume-optimizer/jobs')
    assert detail.status_code==listing.status_code==200
    for response in (detail,listing):
        assert response.headers['cache-control']=='private, no-store'
        assert 'failureDiagnostic' not in response.text and 'fact_numbers_changed' not in response.text
        assert 'facts' not in response.text
    result=detail.json()['data']
    assert set(result)==set(job)
    assert result['errorMessage']==error_message_for_diagnostic(diagnostic)+'本次积分或免费次数已退还。'
    assert listing.json()['data']['jobs'][0]['errorMessage']==result['errorMessage']


def test_success_ignores_failure_diagnostic_and_cannot_be_replaced_by_late_failure(harness):
    h=harness;job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    args=dict(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],now_ms=NOW+1)
    diagnostic=failure_diagnostic('fact_numbers_changed')
    assert h.repo.finish(**args,review={'synthetic':True},draft='合成成功稿',diagnostic=diagnostic)
    assert h.repo.finish(**args,error='invalid_output',diagnostic=diagnostic) is False
    row=h.repo.get(user_id='owner',job_id=job['jobId'],now_ms=NOW+1)
    assert row['status']=='completed' and row['allowance_status']=='settled'
    assert row['error_code'] is None and 'failureDiagnostic' not in row['payload']
    assert h.billing.state_for_user(user_id='owner').balance==100


@pytest.mark.parametrize('failure,category,reason',[
    ('provider','invalid_output','evidence_quote_missing'),
    ('timeout','provider_timeout','runtime_timeout'),
    ('internal','interrupted','runtime_internal_error')])
def test_runtime_diagnosed_failures_persist_and_emit_safe_json_logs(harness,caplog,failure,category,reason):
    h=harness
    private='SYNTHETIC-PRIVATE-PROVIDER-BODY'
    class Failing:
        async def generate(self,**kwargs):
            if failure=='provider':raise ResumeProviderError(reason='evidence_quote_missing') from ValueError(private)
            if failure=='timeout':await asyncio.sleep(10)
            raise ValueError(private)
    h.service.provider=Failing()
    h.service.settings=h.settings.model_copy(update={'cn_resume_optimizer_timeout_seconds':.01})
    job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    async def run():
        runtime=CNResumeOptimizerRuntime(h.service)
        try:await runtime._execute(claim)
        finally:await runtime.shutdown()
    with caplog.at_level(logging.WARNING,logger='offersteady.resume-optimizer'):asyncio.run(run())
    row=h.repo.get(user_id='owner',job_id=job['jobId'],now_ms=NOW+1)
    assert row['error_code']==category and row['payload']['failureDiagnostic']==failure_diagnostic(reason)
    events=[json.loads(record.message) for record in caplog.records if record.name=='offersteady.resume-optimizer']
    assert len(events)==1 and events[0]['event']=='resume_optimizer_task_failed'
    assert events[0]['errorCategory']==category and events[0]['diagnostic']==failure_diagnostic(reason)
    assert type(events[0]['durationMs']) is int and events[0]['durationMs']>=0
    for sentinel in (private,job['jobId'],claim['claim_token'],h.source.document_id,'synthetic@example.invalid'):
        assert sentinel not in caplog.text
    assert h.billing.state_for_user(user_id='owner').balance==200


def test_runtime_late_provider_failure_logs_only_the_committed_interruption_cause(harness,caplog):
    h=harness
    class ExpiredFailure:
        async def generate(self,**kwargs):
            h.now[0]=NOW+h.repo.lease_ms+1
            raise ResumeProviderError(reason='evidence_quote_missing')
    h.service.provider=ExpiredFailure()
    job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    async def run():
        runtime=CNResumeOptimizerRuntime(h.service)
        try:await runtime._execute(claim)
        finally:await runtime.shutdown()
    with caplog.at_level(logging.WARNING,logger='offersteady.resume-optimizer'):asyncio.run(run())
    row=h.repo.get(user_id='owner',job_id=job['jobId'],now_ms=h.now[0])
    diagnostic=failure_diagnostic('runtime_interrupted')
    assert row['status']=='failed' and row['error_code']=='interrupted'
    assert row['payload']['failureDiagnostic']==diagnostic
    events=[json.loads(r.message) for r in caplog.records if r.name=='offersteady.resume-optimizer']
    assert len(events)==1 and events[0]['errorCategory']=='interrupted' and events[0]['diagnostic']==diagnostic
    assert 'evidence_quote_missing' not in caplog.text
    assert h.billing.state_for_user(user_id='owner').balance==200


@pytest.mark.parametrize('terminal',['cancel','delete','source'])
def test_runtime_late_failure_after_terminal_change_has_no_failure_event_or_revived_payload(harness,caplog,terminal):
    h=harness
    job=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    class TerminalWins:
        async def generate(self,**kwargs):
            if terminal=='cancel':await asyncio.to_thread(h.service.cancel,'owner',job['jobId'])
            elif terminal=='delete':await asyncio.to_thread(h.service.delete,'owner',job['jobId'])
            else:await asyncio.to_thread(h.document_service.delete_document,user_id='owner',document_id=h.source.document_id)
            raise ResumeProviderError(reason='evidence_quote_missing')
    h.service.provider=TerminalWins()
    async def run():
        runtime=CNResumeOptimizerRuntime(h.service)
        try:await runtime._execute(claim)
        finally:await runtime.shutdown()
    with caplog.at_level(logging.WARNING,logger='offersteady.resume-optimizer'):asyncio.run(run())
    with h.repo.connect() as c:row=c.execute('SELECT status,payload FROM cn_resume_optimizer_jobs').fetchone()
    assert row['status']=='cancelled' and 'failureDiagnostic' not in row['payload']
    if terminal!='cancel':assert row['payload']=={}
    events=[json.loads(r.message) for r in caplog.records if r.name=='offersteady.resume-optimizer']
    assert not events and 'resume_optimizer_task_failed' not in caplog.text
    assert h.billing.state_for_user(user_id='owner').balance==200


def test_slow_save_callback_never_holds_wallet_lock_and_old_spending_completes(harness):
    from threading import Event
    h=harness;job=complete(h,h.service.create('owner',creation(h)))
    entered,release=Event(),Event()
    def slow_save(row):
        entered.set()
        assert release.wait(3)
        return SimpleNamespace(document_id='synthetic-independent',document_version_id='synthetic-version')
    def save():
        return h.repo.save_as(user_id='owner',job_id=job['jobId'],revision=job['revision'],now_ms=NOW,save_callback=slow_save)
    def spend():
        reservation=h.billing_repository.reserve_usage(usage={'reservation_id':'synthetic-slow-save-spend','usage_id':'synthetic-slow-save-spend',
            'user_id':'owner','usage_kind':'answer','points_reserved':20,'wallet_only':True},created_at_ms=NOW)
        assert reservation['status']=='reserved'
        return h.billing_repository.settle_usage(usage_id='synthetic-slow-save-spend',settled_at_ms=NOW+1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        save_future=pool.submit(save)
        try:
            assert entered.wait(2)
            # This is the real old wallet reservation/settlement path, not just
            # pg_try_advisory_lock. A blocked wallet fails before releasing save.
            spent=pool.submit(spend).result(timeout=1)
            assert spent['status']=='settled'
            assert h.billing_repository.balance(user_id='owner')==80
        finally:release.set()
        assert save_future.result(timeout=2).document_id=='synthetic-independent'


def test_source_delete_wins_before_save_callback_and_cannot_create_copy(harness):
    h=harness;job=complete(h,h.service.create('owner',creation(h)))
    h.repo.purge_by_source(user_id='owner',document_id=h.source.document_id,now_ms=NOW+1,delete_source=True)
    with pytest.raises(DomainRequestError):
        h.repo.save_as(user_id='owner',job_id=job['jobId'],revision=job['revision'],now_ms=NOW+2,
            save_callback=lambda _:pytest.fail('a deleted source cannot create a new copy'))
    assert h.billing.state_for_user(user_id='owner').balance==100


def test_source_delete_waits_for_explicit_save_and_does_not_revive_derived_content(harness):
    from threading import Event
    h=harness;job=complete(h,h.service.create('owner',creation(h)))
    entered,release=Event(),Event()
    def save_callback(row):
        entered.set();assert release.wait(3)
        return SimpleNamespace(document_id='explicit-independent',document_version_id='explicit-version')
    with ThreadPoolExecutor(max_workers=2) as pool:
        save=pool.submit(h.repo.save_as,user_id='owner',job_id=job['jobId'],revision=job['revision'],now_ms=NOW,save_callback=save_callback)
        assert entered.wait(2)
        deleted=pool.submit(h.repo.purge_by_source,user_id='owner',document_id=h.source.document_id,now_ms=NOW+1,delete_source=True)
        try:
            assert not deleted.done()
        finally:release.set()
        assert save.result(timeout=2).document_id=='explicit-independent'
        deleted.result(timeout=2)
    with h.repo.connect() as c:
        row=c.execute('SELECT payload FROM cn_resume_optimizer_jobs').fetchone()
        assert row['payload']=={}


def test_global_capacity_eight_and_single_running_reject_ninth_without_charge(harness):
    h=harness;jobs=[]
    for index in range(9):
        owner='synthetic-'+str(index)
        h.billing.state_for_user(user_id=owner);seed_document(h,owner=owner)
        if index==8:
            with pytest.raises(DomainRequestError) as exc:h.service.create(owner,creation(h,owner=owner))
            assert exc.value.error_code=='resume_optimizer_busy' and h.billing.state_for_user(user_id=owner).balance==200
        else:jobs.append(h.service.create(owner,creation(h,owner=owner)))
    with ThreadPoolExecutor(max_workers=4) as pool:claims=list(pool.map(lambda _:h.repo.claim(now_ms=NOW),range(4)))
    assert sum(c is not None for c in claims)==1
    assert len(jobs)==8


def test_shutdown_and_restart_recovery_refund_without_provider_replay(harness):
    h=harness;entered=asyncio.Event()
    class Slow:
        calls=0
        async def generate(self,**kwargs):self.calls+=1;entered.set();await asyncio.sleep(60)
    provider=Slow();h.service.provider=provider
    async def run():
        runtime=CNResumeOptimizerRuntime(h.service);await runtime.start()
        job=h.service.create('owner',creation(h))
        await asyncio.wait_for(entered.wait(),2)
        await runtime.shutdown()
        result=h.service.get('owner',job['jobId'])
        assert result['status']=='failed' and result['billingStatus']=='released' and result['errorCode']=='interrupted'
        restarted=CNResumeOptimizerRuntime(h.service);await restarted.start();await asyncio.sleep(.03);await restarted.shutdown()
        assert provider.calls==1 and h.billing.state_for_user(user_id='owner').balance==200
    asyncio.run(run())


def test_controlled_table_normalization_same_source_quote_and_real_dual_export(harness):
    from io import BytesIO
    from zipfile import ZipFile
    from pypdf import PdfReader
    from xml.etree import ElementTree
    h=harness
    original=('# 合成候选人\n<table border="1"><tr><th>工作</th><th>联系</th></tr><tr><td>'+QUOTE+
        '，为12个团队提供服务。</td><td>synthetic@example.invalid<br/>2024年</td></tr></table>\n教育：合成大学 本科。')
    h.storage.save_object_bytes(object_key=h.source_key,payload=original.encode(),content_type='text/markdown')
    job=h.service.create('owner',creation(h))
    assert '<table' not in job['sourceText'] and QUOTE in job['sourceText']
    assert '12个团队' in job['sourceText'] and 'synthetic@example.invalid' in job['sourceText']
    assert h.storage.load_object_bytes(object_key=h.source_key).decode()==original
    job=complete(h,job)
    assert '使用Python实现数据接口开发' in job['draftMarkdown'] and '教育：合成大学 本科。' in job['draftMarkdown']
    pdf=h.service.export('owner',job['jobId'],revision=job['revision'],format='pdf',facts_confirmed=True)[0]
    word=h.service.export('owner',job['jobId'],revision=job['revision'],format='docx',facts_confirmed=True)[0]
    pdf_text=''.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    with ZipFile(BytesIO(word)) as archive:word_text=''.join(ElementTree.fromstring(archive.read('word/document.xml')).itertext())
    for text in (pdf_text,word_text):
        assert 'synthetic@example.invalid' in text and '2024' in text and '合成大学' in text
    assert h.billing.state_for_user(user_id='owner').balance==100


def test_ready_owned_jd_and_source_deleted_jd_release_no_late_delivery(harness):
    h=harness;jd,_=seed_document(h,kind='job_description',document_id='jd-source',text=JD)
    job=h.service.create('owner',creation(h,jdDocumentId=jd.document_id,jdVersionId=jd.document_version_id))
    assert job['jdText']==JD and job['hasJd']
    claim=h.repo.claim(now_ms=NOW)
    h.document_service.delete_document(user_id='owner',document_id=jd.document_id)
    assert h.repo.finish(user_id='owner',job_id=job['jobId'],token=claim['claim_token'],revision=claim['revision'],now_ms=NOW+1,review={},draft='迟到') is False
    assert h.billing.state_for_user(user_id='owner').balance==200
    with h.repo.connect() as c:assert c.execute('SELECT payload FROM cn_resume_optimizer_jobs').fetchone()['payload']=={}


def test_creation_during_empty_claim_wakes_without_poll_delay(harness,monkeypatch):
    from threading import Event
    h=harness;empty_claim,release=Event(),Event();original=h.repo.claim
    first=[True]
    def paused_claim(*,now_ms):
        result=original(now_ms=now_ms)
        if first[0] and result is None:
            first[0]=False;empty_claim.set();assert release.wait(3)
        return result
    monkeypatch.setattr(h.repo,'claim',paused_claim)
    async def run():
        runtime=CNResumeOptimizerRuntime(h.service);await runtime.start()
        try:
            assert await asyncio.to_thread(empty_claim.wait,2)
            job=await runtime.db(h.service.create,'owner',creation(h))
            release.set()
            async with asyncio.timeout(2):
                while True:
                    result=await runtime.db(h.service.get,'owner',job['jobId'])
                    if result['status']=='completed':break
                    await asyncio.sleep(.01)
            assert h.service.provider.calls==1
        finally:release.set();await runtime.shutdown()
    asyncio.run(run())


def test_live_interview_stream_and_optimizer_have_independent_capacity_and_cancellation(harness):
    service=harness.service
    request=lambda **updates:creation(harness,**updates)
    """Exercise both real executors together, with synthetic blocked I/O only."""
    import threading
    from app.services.live_answer_stream_executor import LiveAnswerStreamExecutor

    async def run():
        live=LiveAnswerStreamExecutor(max_workers=1,queue_max=0,event_queue_max=1)
        live_release=threading.Event()
        live_closed=threading.Event()
        provider_first=asyncio.Event()
        provider_first_cancelled=asyncio.Event()
        provider_second=asyncio.Event()
        provider_second_release=asyncio.Event()
        provider_calls=[]
        provider_active=0
        provider_peak=0

        def live_producer():
            try:
                yield 'synthetic-interview-first-frame'
                assert live_release.wait(5),'synthetic live producer was not released'
                yield 'synthetic-interview-late-frame'
            finally:
                live_closed.set()

        class Provider:
            async def generate(self,*,resume,jd,target_role,prompt_version=None):
                assert prompt_version is None
                nonlocal provider_active,provider_peak
                call=len(provider_calls)+1
                provider_calls.append(call)
                provider_active+=1
                provider_peak=max(provider_peak,provider_active)
                try:
                    if call==1:
                        provider_first.set()
                        try:
                            await asyncio.Event().wait()
                        except asyncio.CancelledError:
                            provider_first_cancelled.set()
                            raise
                    else:
                        provider_second.set()
                        await provider_second_release.wait()
                    return validate_resume_review(review_payload(),resume=resume,jd=jd)
                finally:
                    provider_active-=1

        service.provider=Provider()
        runtime=CNResumeOptimizerRuntime(service)
        lease=live.try_acquire()
        assert lease is not None
        live_stream=live.stream(lease,live_producer)
        try:
            assert await asyncio.wait_for(anext(live_stream),2)=='synthetic-interview-first-frame'
            assert live.diagnostics()['active']==1
            assert live.try_acquire() is None
            await runtime.start()
            first=await runtime.db(service.create,'owner',request())
            await asyncio.wait_for(provider_first.wait(),2)
            assert live.diagnostics()['active']==1
            assert live.try_acquire() is None
            assert service.get('owner',first['jobId'])['status']=='running'

            # Cancelling optimizer work returns its quota without stopping the
            # already occupied live stream or releasing the live stream lease.
            cancelled=await runtime.db(service.cancel,'owner',first['jobId'])
            assert cancelled['status']=='cancelled' and cancelled['allowanceStatus']=='released'
            await asyncio.wait_for(provider_first_cancelled.wait(),2)
            assert live.diagnostics()['active']==1 and not live_closed.is_set()
            assert live.try_acquire() is None

            second=await runtime.db(service.create,'owner',request(idempotencyKey='second-independent-attempt'))
            await asyncio.wait_for(provider_second.wait(),2)
            assert provider_peak==1 and provider_calls==[1,2]
            assert await runtime.db(service.repository.claim,now_ms=NOW) is None
            with pytest.raises(DomainRequestError) as limit:
                await runtime.db(service.create,'owner',request(idempotencyKey='third-must-not-admit'))
            assert limit.value.status_code==429

            # A live stream disconnect closes that producer/capacity alone;
            # the independently running optimizer remains uncancelled.
            await live_stream.aclose()
            live_release.set()
            assert await asyncio.to_thread(live_closed.wait,2)
            for _ in range(100):
                if live.diagnostics()['completed']==1:break
                await asyncio.sleep(.01)
            assert live.diagnostics()['active']==0 and live.diagnostics()['completed']==1
            assert service.get('owner',second['jobId'])['status']=='running'
            assert not provider_second_release.is_set() and provider_active==1
            recovered_lease=live.try_acquire()
            assert recovered_lease is not None
            def recovered_producer():
                yield 'synthetic-interview-reconnected'
            assert [frame async for frame in live.stream(recovered_lease,recovered_producer)]==['synthetic-interview-reconnected']
            assert service.get('owner',second['jobId'])['status']=='running'

            provider_second_release.set()
            for _ in range(200):
                completed=await runtime.db(service.get,'owner',second['jobId'])
                if completed['status']=='completed':break
                await asyncio.sleep(.01)
            assert completed['status']=='completed' and completed['allowanceStatus']=='settled'
            assert provider_calls==[1,2] and provider_peak==1
            assert service.get('owner',first['jobId'])['status']=='cancelled'
            with service.repository.connect() as connection:
                uses=connection.execute('SELECT status FROM cn_resume_optimizer_usage ORDER BY created_at_ms,job_id').fetchall()
            assert sorted(row['status'] for row in uses)==['released','settled']
        finally:
            live_release.set()
            provider_second_release.set()
            await live_stream.aclose()
            await runtime.shutdown()
            live.shutdown()
    asyncio.run(run())
