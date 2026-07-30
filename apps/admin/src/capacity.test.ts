import { describe, expect, it } from "vitest";

import { capacityLevelLabel, formatCapacityValue } from "./capacity";

describe("capacity presentation", () => {
  it("formats capacity values and status labels", () => {
    expect(formatCapacityValue(72.45, "%")).toBe("72.5%");
    expect(formatCapacityValue(1600, "ms")).toBe("1.60s");
    expect(formatCapacityValue(null, "场")).toBe("暂无数据");
    expect(capacityLevelLabel.critical).toBe("接近容量");
  });
});
