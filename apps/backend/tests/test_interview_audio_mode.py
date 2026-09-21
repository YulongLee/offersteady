from dataclasses import asdict
from pathlib import Path
import logging
import time

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import DomainRequestError
from app.ports.realtime_speech import DesktopDeviceRecord, SessionDesktopBindingRecord, TranscriptSegmentRecord
from app.schemas.session import CreateInterviewSessionRequest, UpdateInterviewAudioModeRequest
from app.services.interview_session_repository import InMemoryInterviewSessionRepository
from app.services.postgres_interview_session_repository import PostgresInterviewSessionRepository
from app.services.realtime_speech_repository import InMemoryRealtimeSpeechRepository
from app.services.realtime_speech_service import RealtimeSpeechService, SyntheticRealtimeAsrGateway
from app.services.session_service import SessionService


class EmptyDocumentRepository:
    def get_by_id(self, document_id):
        return None


def make_sessions():
    repository = InMemoryInterviewSessionRepository()
    service = SessionService(
        settings=Settings(_env_file=None),
        document_repository=EmptyDocumentRepository(),
        repository=repository,
    )
    return service, repository


def make_realtime(sessions: SessionService):
    repository = InMemoryRealtimeSpeechRepository()
    return RealtimeSpeechService(
        settings=Settings(_env_file=None),
        logger=logging.getLogger("mobile-interview-audio-mode"),
        repository=repository,
        session_service=sessions,
        asr_gateway=SyntheticRealtimeAsrGateway(Settings(_env_file=None)),
    ), repository


def test_legacy_request_defaults_to_computer_and_mobile_restart_inherits_mode() -> None:
    sessions, repository = make_sessions()
    legacy = sessions.create_session(user_id="audio-owner", title="Legacy interview")
    mobile = sessions.create_session(
        user_id="audio-owner", title="Mobile interview", interview_audio_mode="mobile"
    )
    sessions.start_session(user_id="audio-owner", session_id=mobile.session_id)
    sessions.end_session(user_id="audio-owner", session_id=mobile.session_id)
    restarted = sessions.restart_session(user_id="audio-owner", session_id=mobile.session_id)

    assert legacy.interview_audio_mode == "computer"
    assert repository.get_session(legacy.session_id).interview_audio_mode == "computer"
    assert CreateInterviewSessionRequest(userId="audio-owner", title="Old client").interview_audio_mode == "computer"
    assert restarted.interview_audio_mode == "mobile"


def test_audio_mode_can_change_only_during_preparation() -> None:
    sessions, _ = make_sessions()
    created = sessions.create_session(user_id="audio-owner", title="Synthetic interview")
    updated = sessions.update_interview_audio_mode(
        user_id="audio-owner", session_id=created.session_id, interview_audio_mode="mobile"
    )
    assert updated.interview_audio_mode == "mobile"

    sessions.start_session(user_id="audio-owner", session_id=created.session_id)
    with pytest.raises(DomainRequestError) as locked:
        sessions.update_interview_audio_mode(
            user_id="audio-owner", session_id=created.session_id, interview_audio_mode="computer"
        )
    assert locked.value.error_code == "interview_audio_mode_locked"

    with pytest.raises(ValidationError):
        UpdateInterviewAudioModeRequest(userId="audio-owner", interviewAudioMode="speakerphone")


def test_postgres_mapping_and_migration_preserve_audio_mode() -> None:
    sessions, _ = make_sessions()
    session = sessions.create_session(
        user_id="audio-owner", title="Mobile interview", interview_audio_mode="mobile"
    )
    row = {
        "session_id": session.session_id,
        "owner_user_id": session.owner_user_id,
        "title": session.title,
        "session_mode": "interview",
        "interview_audio_mode": "mobile",
        "interview_language": "zh-CN",
        "status": session.status,
        "continue_target": session.continue_target,
        "material_binding_json": asdict(session.material_binding),
        "config_snapshot_json": asdict(session.config_snapshot),
        "usage_totals_json": asdict(session.usage_totals),
        "integration_references_json": [],
        "restart_of_session_id": None,
        "started_at_ms": None,
        "ended_at_ms": None,
        "created_at_ms": session.created_at_ms,
        "updated_at_ms": session.updated_at_ms,
        "last_activity_at_ms": session.last_activity_at_ms,
    }
    mapped = object.__new__(PostgresInterviewSessionRepository)._row_to_session(row)
    migration = (Path(__file__).parents[1] / "migrations/versions/0049_interview_audio_mode.sql").read_text(encoding="utf8")

    assert mapped.interview_audio_mode == "mobile"
    assert "DEFAULT 'computer'" in migration
    assert "CHECK (interview_audio_mode IN ('computer', 'mobile'))" in migration


def test_mobile_mode_accepts_microphone_publisher_and_rejects_system_publisher() -> None:
    sessions, _ = make_sessions()
    created = sessions.create_session(
        user_id="audio-owner", title="Mobile interview", interview_audio_mode="mobile"
    )
    sessions.start_session(user_id="audio-owner", session_id=created.session_id)
    realtime, _ = make_realtime(sessions)

    microphone = realtime.create_publisher(
        user_id="audio-owner", session_id=created.session_id,
        source_kind="microphone", client_name="synthetic-mobile",
    )
    assert microphone.source_kind == "microphone"
    with pytest.raises(DomainRequestError) as rejected:
        realtime.create_publisher(
            user_id="audio-owner", session_id=created.session_id,
            source_kind="system", client_name="unexpected-system",
        )
    assert rejected.value.error_code == "mobile_interview_system_audio_disabled"


def test_pairing_status_exposes_persisted_mobile_audio_mode() -> None:
    sessions, _ = make_sessions()
    created = sessions.create_session(
        user_id="audio-owner", title="Mobile interview", interview_audio_mode="mobile"
    )
    realtime, repository = make_realtime(sessions)
    now_ms = int(time.time() * 1000)
    device = repository.save_desktop_device(DesktopDeviceRecord(
        device_id="mobile-device",
        manual_code="246810",
        display_name="Synthetic Mac",
        capabilities={"microphone": True, "systemAudio": True},
        registered_at_ms=now_ms,
        last_seen_at_ms=now_ms,
    ))
    repository.save_session_desktop_binding(SessionDesktopBindingRecord(
        binding_id="mobile-binding",
        session_id=created.session_id,
        owner_user_id="audio-owner",
        device_id=device.device_id,
        manual_code=device.manual_code,
        display_name=device.display_name,
        capabilities=device.capabilities,
        bound_at_ms=now_ms,
        last_seen_at_ms=now_ms,
        binding_generation=device.generation,
    ))

    status = realtime._compute_desktop_pairing_status(
        manual_code=device.manual_code,
        device_id=device.device_id,
    )

    assert status["state"] == "bound"
    assert status["interviewAudioMode"] == "mobile"


def test_mobile_final_microphone_question_enters_question_flow_but_self_talk_does_not() -> None:
    sessions, _ = make_sessions()
    created = sessions.create_session(
        user_id="audio-owner", title="Mobile interview", interview_audio_mode="mobile"
    )
    sessions.start_session(user_id="audio-owner", session_id=created.session_id)
    realtime, repository = make_realtime(sessions)
    realtime._session_audio_mode_cache[created.session_id] = "mobile"

    question = TranscriptSegmentRecord(
        segment_id="mobile-question",
        session_id=created.session_id,
        owner_user_id="audio-owner",
        source_id="mac-microphone",
        source_kind="microphone",
        role="interviewer",
        revision=1,
        text="请介绍一下你最近负责的项目？",
        transcript_confidence=0.98,
        started_at_ms=1,
        ended_at_ms=2,
        is_final=True,
        overlap=False,
        created_at_ms=2,
    )
    self_talk = TranscriptSegmentRecord(
        **{**question.__dict__, "segment_id": "candidate-self-talk", "text": "我先想一下项目背景。"}
    )
    partial = TranscriptSegmentRecord(
        **{**question.__dict__, "segment_id": "partial-question", "is_final": False}
    )
    too_short = TranscriptSegmentRecord(
        **{**question.__dict__, "segment_id": "short-question", "text": "吗？"}
    )
    unexpected_system = TranscriptSegmentRecord(
        **{**question.__dict__, "segment_id": "system-question", "source_kind": "system"}
    )
    repository.save_transcript(question)
    repository.save_transcript(self_talk)

    candidate = realtime._maybe_detect_question(transcript=question)
    assert candidate is not None and candidate.state == "confirmed"
    assert realtime._maybe_detect_question(transcript=self_talk) is None
    assert realtime._maybe_detect_question(transcript=partial) is None
    assert realtime._maybe_detect_question(transcript=too_short) is None
    assert realtime._maybe_detect_question(transcript=unexpected_system) is None

    realtime._clear_session_state_indexes(session_id=created.session_id)
    assert created.session_id not in realtime._session_audio_mode_cache
