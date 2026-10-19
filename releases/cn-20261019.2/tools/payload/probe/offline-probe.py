"""Actual-image, read-only synthetic ASGI probe; no lifespan or runtime services.

Run with image's frozen original environment, --network=none --read-only -B,
/verify/expectations.json and this script read-only mounted at /verify.
Nothing is written, no real model/DB/OSS/runtime service is called.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import asdict, replace
import hashlib
import inspect
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('/app'))
    parser.add_argument('--expectations', type=Path, default=Path('/verify/expectations.json'))
    args = parser.parse_args()
    expected = json.loads(args.expectations.read_text())
    root = args.root.resolve()
    logging.disable(logging.CRITICAL)
    # Initialize the local ASGI test loop before installing the socket audit.
    # No server, TestClient worker, application lifespan or child thread is used.
    loop = asyncio.new_event_loop()
    counters = dict(network=0, database=0, fileWrites=0, threadStarts=0,
                    subprocesses=0, dependenciesResolved=0, lifespan=0, realProvider=0)

    def reject(kind):
        def blocked(*_args, **_kwargs):
            counters[kind] += 1
            raise RuntimeError('offline_probe_side_effect_rejected')
        return blocked

    import psycopg
    import redis
    psycopg.connect = reject('database')
    psycopg.Connection.connect = reject('database')
    psycopg.AsyncConnection.connect = reject('database')
    redis.Redis.execute_command = reject('database')
    threading.Thread.start = reject('threadStarts')
    subprocess.Popen = reject('subprocesses')
    socket.create_connection = reject('network')

    def audit(event, values):
        if event.startswith('socket.'):
            reject('network')()
        if event == 'open':
            mode = values[1] if len(values) > 1 else None
            flags = values[2] if len(values) > 2 else 0
            if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            ):
                reject('fileWrites')()
        if event in ('os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.chmod', 'os.chown',
                     'os.truncate', 'os.link', 'os.symlink', 'os.utime'):
            reject('fileWrites')()
        if event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn'):
            reject('subprocesses')()
    sys.addaudithook(audit)
    sys.path.insert(0, str(root / 'apps/backend'))
    actual = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for directory in ('apps/backend/app', 'apps/backend/migrations', 'ai/prompts')
              for p in (root / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts
              and p.suffix != '.pyc' and p.name != '.desktop-release-manifest.lock'}
    actual['apps/backend/pyproject.toml'] = hashlib.sha256((root / 'apps/backend/pyproject.toml').read_bytes()).hexdigest()
    assert len(actual) == 230 and actual == expected['inventory'], 'candidate_runtime_inventory_mismatch'
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    config_sha = hashlib.sha256(json.dumps(settings.model_dump(mode='json'), sort_keys=True,
        separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    assert sorted(Settings.model_fields) == expected['configFields'], 'settings_fields_changed'
    assert config_sha == expected['configBeforeSha'], 'effective_settings_changed'
    assert settings.product_edition == 'cn' and settings.environment == 'production'
    assert settings.screenshot_vision_delivery_mode == 'inline', 'unsupported_source_capture_mode'
    from app import deps
    # Fail closed on every accidental construction of a real dependency.
    names = ('document_service', 'document_read_service', 'document_processing_service', 'document_parser_service',
        'chat_service', 'realtime_speech_service', 'screenshot_answer_service', 'session_service',
        'cn_resume_optimizer_repository', 'cn_resume_optimizer_service', 'authentication_service',
        'billing_service', 'usage_billing_service', 'global_commerce_service', 'global_checkout_service',
        'admin_service', 'llm_gateway_port', 'storage_port', 'document_repository',
        'processing_task_repository', 'embedding_adapter', 'database_runtime')
    for name in names:
        factory = getattr(deps, name, None)
        if callable(factory):
            blocked = reject('dependenciesResolved')
            blocked.__signature__ = inspect.signature(factory, eval_str=True)
            setattr(deps, name, blocked)
    from app.main import app
    app.router.lifespan_context = reject('lifespan')
    schema = app.openapi()
    assert schema == expected['openapiAfter'] and len(schema['paths']) == 203, 'candidate_api_schema_mismatch'
    before = expected['openapiBefore']
    assert len(before['paths']) == 202
    assert set(schema['paths']) - set(before['paths']) == {
        '/api/v1/screenshot-answer/sessions/{session_id}/batch-answer-requests'}
    for path, methods in before['paths'].items():
        assert schema['paths'][path] == methods, 'old_route_changed'
    added_fields = {
        'ScreenshotValidationPolicyResponse': {'supportsCaptureOnly'},
        'CreateRemoteScreenshotCaptureRequest': {'captureOnly'},
        'RemoteScreenshotCaptureRequestResponse': {'captureOnly', 'capturedImageId', 'captureRequestIds'},
    }
    for name, original in before['components']['schemas'].items():
        candidate = json.loads(json.dumps(schema['components']['schemas'][name]))
        for field in added_fields.get(name, set()):
            assert field in candidate.get('properties', {}) and field not in candidate.get('required', [])
            del candidate['properties'][field]
        assert candidate == original, 'old_schema_incompatible'
    required_routes = ('/api/v1/mock-interviews', '/api/v1/resume-optimizer/jobs', '/api/v1/sessions',
                       '/api/v1/live-answer/questions', '/api/v1/billing/state')
    assert all(path in schema['paths'] for path in required_routes), 'prior_feature_routes_missing'
    from app.services.cn_resume_optimizer_provider import PROMPT_VERSION
    from app.services.cn_resume_optimizer_repository import DAILY_FREE_LIMIT
    from app.services.mock_interview_repository import MockInterviewRepository
    assert PROMPT_VERSION == 'resume-optimizer-zh-CN-v2' and DAILY_FREE_LIMIT == 3
    assert MockInterviewRepository.daily_free_limit == 1 and MockInterviewRepository.duration_limit_ms == 3600000
    from app.core.errors import DomainRequestError
    from app.ports.screenshot_answer import VisionSummary
    from app.schemas.screenshot_answer import CreateRemoteScreenshotCaptureRequest
    from app.services.screenshot_answer_repository import InMemoryScreenshotAnswerRepository
    from app.services.screenshot_answer_service import (
        ScreenshotAnswerService, ScreenshotPreprocessor, InMemoryScreenshotUploadPort,
        OpenAICompatibleVisionGateway, NonRetryableVisionError,
    )
    OpenAICompatibleVisionGateway.analyze = reject('realProvider')
    OpenAICompatibleVisionGateway.stream_analyze = reject('realProvider')
    synthetic_settings = Settings.model_construct(**{
        key: field.get_default(call_default_factory=True)
        for key, field in Settings.model_fields.items()
    })
    # This explicit synthetic object cannot inherit real private env, endpoints,
    # wallets or user data. App's original Settings were only fingerprinted above.
    synthetic_settings = synthetic_settings.model_copy(update={
        'environment':'test', 'database_url':None, 'redis_url':None,
        'screenshot_vision_delivery_mode':'inline', 'screenshot_retry_max_attempts':0,
        'screenshot_progress_emit_interval_ms':0,
    })
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
    user, session_id = 'synthetic-probe-user', 'synthetic-probe-session'

    class Storage:
        def __init__(self): self.saved = {}
        def save_object_bytes(self, **kwargs):
            counters['fileWrites'] += 1
            raise RuntimeError('unexpected_storage_write')
        def object_exists(self, **kwargs): return False
        def create_signed_download_url(self, **kwargs):
            counters['network'] += 1
            raise RuntimeError('unexpected_signed_url')

    class Sessions:
        def __init__(self):
            self.contexts = []
            self.session = SimpleNamespace(status='live', session_mode='written', interview_language='zh-CN',
                material_binding=SimpleNamespace(revision=3))
        def get_session(self, *, user_id, session_id):
            if user_id != user or session_id != 'synthetic-probe-session':
                raise DomainRequestError('synthetic-probe', 'scope', 'synthetic_scope_rejected', 403)
            return self.session
        def touch_activity(self, **kwargs): pass
        def append_context(self, **kwargs): self.contexts.append(kwargs)
        def record_usage(self, **kwargs): pass

    class Billing:
        def __init__(self):
            self.reserved, self.settled, self.released = [], [], []
            self.insufficient = False
        def reserve_usage(self, **kwargs):
            self.reserved.append(kwargs)
            return SimpleNamespace(status='insufficient_balance' if self.insufficient else 'reserved')
        def settle_usage(self, **kwargs): self.settled.append(kwargs)
        def release_usage(self, **kwargs): self.released.append(kwargs)

    class Vision:
        def __init__(self):
            self.calls, self.images = 0, []
            self.hook, self.fail = None, False
        def stream_analyze(self, **kwargs):
            self.calls += 1
            self.images = kwargs['images']
            if self.hook: self.hook()
            if self.fail: raise NonRetryableVisionError('synthetic_failure')
            yield '简要回答\n合成多页答案。'
            yield '\n\n---\n\n详细回答\n合成完整答案。'
        def summary_from_stream(self, *, text, images):
            return VisionSummary(title='合成题', summary_text='合成内容', derived_question='合成题',
                final_answer=text, image_count=len(images), provider_name='synthetic', model_name='synthetic')
        def analyze(self, **kwargs):
            text = ''.join(self.stream_analyze(**kwargs))
            return self.summary_from_stream(text=text, images=kwargs['images'])

    # The real temporary upload port always starts a TTL sweeper. Suppress only
    # that known synthetic instance's scheduling; exercise expiry explicitly.
    def suppress_synthetic_sweeper(thread):
        assert thread.name == 'screenshot-upload-expiry', 'unexpected_synthetic_thread'
    threading.Thread.start = suppress_synthetic_sweeper
    upload_port = InMemoryScreenshotUploadPort(synthetic_settings)
    threading.Thread.start = reject('threadStarts')
    service = ScreenshotAnswerService(settings=synthetic_settings,
        logger=logging.getLogger('synthetic-offline-probe'), session_service=Sessions(),
        retrieval_service=SimpleNamespace(), object_storage=Storage(),
        repository=InMemoryScreenshotAnswerRepository(), upload_port=upload_port,
        preprocessor=ScreenshotPreprocessor(), vision_gateway=Vision(), prompt_template=SimpleNamespace(),
        prompt_builder=SimpleNamespace(), llm_gateway=SimpleNamespace())
    service.billing_service = Billing()
    events = []
    realtime = SimpleNamespace(
        get_desktop_binding=lambda **kwargs: SimpleNamespace(device_id='synthetic-device', manual_code='123456'),
        get_desktop_capture_binding=lambda **kwargs: SimpleNamespace(),
        publish_session_event=lambda **kwargs: events.append(kwargs),
    )
    async def synthetic_service(): return service
    async def synthetic_realtime(): return realtime
    async def synthetic_auth(): return SimpleNamespace(user_id=user)
    app.dependency_overrides[deps.screenshot_answer_service] = synthetic_service
    app.dependency_overrides[deps.realtime_speech_service] = synthetic_realtime
    app.dependency_overrides[deps.optional_authenticated_context] = synthetic_auth
    # Starlette executes sync background tasks in a worker. These thin wrappers
    # keep the actual implementation unchanged and execute it locally instead.
    originals = {}
    for name in ('complete_remote_capture_request_safely', 'complete_batch_answer_request_safely'):
        original = getattr(service, name)
        originals[name] = original
        def wrap(function):
            async def invoke(**kwargs): return function(**kwargs)
            return invoke
        setattr(service, name, wrap(original))

    checks = []
    def check(condition, name):
        assert condition, name
        checks.append(name)

    async def exercise():
        import httpx
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://synthetic.invalid') as client:
            prefix='/api/v1/screenshot-answer'
            async def post(path, body, status=200):
                response = await client.post(prefix + path, json=body)
                assert response.status_code == status, 'synthetic_http_status'
                return response.json().get('data')
            async def get_capture(request_id):
                response = await client.get(prefix+'/capture-requests/'+request_id, params={'userId':user})
                assert response.status_code == 200
                return response.json()['data']
            async def collect(page, capture_only=True):
                body={'userId':user}
                if capture_only: body['captureOnly']=True
                created = await post('/sessions/'+session_id+'/remote-capture-requests', body)
                rid=created['requestId']
                response=await client.post(prefix+'/capture-requests/'+rid+'/desktop-upload',
                    data={'deviceId':'synthetic-device','manualCode':'123456'},
                    files={'screenshot':(f'page-{page}.png', png, 'image/png')})
                assert response.status_code == 200
                return await get_capture(rid)
            async def submit(ids, status=200, override_user=None, override_session=None):
                return await post('/sessions/'+(override_session or session_id)+'/batch-answer-requests',
                    {'userId':override_user or user, 'captureRequestIds':ids}, status)
            policy=(await client.get(prefix+'/validation-policy')).json()['data']
            check(policy['supportsCaptureOnly'] and policy['maxImagesPerTask']==4,'capture_policy')
            check(CreateRemoteScreenshotCaptureRequest(userId=user).capture_only is False,'legacy_default')
            first, second=await collect(1), await collect(2)
            check(all(row['status']=='completed' and row['captureOnly'] and row['capturedImageId'] and row['answerTask'] is None for row in (first,second)), 'capture_only_ready_no_task')
            check(not service.repository.tasks and not service.session_service.contexts and not service.billing_service.reserved and not service.billing_service.settled and service.vision_gateway.calls==0, 'capture_only_no_generation_or_billing')
            ids=[second['requestId'],first['requestId']]
            parent=await submit(ids)
            final=await get_capture(parent['requestId'])
            check(final['status']=='completed' and final['captureRequestIds']==ids and final['answerTask']['imageCount']==2,'batch_http_roundtrip')
            check([image.filename for image in service.vision_gateway.images]==['page-2.png','page-1.png'],'batch_order')
            check(service.vision_gateway.calls==1 and len(service.repository.tasks)==1 and len(service.billing_service.reserved)==len(service.billing_service.settled)==1,'batch_one_task_one_charge')
            check(any(event['payload'].get('answerTask',{}).get('status')=='streaming' and event['payload']['answerTask']['answerText'] for event in events),'streaming_partial_event')
            check(final['answerTask']['materialContextStatus']=='not-used' and final['answerTask']['materialProvenance']['noPersonalMaterialUsed'],'no_personal_material')
            again=await submit(ids)
            check(again['requestId']==parent['requestId'] and service.vision_gateway.calls==1 and len(service.billing_service.settled)==1,'duplicate_no_extra_work')
            check(not service.upload_port.uploaded_images,'batch_releases_bytes')
            await submit([first['requestId']],409)
            await submit([first['requestId']]*2,400)
            await submit(ids,403,override_user='synthetic-other-user')
            await submit(ids,403,override_session='synthetic-other-session')
            check(service.vision_gateway.calls==1 and len(service.billing_service.reserved)==1,'invalid_owner_scope_consumed_duplicate_no_work')
            third=await collect(3)
            before_count=service.vision_gateway.calls
            cancelled=await post('/capture-requests/'+third['requestId']+'/cancel',{'userId':user})
            check(cancelled['status']=='cancelled' and not service.upload_port.uploaded_images,'remove_cleans_capture')
            await submit([third['requestId']],409)
            fourth=await collect(4)
            service.upload_port._sweep_expired(now_ms=10**16)
            await submit([fourth['requestId']],410)
            check(service.vision_gateway.calls==before_count and len(service.billing_service.reserved)==1,'expired_removed_no_work')
            # Admission-only parent before a worker is scheduled, cancelled via real HTTP API.
            fifth=await collect(5)
            pending,created=service.create_batch_answer_request(user_id=user,session_id=session_id,capture_request_ids=[fifth['requestId']],instruction='')
            await post('/capture-requests/'+pending.request_id+'/cancel',{'userId':user})
            originals['complete_batch_answer_request_safely'](request_id=pending.request_id)
            check(service.repository.get_remote_capture_request(pending.request_id).status=='cancelled' and service.vision_gateway.calls==before_count and not service.upload_port.uploaded_images,'cancel_before_generation')
            sixth=await collect(6)
            pending,created=service.create_batch_answer_request(user_id=user,session_id=session_id,capture_request_ids=[sixth['requestId']],instruction='')
            before_settled=len(service.billing_service.settled)
            service.vision_gateway.hook=lambda: service.cancel_remote_capture_request(user_id=user,request_id=pending.request_id)
            originals['complete_batch_answer_request_safely'](request_id=pending.request_id)
            service.vision_gateway.hook=None
            cancelled=await get_capture(pending.request_id)
            check(cancelled['status']=='cancelled' and cancelled['answerTask']['status']=='cancelled' and len(service.billing_service.settled)==before_settled and not service.upload_port.uploaded_images,'cancel_during_generation_no_settlement')
            seventh=await collect(7)
            service.billing_service.insufficient=True
            before_vision=service.vision_gateway.calls
            rejected=await submit([seventh['requestId']])
            rejected=await get_capture(rejected['requestId'])
            check(rejected['status']=='failed' and service.vision_gateway.calls==before_vision and not service.upload_port.uploaded_images,'insufficient_balance_no_model')
            service.billing_service.insufficient=False
            # Actual old single image path, with captureOnly omitted, still auto-generates.
            service.session_service.session.session_mode='interview'
            before_settled=len(service.billing_service.settled)
            legacy=await collect(8,False)
            check(legacy['captureOnly'] is False and legacy['status']=='completed' and legacy['answerTask']['imageCount']==1 and len(service.billing_service.settled)==before_settled+1,'legacy_single_auto_answer')
            for mode,state in (('interview','live'),('mock','live'),('written','ended')):
                service.session_service.session.session_mode=mode
                service.session_service.session.status=state
                response=await client.post(prefix+'/sessions/'+session_id+'/remote-capture-requests',json={'userId':user,'captureOnly':True})
                check(response.status_code in (400,409),'mode_scope_'+mode+'_'+state)
            service.session_service.session.session_mode='written'
            service.session_service.session.status='live'
            # Real existing billing service, in-memory only, validates unchanged 15-point rule.
            from app.services.billing_service import BillingService
            service.billing_service=BillingService(synthetic_settings)
            balance=service.billing_service.state_for_user(user_id=user).balance
            a,b=await collect(9),await collect(10)
            check(service.billing_service.state_for_user(user_id=user).balance==balance,'real_rule_capture_no_points')
            parent=await submit([a['requestId'],b['requestId']])
            await submit([a['requestId'],b['requestId']])
            state=service.billing_service.state_for_user(user_id=user)
            check(balance-state.balance==15 and len([row for row in state.ledger if row.kind=='screenshot_answer_settlement'])==1,'real_rule_batch_one_15_point_settlement')
    try:
        loop.run_until_complete(exercise())
    finally:
        loop.close()
    check(not any(counters.values()),'all_external_side_effect_counters_zero')
    print(json.dumps({
        'passed':True, 'runtimeInputCount':len(actual), 'apiPathCount':len(schema['paths']),
        'settingsSha256':config_sha, 'singleImageCompatible':True, 'multiCaptureBatchSynthetic':True,
        'noModelCalls':True, 'sideEffects':sum(counters.values()), 'syntheticSweepersNotStarted':1, 'counters':counters, 'checks':checks,
    }, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Fixed codes only. Do not print env values, image bytes or request/response text.
        reason = str(error) if isinstance(error, AssertionError) else type(error).__name__
        if len(reason)>100 or not reason.replace('_','').isalnum(): reason=type(error).__name__
        print(json.dumps({'passed':False,'reason':reason},sort_keys=True))
        raise SystemExit(1)
