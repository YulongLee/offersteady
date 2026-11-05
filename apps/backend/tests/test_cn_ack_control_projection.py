from collections import deque
import logging,threading
from types import SimpleNamespace
from unittest.mock import Mock,patch
import pytest
from app.services.realtime_speech_service import RealtimeSpeechService

@pytest.mark.parametrize('stage',['transcript-delivery','transcript-render','answer-first-render','screenshot-first-render'])
def test_cn_all_ack_stages_only_read_authoritative_projection(stage):
    service=object.__new__(RealtimeSpeechService)
    service.settings=SimpleNamespace(product_edition='cn',app_name='Synthetic',environment='test')
    service.logger=logging.getLogger('synthetic-ack-light');service.logger.setLevel(logging.INFO)
    service.session_service=SimpleNamespace(get_control_state=Mock(),get_session=Mock(side_effect=AssertionError('must not refresh resume for telemetry')))
    service._trace_lock=threading.Lock();service._trace_records={};service._trace_order=deque(maxlen=4096)
    service._latest_timing=lambda **kw:None
    with patch('app.services.realtime_speech_service.log_event',side_effect=AssertionError('disabled DEBUG must not serialize')):
        result=service.acknowledge_runtime_timing(user_id='synthetic-owner',session_id='synthetic-session',trace_id='synthetic-trace',stage=stage,duration_ms=20)
    assert result.kind=='performance-ack'
    service.session_service.get_control_state.assert_called_once_with(user_id='synthetic-owner',session_id='synthetic-session')
