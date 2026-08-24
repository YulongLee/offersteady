import { describe, expect, it } from "vitest";

import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError, type MediaDevicesLike } from "../src/renderer/audio/audio-source-adapter";
import { BoundedAudioFrameBuffer, SourceFrameSequencer, createAudioFrame } from "../src/renderer/audio/audio-frame-buffer";
import { SpeechSegmenter, systemAudioRecoveryReason } from "../src/renderer/audio/realtime-publisher";
import { calculateRms, isSilent } from "../src/renderer/audio/signal-diagnostics";

const frame = (sequencer: SourceFrameSequencer, sourceId: string, bytes: number) =>
  createAudioFrame(sequencer, {
    sessionId: "session-1",
    deviceId: "device-1",
    sourceId,
    sourceKind: sourceId.startsWith("mic") ? "microphone" : "system",
    capturedAtMs: 1_000,
    durationMs: 20,
    payload: new Uint8Array(bytes),
  });

describe("audio frame sequencing", () => {
  it("keeps independent sequences for microphone and system audio", () => {
    const sequencer = new SourceFrameSequencer();
    expect(frame(sequencer, "mic-1", 2).sequence).toBe(0);
    expect(frame(sequencer, "system-1", 2).sequence).toBe(0);
    expect(frame(sequencer, "mic-1", 2).sequence).toBe(1);
  });
});

describe("bounded audio buffer", () => {
  it("drops oldest frames rather than growing beyond capacity", () => {
    const sequencer = new SourceFrameSequencer();
    const buffer = new BoundedAudioFrameBuffer(5);
    buffer.push(frame(sequencer, "mic-1", 3));
    const dropped = buffer.push(frame(sequencer, "mic-1", 3));
    expect(dropped).toHaveLength(1);
    expect(buffer.pending()).toHaveLength(1);
  });

  it("removes acknowledged frames and clears memory", () => {
    const sequencer = new SourceFrameSequencer();
    const buffer = new BoundedAudioFrameBuffer(20);
    buffer.push(frame(sequencer, "mic-1", 3));
    buffer.push(frame(sequencer, "mic-1", 3));
    buffer.acknowledge("mic-1", 0);
    expect(buffer.pending().map((item) => item.sequence)).toEqual([1]);
    buffer.clear();
    expect(buffer.pending()).toEqual([]);
  });
});

describe("signal diagnostics", () => {
  it("detects silence and non-silent input", () => {
    expect(isSilent(new Float32Array([0, 0, 0]))).toBe(true);
    expect(isSilent(new Float32Array([0.2, -0.2, 0.2]))).toBe(false);
    expect(calculateRms(new Float32Array([1, -1]))).toBe(1);
  });
});

describe("speech segmenter", () => {
  it("exposes an explicit commercial turn lifecycle and a terminal reason", () => {
    const segmenter = new SpeechSegmenter("microphone");
    const speech = new Uint8Array([1, 2, 3]);

    expect(segmenter.currentState).toBe("idle");
    segmenter.push(speech, 0, 0.01);
    segmenter.push(speech, 100, 0.01);
    expect(segmenter.currentState).toBe("speaking");
    segmenter.push(new Uint8Array([0]), 200, 0.0001);
    expect(segmenter.currentState).toBe("tail");
    const terminal = segmenter.push(new Uint8Array([0]), 800, 0.0001)[0];

    expect(terminal).toMatchObject({ isFinal: true, turnState: "committing", finalizationReason: "silence", sourceGeneration: 1 });
    expect(terminal?.terminalId).toContain(terminal?.segmentId);
    expect(segmenter.currentState).toBe("idle");
  });

  it("adapts to steady meeting noise and closes system speech before the hard deadline", () => {
    const segmenter = new SpeechSegmenter("system");
    const chunk = new Uint8Array([1, 2]);
    for (let index = 0; index < 30; index += 1) segmenter.push(chunk, index * 20, 0.0006);
    segmenter.push(chunk, 700, 0.003);
    segmenter.push(chunk, 800, 0.003);
    let terminal: ReturnType<SpeechSegmenter["push"]>[number] | undefined;
    for (let nowMs = 900; nowMs <= 2_000; nowMs += 100) {
      terminal = segmenter.push(chunk, nowMs, 0.0006).find(item => item.isFinal) ?? terminal;
    }
    expect(terminal?.finalizationReason).toBe("silence");
    expect(terminal?.endedAtMs).toBeLessThan(3_000);
  });

  it("flushes an active turn once with an idempotency key and capture-stop reason", () => {
    const segmenter = new SpeechSegmenter("microphone");
    segmenter.push(new Uint8Array([1]), 0, 0.01);
    segmenter.push(new Uint8Array([2]), 100, 0.01);
    const terminal = segmenter.flush(150)[0];
    expect(terminal).toMatchObject({ isFinal: true, finalizationReason: "capture-stop" });
    expect(terminal?.terminalId).toBeTruthy();
    expect(segmenter.flush(160)).toEqual([]);
  });

  it("keeps a single segment across brief pauses and finalizes only after a longer silence", () => {
    const segmenter = new SpeechSegmenter("microphone");
    const speech = new Uint8Array([1, 2, 3]);

    expect(segmenter.push(speech, 0, 0.013)).toEqual([]);
    const firstPartial = segmenter.push(speech, 130, 0.010);
    expect(firstPartial).toHaveLength(1);
    expect(segmenter.push(new Uint8Array([0]), 800, 0.001)).toEqual([]);
    const secondPartial = segmenter.push(speech, 830, 0.009);
    expect(secondPartial).toHaveLength(1);
    expect(segmenter.push(new Uint8Array([0]), 1_529, 0.001)).toEqual([]);
    const finalized = segmenter.push(new Uint8Array([0]), 1_530, 0.001);

    expect(finalized).toHaveLength(1);
    expect(finalized[0]?.isFinal).toBe(true);
    expect(firstPartial[0]?.segmentId).toBe(secondPartial[0]?.segmentId);
    expect(secondPartial[0]?.segmentId).toBe(finalized[0]?.segmentId);
  });

  it("streams only newly captured PCM in ordered partial revisions", () => {
    const segmenter = new SpeechSegmenter("microphone");
    const first = new Uint8Array([1, 2]);
    const second = new Uint8Array([3, 4]);
    const third = new Uint8Array([5, 6]);

    expect(segmenter.push(first, 0, 0.013)).toEqual([]);
    const firstPartial = segmenter.push(second, 70, 0.013);
    const secondPartial = segmenter.push(third, 180, 0.013);

    expect(firstPartial[0]?.revision).toBe(1);
    expect(firstPartial[0]?.isFinal).toBe(false);
    expect(Array.from(firstPartial[0]?.payload ?? [])).toEqual([1, 2, 3, 4]);
    expect(secondPartial[0]?.revision).toBe(2);
    expect(secondPartial[0]?.segmentId).toBe(firstPartial[0]?.segmentId);
    expect(Array.from(secondPartial[0]?.payload ?? [])).toEqual([5, 6]);
  });

  it("drops very short noise bursts instead of emitting broken transcript segments", () => {
    const segmenter = new SpeechSegmenter("system");
    const burst = new Uint8Array([9, 9]);

    expect(segmenter.push(burst, 0, 0.013)).toEqual([]);
    const finalized = segmenter.push(new Uint8Array([0]), 500, 0.0001);

    expect(finalized).toEqual([]);
  });

  it("publishes low-level computer output that is visible on the system meter", () => {
    const system = new SpeechSegmenter("system");
    const microphone = new SpeechSegmenter("microphone");
    const digitalAudio = new Uint8Array([1, 2, 3, 4]);

    expect(system.push(digitalAudio, 0, 0.001)).toEqual([]);
    const systemPartial = system.push(digitalAudio, 100, 0.001);
    expect(systemPartial).toHaveLength(1);
    expect(systemPartial[0]).toMatchObject({
      vadTriggeredAtMs: 0,
      speechConfirmedAtMs: 100,
      startedAtMs: 0,
    });
    expect(microphone.push(digitalAudio, 0, 0.001)).toEqual([]);
    expect(microphone.push(digitalAudio, 100, 0.001)).toEqual([]);
  });

  it("adapts to a quiet microphone after observing a low noise floor", () => {
    const segmenter = new SpeechSegmenter("microphone");
    const chunk = new Uint8Array([1, 2]);
    for (let index = 0; index < 20; index += 1) {
      expect(segmenter.push(chunk, index * 20, 0.0002)).toEqual([]);
    }
    expect(segmenter.push(chunk, 420, 0.0013)).toEqual([]);
    const partial = segmenter.push(chunk, 500, 0.0013);
    expect(partial).toHaveLength(1);
    expect(partial[0]?.isFinal).toBe(false);
    expect(segmenter.currentNoiseFloor).toBeLessThan(0.00035);
  });

  it("keeps Feishu system speech in one segment across a short digital pause", () => {
    const segmenter = new SpeechSegmenter("system");
    const speech = new Uint8Array([1, 2, 3]);

    expect(segmenter.push(speech, 0, 0.01)).toEqual([]);
    const firstPartial = segmenter.push(speech, 100, 0.01);
    expect(firstPartial).toHaveLength(1);
    expect(segmenter.push(new Uint8Array([0]), 400, 0.0001)).toEqual([]);
    const continued = segmenter.push(speech, 430, 0.01);
    expect(continued).toHaveLength(1);
    expect(continued[0]?.segmentId).toBe(firstPartial[0]?.segmentId);
    expect(segmenter.push(new Uint8Array([0]), 929, 0.0001)).toEqual([]);
    const finalized = segmenter.push(new Uint8Array([0]), 930, 0.0001);
    expect(finalized).toHaveLength(1);
    expect(finalized[0]?.isFinal).toBe(true);
  });

  it("finalizes uninterrupted speech at the bounded maximum duration", () => {
    const segmenter = new SpeechSegmenter("microphone");
    const speech = new Uint8Array([1, 2, 3]);

    expect(segmenter.push(speech, 0, 0.01)).toEqual([]);
    const firstPartial = segmenter.push(speech, 100, 0.01);
    expect(firstPartial).toHaveLength(1);
    const boundedFinal = segmenter.push(speech, 12_000, 0.01);

    expect(boundedFinal).toHaveLength(1);
    expect(boundedFinal[0]?.isFinal).toBe(true);
    expect(boundedFinal[0]?.segmentId).toBe(firstPartial[0]?.segmentId);
    expect(boundedFinal[0]?.durationMs).toBe(12_000);
    expect(boundedFinal[0]?.finalizationReason).toBe("max-duration");
    expect(segmenter.push(speech, 12_020, 0.01)).toEqual([]);
    const nextPartial = segmenter.push(speech, 12_120, 0.01);
    expect(nextPartial[0]?.segmentId).not.toBe(firstPartial[0]?.segmentId);
  });
});

describe("system audio recovery policy", () => {
  const healthy = {
    nowMs: 20_000,
    openedAtMs: 10_000,
    lastProcessAtMs: 19_900,
    lastSignalAtMs: 19_000,
    lastRecoveryAtMs: null,
    recoveryAttempt: 0,
    trackReadyState: "live" as const,
    trackMuted: false,
    contextState: "running",
  };

  it("recovers a live track after previously active system PCM becomes persistently silent", () => {
    expect(systemAudioRecoveryReason({
      ...healthy,
      nowMs: 49_001,
      lastProcessAtMs: 49_000,
      lastSignalAtMs: 19_000,
    })).toBe("system-signal-stalled");
  });

  it("uses bounded backoff after a silent-source recovery attempt", () => {
    expect(systemAudioRecoveryReason({
      ...healthy,
      nowMs: 50_000,
      lastProcessAtMs: 49_999,
      lastSignalAtMs: 10_000,
      lastRecoveryAtMs: 40_000,
      recoveryAttempt: 1,
    })).toBeNull();
    expect(systemAudioRecoveryReason({
      ...healthy,
      nowMs: 160_001,
      lastProcessAtMs: 160_000,
      lastSignalAtMs: 10_000,
      lastRecoveryAtMs: 40_000,
      recoveryAttempt: 1,
    })).toBe("system-signal-stalled");
  });

  it("recovers ended, muted, suspended, and callback-stalled sources", () => {
    expect(systemAudioRecoveryReason({ ...healthy, trackReadyState: "ended" })).toBe("track-ended");
    expect(systemAudioRecoveryReason({ ...healthy, trackMuted: true })).toBe("track-muted");
    expect(systemAudioRecoveryReason({ ...healthy, contextState: "suspended" })).toBe("audio-context-not-running");
    expect(systemAudioRecoveryReason({ ...healthy, lastProcessAtMs: 15_000 })).toBe("audio-callback-stalled");
  });

  it("does not restart a newly opened or never-active silent track", () => {
    expect(systemAudioRecoveryReason({ ...healthy, openedAtMs: 19_000, trackMuted: true })).toBeNull();
    expect(systemAudioRecoveryReason({ ...healthy, lastSignalAtMs: null })).toBeNull();
  });
});

describe("microphone adapter", () => {
  it("reports denied permission without claiming capture is available", async () => {
    const mediaDevices = {
      getUserMedia: async () => { throw new DOMException("denied", "NotAllowedError"); },
      enumerateDevices: async () => [],
      getDisplayMedia: async () => { throw new Error("unused"); },
    } as unknown as MediaDevicesLike;
    await expect(new MicrophoneAudioAdapter(mediaDevices).getPermission()).resolves.toBe("denied");
  });

  it("maps and switches between synthetic input devices", async () => {
    const devices = [
      { kind: "audioinput", deviceId: "mic-a", label: "Headset" },
      { kind: "audioinput", deviceId: "mic-b", label: "Laptop" },
    ] as MediaDeviceInfo[];
    const mediaDevices = {
      enumerateDevices: async () => devices,
      getUserMedia: async () => { throw new Error("unused"); },
      getDisplayMedia: async () => { throw new Error("unused"); },
    } as unknown as MediaDevicesLike;
    const sources = await new MicrophoneAudioAdapter(mediaDevices).listSources();
    expect(sources.map((source) => source.id)).toEqual(["mic-a", "mic-b"]);
  });

  it("requests echo cancellation, noise suppression, and gain control for live microphone capture", async () => {
    const constraints: MediaStreamConstraints[] = [];
    const stream = {
      getAudioTracks: () => [{ id: "mic-a", label: "Headset", stop: () => undefined }],
      getVideoTracks: () => [],
      getTracks: () => [{ stop: () => undefined }],
    } as unknown as MediaStream;
    const mediaDevices = {
      enumerateDevices: async () => [],
      getUserMedia: async (nextConstraints: MediaStreamConstraints) => {
        constraints.push(nextConstraints);
        return stream;
      },
      getDisplayMedia: async () => { throw new Error("unused"); },
    } as unknown as MediaDevicesLike;
    const opened = await new MicrophoneAudioAdapter(mediaDevices).open("mic-a");
    opened.close();
    expect(constraints[0]?.audio).toMatchObject({
      deviceId: { exact: "mic-a" },
      echoCancellation: { ideal: true },
      noiseSuppression: { ideal: true },
      autoGainControl: { ideal: true },
      channelCount: { ideal: 1 },
    });
  });

  it("requests echo cancellation for the default microphone instead of opening an unconstrained stream", async () => {
    const constraints: MediaStreamConstraints[] = [];
    const stream = {
      getAudioTracks: () => [{ id: "default-mic", label: "MacBook Microphone", stop: () => undefined }],
      getVideoTracks: () => [],
      getTracks: () => [{ stop: () => undefined }],
    } as unknown as MediaStream;
    const mediaDevices = {
      enumerateDevices: async () => [],
      getUserMedia: async (nextConstraints: MediaStreamConstraints) => {
        constraints.push(nextConstraints);
        return stream;
      },
      getDisplayMedia: async () => { throw new Error("unused"); },
    } as unknown as MediaDevicesLike;

    const opened = await new MicrophoneAudioAdapter(mediaDevices).open("default");
    opened.close();

    expect(constraints[0]?.audio).toMatchObject({
      echoCancellation: { ideal: true },
      noiseSuppression: { ideal: true },
      autoGainControl: { ideal: true },
      channelCount: { ideal: 1 },
    });
    expect(constraints[0]?.audio).not.toHaveProperty("deviceId");
  });
});

describe("system audio adapter diagnostics", () => {
  it("captures computer output loopback without tying it to a screen source", async () => {
    const stream = {
      getAudioTracks: () => [{ stop: () => undefined }],
      getVideoTracks: () => [],
      getTracks: () => [{ stop: () => undefined }],
    } as unknown as MediaStream;
    let receivedConstraints: DisplayMediaStreamOptions | undefined;
    const mediaDevices = {
      enumerateDevices: async () => [],
      getUserMedia: async () => { throw new Error("unused"); },
      getDisplayMedia: async (constraints?: DisplayMediaStreamOptions) => {
        receivedConstraints = constraints;
        return stream;
      },
    } as unknown as MediaDevicesLike;
    await new SystemAudioAdapter(mediaDevices).open();
    expect(receivedConstraints).toBeDefined();
    expect(receivedConstraints?.audio).not.toBe(false);
    expect(receivedConstraints?.video).toMatchObject({ frameRate: 1, width: 2, height: 2 });
  });

  it("stops the unneeded video track after system loopback is established", async () => {
    const stopped = { value: false };
    const audioTrack = { stop: () => undefined };
    const videoTrack = { stop: () => { stopped.value = true; } };
    let calls = 0;
    const audioOnlyStream = {
      getAudioTracks: () => [],
      getVideoTracks: () => [],
      getTracks: () => [],
    } as unknown as MediaStream;
    const fallbackStream = {
      getAudioTracks: () => [audioTrack],
      getVideoTracks: () => [videoTrack],
      getTracks: () => [audioTrack, videoTrack],
    } as unknown as MediaStream;
    const mediaDevices = {
      enumerateDevices: async () => [],
      getUserMedia: async () => { throw new Error("unused"); },
      getDisplayMedia: async () => {
        calls += 1;
        return calls === 1 ? audioOnlyStream : fallbackStream;
      },
    } as unknown as MediaDevicesLike;
    const opened = await new SystemAudioAdapter(mediaDevices).open();
    expect(opened.stream).toBe(fallbackStream);
    expect(stopped.value).toBe(true);
    opened.close();
    expect(stopped.value).toBe(true);
  });

  it("explains when display capture succeeds but no system audio track is present", async () => {
    const stream = {
      getAudioTracks: () => [],
      getVideoTracks: () => [{ stop: () => undefined }],
      getTracks: () => [{ stop: () => undefined }],
    } as unknown as MediaStream;
    const mediaDevices = {
      enumerateDevices: async () => [],
      getUserMedia: async () => { throw new Error("unused"); },
      getDisplayMedia: async () => stream,
    } as unknown as MediaDevicesLike;
    await expect(new SystemAudioAdapter(mediaDevices).open()).rejects.toThrow("system-audio-unavailable");
    expect(describeMediaError(new Error("system-audio-unavailable"))).toContain("电脑输出音频轨道");
  });

  it("translates common media permission errors for the desktop diagnostics UI", () => {
    expect(describeMediaError(new DOMException("denied", "NotAllowedError"))).toContain("拒绝");
    expect(describeMediaError(new DOMException("missing", "NotFoundError"))).toContain("没有找到");
    expect(describeMediaError(new DOMException("busy", "NotReadableError"))).toContain("占用");
  });
});
