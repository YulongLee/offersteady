from types import SimpleNamespace

from app.ports.realtime_speech import QuestionCandidateRecord, TranscriptSegmentRecord
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService


def synthetic_system_transcript(
    text: str = "介绍一下你最近做的项目",
    *,
    segment_id: str = "synthetic-segment",
    started_at_ms: int = 100,
    ended_at_ms: int = 200,
) -> TranscriptSegmentRecord:
    return TranscriptSegmentRecord(
        segment_id=segment_id,
        session_id="synthetic-session",
        owner_user_id="synthetic-user",
        source_id="system-loopback",
        source_kind="system",
        role="interviewer",
        revision=1,
        text=text,
        transcript_confidence=0.96,
        started_at_ms=started_at_ms,
        ended_at_ms=ended_at_ms,
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


def test_adjacent_system_fragments_form_one_question_turn() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    first = synthetic_system_transcript(
        "结合你刚才介绍的订单系统",
        segment_id="synthetic-context",
        started_at_ms=100,
        ended_at_ms=500,
    )
    final = synthetic_system_transcript(
        "你是怎么保证数据一致性的？",
        segment_id="synthetic-question",
        started_at_ms=800,
        ended_at_ms=1_300,
    )
    repository.save_transcript(first)
    repository.save_transcript(final)

    candidate = service_with_repository(repository)._maybe_detect_question(transcript=final)

    assert candidate is not None
    assert candidate.text == "结合你刚才介绍的订单系统 你是怎么保证数据一致性的？"
    assert candidate.source_segment_ids == ["synthetic-context", "synthetic-question"]


def test_candidate_turn_is_a_hard_question_context_boundary() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    old_system = synthetic_system_transcript(
        "旧问题为什么失败？",
        segment_id="old-system",
        started_at_ms=100,
        ended_at_ms=500,
    )
    candidate_turn = TranscriptSegmentRecord(**{
        **old_system.__dict__,
        "segment_id": "candidate-turn",
        "source_id": "microphone",
        "source_kind": "microphone",
        "role": "candidate",
        "text": "我先解释一下。",
        "started_at_ms": 600,
        "ended_at_ms": 1_000,
    })
    latest = synthetic_system_transcript(
        "现在如何改进？",
        segment_id="latest-system",
        started_at_ms=1_100,
        ended_at_ms=1_500,
    )
    for item in (old_system, candidate_turn, latest):
        repository.save_transcript(item)

    candidate = service_with_repository(repository)._maybe_detect_question(transcript=latest)

    assert candidate is not None
    assert candidate.text == "现在如何改进？"
    assert candidate.source_segment_ids == ["latest-system"]


def test_following_fragment_updates_existing_turn_candidate_without_duplicate() -> None:
    repository = InMemoryRealtimeSpeechRepository()
    first = synthetic_system_transcript(
        "请介绍一下你的项目",
        segment_id="question-first",
        started_at_ms=100,
        ended_at_ms=500,
    )
    repository.save_transcript(first)
    service = service_with_repository(repository)
    initial = service._maybe_detect_question(transcript=first)
    assert initial is not None
    repository.save_candidate(QuestionCandidateRecord(**{**initial.__dict__, "answer_task_id": "answer-existing"}))
    following = synthetic_system_transcript(
        "以及你承担的主要职责",
        segment_id="question-following",
        started_at_ms=700,
        ended_at_ms=1_100,
    )
    repository.save_transcript(following)

    updated = service._maybe_detect_question(transcript=following)

    assert updated is not None
    assert updated.candidate_id == initial.candidate_id
    assert updated.answer_task_id == "answer-existing"
    assert updated.text == "请介绍一下你的项目 以及你承担的主要职责"
    assert len(repository.list_candidates_for_session(session_id="synthetic-session")) == 1
