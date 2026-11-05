from types import SimpleNamespace
import logging,threading
from unittest.mock import Mock
import pytest
from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway,_SourceRealtimeSession
from app.core.config import Settings

def test_deferred_source_detaches_before_slow_physical_close():
    gateway=DashScopeRealtimeAsrGateway(Settings(_env_file=None,product_edition='cn'),logging.getLogger('synthetic-close'))
    started,release=threading.Event(),threading.Event()
    connection=SimpleNamespace(close=lambda:(started.set(),release.wait(2)))
    session=_SourceRealtimeSession(connection,16000,0,0,'synthetic:microphone','microphone')
    gateway._source_sessions['synthetic:microphone']=session
    try:
        assert gateway.close_source_deferred(session_id='synthetic',source_kind='microphone')==1
        assert started.wait(1) and session.closed and not session.accepting_transcript_events and 'synthetic:microphone' not in gateway._source_sessions
        replacement=Mock();gateway._source_sessions['synthetic:microphone']=_SourceRealtimeSession(replacement,16000,0,0,'synthetic:microphone','microphone')
        release.set();gateway.drain_deferred_closes()
        replacement.close.assert_not_called()
    finally:
        release.set();gateway.close_all_sessions()

def test_late_provider_text_after_logical_close_is_ignored():
    import json
    from concurrent.futures import ThreadPoolExecutor
    gateway=DashScopeRealtimeAsrGateway(Settings(_env_file=None,product_edition='cn'),logging.getLogger('synthetic-late'))
    reading,deliver=threading.Event(),threading.Event()
    def recv(**kw):
        reading.set();assert deliver.wait(2)
        return json.dumps({'type':'conversation.item.input_audio_transcription.text','text':'Synthetic late text'})
    session=_SourceRealtimeSession(SimpleNamespace(close=lambda:None,recv=recv),16000,0,0,'synthetic:microphone','microphone')
    gateway._source_sessions['synthetic:microphone']=session
    gateway._partial_listener=Mock()
    try:
        with ThreadPoolExecutor(1) as worker:
            receiving=worker.submit(gateway._receive_events,session)
            assert reading.wait(1)
            gateway.close_source_deferred(session_id='synthetic',source_kind='microphone')
            deliver.set();receiving.result(timeout=1)
        assert session.transcript_text=='' and session.event_revision==0
        gateway._partial_listener.assert_not_called()
    finally:
        deliver.set();gateway.close_all_sessions()
