from types import SimpleNamespace

from app.ports.realtime_speech import QuestionCandidateRecord, TranscriptSegmentRecord
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService


def synthetic_system_transcript(text: str = "介绍一下你最近做的项目") -> TranscriptSegmentRecord:
    return TranscriptSegmentRecord(
        segment_id="synthetic-segment",
        session_id="synthetic-session",
        owner_user_id="synthetic-user",
        source_id="system-loopback",
        source_kind="system",
        role="interviewer",
        revision=1,
        text=text,
        transcript_confidence=0.96,
        started_at_ms=100,
        ended_at_ms=200,
        is_final=True,
        overlap=False,
        created_at_ms=200,
    )


def service_with_repository(repository: InMemoryRealtimeSpeechRepository) -> RealtimeSpeechService:
    service = RealtimeSpeechService.__new__(RealtimeSpeechService)
    service.repository = repository
    service.settings = SimpleNamespace(realtime_question_auto_confirm_threshold=0.85)
    return service


def test_complete_question_without_punctuation_is_auto_confirmed() -> None:
    candidate = service_with_repository(InMemoryRealtimeSpeechRepository())._maybe_detect_question(
        transcript=synthetic_system_transcript()
    )

    assert candidate is not None
    assert candidate.state == "confirmed"
    assert candidate.reason == "auto-confirmed"


def test_existing_candidate_with_answer_task_is_reused_for_duplicate_final_event() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    repository.save_candidate(QuestionCandidateRecord(
        candidate_id="question:synthetic-session:synthetic-segment",
        session_id="synthetic-session",
        owner_user_id="synthetic-user",
        source_segment_ids=["synthetic-segment"],
        text="介绍一下你最近做的项目",
        state="confirmed",
        reason="auto-confirmed",
        confidence=0.96,
        answer_task_id="answer-existing",
        created_at_ms=100,
        updated_at_ms=200,
    ))

    candidate = service_with_repository(repository)._maybe_detect_question(
        transcript=synthetic_system_transcript()
    )

    assert candidate is not None
    assert candidate.answer_task_id == "answer-existing"
    assert len(repository.list_candidates_for_session(session_id="synthetic-session")) == 1


def test_low_confidence_question_still_requires_confirmation() -> None:
    transcript = synthetic_system_transcript("你是怎么处理线上故障的")
    transcript = TranscriptSegmentRecord(**{**transcript.__dict__, "transcript_confidence": 0.6})

    candidate = service_with_repository(InMemoryRealtimeSpeechRepository())._maybe_detect_question(transcript=transcript)

    assert candidate is not None
    assert candidate.state == "needs-confirmation"
