import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import snapshot from "./test/resume-optimizer-safe-edit-http-wire.json";
import { BackendResumeOptimizerClient, resumeInitialDraftSummary, resumeOptimizationFailureMessage, type ResumeOptimization } from "./resume-optimizer-client";
import { ResumeOptimizerPage } from "./ResumeOptimizerPage";
import { optimizerCaps, optimizerState } from "./test/resume-optimizer-fixtures";

const wireSha256 = "7d51bea3252fbb54e82bb3f3ca36d3fcb8de960e55a8488fe78a261ac93a1aee";
const row = (label: string) => snapshot.responses.find(item => item.label === label)!;
const data = (label: string) => row(label).body.data as unknown as ResumeOptimization;
const respond = (label: string) => new Response(JSON.stringify(row(label).body), { status: row(label).status, headers: { "Content-Type": "application/json", "Cache-Control": "private, no-store" } });
afterEach(() => vi.restoreAllMocks());

describe("新增真实隔离PG/FastAPI安全改写响应合同", () => {
  it("五个响应由独立合成服务生成，新增副本SHA固定且未覆盖旧wire", () => {
    const bytes = readFileSync(resolve(process.cwd(), "src/test/resume-optimizer-safe-edit-http-wire.json"));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(wireSha256);
    expect(snapshot).toMatchObject({ synthetic: true, edition: "cn", providerCalls: 2 });
    expect(snapshot.responses.map(item => item.label)).toEqual(["partial-create", "partial-detail", "no-effective-create", "no-effective-detail", "history"]);
  });
  it("真实partial响应为一次积分完成，client保留合法初稿计数且没有坏改写或内部诊断", async () => {
    const client = new BackendResumeOptimizerClient("/", async () => respond("partial-detail"));
    const job = await client.get(data("partial-detail").jobId);
    expect(job).toMatchObject({ status: "completed", billingClass: "points", pointsCharged: 100, billingStatus: "settled", review: { editSummary: { proposedCount: 2, appliedCount: 1, retainedCount: 1 } } });
    expect(resumeInitialDraftSummary(job)).toBe("AI 初稿：已采用 1 项改写，1 项改写未采用，请核实。");
    expect(job.initialDraftMarkdown).not.toBe(job.sourceText); expect(job.review).not.toHaveProperty("edits");
    expect(JSON.stringify(job)).not.toMatch(/failureDiagnostic|fact_english_content_added|replacement/);
  });
  it("真实零有效响应failed并原路释放，client显示固定原因且不生成可下载稿", async () => {
    const client = new BackendResumeOptimizerClient("/", async () => respond("no-effective-detail"));
    const job = await client.get(data("no-effective-detail").jobId);
    expect(job).toMatchObject({ status: "failed", errorCode: "invalid_output", billingStatus: "released", allowanceStatus: "released", pointsCharged: 100, review: null, draftMarkdown: null, initialDraftMarkdown: null });
    expect(resumeOptimizationFailureMessage(job)).toBe("本次未生成可安全应用的有效修改，原简历已保留。"); expect(resumeInitialDraftSummary(job)).toBeNull();
  });
  it("真实history与detail在页面展示partial摘要与失败/100积分退还，打开历史不重新收费", async () => {
    const state = optimizerState(); const partial = data("partial-detail"); const failed = data("no-effective-detail");
    state.account = { ...state.account, id: "owner" };
    state.librarySources = [{ id: partial.sourceDocumentId, documentId: partial.sourceDocumentId, documentVersionId: partial.sourceVersionId, displayName: partial.sourceDisplayName, ownerUserId: "owner", kind: "resume", status: "ready", version: "v1", updatedAtMs: 1 }];
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = new URL(String(input), "http://synthetic.invalid");
      if (init?.method && init.method !== "GET") throw new Error("History must not mutate a synthetic job");
      if (url.pathname.endsWith("/resume-optimizer/capabilities")) return new Response(JSON.stringify({ success: true, data: optimizerCaps() }), { headers: { "Content-Type": "application/json" } });
      if (url.pathname.endsWith("/resume-optimizer/jobs")) return respond("history");
      if (url.pathname.endsWith("/" + partial.jobId)) return respond("partial-detail");
      if (url.pathname.endsWith("/" + failed.jobId)) return respond("no-effective-detail");
      if (url.pathname.endsWith("/billing/state")) return new Response(JSON.stringify({ success: true, data: state.billing }), { headers: { "Content-Type": "application/json" } });
      throw new Error("Unexpected synthetic route");
    });
    render(<MemoryRouter initialEntries={["/app/resume-optimizer"]}><ResumeOptimizerPage state={state} setState={vi.fn()} /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("tab", { name: "我的优化记录" }));
    fireEvent.click(await screen.findByRole("button", { name: /合成简历.md.*已完成/ }));
    expect(await screen.findByLabelText("AI 初稿改写摘要")).toHaveTextContent("AI 初稿：已采用 1 项改写，1 项改写未采用，请核实。");
    expect(screen.getByLabelText("可编辑优化稿")).toHaveValue(partial.draftMarkdown);
    fireEvent.click(screen.getByRole("button", { name: /合成简历.md.*优化失败/ }));
    expect(await screen.findByText("本次未生成可安全应用的有效修改，原简历已保留。")).toBeVisible();
    expect(screen.getByText("本次扣除的 100 积分已原路退还。")).toBeVisible();
    expect(screen.queryByLabelText("可编辑优化稿")).not.toBeInTheDocument();
    expect(fetch.mock.calls.filter(call => call[1]?.method === "POST")).toHaveLength(0);
  });
});
