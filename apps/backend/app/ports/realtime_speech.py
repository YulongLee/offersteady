from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


RealtimeConnectionState = Literal["connected", "receiving-audio", "transcribing", "degraded", "reconnecting", "answer-streaming", "failed", "closed"]
RealtimeEventKind = Literal["connection-state", "transcript-updated", "question-candidate", "question-confirmed", "answer-completed", "degraded", "device-status"]
RealtimeSourceKind = Literal["microphone", "system", "mixed"]
TranscriptRole = Literal["candidate", "interviewer"]
QuestionCandidateState = Literal["needs-confirmation", "confirmed", "dismissed"]
RealtimeAsrFrameStatus = Literal["pending", "accepted", "failed"]


@dataclass(frozen=True)
class RealtimePublisherRecord:
    publisher_id: str
    token: str
    session_id: str
    owner_user_id: str
    source_kind: RealtimeSourceKind
    client_name: str
    issued_at_ms: int
    expires_at_ms: int
    connected_at_ms: int | None = None
    disconnected_at_ms: int | None = None
    status: RealtimeConnectionState = "connected"


@dataclass(frozen=True)
class AudioFrame:
    publisher_id: str
    session_id: str
    device_id: str
    source_id: str
    source_kind: RealtimeSourceKind
    segment_id: str
    revision: int
    sequence: int
    captured_at_ms: int
    started_at_ms: int
    ended_at_ms: int
    duration_ms: int
    codec: Literal["opus", "pcm", "audio/pcm", "audio/raw", "raw", "pcm-s16le"]
    sample_rate_hz: int
    channels: int
    is_final: bool
    audio_bytes: bytes
    trace_id: str | None = None
    sent_at_ms: int | None = None


@dataclass(frozen=True)
class RealtimeFrameReceiptRecord:
    session_id: str
    owner_user_id: str
    publisher_id: str
    device_id: str
    source_id: str
    source_kind: RealtimeSourceKind
    sequence: int
    frame_count: int
    captured_at_ms: int
    received_at_ms: int
    asr_status: RealtimeAsrFrameStatus = "pending"
    error_code: str | None = None


@dataclass(frozen=True)
class AsrUsageReport:
    total_tokens: int
    provider_name: str
    model_name: str


@dataclass(frozen=True)
class TranscriptSegmentRecord:
    segment_id: str
    session_id: str
    owner_user_id: str
    source_id: str
    source_kind: RealtimeSourceKind
    role: TranscriptRole
    revision: int
    text: str
    transcript_confidence: float
    started_at_ms: int
    ended_at_ms: int
    is_final: bool
    overlap: bool
    created_at_ms: int
    published_at_ms: int | None = None
    performance: dict[str, int | None] | None = None
    usage: AsrUsageReport | None = None


@dataclass(frozen=True)
class QuestionCandidateRecord:
    candidate_id: str
    session_id: str
    owner_user_id: str
    source_segment_ids: list[str]
    text: str
    state: QuestionCandidateState
    reason: str
    confidence: float
    answer_task_id: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0


@dataclass(frozen=True)
class RealtimeEvent:
    event_id: str
    session_id: str
    owner_user_id: str
    kind: RealtimeEventKind
    payload: dict[str, object]
    created_at_ms: int


@dataclass(frozen=True)
class DesktopDeviceRecord:
    device_id: str
    manual_code: str
    display_name: str
    capabilities: dict[str, object]
    registered_at_ms: int
    last_seen_at_ms: int
    status: Literal["online", "offline"] = "online"
    generation: int = 1


@dataclass(frozen=True)
class SessionDesktopBindingRecord:
    binding_id: str
    session_id: str
    owner_user_id: str
    device_id: str
    manual_code: str
    display_name: str
    capabilities: dict[str, object]
    bound_at_ms: int
    last_seen_at_ms: int
    status: Literal["bound", "stale"] = "bound"
    binding_generation: int = 1


@dataclass(frozen=True)
class WebSessionHeartbeatRecord:
    session_id: str
    owner_user_id: str
    page: Literal["preparation", "live"]
    seen_at_ms: int
    binding_id: str | None = None


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    confidence: float
    overlap: bool = False
    usage: AsrUsageReport | None = None
    first_text_at_ms: int | None = None
    completed_at_ms: int | None = None
    suppressed_reason: str | None = None


class RealtimeAsrGatewayPort(Protocol):
    def transcribe(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult: ...


class RealtimeSpeechRepository(Protocol):
    def save_desktop_device(self, device: DesktopDeviceRecord) -> DesktopDeviceRecord: ...

    def get_desktop_device_by_code(self, manual_code: str) -> DesktopDeviceRecord | None: ...

    def save_session_desktop_binding(self, binding: SessionDesktopBindingRecord) -> SessionDesktopBindingRecord: ...

    def get_session_desktop_binding(self, *, user_id: str, session_id: str) -> SessionDesktopBindingRecord | None: ...

    def get_latest_session_desktop_binding_for_device(self, *, device_id: str, manual_code: str) -> SessionDesktopBindingRecord | None: ...

    def get_latest_session_desktop_binding_by_code(self, *, manual_code: str) -> SessionDesktopBindingRecord | None: ...

    def save_web_session_heartbeat(self, heartbeat: WebSessionHeartbeatRecord) -> WebSessionHeartbeatRecord: ...

    def get_web_session_heartbeat(self, *, user_id: str, session_id: str) -> WebSessionHeartbeatRecord | None: ...

    def save_publisher(self, publisher: RealtimePublisherRecord) -> RealtimePublisherRecord: ...

    def get_publisher_by_token(self, token: str) -> RealtimePublisherRecord | None: ...

    def get_publisher(self, publisher_id: str) -> RealtimePublisherRecord | None: ...

    def list_publishers_for_session(self, *, session_id: str) -> list[RealtimePublisherRecord]: ...

    def save_frame_receipt(self, receipt: RealtimeFrameReceiptRecord) -> RealtimeFrameReceiptRecord: ...

    def list_frame_receipts_for_session(self, *, session_id: str) -> list[RealtimeFrameReceiptRecord]: ...

    def save_transcript(self, segment: TranscriptSegmentRecord) -> TranscriptSegmentRecord: ...

    def get_transcript(self, session_id: str, segment_id: str) -> TranscriptSegmentRecord | None: ...

    def list_transcripts_for_session(self, *, session_id: str) -> list[TranscriptSegmentRecord]: ...

    def save_candidate(self, candidate: QuestionCandidateRecord) -> QuestionCandidateRecord: ...

    def get_candidate(self, candidate_id: str) -> QuestionCandidateRecord | None: ...

    def list_candidates_for_session(self, *, session_id: str) -> list[QuestionCandidateRecord]: ...

    def save_event(self, event: RealtimeEvent) -> RealtimeEvent: ...

    def list_events_for_session(self, *, session_id: str) -> list[RealtimeEvent]: ...

    def get_session_activity_version(self, *, session_id: str) -> int: ...
