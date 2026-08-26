import type { RealtimeAudioChannel } from "@offersteady/protocol";

const CHANNELS: readonly RealtimeAudioChannel[] = ["system", "microphone"];
const MAX_TRACKED_SEQUENCES = 8_192;
const MAX_DUPLICATE_SAMPLES = 20;

interface MutableChannelCounters {
  captureFrames: number;
  publisherInputFrames: number;
  uniqueFrames: number;
  expectedUniqueAudioBytes: number;
  websocketSendCalls: number;
  websocketAudioPayloadBytes: number;
  websocketTotalBytes: number;
  ackCount: number;
  lastSentSeq: number | null;
  lastAckedSeq: number | null;
  resendFrames: number;
  resendBytes: number;
  sequenceGapCount: number;
  sequenceGapRecoveryFrames: number;
  reconnectCount: number;
  ringBufferDepth: number;
  retransmitQueueDepth: number;
  duplicateSeqSendCount: number;
  maximumSendCount: number;
  unexpectedAudioFormatFrames: number;
  activeAudioListeners: number;
  maximumAudioListeners: number;
  transportGeneration: number;
  inFlightFrames: number;
  oldestUnacknowledgedAtMs: number | null;
  lastGenerationSentSeq: number | null;
  lastGenerationAckedSeq: number | null;
}

interface SequenceSendState {
  readonly sequence: number;
  audioBytes: number;
  sendCount: number;
  publisherRecorded: boolean;
  uniqueRecorded: boolean;
}

export interface RealtimeTransportChannelSnapshot {
  readonly interval_seconds: number;
  readonly capture_frames: number;
  readonly publisher_input_frames: number;
  readonly unique_frames: number;
  readonly websocket_send_calls: number;
  readonly websocket_audio_payload_bytes: number;
  readonly websocket_total_bytes: number;
  readonly ack_count: number;
  readonly last_sent_seq: number | null;
  readonly last_acked_seq: number | null;
  readonly resend_frames: number;
  readonly resend_bytes: number;
  readonly sequence_gap_count: number;
  readonly sequence_gap_recovery_frames: number;
  readonly reconnect_count: number;
  readonly ring_buffer_depth: number;
  readonly retransmit_queue_depth: number;
  readonly duplicate_seq_send_count: number;
  readonly maximum_send_count_for_one_seq: number;
  readonly active_audio_listeners: number;
  readonly maximum_audio_listeners: number;
  readonly unexpected_audio_format_frames: number;
  readonly capture_fps: number;
  readonly publisher_input_fps: number;
  readonly unique_send_fps: number;
  readonly actual_ws_send_fps: number;
  readonly audio_kb_per_second: number;
  readonly total_kb_per_second: number;
  readonly ack_per_second: number;
  readonly resend_fps: number;
  readonly resend_kb_per_second: number;
  readonly send_amplification_ratio: number;
  readonly byte_amplification_ratio: number;
  readonly amplification_status: "normal" | "abnormal" | "severe" | "storm";
  readonly duplicate_sequence_samples: readonly {
    readonly sequence: number;
    readonly send_count: number;
    readonly audio_bytes_per_send: number;
  }[];
  readonly transport_generation: number;
  readonly in_flight_frames: number;
  readonly oldest_unacknowledged_age_ms: number;
  readonly generation_last_sent_seq: number | null;
  readonly generation_last_acked_seq: number | null;
}

export interface RealtimeTransportDiagnosticsSnapshot {
  readonly kind: "realtime-audio-transport-diagnostics";
  readonly captured_at_ms: number;
  readonly session_id: string;
  readonly SYSTEM: RealtimeTransportChannelSnapshot;
  readonly MIC: RealtimeTransportChannelSnapshot;
}

type CounterKey = keyof Pick<MutableChannelCounters,
  | "captureFrames"
  | "publisherInputFrames"
  | "uniqueFrames"
  | "expectedUniqueAudioBytes"
  | "websocketSendCalls"
  | "websocketAudioPayloadBytes"
  | "websocketTotalBytes"
  | "ackCount"
  | "resendFrames"
  | "resendBytes"
>;

const emptyCounters = (): MutableChannelCounters => ({
  captureFrames: 0,
  publisherInputFrames: 0,
  uniqueFrames: 0,
  expectedUniqueAudioBytes: 0,
  websocketSendCalls: 0,
  websocketAudioPayloadBytes: 0,
  websocketTotalBytes: 0,
  ackCount: 0,
  lastSentSeq: null,
  lastAckedSeq: null,
  resendFrames: 0,
  resendBytes: 0,
  sequenceGapCount: 0,
  sequenceGapRecoveryFrames: 0,
  reconnectCount: 0,
  ringBufferDepth: 0,
  retransmitQueueDepth: 0,
  duplicateSeqSendCount: 0,
  maximumSendCount: 0,
  unexpectedAudioFormatFrames: 0,
  activeAudioListeners: 0,
  maximumAudioListeners: 0,
  transportGeneration: 0,
  inFlightFrames: 0,
  oldestUnacknowledgedAtMs: null,
  lastGenerationSentSeq: null,
  lastGenerationAckedSeq: null,
});

const rounded = (value: number, digits = 3) => Number(value.toFixed(digits));

const amplificationStatus = (ratio: number): RealtimeTransportChannelSnapshot["amplification_status"] => {
  if (ratio >= 10) return "storm";
  if (ratio > 2) return "severe";
  if (ratio > 1.2) return "abnormal";
  return "normal";
};

export class RealtimeTransportDiagnostics {
  private readonly counters = new Map<RealtimeAudioChannel, MutableChannelCounters>();
  private readonly previous = new Map<RealtimeAudioChannel, MutableChannelCounters>();
  private readonly sequences = new Map<RealtimeAudioChannel, Map<number, SequenceSendState>>();
  private readonly intervalSentSequences = new Map<RealtimeAudioChannel, Map<number, number>>();
  private timer: number | null = null;
  private lastSnapshotAtMs: number;

  constructor(
    private readonly sessionId: string,
    private readonly emitSnapshot: (snapshot: RealtimeTransportDiagnosticsSnapshot) => void,
    private readonly intervalMs = 10_000,
    nowMs = Date.now(),
  ) {
    this.lastSnapshotAtMs = nowMs;
    for (const channel of CHANNELS) {
      this.counters.set(channel, emptyCounters());
      this.previous.set(channel, emptyCounters());
      this.sequences.set(channel, new Map());
      this.intervalSentSequences.set(channel, new Map());
    }
  }

  start(): void {
    if (this.timer !== null) return;
    this.timer = window.setInterval(() => this.publish(), this.intervalMs);
  }

  stop(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    this.timer = null;
  }

  recordCaptureFrame(channel: RealtimeAudioChannel): void {
    this.channel(channel).captureFrames += 1;
  }

  recordPublisherInputFrame(channel: RealtimeAudioChannel): void {
    this.channel(channel).publisherInputFrames += 1;
  }

  recordAudioListenerAttached(channel: RealtimeAudioChannel): void {
    const counters = this.channel(channel);
    counters.activeAudioListeners += 1;
    counters.maximumAudioListeners = Math.max(counters.maximumAudioListeners, counters.activeAudioListeners);
  }

  recordAudioListenerDetached(channel: RealtimeAudioChannel): void {
    const counters = this.channel(channel);
    counters.activeAudioListeners = Math.max(0, counters.activeAudioListeners - 1);
  }

  recordPublisherFrame(input: {
    readonly channel: RealtimeAudioChannel;
    readonly sequence: number;
    readonly audioBytes: number;
    readonly codec?: unknown;
    readonly sampleRateHz?: unknown;
    readonly channels?: unknown;
  }): void {
    const sequenceState = this.sequenceState(input.channel, input.sequence, input.audioBytes);
    if (!sequenceState.publisherRecorded) {
      sequenceState.publisherRecorded = true;
      const counters = this.channel(input.channel);
      if (input.codec !== "pcm-s16le" || input.sampleRateHz !== 16_000 || input.channels !== 1 || input.audioBytes % 2 !== 0) {
        counters.unexpectedAudioFormatFrames += 1;
      }
    }
  }

  recordWebSocketSend(input: {
    readonly channel: RealtimeAudioChannel;
    readonly sequence: number;
    readonly audioPayloadBytes: number;
    readonly totalBytes: number;
    readonly sequenceGapRecovery: boolean;
  }): void {
    const counters = this.channel(input.channel);
    const sequenceState = this.sequenceState(input.channel, input.sequence, input.audioPayloadBytes);
    const previousSendCount = sequenceState.sendCount;
    if (!sequenceState.uniqueRecorded) {
      sequenceState.uniqueRecorded = true;
      counters.uniqueFrames += 1;
      counters.expectedUniqueAudioBytes += input.audioPayloadBytes;
    }
    sequenceState.sendCount += 1;
    counters.websocketSendCalls += 1;
    counters.websocketAudioPayloadBytes += input.audioPayloadBytes;
    counters.websocketTotalBytes += input.totalBytes;
    counters.lastSentSeq = input.sequence;
    this.intervalSentSequences.get(input.channel)?.set(input.sequence, input.audioPayloadBytes);
    counters.maximumSendCount = Math.max(counters.maximumSendCount, sequenceState.sendCount);
    if (previousSendCount > 0) {
      counters.resendFrames += 1;
      counters.resendBytes += input.audioPayloadBytes;
      counters.duplicateSeqSendCount += 1;
    }
    if (input.sequenceGapRecovery) counters.sequenceGapRecoveryFrames += 1;
  }

  recordAck(channel: RealtimeAudioChannel, sequence: number): void {
    const counters = this.channel(channel);
    counters.ackCount += 1;
    counters.lastAckedSeq = sequence;
  }

  recordSequenceGap(channel: RealtimeAudioChannel): void {
    this.channel(channel).sequenceGapCount += 1;
  }

  recordReconnect(): void {
    for (const channel of CHANNELS) this.channel(channel).reconnectCount += 1;
  }

  setRingBufferDepth(channel: RealtimeAudioChannel, depth: number): void {
    this.channel(channel).ringBufferDepth = Math.max(0, depth);
  }

  setRetransmitQueueDepth(channel: RealtimeAudioChannel, depth: number): void {
    this.channel(channel).retransmitQueueDepth = Math.max(0, depth);
  }

  setDeliveryProgress(channel: RealtimeAudioChannel, input: {
    readonly transportGeneration: number;
    readonly inFlightFrames: number;
    readonly oldestUnacknowledgedAtMs: number | null;
    readonly lastGenerationSentSeq: number | null;
    readonly lastGenerationAckedSeq: number | null;
  }): void {
    const counters = this.channel(channel);
    counters.transportGeneration = input.transportGeneration;
    counters.inFlightFrames = Math.max(0, input.inFlightFrames);
    counters.oldestUnacknowledgedAtMs = input.oldestUnacknowledgedAtMs;
    counters.lastGenerationSentSeq = input.lastGenerationSentSeq;
    counters.lastGenerationAckedSeq = input.lastGenerationAckedSeq;
  }

  snapshot(nowMs = Date.now()): RealtimeTransportDiagnosticsSnapshot {
    const intervalSeconds = Math.max(0.001, (nowMs - this.lastSnapshotAtMs) / 1_000);
    return {
      kind: "realtime-audio-transport-diagnostics",
      captured_at_ms: nowMs,
      session_id: this.sessionId,
      SYSTEM: this.channelSnapshot("system", intervalSeconds, nowMs),
      MIC: this.channelSnapshot("microphone", intervalSeconds, nowMs),
    };
  }

  publish(nowMs = Date.now()): RealtimeTransportDiagnosticsSnapshot {
    const snapshot = this.snapshot(nowMs);
    this.emitSnapshot(snapshot);
    this.lastSnapshotAtMs = nowMs;
    for (const channel of CHANNELS) {
      this.previous.set(channel, { ...this.channel(channel) });
      this.intervalSentSequences.get(channel)?.clear();
    }
    return snapshot;
  }

  private channelSnapshot(channel: RealtimeAudioChannel, intervalSeconds: number, nowMs: number): RealtimeTransportChannelSnapshot {
    const counters = this.channel(channel);
    const previous = this.previous.get(channel) ?? emptyCounters();
    const delta = (key: CounterKey) => Math.max(0, counters[key] - previous[key]);
    const intervalSequences = this.intervalSentSequences.get(channel) ?? new Map<number, number>();
    const intervalUniqueFrames = intervalSequences.size;
    const intervalWsSends = delta("websocketSendCalls");
    const intervalExpectedBytes = [...intervalSequences.values()].reduce((sum, bytes) => sum + bytes, 0);
    const intervalAudioBytes = delta("websocketAudioPayloadBytes");
    const sendAmplificationRatio = intervalWsSends / Math.max(1, intervalUniqueFrames);
    const byteAmplificationRatio = intervalAudioBytes / Math.max(1, intervalExpectedBytes);
    const maximumRatio = Math.max(sendAmplificationRatio, byteAmplificationRatio);
    const duplicateSamples = [...(this.sequences.get(channel)?.values() ?? [])]
      .filter(item => item.sendCount > 1)
      .sort((left, right) => right.sendCount - left.sendCount || right.sequence - left.sequence)
      .slice(0, MAX_DUPLICATE_SAMPLES)
      .map(item => ({ sequence: item.sequence, send_count: item.sendCount, audio_bytes_per_send: item.audioBytes }));
    return {
      interval_seconds: rounded(intervalSeconds),
      capture_frames: counters.captureFrames,
      publisher_input_frames: counters.publisherInputFrames,
      unique_frames: counters.uniqueFrames,
      websocket_send_calls: counters.websocketSendCalls,
      websocket_audio_payload_bytes: counters.websocketAudioPayloadBytes,
      websocket_total_bytes: counters.websocketTotalBytes,
      ack_count: counters.ackCount,
      last_sent_seq: counters.lastSentSeq,
      last_acked_seq: counters.lastAckedSeq,
      resend_frames: counters.resendFrames,
      resend_bytes: counters.resendBytes,
      sequence_gap_count: counters.sequenceGapCount,
      sequence_gap_recovery_frames: counters.sequenceGapRecoveryFrames,
      reconnect_count: counters.reconnectCount,
      ring_buffer_depth: counters.ringBufferDepth,
      retransmit_queue_depth: counters.retransmitQueueDepth,
      duplicate_seq_send_count: counters.duplicateSeqSendCount,
      maximum_send_count_for_one_seq: counters.maximumSendCount,
      active_audio_listeners: counters.activeAudioListeners,
      maximum_audio_listeners: counters.maximumAudioListeners,
      unexpected_audio_format_frames: counters.unexpectedAudioFormatFrames,
      capture_fps: rounded(delta("captureFrames") / intervalSeconds),
      publisher_input_fps: rounded(delta("publisherInputFrames") / intervalSeconds),
      unique_send_fps: rounded(intervalUniqueFrames / intervalSeconds),
      actual_ws_send_fps: rounded(intervalWsSends / intervalSeconds),
      audio_kb_per_second: rounded(intervalAudioBytes / 1_024 / intervalSeconds),
      total_kb_per_second: rounded(delta("websocketTotalBytes") / 1_024 / intervalSeconds),
      ack_per_second: rounded(delta("ackCount") / intervalSeconds),
      resend_fps: rounded(delta("resendFrames") / intervalSeconds),
      resend_kb_per_second: rounded(delta("resendBytes") / 1_024 / intervalSeconds),
      send_amplification_ratio: rounded(sendAmplificationRatio),
      byte_amplification_ratio: rounded(byteAmplificationRatio),
      amplification_status: amplificationStatus(maximumRatio),
      duplicate_sequence_samples: duplicateSamples,
      transport_generation: counters.transportGeneration,
      in_flight_frames: counters.inFlightFrames,
      oldest_unacknowledged_age_ms: counters.oldestUnacknowledgedAtMs === null ? 0 : Math.max(0, nowMs - counters.oldestUnacknowledgedAtMs),
      generation_last_sent_seq: counters.lastGenerationSentSeq,
      generation_last_acked_seq: counters.lastGenerationAckedSeq,
    };
  }

  private channel(channel: RealtimeAudioChannel): MutableChannelCounters {
    const existing = this.counters.get(channel);
    if (existing) return existing;
    const counters = emptyCounters();
    this.counters.set(channel, counters);
    return counters;
  }

  private sequenceState(channel: RealtimeAudioChannel, sequence: number, audioBytes: number): SequenceSendState {
    const sequences = this.sequences.get(channel) ?? new Map<number, SequenceSendState>();
    this.sequences.set(channel, sequences);
    const existing = sequences.get(sequence);
    if (existing) return existing;
    const state = { sequence, audioBytes, sendCount: 0, publisherRecorded: false, uniqueRecorded: false };
    sequences.set(sequence, state);
    while (sequences.size > MAX_TRACKED_SEQUENCES) {
      const oldest = sequences.keys().next().value as number | undefined;
      if (oldest === undefined) break;
      sequences.delete(oldest);
    }
    return state;
  }
}
