import { describe, expect, it } from "vitest";

import { paymentChannelStatus } from "./payment-channel-status";

describe("payment channel status", () => {
  it("keeps a draft channel visibly unavailable and reports validation errors", () => {
    const status = paymentChannelStatus({
      enabled: false,
      validationStatus: "draft",
      validationErrors: ["缺少字段：appId"],
    });

    expect(status.active).toBe(false);
    expect(status.ready).toBe(false);
    expect(status.usageLabel).toBe("用户端未使用");
    expect(status.readinessLabel).toBe("配置待完善");
    expect(status.validationErrors).toEqual(["缺少字段：appId"]);
  });

  it("distinguishes ready-but-disabled from an active user channel", () => {
    const ready = paymentChannelStatus({ enabled: false, validationStatus: "ready" });
    const active = paymentChannelStatus({ enabled: true, validationStatus: "ready" });

    expect(ready.ready).toBe(true);
    expect(ready.active).toBe(false);
    expect(ready.readinessLabel).toBe("配置可启用");
    expect(ready.usageLabel).toBe("用户端未使用");
    expect(active.active).toBe(true);
    expect(active.usageLabel).toBe("用户端正在使用");
    expect(active.usageDescription).toContain("用户支付页现在可以选择");
  });

  it("never presents an inconsistent enabled draft as active", () => {
    const status = paymentChannelStatus({ enabled: true, validationStatus: "draft" });

    expect(status.active).toBe(false);
    expect(status.usageLabel).toBe("用户端未使用");
  });
});
