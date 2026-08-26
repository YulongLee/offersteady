from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.ports.interview_session import InterviewLanguage


RealtimeConnectionState = Literal["connected", "receiving-audio", "transcribing", "degraded", "reconnecting", "answer-streaming", "failed", "closed"]
RealtimeEventKind = Literal["connection-state", "transcript-updated", "question-stable", "question-candidate", "question-confirmed", "answer-stream", "answer-completed", "answer-task-updated", "screenshot-capture-updated", "performance-ack", "degraded", "device-status", "capture-control", "screenshot-shortcut-accepted"]
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
    turn_state: str | None = None
    finalization_reason: str | None = None
    source_generation: int | None = None
    terminal_id: str | None = None
    trace_id: str | None = None
    sent_at_ms: int | None = None
    vad_triggered_at_ms: int | None = None
    speech_confirmed_at_ms: int | None = None
    backend_received_at_ms: int | None = None
    diagnostics: dict[str, object] = field(default_factory=dict)
    interview_language: InterviewLanguage = "zh-CN"


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
    terminal_state: Literal["final", "incomplete"] | None = None
    finalization_reason: str | None = None
    published_at_ms: int | None = None
    performance: dict[str, object] | None = None
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
class AccountDesktopDeviceRecord:
    owner_user_id: str
    device_id: str
    manual_code: str
    linked_at_ms: int
    last_used_at_ms: int


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
    page_instance_id: str | None = None
    lease_generation: int = 0
    lease_expires_at_ms: int = 0


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    confidence: float
    overlap: bool = False
    usage: AsrUsageReport | None = None
    first_text_at_ms: int | None = None
    partial_received_at_ms: int | None = None
    completed_at_ms: int | None = None
    audio_appended_at_ms: int | None = None
    first_audio_appended_at_ms: int | None = None
    commit_sent_at_ms: int | None = None
    suppressed_reason: str | None = None
    asr_lock_wait_start_at_ms: int | None = None
    asr_lock_acquired_at_ms: int | None = None
    qwen_send_enqueue_at_ms: int | None = None
    qwen_ws_send_start_at_ms: int | None = None
    qwen_ws_send_complete_at_ms: int | None = None
    provider_revision: int | None = None
    connection_id: str | None = None


class RealtimeAsrGatewayPort(Protocol):
    def warm_session(
        self,
        *,
        session_id: str,
        source_kind: RealtimeSourceKind,
        sample_rate_hz: int = 16_000,
        interview_language: InterviewLanguage = "zh-CN",
    ) -> None: ...

    def transcribe(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult: ...

    def finalize(self, *, frame: AudioFrame, attempt: int) -> TranscriptResult: ...

    def close_source(self, *, session_id: str, source_kind: RealtimeSourceKind) -> int: ...

    def close_session(self, *, session_id: str) -> int: ...


class RealtimeSpeechRepository(Protocol):
    def save_desktop_device(self, device: DesktopDeviceRecord) -> DesktopDeviceRecord: ...

    def get_desktop_device_by_code(self, manual_code: str) -> DesktopDeviceRecord | None: ...

    def save_account_desktop_device(self, association: AccountDesktopDeviceRecord) -> AccountDesktopDeviceRecord: ...

    def get_account_desktop_device(self, *, user_id: str, device_id: str) -> AccountDesktopDeviceRecord | None: ...

    def get_last_account_desktop_device(self, *, user_id: str) -> AccountDesktopDeviceRecord | None: ...

    def list_account_desktop_devices(self, *, user_id: str) -> list[AccountDesktopDeviceRecord]: ...

    def save_session_desktop_binding(self, binding: SessionDesktopBindingRecord) -> SessionDesktopBindingRecord: ...

    def get_session_desktop_binding(self, *, user_id: str, session_id: str) -> SessionDesktopBindingRecord | None: ...

    def get_latest_session_desktop_binding_for_device(self, *, device_id: str, manual_code: str) -> SessionDesktopBindingRecord | None: ...

    def get_latest_session_desktop_binding_by_code(self, *, manual_code: str) -> SessionDesktopBindingRecord | None: ...

    def list_session_desktop_bindings_for_device(self, *, device_id: str, manual_code: str) -> list[SessionDesktopBindingRecord]: ...

    def list_session_desktop_bindings_for_user(self, *, user_id: str) -> list[SessionDesktopBindingRecord]: ...

    def save_web_session_heartbeat(self, heartbeat: WebSessionHeartbeatRecord) -> WebSessionHeartbeatRecord: ...

    def get_web_session_heartbeat(self, *, user_id: str, session_id: str) -> WebSessionHeartbeatRecord | None: ...

    def claim_live_web_session(self, heartbeat: WebSessionHeartbeatRecord) -> WebSessionHeartbeatRecord: ...

    def get_active_live_web_session(self, *, user_id: str) -> WebSessionHeartbeatRecord | None: ...

    def save_publisher(self, publisher: RealtimePublisherRecord) -> RealtimePublisherRecord: ...

    def get_publisher_by_token(self, token: str) -> RealtimePublisherRecord | None: ...

    def get_publisher(self, publisher_id: str) -> RealtimePublisherRecord | None: ...

    def list_publishers_for_session(self, *, session_id: str) -> list[RealtimePublisherRecord]: ...

    def prune_publishers_for_session(self, *, session_id: str, keep_publisher_ids: set[str]) -> None: ...

    def save_frame_receipt(self, receipt: RealtimeFrameReceiptRecord) -> RealtimeFrameReceiptRecord: ...

    def get_frame_receipt(self, *, session_id: str, source_kind: str, source_id: str) -> RealtimeFrameReceiptRecord | None: ...

    def list_frame_receipts_for_session(self, *, session_id: str) -> list[RealtimeFrameReceiptRecord]: ...

    def save_transcript(self, segment: TranscriptSegmentRecord) -> TranscriptSegmentRecord: ...

    def persist_transcript(self, segment: TranscriptSegmentRecord) -> None: ...

    def get_transcript(self, session_id: str, segment_id: str) -> TranscriptSegmentRecord | None: ...

    def list_transcripts_for_session(self, *, session_id: str) -> list[TranscriptSegmentRecord]: ...

    def save_candidate(self, candidate: QuestionCandidateRecord) -> QuestionCandidateRecord: ...

    def get_candidate(self, candidate_id: str) -> QuestionCandidateRecord | None: ...

    def list_candidates_for_session(self, *, session_id: str) -> list[QuestionCandidateRecord]: ...

    def save_event(self, event: RealtimeEvent) -> RealtimeEvent: ...

    def list_events_for_session(self, *, session_id: str) -> list[RealtimeEvent]: ...

    def list_latest_events_for_session(
        self, *, session_id: str, kinds: set[RealtimeEventKind]
    ) -> list[RealtimeEvent]: ...

    def list_events_after(self, *, session_id: str, cursor: int) -> tuple[int, list[RealtimeEvent], bool]: ...

    def wait_for_events_after(
        self, *, session_id: str, cursor: int, timeout_ms: int
    ) -> tuple[int, list[RealtimeEvent], bool]: ...

    def get_session_activity_version(self, *, session_id: str) -> int: ...
