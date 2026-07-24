from __future__ import annotations

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
    backend_push_ms: int | None = Field(default=None, alias="backendPushMs")
    capture_to_publish_ms: int | None = Field(default=None, alias="captureToPublishMs")
    frontend_render_ms: int | None = Field(default=None, alias="frontendRenderMs")


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
    serialized_audio_bytes: int = Field(alias="serializedAudioBytes")


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


class RealtimeCandidateCommandRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")


class RealtimeDeviceStatusRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    capture_state: RealtimeConnectionState | str = Field(alias="captureState")
    device_id: str = Field(min_length=1, alias="deviceId")
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
    ended_at_ms: int = Field(alias="endedAtMs")
    duration_ms: int = Field(alias="durationMs")
    codec: str
    sample_rate_hz: int = Field(alias="sampleRateHz")
    channels: int
    is_final: bool = Field(alias="isFinal")
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


class BindDesktopDeviceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    user_id: str = Field(min_length=1, alias="userId")
    manual_code: str = Field(min_length=6, max_length=6, alias="manualCode")


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
