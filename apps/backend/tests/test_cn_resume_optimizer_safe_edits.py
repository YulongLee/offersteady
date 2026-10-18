"""Real isolated PG and HTTP safe-edit acceptance; synthetic data, no model network."""
import asyncio
from io import BytesIO
import json
import os
from pathlib import Path
from zipfile import ZipFile
import pytest
from app.services.cn_resume_optimizer_diagnostics import failure_diagnostic
from app.services.cn_resume_optimizer_provider import PROMPT_VERSION, validate_resume_review
from app.services.cn_resume_optimizer_service import CNResumeOptimizerRuntime
from cn_resume_optimizer_test_support import (NOW, QUOTE, RESUME, api, creation,
    ensure_synthetic_database, harness, member, review_payload)

BAD = '为12个团队提供Kubernetes服务'
NO_EFFECT = '本次未生成可安全应用的有效修改，原简历已保留。'


def mixed_review():
    result = review_payload()
    result['edits'].append({'sourceQuote':'为12个团队提供服务','replacement':BAD})
    return result


def execute(h, claim, payload, before_return=None):
    class Provider:
        calls = 0
        async def generate(self, *, resume, jd, target_role, prompt_version=None):
            assert prompt_version is None
            self.calls += 1
            if before_return: before_return()
            return validate_resume_review(payload, resume=resume, jd=jd)
    h.service.provider = Provider()
    async def run():
        runtime = CNResumeOptimizerRuntime(h.service)
        try: await runtime._execute(claim)
        finally: await runtime.shutdown()
    asyncio.run(run())
    assert h.service.provider.calls == 1


def entries(h):
    with h.repo.connect() as c:
        return [r['points'] for r in c.execute("SELECT points FROM points_redemption_ledger WHERE kind LIKE 'resume_optimizer_%%' ORDER BY points").fetchall()]


def late(h, claim):
    assert h.repo.finish(user_id='owner',job_id=claim['job_id'],token=claim['claim_token'],
        revision=claim['revision'],now_ms=h.now[0]+1,review={'private':BAD},draft=BAD) is False


@pytest.mark.parametrize('free',[False,True])
def test_partial_settles_once_and_rejected_replacement_never_persists(harness,free,caplog):
    h=harness
    if free: member(h)
    request=creation(h);created=h.service.create('owner',request);claim=h.repo.claim(now_ms=NOW)
    assert created['promptVersion']=='resume-optimizer-zh-CN-v2'
    execute(h,claim,mixed_review())
    result=h.service.get('owner',created['jobId'])
    assert result['status']=='completed' and result['allowanceStatus']=='settled'
    assert result['draftMarkdown']==RESUME.replace(QUOTE,'使用Python实现数据接口开发')
    expected={'proposedCount':2,'appliedCount':1,'retainedCount':1,
        'retainedReasonCounts':{'factCheck':1,'sourceQuote':0,'overlap':0,'unchanged':0}}
    assert result['review']['editSummary']==expected
    with h.repo.connect() as c: stored=c.execute('SELECT payload FROM cn_resume_optimizer_jobs').fetchone()['payload']
    assert BAD not in json.dumps(stored,ensure_ascii=False)+json.dumps(result,ensure_ascii=False)+caplog.text
    assert 'fact_english_content_added' not in json.dumps(stored)
    late(h,claim)
    assert h.service.create('owner',request)['jobId']==created['jobId']
    assert entries(h)==([] if free else [-100])
    assert h.billing.state_for_user(user_id='owner').balance==(200 if free else 100)
    if free: assert h.service.capabilities('owner')['dailyRemaining']==2
    edited=h.service.update_draft('owner',created['jobId'],revision=result['revision'],markdown=result['draftMarkdown']+'\n用户核实后的补充。')
    assert edited['review']['editSummary']==expected
    data,_,_=h.service.export('owner',created['jobId'],revision=edited['revision'],format='docx',facts_confirmed=True)
    with ZipFile(BytesIO(data)) as document: assert 'Kubernetes' not in document.read('word/document.xml').decode()
    assert entries(h)==([] if free else [-100])


@pytest.mark.parametrize('free',[False,True])
@pytest.mark.parametrize('kind',['empty','noop','cosmetic','bad','noop-bad'])
def test_zero_effective_fails_and_original_acceptance_refunds_once(harness,free,kind,caplog):
    h=harness
    if free: member(h)
    request=creation(h);created=h.service.create('owner',request);claim=h.repo.claim(now_ms=NOW)
    payload=review_payload(edits=False)
    if kind in ('noop','noop-bad'): payload['edits']=[{'sourceQuote':QUOTE,'replacement':QUOTE}]
    elif kind=='cosmetic': payload['edits']=[{'sourceQuote':QUOTE,'replacement':QUOTE+'。'}]
    if kind in ('bad','noop-bad'): payload['edits'].append({'sourceQuote':'为12个团队提供服务','replacement':BAD})
    execute(h,claim,payload)
    result=h.service.get('owner',created['jobId'])
    assert result['status']=='failed' and result['billingStatus']=='released' and result['errorCode']=='invalid_output'
    assert result['review'] is result['draftMarkdown'] is result['initialDraftMarkdown'] is None
    reason='fact_english_content_added' if kind in ('bad','noop-bad') else 'no_effective_edits'
    with h.repo.connect() as c: stored=c.execute('SELECT payload FROM cn_resume_optimizer_jobs').fetchone()['payload']
    assert stored['failureDiagnostic']==failure_diagnostic(reason)
    assert BAD not in json.dumps(stored,ensure_ascii=False)+caplog.text
    if reason=='no_effective_edits': assert result['errorMessage']==NO_EFFECT+'本次积分或免费次数已退还。'
    late(h,claim)
    assert h.service.create('owner',request)['jobId']==created['jobId']
    assert entries(h)==([] if free else [-100,100]) and h.billing.state_for_user(user_id='owner').balance==200
    if free: assert h.service.capabilities('owner')['dailyRemaining']==3


@pytest.mark.parametrize('free',[False,True])
@pytest.mark.parametrize('terminal',['cancel','delete','source'])
def test_partial_provider_cannot_revive_terminal_winner(harness,free,terminal):
    h=harness
    if free: member(h)
    created=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    def terminate():
        if terminal=='cancel': h.service.cancel('owner',created['jobId'])
        elif terminal=='delete': h.service.delete('owner',created['jobId'])
        else: h.document_service.delete_document(user_id='owner',document_id=h.source.document_id)
    execute(h,claim,mixed_review(),terminate)
    with h.repo.connect() as c: row=c.execute('SELECT status,payload FROM cn_resume_optimizer_jobs').fetchone()
    assert row['status']=='cancelled' and 'review' not in row['payload']
    if terminal!='cancel': assert row['payload']=={}
    assert entries(h)==([] if free else [-100,100]) and h.billing.state_for_user(user_id='owner').balance==200
    late(h,claim)


@pytest.mark.parametrize('free',[False,True])
def test_release_and_failure_diagnostic_rollback_in_same_transaction(harness,free,monkeypatch):
    h=harness
    if free: member(h)
    created=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW);original=h.repo._release
    def fail_after_release(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('synthetic transaction fault')
    with monkeypatch.context() as patch:
        patch.setattr(h.repo,'_release',fail_after_release)
        with pytest.raises(RuntimeError,match='synthetic transaction fault'):
            h.repo.finish(user_id='owner',job_id=created['jobId'],token=claim['claim_token'],revision=claim['revision'],
                now_ms=NOW+1,error='invalid_output',diagnostic=failure_diagnostic('no_effective_edits'))
    reserved=h.service.get('owner',created['jobId'])
    assert reserved['status']=='running' and reserved['allowanceStatus']=='reserved' and reserved['errorCode'] is None
    assert entries(h)==([] if free else [-100])
    execute(h,claim,review_payload(edits=False))
    assert h.service.get('owner',created['jobId'])['allowanceStatus']=='released' and entries(h)==([] if free else [-100,100])


def test_legacy_no_summary_is_readable_editable_exportable_without_version_rewrite(harness):
    h=harness;created=h.service.create('owner',creation(h));claim=h.repo.claim(now_ms=NOW)
    execute(h,claim,review_payload())
    with h.repo.connect() as c:
        c.execute("UPDATE cn_resume_optimizer_jobs SET payload=jsonb_set(payload #- '{review,editSummary}', '{promptVersion}', '\"resume-optimizer-zh-CN-v1\"'::jsonb)")
    legacy=h.service.get('owner',created['jobId'])
    assert legacy['promptVersion']=='resume-optimizer-zh-CN-v1' and 'editSummary' not in legacy['review']
    edited=h.service.update_draft('owner',created['jobId'],revision=legacy['revision'],markdown=legacy['draftMarkdown'])
    data,_,_=h.service.export('owner',created['jobId'],revision=edited['revision'],format='docx',facts_confirmed=True)
    assert data.startswith(b'PK') and entries(h)==[-100]


def test_real_private_http_partial_and_no_effective_wire(harness,monkeypatch,tmp_path):
    h=harness;client=api(h,monkeypatch);snapshot={'synthetic':True,'edition':'cn','providerCalls':2,'responses':[]}
    def record(label,response):
        assert response.status_code==200 and response.headers['cache-control']=='private, no-store'
        assert BAD not in response.text and 'failureDiagnostic' not in response.text
        snapshot['responses'].append({'label':label,'status':response.status_code,'body':response.json()})
        return response.json()['data']
    first=record('partial-create',client.post('/api/v1/resume-optimizer/jobs',json=creation(h).model_dump(by_alias=True)))
    execute(h,h.repo.claim(now_ms=NOW),mixed_review())
    completed=record('partial-detail',client.get('/api/v1/resume-optimizer/jobs/'+first['jobId']))
    assert completed['review']['editSummary']['appliedCount']==1
    second=record('no-effective-create',client.post('/api/v1/resume-optimizer/jobs',json=creation(h,key='no-effective-http').model_dump(by_alias=True)))
    execute(h,h.repo.claim(now_ms=NOW),review_payload(edits=False))
    failed=record('no-effective-detail',client.get('/api/v1/resume-optimizer/jobs/'+second['jobId']))
    assert failed['errorMessage']==NO_EFFECT+'本次积分或免费次数已退还。'
    listing=record('history',client.get('/api/v1/resume-optimizer/jobs'))
    assert len(listing['jobs'])==2 and all('sourceText' not in row and 'review' not in row for row in listing['jobs'])
    denied=api(h,monkeypatch,auth=False).get('/api/v1/resume-optimizer/jobs/'+first['jobId'])
    assert denied.status_code==401 and denied.headers['cache-control']=='private, no-store'
    target=Path(os.environ.get('CN_RESUME_OPTIMIZER_SAFE_WIRE_OUT',tmp_path/'safe-edits-http-wire.json'))
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
