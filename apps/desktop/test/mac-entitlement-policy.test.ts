import { describe, expect, it } from "vitest";
import { assertAudioInputEntitlement, hasEnabledEntitlement } from "../scripts/mac-entitlement-policy.mjs";

describe("actual signed microphone entitlement policy", () => {
  const key = "com.apple.security.device.audio-input";

  it("requires an enabled boolean and rejects missing or disabled signatures", () => {
    expect(() => assertAudioInputEntitlement(`<dict><key>${key}</key><true/></dict>`, "synthetic.app")).not.toThrow();
    expect(() => assertAudioInputEntitlement("<dict/>", "synthetic.app")).toThrow("synthetic.app");
    expect(() => assertAudioInputEntitlement(`<dict><key>${key}</key><false/></dict>`, "synthetic Helper (Renderer)")).toThrow("Renderer");
    expect(hasEnabledEntitlement(`<key>${key.replaceAll(".", "x")}</key><true/>`, key)).toBe(false);
    expect(hasEnabledEntitlement(`<key>${key}</key><string>true</string>`, key)).toBe(false);
  });
});
