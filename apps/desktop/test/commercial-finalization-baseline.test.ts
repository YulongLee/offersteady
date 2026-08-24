import { describe, expect, it } from "vitest";
import { commercialFinalizationBaseline } from "../scripts/benchmark-commercial-finalization-baseline";

describe("commercial finalization baseline", () => {
  it("records the current persistent-noise and queue-pressure failure modes", () => {
    expect(commercialFinalizationBaseline.scenarios.systemCleanSilence.finalAtMs).toBeLessThan(2_000);
    expect(commercialFinalizationBaseline.scenarios.systemPersistentMeetingNoise.finalAtMs).toBeGreaterThanOrEqual(30_000);
    expect(commercialFinalizationBaseline.scenarios.microphoneContinuousSignal.finalAtMs).toBeGreaterThanOrEqual(30_000);
    expect(commercialFinalizationBaseline.scenarios.desktopQueuePressure).toMatchObject({
      droppedKind: "terminal",
      terminalReservedCapacity: false,
      terminalAcknowledgement: false,
    });
  });
});
