import { describe, expect, it } from "vitest";

import { buildLinePath, formatTrendChange, formatTrendValue } from "./analytics";

describe("operations trend helpers", () => {
  it("breaks the line across unavailable historical dates", () => {
    const path = buildLinePath([
      { date: "2026-07-01", value: 2, coverage: "complete" },
      { date: "2026-07-02", value: null, coverage: "unavailable" },
      { date: "2026-07-03", value: 4, coverage: "complete" },
    ]);
    expect(path.match(/M/g)).toHaveLength(2);
    expect(path).not.toContain("NaN");
  });

  it("formats money, latency and period comparison", () => {
    expect(formatTrendValue(1299, "分")).toBe("¥12.99");
    expect(formatTrendValue(1500, "ms")).toBe("1.50s");
    expect(formatTrendChange(12.345)).toBe("+12.3%");
    expect(formatTrendChange(null)).toBe("暂无可比数据");
  });
});

