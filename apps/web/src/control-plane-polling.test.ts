import { describe, expect, it } from "vitest";

import { PREPARATION_HEARTBEAT_INTERVAL_MS } from "./App";

describe("web control-plane polling", () => {
  it("keeps preparation heartbeats below the web lease TTL without chatty polling", () => {
    expect(PREPARATION_HEARTBEAT_INTERVAL_MS).toBe(10_000);
    expect(PREPARATION_HEARTBEAT_INTERVAL_MS).toBeLessThan(60_000);
  });
});
