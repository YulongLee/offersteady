import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings
from app.deps import chat_service
from app.main import create_app
from app.modules import live_answer
from app.ports.chat import ChatAnswerTaskRecord
from app.schemas.live_answer import LiveAnswerQuestionRequest
from app.services.chat_repository import InMemoryChatRepository
from app.services.chat_service import ChatService
from app.services.redis_live_task_repositories import RedisChatRepository
from app.services.live_answer_stream_executor import LiveAnswerStreamExecutor
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService
from app.services.global_usage_billing_adapter import GlobalUsageBillingAdapter
from test_redis_live_task_repositories import FakeRedis


@pytest.mark.parametrize('late_status', ['streaming', 'completed', 'failed'])
@pytest.mark.parametrize('redis', [False, True])
def test_cancelled_result_cannot_be_revived(late_status, redis):
    repository = RedisChatRepository(Settings(_env_file=None), redis_client=FakeRedis()) if redis else InMemoryChatRepository()
    task = ChatAnswerTaskRecord(task_id='synthetic', session_id='synthetic', owner_user_id='synthetic',
        question='How do caches work?', answer_text='Bounded caches reduce repeat work.', status='cancelled',
        stream_mode=True, updated_at_ms=10**15)
    repository.save_task(task)
    assert repository.save_task(replace(task, status=late_status, answer_text='Late result', updated_at_ms=10**15+1)) == task
    assert repository.get_task(task.task_id) == task


class CaptureProducer(LiveAnswerStreamExecutor):
    def stream(self, lease, producer_factory):
        self.producer = producer_factory()
        self.lease = lease
        async def empty():
            if False:
                yield ''
        return empty()


@pytest.mark.parametrize('automatic', [False, True])
def test_disconnect_before_task_ack_releases_global_reservation(monkeypatch, automatic):
    user = 'synthetic-' + uuid4().hex
    billing = GlobalUsageBillingAdapter(GlobalCommerceService(Settings(_env_file=None, product_edition='global'), InMemoryGlobalCommerceRepository()))
    with TestClient(create_app()) as client:
        created = client.post('/api/v1/sessions', json={'userId': user, 'title': 'Synthetic', 'interviewLanguage': 'en-US'})
        created.raise_for_status()
        session = created.json()['data']['sessionId']
        client.post(f'/api/v1/sessions/{session}/start', json={'userId': user}).raise_for_status()
        service = chat_service()
        monkeypatch.setattr(service, 'settings', service.settings.model_copy(update={'product_edition': 'global'}))
        monkeypatch.setattr(service, 'billing_service', billing)
        executor = CaptureProducer(max_workers=1, queue_max=0, event_queue_max=1)
        request = Request({'type': 'http', 'app': SimpleNamespace(state=SimpleNamespace(live_answer_stream_executor=executor))})
        realtime = MagicMock()
        realtime.claim_auto_answer_candidate.return_value = SimpleNamespace(candidate_id='candidate', answer_task_id='claim')
        phases = []
        monkeypatch.setattr(live_answer, '_publish_answer_task_event', lambda *args, **kw: phases.append(kw['phase']))
        try:
            asyncio.run(live_answer.stream_live_answer(request_context=request,
                request=LiveAnswerQuestionRequest(userId=user, sessionId=session, question='How do caches work?',
                    idempotencyKey='synthetic-usage', questionId='candidate', triggerMode='auto' if automatic else 'manual'),
                auth_context=None, service=service, realtime=realtime))
            assert 'task-started' in next(executor.producer)
            assert billing._records['synthetic-usage'].status == 'reserved'
            executor.producer.close()
            executor.producer.close()
            task = service.list_session_history(user_id=user, session_id=session)[-1]
            assert task.status == 'cancelled'
            assert billing._records['synthetic-usage'].status == 'released'
            assert phases == ['task-started', 'cancelled']
            assert realtime.finish_auto_answer_candidate.call_count == int(automatic)
            assert billing.commerce.state(user)['copilot']['remaining'] == 15
        finally:
            executor.lease.release()
            executor.shutdown()
            client.post(f'/api/v1/sessions/{session}/end', json={'userId': user})


@pytest.mark.parametrize('terminal', ['completed', 'failed'])
def test_terminal_answer_is_not_cancelled_on_close(terminal):
    task = ChatAnswerTaskRecord(task_id='synthetic', session_id='synthetic', owner_user_id='synthetic',
        question='Test?', answer_text='Preserve this', status=terminal, stream_mode=True)
    service = MagicMock()
    service.stream_answer_question.return_value = iter([{'type': 'task-started', 'task': task}, {'type': terminal, 'task': task}])
    executor = CaptureProducer(max_workers=1, queue_max=0, event_queue_max=1)
    context = Request({'type': 'http', 'app': SimpleNamespace(state=SimpleNamespace(live_answer_stream_executor=executor))})
    try:
        asyncio.run(live_answer.stream_live_answer(request_context=context,
            request=LiveAnswerQuestionRequest(userId='synthetic', sessionId='synthetic', question='Test?'),
            auth_context=None, service=service, realtime=MagicMock()))
        assert len(list(executor.producer)) == 2
        executor.producer.close()
        service.cancel_task.assert_not_called()
    finally:
        executor.lease.release()
        executor.shutdown()
