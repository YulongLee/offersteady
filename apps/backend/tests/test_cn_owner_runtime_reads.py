"""Owned Redis and synthetic history only; no production record fixtures."""
from collections import Counter
from dataclasses import asdict,replace
import json
from unittest.mock import Mock
import pytest
from test_cn_realtime_entity_state import pair,redis_url,binding
from app.ports.realtime_speech import AccountDesktopDeviceRecord
from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository

@pytest.mark.parametrize('size',[1,1242,10000])
def test_owner_binding_and_account_reads_are_bounded_by_owner(pair,monkeypatch,size,record_testsuite_property):
    first,_,client,settings=pair
    current=binding();first.save_session_desktop_binding(current)
    account=AccountDesktopDeviceRecord('u','d','123456',1,20)
    first.save_account_desktop_device(account)
    data={f'history-owner-{i}|history-session-{i}':json.dumps(asdict(replace(current,owner_user_id=f'history-owner-{i}',session_id=f'history-session-{i}',binding_id=f'history-binding-{i}'))) for i in range(size-1)}
    if data:client.hset(first._binding_entity_key,mapping=data)
    accounts={f'history-owner-{i}|history-device-{i}':json.dumps(asdict(replace(account,owner_user_id=f'history-owner-{i}',device_id=f'history-device-{i}'))) for i in range(size-1)}
    if accounts:client.hset(first._cn_controls.accounts,mapping=accounts)
    # Simulate the actual previous protocol, which has no owner indexes.
    extra=first._cn_controls.keys[15:]
    if extra:client.delete(*extra)
    reader=RedisRealtimeSpeechRepository(settings)
    calls=Counter();original=reader._redis.execute_command
    def counted(command,*args,**kwargs):
        calls[str(command).upper()]+=1
        return original(command,*args,**kwargs)
    monkeypatch.setattr(reader._redis,'execute_command',counted)
    decode=Mock(wraps=reader._cn_controls.decode);monkeypatch.setattr(reader._cn_controls,'decode',decode)
    before=client.info('commandstats')
    assert reader.list_session_desktop_bindings_for_user(user_id='u')==[current]
    assert reader.list_account_desktop_devices(user_id='u')==[account]
    after=client.info('commandstats')
    assert calls['HVALS']==calls['HGETALL']==calls['HSCAN']==calls['HEXISTS']==0,dict(calls)
    assert sum(calls.values())==2,dict(calls)
    assert decode.call_count==2
    for cmd in ('hvals','hgetall','hscan'):
        assert after.get('cmdstat_'+cmd,{}).get('calls',0)==before.get('cmdstat_'+cmd,{}).get('calls',0)
    record_testsuite_property('owner_reads_'+str(size),json.dumps({'history':size,'transportCalls':dict(calls),'recordDecodes':decode.call_count,'globalServerScans':0}))

def test_single_session_end_never_lists_all_user_bindings(monkeypatch):
    from test_cn_realtime_capture_isolation import target
    service,session,_=target()
    service.repository.get_session_desktop_binding=lambda **kw:None
    service.repository.list_session_desktop_bindings_for_user=lambda **kw:pytest.fail('single end must use canonical getter')
    result=service.terminate_session_for_admin(user_id='synthetic-owner',session_id='synthetic-session')
    assert result['status']=='ended' and session.status=='ended'
