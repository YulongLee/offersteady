import { describe, expect, it } from "vitest";
import { DEVICE_STATUS_KEEPALIVE_MS, DeviceStatusPublishGate, deviceStatusFingerprint } from "../src/renderer/device-status-publish-gate";

describe("device status publish gate", () => {
  it("suppresses stable payloads until keepalive and ignores object key order", () => {
    const gate = new DeviceStatusPublishGate();
    const first = gate.shouldPublish({ captureState: "capturing", capabilities: { screen: true, audio: true } }, 1_000);
    expect(first.publish).toBe(true);
    gate.markSuccessful(first.fingerprint, 1_000);

    expect(gate.shouldPublish({ capabilities: { audio: true, screen: true }, captureState: "capturing" }, 2_000).publish).toBe(false);
    expect(gate.shouldPublish({ captureState: "capturing", capabilities: { audio: true, screen: true } }, 1_000 + DEVICE_STATUS_KEEPALIVE_MS).publish).toBe(true);
  });

  it("publishes semantic transitions immediately", () => {
    const gate = new DeviceStatusPublishGate();
    const healthy = gate.shouldPublish({ captureState: "capturing" }, 1_000);
    gate.markSuccessful(healthy.fingerprint, 1_000);
    expect(gate.shouldPublish({ captureState: "error" }, 1_001).publish).toBe(true);
  });

  it("retries when a publish was not marked successful", () => {
    const gate = new DeviceStatusPublishGate();
    const payload = { captureState: "reconnecting" };
    expect(gate.shouldPublish(payload, 1_000).publish).toBe(true);
    expect(gate.shouldPublish(payload, 2_000).publish).toBe(true);
    expect(deviceStatusFingerprint(payload)).toBe(deviceStatusFingerprint({ captureState: "reconnecting" }));
  });
});
