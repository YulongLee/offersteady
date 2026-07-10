import { describe, expect, it } from "vitest";
import { evaluateGroundedAdvice } from "./advice-policy";

describe("generated advice grounding policy", () => {
  const evidence = ["负责跨端工作台", "参与前端性能治理", "使用 React 与 TypeScript"];

  it("accepts claims that are present in source material", () => {
    expect(evaluateGroundedAdvice(["负责跨端工作台"], evidence)).toEqual({ accepted: true, unsupportedClaims: [] });
  });

  it.each([
    "曾就职于不存在的公司",
    "主导了资料中没有的支付项目",
    "独自负责全部系统架构",
    "将性能提升了 80%",
  ])("rejects unsupported employer, project, responsibility or metric: %s", claim => {
    const result = evaluateGroundedAdvice([claim], evidence);
    expect(result.accepted).toBe(false);
    expect(result.unsupportedClaims).toContain(claim);
    expect(result.safeMessage).toMatch(/真实信息/);
  });
});
