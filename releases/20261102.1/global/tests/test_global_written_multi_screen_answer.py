from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from time import time

import pytest

from app.core.config import Settings
from app.ports.screenshot_answer import VisionSummary
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_usage_billing_adapter import GlobalUsageBillingAdapter
from app.services.screenshot_answer_service import FileScreenshotPromptTemplateAdapter, OpenAICompatibleVisionGateway
from test_written_multi_screen_answer import batch, capture, service_fixture


class EnglishBatchVision:
    def __init__(self, *, fail=False):
        self.calls=[]
        self.fail=fail

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            from app.services.screenshot_answer_service import NonRetryableVisionError
            raise NonRetryableVisionError('synthetic_failure')
        return VisionSummary(title='Synthetic diagram', summary_text='Synthetic screenshot evidence only.',
            derived_question='Explain the supplied algorithm constraints.',
            final_answer='Quick Answer\nUse topological ordering.\n\n---\n\nDetailed Answer\nProcess each edge in dependency order.',
            image_count=len(kwargs['images']), provider_name='synthetic', model_name='synthetic')


def global_fixture(offer='global-interview-pass', *, fail=False):
    service, storage, repository, uploads=service_fixture()
    service.settings=Settings(_env_file=None, product_edition='global', screenshot_vision_delivery_mode='inline')
    service.session_service.session.interview_language='en-US'
    service.vision_gateway=EnglishBatchVision(fail=fail)
    commerce=GlobalCommerceService(service.settings,InMemoryGlobalCommerceRepository())
    if offer:
        commerce.grant_purchase(user_id='synthetic-user', offer_code=offer, source_kind='order', source_id='synthetic-order', starts_at_ms=int(time()*1000))
    commerce.state('synthetic-user')
    service.billing_service=GlobalUsageBillingAdapter(commerce)
    return service,storage,repository,uploads,commerce


@pytest.mark.parametrize('offer',['global-interview-pass','global-pro-weekly','global-pro-monthly'])
def test_global_paid_batch_keeps_one_entitlement_operation_and_english_output(offer):
    service,storage,repository,uploads,commerce=global_fixture(offer)
    before=deepcopy(commerce.state('synthetic-user'))
    first=capture(service,filename='statement.png');second=capture(service,filename='constraints.png')
    assert commerce.state('synthetic-user')==before
    assert not service.billing_service._records and not commerce.repository._reservations
    request,created=batch(service,[second,first]);assert created
    same,created_again=batch(service,[second,first]);assert not created_again and same.request_id==request.request_id
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    result=repository.get_remote_capture_request(request.request_id)
    assert result.status=='completed'
    task=repository.get_task(result.answer_task_id)
    assert 'Quick Answer' in task.answer_text and '详细回答' not in task.answer_text
    assert task.material_provenance['interviewLanguage']=='en-US'
    assert task.material_provenance['noPersonalMaterialUsed'] and task.material_context_status=='not-used'
    assert len(service.vision_gateway.calls)==1
    call=service.vision_gateway.calls[0]
    assert call['interview_language']=='en-US'
    assert [image.filename for image in call['images']]==['constraints.png','statement.png']
    assert len(service.billing_service._records)==len(commerce.repository._reservations)==1
    record=next(iter(service.billing_service._records.values()))
    assert record.status=='settled' and record.points_reserved==0 and record.billing_source=='global_entitlement'
    usage=next(iter(commerce.repository._reservations.values()))
    assert usage.usage_kind=='screen_assist' and usage.amount==1 and usage.status=='settled'
    assert commerce.state('synthetic-user')['screenAssist']==before['screenAssist']
    assert not uploads.uploaded_images and not storage.saved


def test_exhausted_global_usage_denies_batch_without_model_or_domestic_wallet():
    # An existing active-session stub exercises the screenshot billing seam.
    # The actual free account's written-entry rule is separately asserted below.
    service,_,repository,uploads,commerce=global_fixture(None)
    assert commerce.state('synthetic-user')['features']['writtenExam'] is False
    for i in range(3):
        usage=f'synthetic-existing-usage-{i}'
        service.billing_service.reserve_usage(user_id='synthetic-user',usage_id=usage,usage_kind='screenshot_answer')
        service.billing_service.settle_usage(usage_id=usage)
    assert commerce.state('synthetic-user')['screenAssist']['remaining']==0
    sources=[capture(service),capture(service)]
    request,_=batch(service,sources)
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    assert repository.get_remote_capture_request(request.request_id).status=='failed'
    assert not service.vision_gateway.calls and not uploads.uploaded_images
    assert len(commerce.repository._reservations)==3
    assert all(item.points_reserved==0 for item in service.billing_service._records.values())
    assert service.billing_service.reserve_usage(user_id='synthetic-user',usage_id='synthetic-free-entry',usage_kind='written_exam_entry').status=='insufficient_balance'


def test_global_failed_batch_releases_only_reserved_screen_entitlement():
    service,_,repository,uploads,commerce=global_fixture(None,fail=True)
    before=commerce.state('synthetic-user')['screenAssist']
    request,_=batch(service,[capture(service),capture(service)])
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    assert repository.get_remote_capture_request(request.request_id).status=='failed'
    assert len(service.vision_gateway.calls)==1
    assert commerce.state('synthetic-user')['screenAssist']==before
    assert len(commerce.repository._reservations)==1
    assert next(iter(commerce.repository._reservations.values())).status=='released'
    assert next(iter(service.billing_service._records.values())).points_reserved==0
    assert not uploads.uploaded_images and not service.session_service.contexts


@pytest.mark.parametrize('locale,language',[('en-US','English'),('ja-JP','Japanese')])
def test_global_batch_passes_existing_language_to_unchanged_gateway(locale,language):
    service,_,repository,_,_=global_fixture()
    service.session_service.session.interview_language=locale
    gateway=service.vision_gateway
    request,_=batch(service,[capture(service),capture(service)])
    if locale!='en-US':
        # Valid non-English synthetic results exercise the original language guard.
        original=gateway.analyze
        def localized(**kwargs):
            result=original(**kwargs)
            return replace(result, final_answer=('トポロジカル順序で各辺を処理します。' if locale=='ja-JP' else 'Utilisez un ordre topologique pour traiter chaque arc.'))
        gateway.analyze=localized
    service.complete_batch_answer_request_safely(request_id=request.request_id)
    assert repository.get_remote_capture_request(request.request_id).status=='completed'
    assert gateway.calls[0]['interview_language']==locale
    prompt,config=FileScreenshotPromptTemplateAdapter(service.settings).load_system_prompt(locale)
    assert language in prompt
    assert '<commercial_answer_contract>' in prompt
    assert config.template_id==('screenshot-answer-en-system' if locale=='en-US' else f'screenshot-answer-{locale}-system')


def test_global_prompt_gateway_and_existing_language_completion_methods_are_unchanged():
    root=(Path(__file__).resolve().parents[1] / "backend-candidate")
    baseline=root/'releases/global-20261019.1/fixtures/screenshot_answer_service_before.py'
    current=root/'apps/backend/app/services/screenshot_answer_service.py'
    def nodes(path):
        tree=ast.parse(path.read_text());result={}
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                result[node.name]=ast.dump(node,include_attributes=False)
            if isinstance(node,ast.ClassDef):
                for child in node.body:
                    if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        result[node.name+'.'+child.name]=ast.dump(child,include_attributes=False)
        return result
    old,new=nodes(baseline),nodes(current)
    protected=[name for name in old if name.startswith(('OpenAICompatibleVisionGateway.','FileScreenshotPromptTemplateAdapter.','ScreenshotAnswerPromptBuilder.'))]
    protected+=['ScreenshotAnswerService._complete_vision_direct_task','_vision_language_kwargs','_screenshot_only_instruction']
    for name in protected:assert old[name]==new[name],name
