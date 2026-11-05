"""Synthetic-only boundaries for scoped reads, close admission and ACK access."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import logging
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from redis.exceptions import ResponseError
from test_cn_realtime_entity_state import pair, redis_url, binding
from test_cn_realtime_capture_isolation import target
from app.core.errors import DomainRequestError
from app.ports.realtime_speech import AccountDesktopDeviceRecord
from app.services.cn_provider_close_executor import CnProviderCloseExecutor
from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor
from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService


def test_owner_order_precision_retirement_and_restart(pair):
    a,b,_,settings=pair
    high=9007199254740993
    first=binding(at=high)
    a.save_session_desktop_binding(first)
    second=replace(binding(session='s2',at=high+1),capabilities={'nested':[]})
    b.save_session_desktop_binding(second)
    a.clear_session_runtime(session_id='s')
    accounts=[AccountDesktopDeviceRecord('u',name,'123456',1,20) for name in ('a','z')]
    for item in accounts:a.save_account_desktop_device(item)
    restarted=RedisRealtimeSpeechRepository(settings)
    assert restarted.list_session_desktop_bindings_for_user(user_id='u')==[replace(first,status='stale'),second]
    assert restarted.list_account_desktop_devices(user_id='u')==list(reversed(accounts))
    assert restarted.list_session_desktop_bindings_for_user(user_id='foreign')==[]
    assert b.save_session_desktop_binding(first).status=='stale'


@pytest.mark.parametrize('damage',['ready','members','members-and-proof','duplicate','identity'])
def test_partial_index_loss_fails_without_global_scan(pair,damage):
    a,_,client,_=pair
    a.save_session_desktop_binding(binding())
    refs,_,proof=a._cn_controls.keys[15:]
    if damage=='ready':client.hdel(proof,'__ready__')
    elif damage=='members':client.hdel(refs,'u')
    elif damage=='members-and-proof':
        client.hdel(refs,'u');client.hdel(proof,'owner:u')
    elif damage=='duplicate':
        client.hset(refs,'u',json.dumps(['u|s','u|s']))
        client.hset(proof,'owner:u',json.dumps({'bindings':2,'accounts':0}))
    else:client.hset(a._binding_entity_key,'u|s',a._cn_controls.encode(binding(owner='foreign')))
    before=client.info('commandstats')
    with pytest.raises(ResponseError,match='cn_'):
        a.list_session_desktop_bindings_for_user(user_id='u')
    after=client.info('commandstats')
    for cmd in ('hvals','hgetall','hscan'):
        assert after.get('cmdstat_'+cmd,{}).get('calls',0)==before.get('cmdstat_'+cmd,{}).get('calls',0)


def test_shared_expiry_and_owner_write_interleaving(pair):
    a,b,client,_=pair
    with ThreadPoolExecutor(4) as workers:
        list(workers.map(lambda n:(a if n%2 else b).save_session_desktop_binding(binding(session='s'+str(n))),range(30)))
    assert len(b.list_session_desktop_bindings_for_user(user_id='u'))==30
    a.save_account_desktop_device(AccountDesktopDeviceRecord('u','d','123456',1,20))
    for key in a._cn_controls.keys[15:]:client.expire(key,5)
    b.save_session_desktop_binding(binding(owner='other',session='other-s'))
    assert all(client.ttl(key)>=299 for key in a._cn_controls.keys[15:])
    client.delete(a._cn_controls.accounts,a._binding_entity_key,*a._cn_controls.keys[15:])
    assert a.list_account_desktop_devices(user_id='u')==[]
    assert a.list_session_desktop_bindings_for_user(user_id='u')==[]
    a.save_session_desktop_binding(binding(owner='__ready__',session='fresh'))
    assert len(b.list_session_desktop_bindings_for_user(user_id='__ready__'))==1


def test_restart_rebuilds_references_after_previous_protocol_wrote_same_size(pair):
    a,_,client,settings=pair
    a.save_session_desktop_binding(binding())
    client.hdel(a._binding_entity_key,'u|s')
    new=binding(owner='new-owner',session='new-session')
    client.hset(a._binding_entity_key,'new-owner|new-session',a._cn_controls.encode(new))
    restarted=RedisRealtimeSpeechRepository(settings)
    assert restarted.list_session_desktop_bindings_for_user(user_id='u')==[]
    assert restarted.list_session_desktop_bindings_for_user(user_id='new-owner')==[new]


def test_full_close_queue_inline_failure_and_shutdown_drain():
    pool=CnProviderCloseExecutor(logging.getLogger('synthetic-close'),workers=1,queue_max=1)
    started,release=threading.Event(),threading.Event()
    calls=[]
    def slow():
        started.set();assert release.wait(3);calls.append('pooled')
    try:
        pool.close(slow);assert started.wait(1)
        pool.close(lambda:calls.append('queued'))
        caller=threading.get_ident()
        pool.close(lambda:calls.append(threading.get_ident()))
        assert calls==[caller]
        assert pool.diagnostics()['pending']==2 and pool.diagnostics()['inline']==1
        with ThreadPoolExecutor(1) as worker:
            stopping=worker.submit(pool.shutdown)
            assert not stopping.done()
            release.set();stopping.result(timeout=2)
        assert calls==[caller,'pooled','queued']
        pool.close(lambda:(_ for _ in ()).throw(ValueError('synthetic-private-message')))
        assert pool.diagnostics()=={'pending':0,'completed':4,'failed':1,'inline':2,'submitted':2,'closed':1}
    finally:
        release.set();pool.shutdown()


def test_submit_failure_after_queueing_cannot_close_twice_or_release_twice(monkeypatch):
    pool=CnProviderCloseExecutor(logging.getLogger('synthetic-submit-failure'),workers=1,queue_max=0)
    queued=[];close=Mock()
    def ambiguous_submit(operation,*args):
        queued.append((operation,args))
        raise RuntimeError('synthetic worker start failure after enqueue')
    monkeypatch.setattr(pool._pool,'submit',ambiguous_submit)
    try:
        pool.close(close)
        operation,args=queued[0];operation(*args)
        close.assert_called_once()
        assert pool.diagnostics()['pending']==0
        pool.close(lambda:None)
        assert len(queued)==1
    finally:pool.shutdown()


def test_optional_close_selection_and_legacy_global_sync():
    for edition in ('cn','global'):
        service,_,_=target(edition)
        deferred=Mock(return_value=2)
        service.asr_gateway.close_session_deferred=deferred
        assert service._close_asr_session(session_id='synthetic')==(2 if edition=='global' else 1)
        assert deferred.call_count==int(edition=='global')
        assert service.asr_gateway.close_session.call_count==int(edition=='cn')
    del service.asr_gateway.close_session_deferred
    service.settings.product_edition='global'
    assert service._close_asr_session(session_id='synthetic')==1


def test_ack_cache_expiry_foreign_and_missing(monkeypatch):
    service=object.__new__(RealtimeSpeechService)
    service.settings=SimpleNamespace(product_edition='global',runtime_performance_ack_session_cache_seconds=60)
    service._performance_ack_access_lock=threading.Lock();service._performance_ack_access_cache={};service._performance_ack_access_hits=0;service._performance_ack_access_misses=0
    read=Mock();service.session_service=SimpleNamespace(get_control_state=read)
    now=[100.0];monkeypatch.setattr('app.services.realtime_speech_service.monotonic',lambda:now[0])
    service._verify_performance_ack_session(user_id='owner',session_id='session',cacheable=True)
    service._verify_performance_ack_session(user_id='owner',session_id='session',cacheable=True)
    assert read.call_count==1
    with pytest.raises(DomainRequestError) as denied:
        service._verify_performance_ack_session(user_id='foreign',session_id='session',cacheable=True)
    assert denied.value.status_code==403
    now[0]=161
    service._verify_performance_ack_session(user_id='owner',session_id='session',cacheable=True)
    assert read.call_count==2
    read.side_effect=DomainRequestError('session','get','synthetic-missing',404)
    with pytest.raises(DomainRequestError):
        service._verify_performance_ack_session(user_id='owner',session_id='missing',cacheable=True)
    assert 'missing' not in service._performance_ack_access_cache


@pytest.mark.parametrize('edition',['cn','global'])
def test_ack_legacy_service_and_global_keep_full_read(edition):
    service=object.__new__(RealtimeSpeechService);service.settings=SimpleNamespace(product_edition=edition)
    service.session_service=SimpleNamespace(get_session=Mock())
    service._read_performance_ack_access(user_id='u',session_id='s')
    service.session_service.get_session.assert_called_once_with(user_id='u',session_id='s')


def test_preparation_progresses_while_lifecycle_is_full_and_cancelled_create_drains():
    async def scenario():
        executor=CnRealtimeIoExecutor(lifecycle_workers=1,lifecycle_queue_max=0)
        started,release=threading.Event(),threading.Event()
        def block():started.set();assert release.wait(3)
        blocker=asyncio.create_task(executor.run(block,lane='lifecycle',operation_name='publisher_disconnect'))
        try:
            assert await asyncio.to_thread(started.wait,1)
            result=await asyncio.wait_for(executor.run(lambda:7,lane='preparation',operation_name='publisher_prepare'),.5)
            assert result==7
            entered,finish=threading.Event(),threading.Event();cleaned=[]
            def create():entered.set();assert finish.wait(2);return 'created'
            task=asyncio.create_task(executor.run(create,lane='preparation',operation_name='publisher_create',on_abandoned_result=cleaned.append))
            assert await asyncio.to_thread(entered.wait,1)
            task.cancel();finish.set();release.set()
            with pytest.raises(asyncio.CancelledError):await task
            assert cleaned==['created']
            await blocker
            assert executor.diagnostics()['preparation']['maxPending']<=10
        finally:
            release.set();await blocker;executor.shutdown()
    asyncio.run(scenario())
