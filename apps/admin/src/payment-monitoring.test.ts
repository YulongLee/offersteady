import { describe, expect, it } from "vitest";

import { diagnosticLabel, formatCny } from "./payment-monitoring";
import { formatUptime } from "./server-health";

describe("admin payment and server presentation", () => {
  it("formats real settled amounts without losing cents", () => {
    expect(formatCny(5980)).toBe("¥59.80");
    expect(formatCny(0)).toBe("¥0.00");
  });

  it("does not mistake an unperformed diagnostic for success", () => {
    expect(diagnosticLabel(true)).toBe("通过");
    expect(diagnosticLabel(false)).toBe("失败");
    expect(diagnosticLabel(null)).toBe("未检查");
  });

  it("formats host uptime for operators", () => {
    expect(formatUptime(90_000)).toBe("1 天 1 小时");
    expect(formatUptime(null)).toBe("—");
  });
});
