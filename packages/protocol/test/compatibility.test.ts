import { describe, expect, it } from "vitest";

import { isProtocolCompatible } from "../src/compatibility";

describe("isProtocolCompatible", () => {
  it("accepts versions with the same major", () => {
    expect(isProtocolCompatible("1.4.2", "1.0.0")).toBe(true);
  });

  it("rejects versions with a different major", () => {
    expect(isProtocolCompatible("2.0.0", "1.9.0")).toBe(false);
  });

  it("rejects malformed versions", () => {
    expect(isProtocolCompatible("latest", "1.0.0")).toBe(false);
  });
});
