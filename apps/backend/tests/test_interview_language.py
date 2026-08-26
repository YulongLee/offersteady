from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.schemas.session import CreateInterviewSessionRequest, UpdateInterviewLanguageRequest
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.session_service import SessionService
from app.ports.realtime_speech import TranscriptSegmentRecord
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService, SyntheticRealtimeAsrGateway
import logging


class EmptyDocumentRepository:
    def get_by_id(self, document_id):
        return None


def make_service(repository=None):
    store = repository or InMemoryInterviewSessionRepository()
    return SessionService(
        settings=Settings(),
        document_repository=EmptyDocumentRepository(),
        repository=store,
    ), store


def test_new_and_old_client_sessions_default_to_chinese() -> None:
    service, repository = make_service()

    created = service.create_session(user_id="language-owner", title="Synthetic interview")
    stored = repository.get_session(created.session_id)

    assert created.interview_language == "zh-CN"
    assert stored is not None and stored.interview_language == "zh-CN"
    assert CreateInterviewSessionRequest(userId="language-owner", title="Legacy request").interview_language == "zh-CN"


def test_preparing_owner_can_persist_english_and_restart_inherits_it() -> None:
    service, _ = make_service()
    created = service.create_session(user_id="language-owner", title="Synthetic interview")

    english = service.update_interview_language(
        user_id="language-owner", session_id=created.session_id, interview_language="en-US"
    )
    ended = service.end_session(
        user_id="language-owner",
        session_id=service.start_session(user_id="language-owner", session_id=created.session_id).session_id,
    )
    restarted = service.restart_session(user_id="language-owner", session_id=ended.session_id)

    assert english.interview_language == "en-US"
    assert restarted.interview_language == "en-US"
    assert restarted.status == "preparing"
    assert service.update_interview_language(
        user_id="language-owner", session_id=restarted.session_id, interview_language="zh-CN"
    ).interview_language == "zh-CN"


def test_language_update_rejects_non_owner_and_live_session() -> None:
    service, _ = make_service()
    created = service.create_session(user_id="language-owner", title="Synthetic interview")

    with pytest.raises(DomainRequestError) as forbidden:
        service.update_interview_language(
            user_id="different-user", session_id=created.session_id, interview_language="en-US"
        )
    assert forbidden.value.status_code == 403

    service.start_session(user_id="language-owner", session_id=created.session_id)
    with pytest.raises(DomainRequestError) as locked:
        service.update_interview_language(
            user_id="language-owner", session_id=created.session_id, interview_language="en-US"
        )
    assert locked.value.status_code == 409
    assert locked.value.error_code == "interview_language_locked"


def test_language_request_rejects_unsupported_value() -> None:
    with pytest.raises(ValidationError):
        UpdateInterviewLanguageRequest(userId="language-owner", interviewLanguage="fr-FR")


def test_concurrent_start_and_language_update_never_mutate_a_live_session_after_start() -> None:
    service, repository = make_service()
    created = service.create_session(user_id="race-owner", title="Synthetic race")
    barrier = Barrier(2)

    def start():
        barrier.wait()
        return service.start_session(user_id="race-owner", session_id=created.session_id)

    def update():
        barrier.wait()
        try:
            return service.update_interview_language(
                user_id="race-owner", session_id=created.session_id, interview_language="en-US"
            )
        except DomainRequestError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        start_future = executor.submit(start)
        update_future = executor.submit(update)
        started = start_future.result()
        update_result = update_future.result()

    final = repository.get_session(created.session_id)
    assert started.status == "live"
    assert final is not None and final.status == "live"
    if isinstance(update_result, DomainRequestError):
        assert update_result.error_code == "interview_language_locked"
        assert final.interview_language == "zh-CN"
    else:
        assert update_result.interview_language == "en-US"
        assert final.interview_language == "en-US"


def test_postgres_row_mapping_and_migration_preserve_closed_language_enum() -> None:
    service, _ = make_service()
    session = service.create_session(
        user_id="language-owner", title="Synthetic interview", interview_language="en-US"
    )
    row = {
        "session_id": session.session_id,
        "owner_user_id": session.owner_user_id,
        "title": session.title,
        "interview_language": "en-US",
        "status": session.status,
        "continue_target": session.continue_target,
        "material_binding_json": asdict(session.material_binding),
        "config_snapshot_json": asdict(session.config_snapshot),
        "usage_totals_json": asdict(session.usage_totals),
        "integration_references_json": [asdict(item) for item in session.integration_references],
        "restart_of_session_id": None,
        "started_at_ms": None,
        "ended_at_ms": None,
        "created_at_ms": session.created_at_ms,
        "updated_at_ms": session.updated_at_ms,
        "last_activity_at_ms": session.last_activity_at_ms,
    }

    repository = object.__new__(PostgresInterviewSessionRepository)
    mapped = repository._row_to_session(row)
    migration = (Path(__file__).parents[1] / "migrations/versions/0033_interview_language.sql").read_text(encoding="utf8")

    assert mapped.interview_language == "en-US"
    assert "ADD COLUMN IF NOT EXISTS interview_language" in migration
    assert "DEFAULT 'zh-CN'" in migration
    assert "CHECK (interview_language IN ('zh-CN', 'en-US'))" in migration


def test_english_question_detection_confirms_system_audio_but_ignores_microphone() -> None:
    sessions, _ = make_service()
    created = sessions.create_session(
        user_id="language-owner", title="English interview", interview_language="en-US"
    )
    sessions.start_session(user_id="language-owner", session_id=created.session_id)
    realtime_repository = InMemoryRealtimeSpeechRepository()
    realtime = RealtimeSpeechService(
        settings=Settings(),
        logger=logging.getLogger("english-question-detection"),
        repository=realtime_repository,
        session_service=sessions,
        asr_gateway=SyntheticRealtimeAsrGateway(Settings()),
    )
    system = TranscriptSegmentRecord(
        segment_id="english-system-question",
        session_id=created.session_id,
        owner_user_id="language-owner",
        source_id="system-loopback",
        source_kind="system",
        role="interviewer",
        revision=1,
        text="Tell me about a difficult production incident you handled.",
        transcript_confidence=0.98,
        started_at_ms=1,
        ended_at_ms=2,
        is_final=True,
        overlap=False,
        created_at_ms=2,
    )
    microphone = TranscriptSegmentRecord(
        **{**system.__dict__, "segment_id": "english-microphone-answer", "source_kind": "microphone", "role": "candidate", "text": "I would start with the incident context."}
    )
    realtime_repository.save_transcript(system)
    realtime_repository.save_transcript(microphone)

    candidate = realtime._maybe_detect_question(transcript=system)

    assert candidate is not None and candidate.state == "confirmed"
    assert candidate.text == system.text
    assert realtime._maybe_detect_question(transcript=microphone) is None
