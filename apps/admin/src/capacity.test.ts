import { describe, expect, it } from "vitest";

import { capacityLevelLabel, formatCapacityValue, hasRequestBreakdownData, requestClassLabels } from "./capacity";

describe("capacity presentation", () => {
  it("formats capacity values and status labels", () => {
    expect(formatCapacityValue(72.45, "%")).toBe("72.5%");
    expect(formatCapacityValue(1600, "ms")).toBe("1.60s");
    expect(formatCapacityValue(null, "场")).toBe("暂无数据");
    expect(capacityLevelLabel.critical).toBe("接近容量");
  });

  it("supports additive request diagnostics and older response fallback", () => {
    expect(requestClassLabels.user_api).toBe("用户请求");
    expect(hasRequestBreakdownData(undefined)).toBe(false);
    expect(hasRequestBreakdownData({ classes: {}, slowRoutes: [] })).toBe(true);
    expect(hasRequestBreakdownData({ classes: { telemetry: { requestCount: 1, p95Ms: 620, errorCount: 0, errorRate: 0 } }, slowRoutes: [] })).toBe(true);
  });
});
