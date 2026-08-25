import { afterEach, describe, expect, it, vi } from "vitest";

import { RealtimeTransportDiagnostics } from "../src/renderer/audio/realtime-transport-diagnostics";

describe("realtime transport diagnostics", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("reports a normal one-to-one send without retaining audio content", () => {
    vi.stubGlobal("window", { setInterval, clearInterval });
    const emitted: unknown[] = [];
    const diagnostics = new RealtimeTransportDiagnostics("session-normal", snapshot => emitted.push(snapshot), 10_000, 0);

    diagnostics.recordCaptureFrame("system");
    diagnostics.recordPublisherInputFrame("system");
    diagnostics.recordAudioListenerAttached("system");
    diagnostics.recordPublisherFrame({ channel: "system", sequence: 100, audioBytes: 3_200, codec: "pcm-s16le", sampleRateHz: 16_000, channels: 1 });
    diagnostics.recordWebSocketSend({ channel: "system", sequence: 100, audioPayloadBytes: 3_200, totalBytes: 3_460, sequenceGapRecovery: false });
    diagnostics.recordAck("system", 100);
    diagnostics.setRingBufferDepth("system", 0);
    diagnostics.setRetransmitQueueDepth("system", 0);

    const snapshot = diagnostics.publish(10_000);
    expect(emitted).toHaveLength(1);
    expect(snapshot.SYSTEM).toMatchObject({
      capture_frames: 1,
      publisher_input_frames: 1,
      unique_frames: 1,
      websocket_send_calls: 1,
      websocket_audio_payload_bytes: 3_200,
      ack_count: 1,
      last_sent_seq: 100,
      last_acked_seq: 100,
      send_amplification_ratio: 1,
      byte_amplification_ratio: 1,
      amplification_status: "normal",
      maximum_audio_listeners: 1,
      unexpected_audio_format_frames: 0,
    });
    expect(JSON.stringify(snapshot)).not.toContain("audioBase64");
  });

  it("marks repeated sequence writes and recovery traffic as a resend storm", () => {
    vi.stubGlobal("window", { setInterval, clearInterval });
    const diagnostics = new RealtimeTransportDiagnostics("session-storm", () => undefined, 10_000, 0);
    diagnostics.recordPublisherFrame({ channel: "microphone", sequence: 102, audioBytes: 640, codec: "pcm-s16le", sampleRateHz: 16_000, channels: 1 });
    diagnostics.recordSequenceGap("microphone");
    diagnostics.recordReconnect();
    diagnostics.recordAudioListenerAttached("microphone");
    diagnostics.recordAudioListenerAttached("microphone");
    for (let attempt = 0; attempt < 17; attempt += 1) {
      diagnostics.recordWebSocketSend({
        channel: "microphone",
        sequence: 102,
        audioPayloadBytes: 640,
        totalBytes: 900,
        sequenceGapRecovery: attempt > 0,
      });
    }
    diagnostics.setRingBufferDepth("microphone", 4);
    diagnostics.setRetransmitQueueDepth("microphone", 9);

    const snapshot = diagnostics.publish(10_000);
    expect(snapshot.MIC).toMatchObject({
      unique_frames: 1,
      websocket_send_calls: 17,
      resend_frames: 16,
      resend_bytes: 10_240,
      duplicate_seq_send_count: 16,
      maximum_send_count_for_one_seq: 17,
      sequence_gap_count: 1,
      sequence_gap_recovery_frames: 16,
      reconnect_count: 1,
      ring_buffer_depth: 4,
      retransmit_queue_depth: 9,
      maximum_audio_listeners: 2,
      send_amplification_ratio: 17,
      byte_amplification_ratio: 17,
      amplification_status: "storm",
    });
    expect(snapshot.MIC.duplicate_sequence_samples[0]).toEqual({
      sequence: 102,
      send_count: 17,
      audio_bytes_per_send: 640,
    });
  });

  it("uses interval deltas rather than diluting a new resend burst with old traffic", () => {
    vi.stubGlobal("window", { setInterval, clearInterval });
    const diagnostics = new RealtimeTransportDiagnostics("session-window", () => undefined, 10_000, 0);
    diagnostics.recordPublisherFrame({ channel: "system", sequence: 1, audioBytes: 320, codec: "pcm-s16le", sampleRateHz: 16_000, channels: 1 });
    diagnostics.recordWebSocketSend({ channel: "system", sequence: 1, audioPayloadBytes: 320, totalBytes: 500, sequenceGapRecovery: false });
    expect(diagnostics.publish(10_000).SYSTEM.send_amplification_ratio).toBe(1);

    for (let retry = 0; retry < 4; retry += 1) {
      diagnostics.recordWebSocketSend({ channel: "system", sequence: 1, audioPayloadBytes: 320, totalBytes: 500, sequenceGapRecovery: true });
    }
    const second = diagnostics.publish(20_000);
    expect(second.SYSTEM.send_amplification_ratio).toBe(4);
    expect(second.SYSTEM.byte_amplification_ratio).toBe(4);
    expect(second.SYSTEM.amplification_status).toBe("severe");
  });
});
