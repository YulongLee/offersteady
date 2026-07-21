import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { syntheticState } from "./test-state";

describe("commercial account data consistency", () => {
  it("shows real material counts while keeping the dashboard history limit", () => {
    const state = structuredClone(syntheticState);
    state.interviews = Array.from({ length: 6 }, (_, index) => ({
      id: `history-${index + 1}`,
      title: `历史面试 ${index + 1}`,
      role: "测试岗位",
      status: "ended" as const,
      updatedAt: `第 ${index + 1} 场`,
      readiness: 100,
    }));
    state.librarySources = [
      { id: "resume-ready", ownerUserId: "admin", kind: "resume", displayName: "可用简历", version: "v1", status: "ready", syncStatus: "synced", updatedAtMs: 1, summary: "" },
      { id: "resume-processing", ownerUserId: "admin", kind: "resume", displayName: "处理中简历", version: "v1", status: "processing", syncStatus: "processing", updatedAtMs: 2, summary: "" },
      { id: "jd-failed", ownerUserId: "admin", kind: "jd", displayName: "失败 JD", version: "v1", status: "failed", syncStatus: "failed", updatedAtMs: 3, summary: "" },
      { id: "knowledge-ready", ownerUserId: "admin", kind: "knowledge", displayName: "可用知识材料", version: "v1", status: "ready", syncStatus: "synced", updatedAtMs: 4, summary: "" },
      { id: "knowledge-disabled", ownerUserId: "admin", kind: "knowledge", displayName: "停用知识材料", version: "v1", status: "disabled", updatedAtMs: 5, summary: "" },
    ];
    window.history.pushState({}, "", "/app");

    render(<App initialAuthenticated initialState={state} />);

    expect(screen.getByText("2", { selector: ".readiness-ring strong" })).toBeInTheDocument();
    expect(screen.getByText("1 / 2 份可用")).toBeInTheDocument();
    expect(screen.getByText("0 / 1 份可用")).toBeInTheDocument();
    expect(screen.getByText("1 / 1 份可用")).toBeInTheDocument();
    expect(screen.getByText("1 份资料正在后台处理中")).toBeInTheDocument();
    expect(screen.getByText("5 / 5 场")).toBeInTheDocument();
    expect(screen.getByText("历史面试 5")).toBeInTheDocument();
    expect(screen.queryByText("历史面试 6")).not.toBeInTheDocument();
  });
});
