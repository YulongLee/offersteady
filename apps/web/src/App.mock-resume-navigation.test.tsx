import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { MockQuote, MockSession } from "./mock-interview-client";
import { optimizerCaps, optimizerState } from "./test/resume-optimizer-fixtures";

const quote: MockQuote = {
  activeTimeMember: true, dailyFreeRemaining: 1, entryPoints: 0, minutePoints: 0,
  billingClass: "daily_pass_free", savedCount: 1, savedLimit: 2, dailyFreeLimit: 1,
  durationLimitMinutes: 60, quotaDay: "2026-10-18", timezone: "Asia/Shanghai",
  nowMs: Date.parse("2026-10-18T12:00:00+08:00"),
};
const historySession: MockSession = {
  sessionId: "synthetic-navigation-report", title: "合成历史模拟面试", targetRole: "后端工程师",
  billingClass: "daily_pass_free", refunded: false, createdAtMs: 1,
  resumeId: "synthetic-resume", resumeVersion: "synthetic-version", error: null,
  billableMs: 10000, billedMinutes: 1, interacting: false, partial: true,
  state: { phase: "completed", version: 3, capture_epoch: null,
    rounds: [{ question_id: "synthetic-question", question: "如何防止重复请求？", answer: "使用幂等键。", submission_id: "synthetic-answer" }] },
  report: { summary: "合成报告：保留已完成的模拟面试复盘。", overall_score: 80, dimensions: null,
    feedback: [], practice_priorities: ["结合真实经历说明幂等方案。"] },
};

function setup(capability: boolean | "unavailable", path = "/app/resume-optimizer") {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async input => {
    const pathname = new URL(String(input), window.location.origin).pathname;
    let data: unknown;
    if (pathname === "/api/v1/mock-interviews/capabilities") {
      if (capability === "unavailable") throw new TypeError("Synthetic capability request failed");
      data = { enabled: capability };
    } else if (pathname === "/api/v1/mock-interviews") {
      data = { sessions: [historySession], quote };
    } else if (pathname === `/api/v1/mock-interviews/${historySession.sessionId}`) {
      data = historySession;
    } else if (pathname === "/api/v1/resume-optimizer/capabilities") {
      data = optimizerCaps();
    } else if (pathname === "/api/v1/resume-optimizer/jobs") {
      data = { jobs: [] };
    } else {
      throw new Error(`Unexpected synthetic request: ${pathname}`);
    }
    return new Response(JSON.stringify({ success: true, data, error: null, requestId: "synthetic-navigation", meta: { apiVersion: "v1", timestamp: "2026-10-18T04:00:00Z" } }), { headers: { "Content-Type": "application/json" } });
  });
  window.history.replaceState({}, "", path);
  render(<App initialAuthenticated initialState={optimizerState()} />);
  return fetch;
}

afterEach(() => vi.restoreAllMocks());

describe("新增简历优化保留模拟面试", () => {
  it("同时保留桌面和移动导航中的普通面试、笔试、模拟面试和简历优化", async () => {
    setup(true);
    await screen.findByRole("heading", { level: 1, name: "简历优化" });
    for (const name of ["应用导航", "移动端应用导航"]) {
      const navigation = within(screen.getByRole("navigation", { name }));
      expect(await navigation.findByRole("link", { name: "模拟面试" })).toHaveAttribute("href", "/app/mock-interviews");
      expect(navigation.getByRole("link", { name: "简历优化" })).toHaveAttribute("href", "/app/resume-optimizer");
      expect(navigation.getByRole("link", { name: "面试模式" })).toHaveAttribute("href", "/app");
      expect(navigation.getByRole("link", { name: "笔试模式" })).toHaveAttribute("href", "/app/written-exams");
    }
  });

  it("能从简历优化进入模拟面试和历史报告，再通过移动导航返回简历优化", async () => {
    const fetch = setup(true);
    const desktopNavigation = within(screen.getByRole("navigation", { name: "应用导航" }));
    fireEvent.click(await desktopNavigation.findByRole("link", { name: "模拟面试" }));
    expect(await screen.findByRole("heading", { level: 1, name: "把下一次面试，提前练一遍。" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "创建模拟面试 →" })).toBeEnabled();
    fireEvent.click(await screen.findByRole("link", { name: "查看报告" }));
    expect(await screen.findByRole("heading", { level: 1, name: historySession.title })).toBeInTheDocument();
    expect(screen.getByText(historySession.report!.summary)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下载 Word" })).toBeEnabled();
    fireEvent.click(within(screen.getByRole("navigation", { name: "移动端应用导航" })).getByRole("link", { name: "简历优化" }));
    expect(await screen.findByRole("heading", { level: 1, name: "简历优化" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/app/resume-optimizer");
    expect(fetch.mock.calls.some(([, init]) => init?.method && init.method !== "GET")).toBe(false);
  });

  it("真实能力关闭时继续隐藏模拟面试，并禁止直接页面创建而保留简历优化", async () => {
    const fetch = setup(false, "/app/mock-interviews");
    expect(await screen.findByText("模拟面试尚未开放")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "模拟面试" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "创建模拟面试 →" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "简历优化" })).toHaveLength(2);
    expect(fetch.mock.calls.some(([input]) => new URL(String(input), window.location.origin).pathname === "/api/v1/mock-interviews")).toBe(false);
  });

  it("能力读取失败时保留原模拟面试门禁，简历优化页面仍可使用", async () => {
    const fetch = setup("unavailable");
    expect(await screen.findByRole("heading", { level: 1, name: "简历优化" })).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/mock-interviews/capabilities"), expect.anything()));
    expect(screen.queryByRole("link", { name: "模拟面试" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "简历优化" })).toHaveLength(2);
  });
});
