import { describe, expect, it } from "vitest";

import { RealtimeReliabilityController } from "../src/renderer/audio/realtime-reliability";

describe("dual-channel publisher recovery", () => {
  it("does not let one channel acknowledgement hide its stalled sibling", () => {
    const reliability = new RealtimeReliabilityController({ lostAckMs: 3_000 });
    reliability.start("microphone", 0);
    reliability.start("system", 0);
    reliability.markRecovering("microphone", "transport-sequence-reset");
    reliability.markRecovering("system", "transport-sequence-reset");
    reliability.recordAudioCapture("microphone", 500);
    reliability.recordAudioCapture("system", 500);
    reliability.recordFrameSent("microphone", 500, 8);
    reliability.recordFrameSent("system", 500, 8);
    reliability.recordFrameAck("system", 700, 0);
    reliability.recordAudioCapture("microphone", 3_500);
    reliability.recordAudioCapture("system", 3_500);

    expect(reliability.evaluate(3_501)).toEqual([
      expect.objectContaining({ sourceKind: "microphone", state: "LOST", action: "recover-transport", reason: "frame-ack-stalled" }),
      expect.objectContaining({ sourceKind: "system", state: "HEALTHY", action: "none" }),
    ]);
  });

  it("keeps a silent replacement channel ready without an ACK deadline", () => {
    const reliability = new RealtimeReliabilityController({ startupGraceMs: 100, lostAckMs: 3_000 });
    reliability.start("microphone", 0);
    reliability.recordAudioCapture("microphone", 19_900);
    expect(reliability.evaluate(20_000)[0]).toMatchObject({ sourceKind: "microphone", state: "STARTING", action: "none" });
  });
});
