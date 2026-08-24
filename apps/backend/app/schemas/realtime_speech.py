from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ports.realtime_speech import QuestionCandidateState, RealtimeConnectionState, RealtimeEventKind, RealtimeSourceKind, TranscriptRole


class CreateRealtimePublisherRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    session_id: str = Field(min_length=1, alias="sessionId")
    source_kind: RealtimeSourceKind = Field(alias="sourceKind")
    client_name: str = Field(min_length=1, alias="clientName")
    device_id: str | None = Field(default=None, min_length=1, alias="deviceId")
    manual_code: str | None = Field(default=None, min_length=6, max_length=6, alias="manualCode")


class RealtimePublisherResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    publisher_id: str = Field(alias="publisherId")
    token: str
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    source_kind: RealtimeSourceKind = Field(alias="sourceKind")
    client_name: str = Field(alias="clientName")
    issued_at_ms: int = Field(alias="issuedAtMs")
    expires_at_ms: int = Field(alias="expiresAtMs")
    connected_at_ms: int | None = Field(default=None, alias="connectedAtMs")
    disconnected_at_ms: int | None = Field(default=None, alias="disconnectedAtMs")
    status: RealtimeConnectionState


class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    segment_id: str = Field(alias="segmentId")
    source_id: str = Field(alias="sourceId")
    source_kind: RealtimeSourceKind = Field(alias="sourceKind")
    role: TranscriptRole
    revision: int
    text: str
    transcript_confidence: float = Field(alias="transcriptConfidence")
    started_at_ms: int = Field(alias="startedAtMs")
    ended_at_ms: int = Field(alias="endedAtMs")
    is_final: bool = Field(alias="isFinal")
    terminal_state: Literal["final", "incomplete"] | None = Field(default=None, alias="terminalState")
    finalization_reason: str | None = Field(default=None, alias="finalizationReason")
    overlap: bool
    created_at_ms: int = Field(alias="createdAtMs")
    published_at_ms: int | None = Field(default=None, alias="publishedAtMs")
    performance: RealtimeStageTimingResponse | None = None


class QuestionCandidateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    candidate_id: str = Field(alias="candidateId")
    source_segment_ids: list[str] = Field(alias="sourceSegmentIds")
    text: str
    state: QuestionCandidateState
    reason: str
    confidence: float
    answer_task_id: str | None = Field(default=None, alias="answerTaskId")
    created_at_ms: int = Field(alias="createdAtMs")
    updated_at_ms: int = Field(alias="updatedAtMs")


class RealtimeEventResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    event_id: str = Field(alias="eventId")
    kind: RealtimeEventKind
    payload: dict[str, object]
    created_at_ms: int = Field(alias="createdAtMs")


class RealtimeSourceHealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    source_id: str = Field(alias="sourceId")
    source_kind: str = Field(alias="sourceKind")
    label: str
    state: str
    level: float
    stage: str | None = None
    last_signal_at_ms: int | None = Field(default=None, alias="lastSignalAtMs")
    frame_count: int | None = Field(default=None, alias="frameCount")
    last_frame_at_ms: int | None = Field(default=None, alias="lastFrameAtMs")
    backend_frame_count: int | None = Field(default=None, alias="backendFrameCount")
    last_backend_frame_at_ms: int | None = Field(default=None, alias="lastBackendFrameAtMs")
    pending_frame_count: int | None = Field(default=None, alias="pendingFrameCount")
    oldest_pending_frame_age_ms: int | None = Field(default=None, alias="oldestPendingFrameAgeMs")
    dropped_frame_count: int | None = Field(default=None, alias="droppedFrameCount")
    reconnect_count: int | None = Field(default=None, alias="reconnectCount")
    last_ack_at_ms: int | None = Field(default=None, alias="lastAckAtMs")
    last_reconnect_reason: str | None = Field(default=None, alias="lastReconnectReason")
    noise_floor: float | None = Field(default=None, alias="noiseFloor")
    capture_processor: str | None = Field(default=None, alias="captureProcessor")
    endpointing_mode: str | None = Field(default=None, alias="endpointingMode")
    turn_state: str | None = Field(default=None, alias="turnState")
    finalization_reason: str | None = Field(default=None, alias="finalizationReason")
    source_generation: int | None = Field(default=None, alias="sourceGeneration")
    terminal_pending_since_ms: int | None = Field(default=None, alias="terminalPendingSinceMs")
    terminal_age_ms: int | None = Field(default=None, alias="terminalAgeMs")
    terminal_resend_count: int | None = Field(default=None, alias="terminalResendCount")
    terminal_ack_at_ms: int | None = Field(default=None, alias="terminalAckAtMs")
    error_code: str | None = Field(default=None, alias="errorCode")
    provider_mode: str | None = Field(default=None, alias="providerMode")
    provider_connection_state: str | None = Field(default=None, alias="providerConnectionState")
    provider_error_code: str | None = Field(default=None, alias="providerErrorCode")


class RealtimeFrameReceiptResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    source_kind: RealtimeSourceKind = Field(alias="sourceKind")
    source_id: str = Field(alias="sourceId")
    frame_count: int = Field(alias="frameCount")
    last_frame_at_ms: int = Field(alias="lastFrameAtMs")
    last_sequence: int = Field(alias="lastSequence")
    last_asr_status: str = Field(alias="lastAsrStatus")
    last_error_code: str | None = Field(default=None, alias="lastErrorCode")


class RealtimeStageTimingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    trace_id: str | None = Field(default=None, alias="traceId")
    capture_to_send_ms: int | None = Field(default=None, alias="captureToSendMs")
    send_to_ingest_ms: int | None = Field(default=None, alias="sendToIngestMs")
    capture_to_ingest_ms: int | None = Field(default=None, alias="captureToIngestMs")
    queue_wait_ms: int | None = Field(default=None, alias="queueWaitMs")
    asr_ttft_ms: int | None = Field(default=None, alias="asrTtftMs")
    final_transcript_ms: int | None = Field(default=None, alias="finalTranscriptMs")
    stop_to_terminal_ms: int | None = Field(default=None, alias="stopToTerminalMs")
    backend_push_ms: int | None = Field(default=None, alias="backendPushMs")
    capture_to_publish_ms: int | None = Field(default=None, alias="captureToPublishMs")
    frontend_render_ms: int | None = Field(default=None, alias="frontendRenderMs")
    session_id: str | None = Field(default=None, alias="sessionId")
    channel: str | None = None
    sequence: int | None = None
    utterance_id: str | None = Field(default=None, alias="utteranceId")
    event_id: str | None = Field(default=None, alias="eventId")
    speech_start_at_ms: int | None = Field(default=None, alias="speechStartAtMs")
    system_vad_trigger_at_ms: int | None = Field(default=None, alias="systemVadTriggerAtMs")
    system_speech_start_at_ms: int | None = Field(default=None, alias="systemSpeechStartAtMs")
    system_first_effective_partial_at_ms: int | None = Field(default=None, alias="systemFirstEffectivePartialAtMs")
    frames_before_first_partial: int | None = Field(default=None, alias="framesBeforeFirstPartial")
    desktop_audio_capture_at_ms: int | None = Field(default=None, alias="desktopAudioCaptureAtMs")
    desktop_ws_send_at_ms: int | None = Field(default=None, alias="desktopWsSendAtMs")
    backend_ws_receive_at_ms: int | None = Field(default=None, alias="backendWsReceiveAtMs")
    queue_enter_at_ms: int | None = Field(default=None, alias="queueEnterAtMs")
    queue_leave_at_ms: int | None = Field(default=None, alias="queueLeaveAtMs")
    qwen_audio_append_at_ms: int | None = Field(default=None, alias="qwenAudioAppendAtMs")
    qwen_partial_received_at_ms: int | None = Field(default=None, alias="qwenPartialReceivedAtMs")
    qwen_final_received_at_ms: int | None = Field(default=None, alias="qwenFinalReceivedAtMs")
    redis_event_xadd_at_ms: int | None = Field(default=None, alias="redisEventXaddAtMs")
    redis_event_xread_at_ms: int | None = Field(default=None, alias="redisEventXreadAtMs")
    redis_read_mode: str | None = Field(default=None, alias="redisReadMode")
    sse_event_send_at_ms: int | None = Field(default=None, alias="sseEventSendAtMs")
    browser_event_receive_at_ms: int | None = Field(default=None, alias="browserEventReceiveAtMs")
    browser_state_update_at_ms: int | None = Field(default=None, alias="browserStateUpdateAtMs")
    browser_render_at_ms: int | None = Field(default=None, alias="browserRenderAtMs")
    speech_end_detected_at_ms: int | None = Field(default=None, alias="speechEndDetectedAtMs")
    manual_commit_sent_at_ms: int | None = Field(default=None, alias="manualCommitSentAtMs")


class RealtimeRuntimeCountersResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    queue_depth: int = Field(alias="queueDepth")
    dropped_partial_updates: int = Field(alias="droppedPartialUpdates")
    connection_recreations: int = Field(alias="connectionRecreations")
    empty_results_suppressed: int = Field(alias="emptyResultsSuppressed")
    phantom_results_suppressed: int = Field(alias="phantomResultsSuppressed")
    repetitive_results_suppressed: int = Field(alias="repetitiveResultsSuppressed")
    duplicate_results_suppressed: int = Field(alias="duplicateResultsSuppressed")
    filler_results_suppressed: int = Field(alias="fillerResultsSuppressed")
    chunks_produced: int = Field(alias="chunksProduced")
    chunks_uploaded: int = Field(alias="chunksUploaded")
    frames_consumed: int = Field(default=0, alias="framesConsumed")
    serialized_audio_bytes: int = Field(alias="serializedAudioBytes")
    provider_append_count: int = Field(default=0, alias="providerAppendCount")
    provider_commit_count: int = Field(default=0, alias="providerCommitCount")
    provider_completed_missing: int = Field(default=0, alias="providerCompletedMissing")
    blank_partial_suppressed: int = Field(default=0, alias="blankPartialSuppressed")
    vad_to_manual_fallbacks: int = Field(default=0, alias="vadToManualFallbacks")
    idle_provider_session_closures: int = Field(default=0, alias="idleProviderSessionClosures")
    active_provider_sessions: int = Field(default=0, alias="activeProviderSessions")
    asr_connection_create_count: int = Field(default=0, alias="asrConnectionCreateCount")
    asr_connection_reconnect_count: int = Field(default=0, alias="asrConnectionReconnectCount")
    asr_connection_lifetime_ms: int = Field(default=0, alias="asrConnectionLifetimeMs")
    utterance_count: int = Field(default=0, alias="utteranceCount")
    utterances_per_connection: float = Field(default=0, alias="utterancesPerConnection")
    terminal_admissions: int = Field(default=0, alias="terminalAdmissions")
    terminal_duplicates: int = Field(default=0, alias="terminalDuplicates")
    terminal_admission_failures: int = Field(default=0, alias="terminalAdmissionFailures")
    terminal_resends: int = Field(default=0, alias="terminalResends")
    incomplete_recoveries: int = Field(default=0, alias="incompleteRecoveries")
    source_reconnects: int = Field(default=0, alias="sourceReconnects")


class RealtimeRuntimePerformanceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    latest_by_source: dict[str, RealtimeStageTimingResponse] = Field(default_factory=dict, alias="latestBySource")
    counters_by_source: dict[str, RealtimeRuntimeCountersResponse] = Field(default_factory=dict, alias="countersBySource")


class RealtimeSessionRuntimeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    session_status: str = Field(default="unknown", alias="sessionStatus")
    stage: str = "registered"
    backend_reachable: bool = Field(default=True, alias="backendReachable")
    device_registered: bool = Field(default=False, alias="deviceRegistered")
    machine_code_bound: bool = Field(default=False, alias="machineCodeBound")
    session_live: bool = Field(default=False, alias="sessionLive")
    capture_state: str = Field(default="ready", alias="captureState")
    manual_code: str | None = Field(default=None, alias="manualCode")
    device_id: str | None = Field(default=None, alias="deviceId")
    display_name: str | None = Field(default=None, alias="displayName")
    publishers: list[RealtimePublisherResponse]
    source_health: list[RealtimeSourceHealthResponse] = Field(default_factory=list, alias="sourceHealth")
    frame_receipts: list[RealtimeFrameReceiptResponse] = Field(default_factory=list, alias="frameReceipts")
    transcript_count: int = Field(alias="transcriptCount")
    question_candidate_count: int = Field(alias="questionCandidateCount")
    latest_state: RealtimeConnectionState | None = Field(default=None, alias="latestState")
    last_error_code: str | None = Field(default=None, alias="lastErrorCode")
    anomaly_reasons: list[str] = Field(default_factory=list, alias="anomalyReasons")
    dominant_bottleneck: str | None = Field(default=None, alias="dominantBottleneck")
    performance: RealtimeRuntimePerformanceResponse | None = None
    evidence: dict[str, object] = Field(default_factory=dict)
    updated_at_ms: int = Field(alias="updatedAtMs")


class RealtimeTranscriptListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    transcripts: list[TranscriptSegmentResponse]


class RealtimeQuestionCandidateListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    candidates: list[QuestionCandidateResponse]


class RealtimeEventListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    events: list[RealtimeEventResponse]


class RealtimeSessionSnapshotResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    cursor: int
    resumable: bool = True
    transcripts: RealtimeTranscriptListResponse
    candidates: RealtimeQuestionCandidateListResponse
    events: RealtimeEventListResponse
    runtime: RealtimeSessionRuntimeResponse


class RealtimeCandidateCommandRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")


class RealtimeCaptureControlRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    action: str = Field(pattern="^(pause|resume)$")


class RealtimeDeviceStatusRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str | None = Field(default=None, min_length=1, alias="userId")
    capture_state: RealtimeConnectionState | str = Field(alias="captureState")
    device_id: str = Field(min_length=1, alias="deviceId")
    manual_code: str | None = Field(default=None, min_length=6, max_length=6, alias="manualCode")
    source_health: list[dict[str, object]] = Field(default_factory=list, alias="sourceHealth")
    capabilities: dict[str, object] = Field(default_factory=dict)


class RealtimeFrameRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    type: str
    device_id: str = Field(min_length=1, alias="deviceId")
    source_id: str = Field(min_length=1, alias="sourceId")
    sequence: int
    source_kind: RealtimeSourceKind = Field(alias="sourceKind")
    segment_id: str = Field(alias="segmentId")
    revision: int
    captured_at_ms: int = Field(alias="capturedAtMs")
    started_at_ms: int = Field(alias="startedAtMs")
    vad_triggered_at_ms: int | None = Field(default=None, alias="vadTriggeredAtMs")
    speech_confirmed_at_ms: int | None = Field(default=None, alias="speechConfirmedAtMs")
    ended_at_ms: int = Field(alias="endedAtMs")
    duration_ms: int = Field(alias="durationMs")
    codec: str
    sample_rate_hz: int = Field(alias="sampleRateHz")
    channels: int
    is_final: bool = Field(alias="isFinal")
    turn_state: str | None = Field(default=None, alias="turnState")
    finalization_reason: str | None = Field(default=None, alias="finalizationReason")
    source_generation: int | None = Field(default=None, ge=1, alias="sourceGeneration")
    terminal_id: str | None = Field(default=None, min_length=1, max_length=256, alias="terminalId")
    trace_id: str | None = Field(default=None, alias="traceId")
    sent_at_ms: int | None = Field(default=None, alias="sentAtMs")
    audio_base64: str = Field(alias="audioBase64")


class RealtimeFrameIngestRequest(RealtimeFrameRequest):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    token: str = Field(min_length=1)


class RealtimeWsEventEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    kind: str
    payload: dict[str, object]


class RegisterDesktopDeviceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    device_id: str = Field(min_length=1, alias="deviceId")
    manual_code: str = Field(min_length=6, max_length=6, alias="manualCode")
    display_name: str = Field(min_length=1, alias="displayName")
    capabilities: dict[str, object] = Field(default_factory=dict)


class DesktopDeviceHeartbeatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    manual_code: str = Field(min_length=6, max_length=6, alias="manualCode")
    display_name: str | None = Field(default=None, alias="displayName")
    capabilities: dict[str, object] = Field(default_factory=dict)


class WebSessionHeartbeatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    binding_id: str | None = Field(default=None, alias="bindingId")
    page: str = "preparation"
    page_instance_id: str | None = Field(default=None, min_length=8, max_length=128, alias="pageInstanceId")


class BindDesktopDeviceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    manual_code: str | None = Field(default=None, min_length=6, max_length=6, alias="manualCode")
    reuse_last_device: bool = Field(default=False, alias="reuseLastDevice")


class DesktopDeviceBindingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    binding_id: str = Field(alias="bindingId")
    session_id: str = Field(alias="sessionId")
    owner_user_id: str = Field(alias="ownerUserId")
    device_id: str = Field(alias="deviceId")
    manual_code: str = Field(alias="manualCode")
    display_name: str = Field(alias="displayName")
    capabilities: dict[str, object]
    status: str
    bound_at_ms: int = Field(alias="boundAtMs")
    last_seen_at_ms: int = Field(alias="lastSeenAtMs")
    binding_generation: int = Field(alias="bindingGeneration")
    permission_status: dict[str, object] = Field(default_factory=dict, alias="permissionStatus")
    device_presence: str = Field(default="online", alias="devicePresence")
    account_bound: bool = Field(default=True, alias="accountBound")
    session_connection: str = Field(default="connected", alias="sessionConnection")


class RuntimePerformanceAcknowledgementRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True, extra="forbid")
    user_id: str = Field(min_length=1, max_length=128, alias="userId")
    trace_id: str = Field(min_length=1, max_length=128, alias="traceId", pattern=r"^[A-Za-z0-9:._-]+$")
    stage: Literal["transcript-render", "screenshot-first-render", "answer-first-render"]
    duration_ms: int = Field(ge=0, le=120_000, alias="durationMs")
    task_id: str | None = Field(default=None, min_length=1, max_length=128, alias="taskId", pattern=r"^[A-Za-z0-9:._-]+$")
    event_id: str | None = Field(default=None, min_length=1, max_length=128, alias="eventId", pattern=r"^[A-Za-z0-9:._-]+$")
    browser_event_receive_at_ms: int | None = Field(default=None, ge=0, alias="browserEventReceiveAtMs")
    browser_state_update_at_ms: int | None = Field(default=None, ge=0, alias="browserStateUpdateAtMs")
    browser_render_at_ms: int | None = Field(default=None, ge=0, alias="browserRenderAtMs")


class RealtimeDeliveryMetricRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True, extra="forbid")
    user_id: str = Field(min_length=1, max_length=128, alias="userId")
    kind: Literal["connect", "first-snapshot", "connected-duration", "reconnect", "fallback-snapshot"]
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000, alias="durationMs")
    attempt: int | None = Field(default=None, ge=0, le=100)
    reason: Literal["opened", "eof", "network", "aborted", "recovered", "unknown"] | None = None
