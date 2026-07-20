from types import SimpleNamespace

from app.services.realtime_speech_service import RealtimeSpeechService


def timeout_budget(*, configured: float, finalize: float, is_final: bool) -> float:
    service = object.__new__(RealtimeSpeechService)
    service.settings = SimpleNamespace(
        realtime_asr_frame_timeout_seconds=configured,
        realtime_asr_finalize_timeout_seconds=finalize,
    )
    frame = SimpleNamespace(is_final=is_final)
    return service._asr_timeout_seconds(frame)


def test_partial_frame_uses_configured_asr_budget() -> None:
    assert timeout_budget(configured=4.0, finalize=8.0, is_final=False) == 4.0


def test_final_frame_budget_covers_finalize_wait() -> None:
    assert timeout_budget(configured=4.0, finalize=8.0, is_final=True) == 9.0


def test_asr_budget_remains_bounded() -> None:
    assert timeout_budget(configured=60.0, finalize=8.0, is_final=True) == 30.0
