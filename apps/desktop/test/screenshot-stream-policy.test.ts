import { describe, expect, it } from "vitest";
import {
  screenshotStreamAdmissionAction,
  screenshotStreamEligible,
  screenshotStreamSuspensionTransition,
  screenshotStreamTransition,
} from "../src/main/screenshot-stream-policy";

describe("screenshot stream lifecycle policy", () => {
  it("preserves one stream across eligible runtime state changes", () => {
    expect(screenshotStreamEligible("capturing")).toBe(true);
    expect(screenshotStreamEligible("error")).toBe(true);
    expect(screenshotStreamEligible("reconnecting")).toBe(true);
    expect(screenshotStreamEligible("paused")).toBe(true);
    expect(screenshotStreamTransition("capturing", "error")).toBe("preserve");
    expect(screenshotStreamTransition("error", "reconnecting")).toBe("preserve");
  });

  it("only starts and stops when eligibility changes", () => {
    expect(screenshotStreamTransition("ready", "capturing")).toBe("start");
    expect(screenshotStreamTransition("capturing", "ready")).toBe("stop");
    expect(screenshotStreamTransition("ready", "not-connected")).toBe("preserve");
  });

  it("suspends terminal missing bindings but retries transport and server failures", () => {
    expect(screenshotStreamAdmissionAction(404)).toBe("suspend");
    expect(screenshotStreamAdmissionAction(409)).toBe("suspend");
    expect(screenshotStreamAdmissionAction(429)).toBe("retry");
    expect(screenshotStreamAdmissionAction(503)).toBe("retry");
    expect(screenshotStreamAdmissionAction(null)).toBe("retry");
  });

  it("resumes a suspended stream only for a meaningful eligible transition", () => {
    expect(screenshotStreamSuspensionTransition("reconnecting", "capturing")).toBe("resume");
    expect(screenshotStreamSuspensionTransition("ready", "paused")).toBe("resume");
    expect(screenshotStreamSuspensionTransition("capturing", "capturing")).toBe("preserve");
    expect(screenshotStreamSuspensionTransition("ready", "reconnecting")).toBe("preserve");
    expect(screenshotStreamSuspensionTransition("reconnecting", "ready")).toBe("preserve");
  });
});
