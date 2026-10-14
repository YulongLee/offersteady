import { describe, expect, it } from "vitest";
import { DesktopCapabilitySnapshot } from "../src/main/desktop-capability-snapshot";

describe("device registration capture capabilities", () => {
  it("always advertises supported mock protocol while keeping unverified permissions unknown", () => {
    const snapshot = new DesktopCapabilitySnapshot();
    expect(snapshot.forDevice("synthetic", { protocolVersion: "2.0" })).toMatchObject({ mockInterviewProtocol: 1, microphone: "unknown" });
  });

  it("preserves successful renderer capture reports without allowing runtime identity overrides", () => {
    const snapshot = new DesktopCapabilitySnapshot();
    snapshot.remember("synthetic", { microphone: "granted", systemAudio: "denied", availableSources: [{ id: "synthetic-mic" }], appVersion: "fake", mockInterviewProtocol: 999 });
    expect(snapshot.forDevice("synthetic", { appVersion: "local" })).toMatchObject({
      microphone: "granted", systemAudio: "denied", availableSources: [{ id: "synthetic-mic" }], appVersion: "local", mockInterviewProtocol: 1,
    });
  });

  it("current OS denial or pending permission replaces stale granted status", () => {
    const snapshot = new DesktopCapabilitySnapshot();
    snapshot.remember("synthetic", { microphone: "granted" });
    expect(snapshot.forDevice("synthetic", {}, "denied").microphone).toBe("denied");
    expect(snapshot.forDevice("synthetic", {}, "restricted").microphone).toBe("denied");
    expect(snapshot.forDevice("synthetic", {}, "not-determined").microphone).toBe("unknown");
    snapshot.remember("synthetic", { microphone: "denied" });
    expect(snapshot.forDevice("synthetic", {}, "granted").microphone).toBe("granted");
  });

  it("never shares permissions across device identities or process snapshots", () => {
    const snapshot = new DesktopCapabilitySnapshot();
    snapshot.remember("synthetic-a", { microphone: "granted", systemAudio: "granted" });
    expect(snapshot.forDevice("synthetic-b", {}).microphone).toBe("unknown");
    snapshot.remember("synthetic-b", { screenCapture: true });
    expect(snapshot.forDevice("synthetic-b", {}).systemAudio).toBe("unknown");
    expect(new DesktopCapabilitySnapshot().forDevice("synthetic-a", {}).microphone).toBe("unknown");
  });
});
