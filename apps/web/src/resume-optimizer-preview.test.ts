import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("react-dom/client", () => ({ createRoot: () => ({ render: vi.fn() }) }));
vi.mock("./App", () => ({ App: () => null }));
const originalFetch = globalThis.fetch;
async function data(path: string) {
  const response = await fetch(new URL(path, location.origin));
  expect(response.status).toBe(200);
  return (await response.json()).data;
}
async function createQuotedJob() {
  const quote = await data("/api/v1/resume-optimizer/capabilities");
  const response = await fetch("/api/v1/resume-optimizer/jobs", { method: "POST", body: JSON.stringify({ sourceDocumentId: "synthetic-resume", sourceVersionId: "synthetic-version", quotedBillingClass: quote.billingClass, quotedPoints: quote.entryPoints, confirmPointsCharge: quote.billingClass === "points", confirmProcessing: true }) });
  expect(response.status).toBe(200);
  return (await response.json()).data;
}
beforeEach(async () => {
  vi.resetModules();
  document.body.innerHTML = '<div id="root"></div><output id="qa-receipt"></output>';
  window.history.replaceState({}, "", "/test-previews/resume-optimizer-app.html?scenario=free");
  await import("../test-previews/resume-optimizer");
});
afterEach(() => { globalThis.fetch = originalFetch; });
describe("synthetic preview preserves existing mock interview", () => {
  it.each([
    ["partial", "completed", { proposedCount: 2, appliedCount: 1, retainedCount: 1 }],
    ["no-effective", "failed", null], ["failed-known", "failed", null], ["legacy", "completed", null],
  ] as const)("新场景%s保留合成状态和模拟入口，不调用真实服务", async (scenario, status, summary) => {
    vi.resetModules(); window.history.replaceState({}, "", `/test-previews/resume-optimizer-app.html?scenario=${scenario}`);
    await import("../test-previews/resume-optimizer");
    const list = await data("/api/v1/resume-optimizer/jobs"); const job = list.jobs[0];
    expect(job.status).toBe(status); if (summary) expect(job.review.editSummary).toMatchObject(summary); else expect(job.review?.editSummary).toBeUndefined();
    if (scenario === "no-effective") expect(job.errorMessage).toContain("未生成可安全应用的有效修改");
    if (scenario === "failed-known") expect(job.errorMessage).toContain("原文事实检查");
    expect(await data("/api/v1/mock-interviews/capabilities")).toEqual({ enabled: true });
    await expect(fetch("https://mianshiwen.cn/api/v1/resume-optimizer/jobs")).rejects.toThrow("External network is disabled");
    expect(JSON.parse(document.getElementById("qa-receipt")!.textContent!)).toMatchObject({ providerCalls: 0, syntheticOnly: true });
  });
  it("explicitly enables both features instead of hiding mock interview via generic capabilities", async () => {
    expect(await data("/api/v1/mock-interviews/capabilities")).toEqual({ enabled: true });
    expect(await data("http://127.0.0.1:8000/api/v1/mock-interviews/capabilities")).toEqual({ enabled: true });
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ enabled: true, dailyLimit: 3, dailyRemaining: 3 });
    expect(await data("/api/v1/unrelated/capabilities")).toEqual({ enabled: false });
  });
  it("serves existing mock list, quote and completed report locally", async () => {
    const history = await data("/api/v1/mock-interviews");
    expect(history.quote).toMatchObject({ dailyFreeLimit: 1, durationLimitMinutes: 60, entryPoints: 0 });
    const session = await data(`/api/v1/mock-interviews/${history.sessions[0].sessionId}`);
    expect(session).toEqual(history.sessions[0]);
    expect(session.state.phase).toBe("completed");
    expect(session.report.feedback).toHaveLength(1);
  });
  it("never connects to production or pretends to create a live interview", async () => {
    await expect(fetch("https://mianshiwen.cn/api/v1/mock-interviews")).rejects.toThrow("External network is disabled");
    const response = await fetch("/api/v1/mock-interviews", { method: "POST", body: "{}" });
    expect(response.status).toBe(422);
    expect((await response.json()).error.message).toContain("本地合成预览不创建真实面试");
    expect(JSON.parse(document.getElementById("qa-receipt")!.textContent!)).toMatchObject({ syntheticOnly: true, providerCalls: 0 });
  });
  it.each([
    { targetRole: "合成前端工程师", jdText: "合成岗位要求：熟悉TypeScript", jdDocumentId: null, jdVersionId: null },
    { targetRole: "合成后端工程师", jdText: "", jdDocumentId: "synthetic-jd", jdVersionId: "synthetic-jd-version" },
  ])("preserves submitted role and JD fields through synthetic creation and completion", async input => {
    const response = await fetch("/api/v1/resume-optimizer/jobs", { method: "POST", body: JSON.stringify({ ...input, sourceDocumentId: "synthetic-resume", sourceVersionId: "synthetic-version", quotedBillingClass: "daily_pass_free", quotedPoints: 0, confirmProcessing: true }) });
    expect(response.status).toBe(200);
    const created = (await response.json()).data;
    expect(created).toMatchObject({ ...input, hasJd: true, status: "queued" });
    await data(`/api/v1/resume-optimizer/jobs/${created.jobId}`);
    expect(await data(`/api/v1/resume-optimizer/jobs/${created.jobId}`)).toMatchObject({ ...input, hasJd: true, status: "completed", review: { roleMatchingAssessed: true } });
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ dailyLimit: 3, dailyRemaining: 2 });
    expect(JSON.parse(document.getElementById("qa-receipt")!.textContent!)).toMatchObject({ syntheticOnly: true, providerCalls: 0 });
  });
  it("offers three free completions then a paid fourth, preserving spent free quota after deletion", async () => {
    const ids: string[] = [];
    for (let i = 0; i < 3; i += 1) {
      expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ billingClass: "daily_pass_free", dailyRemaining: 3 - i });
      const created = await createQuotedJob(); ids.push(created.jobId);
      await data(`/api/v1/resume-optimizer/jobs/${created.jobId}`);
      expect(await data(`/api/v1/resume-optimizer/jobs/${created.jobId}`)).toMatchObject({ status: "completed", pointsCharged: 0 });
    }
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ billingClass: "points", dailyRemaining: 0, availablePoints: 250 });
    expect((await fetch(`/api/v1/resume-optimizer/jobs/${ids[0]}`, { method: "DELETE" })).status).toBe(200);
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ billingClass: "points", dailyRemaining: 0 });
    const paid = await createQuotedJob();
    expect(paid).toMatchObject({ billingClass: "points", pointsCharged: 100 });
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ dailyRemaining: 0, availablePoints: 150, canStart: false });
    const cancelled = await fetch(`/api/v1/resume-optimizer/jobs/${paid.jobId}/cancel`, { method: "POST" });
    expect((await cancelled.json()).data).toMatchObject({ billingStatus: "released", status: "cancelled" });
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ dailyRemaining: 0, availablePoints: 250, canStart: true });
  });
  it("releases only the cancelled unfinished free synthetic task", async () => {
    const created = await createQuotedJob();
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ dailyRemaining: 2 });
    await fetch(`/api/v1/resume-optimizer/jobs/${created.jobId}/cancel`, { method: "POST" });
    expect(await data("/api/v1/resume-optimizer/capabilities")).toMatchObject({ dailyRemaining: 3, availablePoints: 250 });
  });
});
