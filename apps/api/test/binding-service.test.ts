import { describe, expect, it } from "vitest";
import type { CompanionCapabilities, DesktopBindingExchangeRequest } from "@offersteady/protocol";

import { BindingError, DesktopBindingService } from "../src/binding-service.js";

const capabilities: CompanionCapabilities = {
  protocolVersion: "1.0.0",
  appVersion: "0.1.0",
  platform: "windows",
  platformVersion: "macOS 14.2+ universal",
  microphone: "prompt",
  systemAudio: "prompt",
  availableSources: [],
};

const request = (tokenOrCode: string): DesktopBindingExchangeRequest => ({
  tokenOrCode,
  sessionId: "session-1",
  userId: "user-1",
  deviceId: "device-1",
  displayName: "Office PC",
  capabilities,
});

const expectCode = (action: () => unknown, code: BindingError["code"]) => {
  try {
    action();
    throw new Error("Expected BindingError");
  } catch (error) {
    expect(error).toBeInstanceOf(BindingError);
    expect((error as BindingError).code).toBe(code);
  }
};

describe("DesktopBindingService", () => {
  it("creates a scoped one-time binding and exchanges it for a device credential", () => {
    const service = new DesktopBindingService();
    const binding = service.createBinding("session-1", "user-1", 1_000);
    expect(binding.manualCode).toMatch(/^\d{6}$/);
    expect(binding.deepLink).toContain("offersteady://bind");
    const result = service.exchange(request(binding.token), 1_001);
    expect(result.deviceStatus.captureState).toBe("permission-required");
    expect(service.authorize(result.deviceCredential, "session-1", 1_002)).toEqual({
      userId: "user-1",
      deviceId: "device-1",
    });
  });

  it("supports manual code exchange and blocks replay", () => {
    const service = new DesktopBindingService();
    const binding = service.createBinding("session-1", "user-1", 1_000);
    service.exchange(request(binding.manualCode), 1_001);
    expectCode(() => service.exchange(request(binding.token), 1_002), "binding-used");
  });

  it("rejects expired and wrong-session bindings", () => {
    const service = new DesktopBindingService();
    const expired = service.createBinding("session-1", "user-1", 1_000);
    expectCode(() => service.exchange(request(expired.token), 1_000 + 10 * 60 * 1_000), "binding-expired");

    const scoped = service.createBinding("session-1", "user-1", 2_000);
    expectCode(
      () => service.exchange({ ...request(scoped.token), sessionId: "session-2" }, 2_001),
      "binding-scope-mismatch",
    );
  });

  it("revokes an exchanged desktop device", () => {
    const service = new DesktopBindingService();
    const binding = service.createBinding("session-1", "user-1", 1_000);
    const result = service.exchange(request(binding.token), 1_001);
    expect(service.revoke("device-1")).toBe(true);
    expectCode(() => service.authorize(result.deviceCredential, "session-1", 1_002), "device-revoked");
  });

  it("never stores or accepts an unknown raw credential", () => {
    const service = new DesktopBindingService();
    expectCode(() => service.authorize("unknown-secret", "session-1"), "device-credential-invalid");
  });
});
