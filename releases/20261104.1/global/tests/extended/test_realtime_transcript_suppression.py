from types import SimpleNamespace

import pytest

from app.services.realtime_speech_service import RealtimeSpeechService


@pytest.mark.parametrize("text", ["好的", "是的", "对", "行", "好", "然后呢", "这个可以"])
def test_meaningful_short_chinese_responses_are_not_suppressed(text: str) -> None:
    frame = SimpleNamespace(source_kind="microphone")

    assert RealtimeSpeechService._suppression_reason(text, frame=frame) is None


@pytest.mark.parametrize("text", ["嗯", "嗯嗯", "啊", "呃额", "哦哦"])
def test_pure_vocal_fillers_are_suppressed(text: str) -> None:
    frame = SimpleNamespace(source_kind="microphone")

    assert RealtimeSpeechService._suppression_reason(text, frame=frame) == "filler-transcript"
