import { describe, expect, it } from "vitest";

import { globalApiErrorMessage } from "./global-errors";

describe("globalApiErrorMessage", () => {
  it("keeps an expired or mismatched verification flow actionable", () => {
    expect(globalApiErrorMessage("email_challenge_not_found", 404)).toBe(
      "This verification session is no longer available. Request a new code and try again.",
    );
  });
});
