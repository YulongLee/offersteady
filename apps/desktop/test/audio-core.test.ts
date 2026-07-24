import { describe, expect, it } from "vitest";

import { MicrophoneAudioAdapter, SystemAudioAdapter, describeMediaError, type MediaDevicesLike } from "../src/renderer/audio/audio-source-adapter";
import { BoundedAudioFrameBuffer, SourceFrameSequencer, createAudioFrame } from "../src/renderer/audio/audio-frame-buffer";
import { SpeechSegmenter } from "../src/renderer/audio/realtime-publisher";
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
  it("keeps a single segment across brief pauses and finalizes only after a longer silence", () => {
    const segmenter = new SpeechSegmenter("microphone");
    const speech = new Uint8Array([1, 2, 3]);

    expect(segmenter.push(speech, 0, 0.013)).toEqual([]);
    const firstPartial = segmenter.push(speech, 130, 0.010);
    expect(firstPartial).toHaveLength(1);
    expect(segmenter.push(new Uint8Array([0]), 260, 0.001)).toEqual([]);
    const secondPartial = segmenter.push(speech, 440, 0.009);
    expect(secondPartial).toHaveLength(1);
    const finalized = segmenter.push(new Uint8Array([0]), 860, 0.001);

    expect(finalized).toHaveLength(1);
    expect(finalized[0]?.isFinal).toBe(true);
    expect(firstPartial[0]?.segmentId).toBe(secondPartial[0]?.segmentId);
    expect(secondPartial[0]?.segmentId).toBe(finalized[0]?.segmentId);
  });

  it("drops very short noise bursts instead of emitting broken transcript segments", () => {
    const segmenter = new SpeechSegmenter("system");
    const burst = new Uint8Array([9, 9]);

    expect(segmenter.push(burst, 0, 0.013)).toEqual([]);
    const finalized = segmenter.push(new Uint8Array([0]), 500, 0.001);

    expect(finalized).toEqual([]);
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

  it("keeps the fallback preview track alive when audio-only capture does not expose a system track", async () => {
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
    expect(stopped.value).toBe(false);
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
