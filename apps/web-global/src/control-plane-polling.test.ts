import { describe, expect, it } from "vitest";

import { PREPARATION_BINDING_REFRESH_INTERVAL_MS, PREPARATION_HEARTBEAT_INTERVAL_MS } from "./App";

describe("global web control-plane polling", () => {
  it("keeps preparation heartbeat and binding refresh within the lease budget", () => {
    expect(PREPARATION_HEARTBEAT_INTERVAL_MS).toBe(10_000);
    expect(PREPARATION_BINDING_REFRESH_INTERVAL_MS).toBe(10_000);
    expect(PREPARATION_HEARTBEAT_INTERVAL_MS).toBeLessThan(60_000);
  });
});
