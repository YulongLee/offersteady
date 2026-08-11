import { describe, expect, it } from "vitest";

import { validateGrowthSettings } from "./growth-settings";

describe("growth referral settings", () => {
  it("accepts an integer reward and meaningful reason", () => {
    expect(validateGrowthSettings("500", "上线邀请活动")).toEqual({ valid: true, message: "" });
  });

  it.each(["0", "-1", "1.5", "100001", "not-a-number"])("rejects invalid reward %s", reward => {
    expect(validateGrowthSettings(reward, "测试变更原因")).toEqual({
      valid: false,
      message: "单次奖励必须是 1–100000 的整数。",
    });
  });

  it("requires a change reason", () => {
    expect(validateGrowthSettings("500", "短").valid).toBe(false);
  });
});
