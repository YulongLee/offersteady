import { describe, expect, it } from "vitest";

import { RealtimeReliabilityController } from "../src/renderer/audio/realtime-reliability";

describe("desktop realtime reliability watchdog", () => {
  it("does not claim delivery health from silent worklet callbacks alone", () => {
    const controller = new RealtimeReliabilityController({ startupGraceMs: 100, degradedCaptureMs: 1_000, lostCaptureMs: 2_000 });
    controller.start("system", 0);
    for (let nowMs = 100; nowMs <= 10_000; nowMs += 100) controller.recordAudioCapture("system", nowMs);
    expect(controller.evaluate(10_500)).toEqual([{
      sourceKind: "system",
      state: "STARTING",
      action: "none",
      reason: null,
    }]);
  });

  it("marks a source lost after capture callbacks stop for two seconds", () => {
    const controller = new RealtimeReliabilityController({ startupGraceMs: 100, degradedCaptureMs: 1_000, lostCaptureMs: 2_000 });
    controller.start("system", 0);
    controller.recordAudioCapture("system", 500);
    expect(controller.evaluate(2_501)[0]).toMatchObject({ state: "LOST", action: "recover-source", reason: "capture-callback-stalled" });
  });

  it("only applies the ACK watchdog while frames are pending", () => {
    const controller = new RealtimeReliabilityController({ lostAckMs: 3_000 });
    controller.start("microphone", 0);
    controller.recordAudioCapture("microphone", 3_900);
    controller.recordFrameSent("microphone", 500, 1);
    controller.recordFrameSent("microphone", 3_900, 2);
    expect(controller.evaluate(4_000)[0]).toMatchObject({ state: "LOST", action: "recover-transport", reason: "frame-ack-stalled" });
    controller.recordFrameAck("microphone", 4_100, 0);
    controller.recordAudioCapture("microphone", 10_000);
    expect(controller.evaluate(10_500)[0]).toMatchObject({ state: "HEALTHY", action: "none" });
  });

  it("keeps the oldest pending deadline while continuous sends arrive", () => {
    const controller = new RealtimeReliabilityController({ lostAckMs: 3_000 });
    controller.start("microphone", 0);
    controller.recordAudioCapture("microphone", 3_900);
    controller.recordFrameSent("microphone", 500, 1);
    for (let nowMs = 1_000; nowMs <= 3_900; nowMs += 100) {
      controller.recordFrameSent("microphone", nowMs, 8);
    }
    expect(controller.snapshot()[0]?.pendingSinceAt).toBe(500);
    expect(controller.evaluate(4_000)[0]).toMatchObject({ action: "recover-transport", reason: "frame-ack-stalled" });
  });

  it("does not exempt a recovering channel after it produces unacknowledged media", () => {
    const controller = new RealtimeReliabilityController({ lostAckMs: 3_000 });
    controller.start("microphone", 0);
    controller.markRecovering("microphone", "transport-sequence-reset");
    controller.recordAudioCapture("microphone", 500);
    controller.recordFrameSent("microphone", 500, 1);
    expect(controller.evaluate(3_501)[0]).toMatchObject({ state: "LOST", action: "recover-transport", reason: "frame-ack-stalled" });
  });

  it("moves through recovering and returns healthy only after a fresh ACK", () => {
    const controller = new RealtimeReliabilityController();
    controller.start("system", 1_000);
    controller.markRecovering("system", "capture-callback-stalled");
    expect(controller.snapshot()[0]).toMatchObject({ state: "RECOVERING", recoveryCount: 1 });
    controller.recordAudioCapture("system", 2_000);
    expect(controller.snapshot()[0]).toMatchObject({ state: "RECOVERING" });
    controller.recordFrameAck("system", 2_100);
    expect(controller.snapshot()[0]).toMatchObject({ state: "HEALTHY" });
  });

  it("keeps a missing transient transport recoverable while capture continues", () => {
    const controller = new RealtimeReliabilityController();
    controller.start("microphone", 1_000);
    controller.recordAudioCapture("microphone", 1_100);
    controller.markRecovering("microphone", "publisher-transport-missing");
    controller.markRecovering("microphone", "publisher-transport-missing");

    expect(controller.snapshot()[0]).toMatchObject({
      state: "RECOVERING",
      recoveryCount: 1,
      terminalFailure: false,
      lastFailureReason: "publisher-transport-missing",
    });

    controller.recordFrameSent("microphone", 1_200, 1);
    controller.recordFrameAck("microphone", 1_300, 0);
    expect(controller.evaluate(1_350)[0]).toMatchObject({ state: "HEALTHY", action: "none" });
  });

  it("keeps terminal delivery loss sticky while capture callbacks continue", () => {
    const controller = new RealtimeReliabilityController();
    controller.start("system", 1_000);
    controller.recordAudioCapture("system", 1_100);
    controller.recordFrameAck("system", 1_150);
    controller.markTerminalLost("system", "publisher-recovery-exhausted");
    controller.recordAudioCapture("system", 9_000);
    controller.recordFrameAck("system", 9_010);

    expect(controller.evaluate(9_100)[0]).toMatchObject({
      state: "LOST",
      action: "none",
      reason: "publisher-recovery-exhausted",
    });
    expect(controller.snapshot()[0]).toMatchObject({ terminalFailure: true });
  });
});
