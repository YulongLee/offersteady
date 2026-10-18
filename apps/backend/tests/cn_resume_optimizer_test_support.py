"""Synthetic-only CN optimizer fixture; local PostgreSQL and no model network."""
from __future__ import annotations
from datetime import datetime
import json
import logging
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
import pytest

from app.adapters.oss_storage import AliyunOssStorageAdapter
from app.core.config import Settings
from app.core.errors import install_exception_handlers
from app.deps import require_authenticated_context
from app.modules import cn_resume_optimizer as module
from app.ports.document_repository import DocumentRecord
from app.schemas.cn_resume_optimizer import CreateResumeOptimization
from app.services.billing_service import BillingService
from app.services.cn_resume_optimizer_repository import CNResumeOptimizerRepository,quota_day
from app.services.cn_resume_optimizer_service import CNResumeOptimizerService
from app.services.cn_resume_optimizer_provider import PROMPT_VERSION,validate_resume_review
from app.services.document_service import DocumentService,InMemoryKnowledgeCollectionStore
from app.services.material_object_keys import MaterialObjectKeyFactory
from app.services.mock_interview_repository import MockInterviewRepository
from app.services.postgres_billing_repository import PostgresBillingRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.postgres_material_persistence import PostgresDocumentRepository

LOCAL_ADMIN='postgresql://synthetic_local:synthetic-local-only@127.0.0.1:55445/postgres'
DATABASE='cn_resume_optimizer_20261018'
DB=LOCAL_ADMIN.rsplit('/',1)[0]+'/'+DATABASE
NOW=int(datetime(2026,10,18,23,59,30,tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()*1000)
QUOTE='负责使用Python开发数据接口'
RESUME='# 合成候选人\nsynthetic@example.invalid\n'+QUOTE+'，为12个团队提供服务。\n2024年 合成科技有限公司\n教育：合成大学 本科。'
JD='岗位要求Python及容器编排经验。'


def review_payload(*,with_jd=False,edits=True):
    dimensions=[{'key':key,'score':score,'reason':'现有描述具有真实依据，可进一步清晰说明。','evidence':[{'source':'resume','quote':QUOTE}]}
                for key,score in zip(('completeness','impact','clarity','structure'),(70,71,72,73))]
    if with_jd:
        dimensions.append({'key':'roleMatch','score':74,'reason':'Python已有依据，其他岗位技能需核实。','evidence':[{'source':'resume','quote':'Python'},{'source':'jd','quote':'容器编排'}]})
    return {'dimensions':dimensions,'suggestions':[{'priority':'high','title':'清晰描述已有开发工作','explanation':'现有措辞可以更直接，缺失成果应另行核实。','recommendation':'使用已核实事实说明数据接口开发工作。','evidence':[{'source':'resume','quote':QUOTE}]}],
            'missingFacts':['如有可核实的成果，请补充具体依据，不要编造指标。'],
            'edits':[{'sourceQuote':QUOTE,'replacement':'使用Python实现数据接口开发'}] if edits else []}


@pytest.fixture(scope='session',autouse=True)
def ensure_synthetic_database():
    with psycopg.connect(LOCAL_ADMIN,autocommit=True,connect_timeout=3) as connection:
        if not connection.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DATABASE,)).fetchone():
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DATABASE)))


def seed_document(h,owner='owner',*,document_id=None,kind='resume',text=RESUME):
    document_id=document_id or 'source-'+owner
    version='version-'+document_id
    doc=DocumentRecord(document_id=document_id,owner_user_id=owner,document_kind=kind,display_name='合成简历.md',file_kind='md',
        content_type='text/markdown',size_bytes=len(text.encode()),object_key='synthetic-original-'+document_id,status='ready',
        knowledge_collection_id=None,processing_requested_at_ms=None,deleted_at_ms=None,created_at_ms=NOW,updated_at_ms=NOW,
        summary='合成资料',object_id=document_id,document_version_id=version,version=1,index_state='indexed')
    h.documents.save(doc)
    key=MaterialObjectKeyFactory(h.settings).processed_artifact_key(owner_user_id=owner,document_kind=kind,document_id=document_id,
        document_version_id=version,artifact_kind='normalized_markdown')
    h.storage.save_object_bytes(object_key=key,payload=text.encode(),content_type='text/markdown')
    return doc,key


def member(h,owner='owner',*,days=1,starts=NOW-1,ends=NOW+86400000,admin=False):
    with h.repo.connect() as c:
        if admin:
            c.execute('CREATE TABLE IF NOT EXISTS admin_time_entitlements(entitlement_id TEXT PRIMARY KEY,user_id TEXT,starts_at_ms BIGINT,ends_at_ms BIGINT)')
            c.execute('INSERT INTO admin_time_entitlements VALUES(%s,%s,%s,%s)',('synthetic-admin-'+uuid4().hex,owner,starts,ends))
        else:
            order=h.billing.create_checkout_order(user_id=owner,product_id=f"pass-{days}",channel="alipay",
                idempotency_key="synthetic-membership-"+uuid4().hex,payment_url="https://synthetic.invalid",expires_at_ms=NOW+172800000)
            h.billing.confirm_checkout_paid(order_id=order.id,amount_cents=order.amount_cents,provider_trade_no="synthetic-"+uuid4().hex)
            c.execute("UPDATE billing_time_pass_entitlements SET starts_at_ms=%s,ends_at_ms=%s WHERE user_id=%s AND order_id=%s",(starts,ends,owner,order.id))



@pytest.fixture
def harness(monkeypatch):
    schema='synthetic_cn_resume_'+uuid4().hex
    with psycopg.connect(DB,autocommit=True) as c:
        c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    settings=Settings(_env_file=None).model_copy(update={'environment':'test','product_edition':'cn',
        'database_url':DB+'?'+urlencode({'options':'-csearch_path='+schema}), 'cn_resume_optimizer_enabled':True,
        'chat_qwen_api_key':'synthetic-only-not-a-real-key','chat_qwen_base_url':'https://provider.invalid/v1',
        'chat_qwen_model':'synthetic-model','document_processing_inline_worker_enabled':False,'oss_key_prefix':'synthetic-cn-resume'})
    sessions=PostgresInterviewSessionRepository(settings)
    billing_repository=PostgresBillingRepository(settings)
    mock=MockInterviewRepository(settings)
    documents=PostgresDocumentRepository(settings)
    repo=CNResumeOptimizerRepository(settings)
    billing=BillingService(settings,billing_repository=billing_repository)
    storage=AliyunOssStorageAdapter(settings)
    h=SimpleNamespace(settings=settings,schema=schema,repo=repo,billing=billing,billing_repository=billing_repository,
        mock=mock,documents=documents,storage=storage,sessions=sessions,now=[NOW])
    billing.state_for_user(user_id='owner')
    h.source,h.source_key=seed_document(h)
    monkeypatch.setattr('app.services.document_service.get_settings',lambda:settings)
    h.document_service=DocumentService(storage,documents,InMemoryKnowledgeCollectionStore(),
        optimizer_delete_hook=lambda d,t:repo.purge_by_source(user_id=d.owner_user_id,document_id=d.document_id,now_ms=t,delete_source=True))
    class Provider:
        calls=0
        async def generate(self,*,resume,jd,target_role,prompt_version=None):
            assert prompt_version is None
            self.calls+=1
            return validate_resume_review(review_payload(with_jd=bool(jd)),resume=resume,jd=jd)
    h.service=CNResumeOptimizerService(settings=settings,repository=repo,documents=documents,storage=storage,
        document_service=h.document_service,provider=Provider(),clock=lambda:h.now[0])
    try:
        yield h
    finally:
        with psycopg.connect(DB,autocommit=True) as c:
            c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def creation(h,*,owner='owner',key='synthetic-key',**updates):
    cap=h.service.capabilities(owner)
    raw={'idempotencyKey':key,'sourceDocumentId':'source-'+owner,'sourceVersionId':'version-source-'+owner,
         'quotedQuotaDay':cap['quotaDay'],'quotedBillingClass':cap['billingClass'],'quotedPoints':cap['entryPoints'],
         'confirmProcessing':True,'confirmPointsCharge':cap['entryPoints']==100,**updates}
    return CreateResumeOptimization(**raw)


def complete(h,job,*,error=None):
    claim=h.repo.claim(now_ms=h.now[0])
    assert claim and claim['job_id']==job['jobId']
    review,draft=validate_resume_review(review_payload(with_jd=job['hasJd']),resume=job['sourceText'],jd=job['jdText'])
    h.repo.finish(user_id=claim['owner_user_id'],job_id=claim['job_id'],token=claim['claim_token'],revision=claim['revision'],
        now_ms=h.now[0]+1,review=review,draft=draft,error=error)
    return h.service.get(claim['owner_user_id'],claim['job_id'])


def api(h,monkeypatch,*,auth=True):
    monkeypatch.setattr(module,'get_settings',lambda:h.service.settings)
    monkeypatch.setattr(module,'cn_resume_optimizer_service',lambda:h.service)
    app=FastAPI()
    app.include_router(module.router,prefix='/api/v1')
    app.add_middleware(module.CNResumeOptimizerPrivacyMiddleware,api_prefix='/api/v1')
    install_exception_handlers(app,settings=h.settings,logger=logging.getLogger('synthetic-cn-resume'))
    if auth:
        app.dependency_overrides[require_authenticated_context]=lambda:SimpleNamespace(user_id='owner')
    app.dependency_overrides[module.require_service]=lambda:h.service
    return TestClient(app)
