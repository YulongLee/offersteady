import { describe, expect, it } from "vitest";
import { screenshotStreamEligible, screenshotStreamTransition } from "../src/main/screenshot-stream-policy";

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
});
