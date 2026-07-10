import { describe, expect, it } from "vitest";

import { initialCaptureState, transitionCaptureState } from "../src/shared/capture-machine";

describe("capture state machine", () => {
  it("always starts disconnected and never resumes capture implicitly", () => {
    expect(initialCaptureState()).toBe("not-connected");
    expect(transitionCaptureState(initialCaptureState(), "start")).toBe("not-connected");
  });

  it("requires connection and permissions before capture", () => {
    const permission = transitionCaptureState("not-connected", "connect");
    const ready = transitionCaptureState(permission, "permissions-granted");
    expect(permission).toBe("permission-required");
    expect(ready).toBe("ready");
    expect(transitionCaptureState(ready, "start")).toBe("capturing");
  });

  it("supports explicit pause, resume and stop", () => {
    expect(transitionCaptureState("capturing", "pause")).toBe("paused");
    expect(transitionCaptureState("paused", "resume")).toBe("capturing");
    expect(transitionCaptureState("capturing", "stop")).toBe("ready");
  });

  it("moves active capture to reconnecting after connection loss", () => {
    expect(transitionCaptureState("capturing", "connection-lost")).toBe("reconnecting");
    expect(transitionCaptureState("reconnecting", "reconnected")).toBe("capturing");
  });

  it("disconnects from every active state", () => {
    expect(transitionCaptureState("capturing", "disconnect")).toBe("not-connected");
    expect(transitionCaptureState("paused", "disconnect")).toBe("not-connected");
    expect(transitionCaptureState("error", "disconnect")).toBe("not-connected");
  });
});
