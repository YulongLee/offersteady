import { afterEach, describe, expect, it, vi } from "vitest";
import { authClient } from "./auth-client";
import { BackendResumeOptimizerClient, downloadOptimizedResume, ResumeOptimizerError } from "./resume-optimizer-client";
const response = (data: unknown) => new Response(JSON.stringify({ success: true, data }), { headers: { "Content-Type": "application/json" } });
afterEach(() => vi.restoreAllMocks());
describe("Global resume optimizer transport", () => {
  it("uses authoritative auth with private no-store requests and encodes opaque job identifiers", async () => {
    vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic-only" } as never);
    const fetch = vi.fn(async () => response({ jobId: "synthetic" })); const client = new BackendResumeOptimizerClient("https://example.invalid/api/v1/", fetch);
    await client.get("job/foreign?x");
    expect(fetch.mock.calls[0]![0]).toBe("https://example.invalid/api/v1/resume-optimizer/jobs/job%2Fforeign%3Fx");
    const init = fetch.mock.calls[0]![1] as RequestInit; expect(new Headers(init.headers).get("Authorization")).toBe("Bearer synthetic-only"); expect(init.cache).toBe("no-store");
  });
  it("surfaces the nested domain error instead of a generic 429", async () => {
    const client = new BackendResumeOptimizerClient("/", async () => new Response(JSON.stringify({ error: { code: "domain_error", message: "private provider error", details: { errorCode: "resume_optimizer_daily_limit" } } }), { status: 429 }));
    await expect(client.create({} as never)).rejects.toMatchObject({ code: "resume_optimizer_daily_limit", status: 429, message: expect.stringContaining("00:00 UTC") });
  });
  it("never exposes raw provider or personal failure strings", async () => {
    const client = new BackendResumeOptimizerClient("/", async () => new Response(JSON.stringify({ error: { message: "private resume contents" } }), { status: 500 }));
    await expect(client.list()).rejects.not.toThrow("private resume contents");
  });
  it("passes a cancellation signal without treating abort as network failure", async () => {
    const controller = new AbortController(); const fetch = vi.fn(async (_: unknown, init?: RequestInit) => { expect(init?.signal).toBe(controller.signal); throw new DOMException("Aborted", "AbortError"); });
    const client = new BackendResumeOptimizerClient("/", fetch);
    await expect(client.get("synthetic", controller.signal)).rejects.toMatchObject({ name: "AbortError" });
  });
  it("binds edited draft and explicit independent factual confirmation to the saved revision", async () => {
    const fetch = vi.fn(async () => response({ document: {} })); const client = new BackendResumeOptimizerClient("/", fetch);
    await client.saveDraft("synthetic", 2, "# Test\nSynthetic source only"); await client.saveAs("synthetic", 3);
    expect(JSON.parse(String((fetch.mock.calls[0]![1] as RequestInit).body))).toEqual({ expectedRevision: 2, markdown: "# Test\nSynthetic source only" });
    expect(JSON.parse(String((fetch.mock.calls[1]![1] as RequestInit).body))).toEqual({ expectedRevision: 3, confirmIndependentCopy: true, factsConfirmed: true });
  });
  it("downloads real attachment bytes with UTF-8 filenames and revision confirmation", async () => {
    const fetch = vi.fn(async () => new Response("%PDF-synthetic", { headers: { "Content-Type": "application/pdf", "Content-Disposition": "attachment; filename*=UTF-8''%E6%9D%8E%20R%C3%A9sum%C3%A9.pdf" } }));
    const client = new BackendResumeOptimizerClient("/", fetch); const result = await client.download("test/id", "pdf", 4);
    expect(result.filename).toBe("李 Résumé.pdf"); expect(await result.blob.text()).toBe("%PDF-synthetic");
    expect(fetch.mock.calls[0]![0]).toBe("/api/v1/resume-optimizer/jobs/test%2Fid/export?format=pdf&expectedRevision=4&factsConfirmed=true");
  });
  it("does not turn an unauthorized export into a downloadable error blob", async () => {
    const client = new BackendResumeOptimizerClient("/", async () => new Response("no", { status: 401 }));
    await expect(client.download("x", "docx", 1)).rejects.toBeInstanceOf(ResumeOptimizerError);
  });
  it("cleans temporary local anchors and object URLs after a download", () => {
    vi.useFakeTimers(); const create = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:synthetic"); const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined); const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    downloadOptimizedResume({ blob: new Blob(["synthetic"]), filename: "Resume.docx" });
    expect(create).toHaveBeenCalledOnce(); expect(click).toHaveBeenCalledOnce(); expect((click.mock.instances[0] as HTMLAnchorElement).isConnected).toBe(false);
    vi.runAllTimers(); expect(revoke).toHaveBeenCalledWith("blob:synthetic"); vi.useRealTimers();
  });
  it("rejects HTML error pages and invalid binary signatures even when a proxy returns HTTP 200", async () => {
    const html = new BackendResumeOptimizerClient("/", async () => new Response("<html>Login</html>", { headers: { "Content-Type": "text/html" } }));
    const invalid = new BackendResumeOptimizerClient("/", async () => new Response("not a PDF", { headers: { "Content-Type": "application/pdf" } }));
    await expect(html.download("synthetic", "pdf", 1)).rejects.toThrow("not a valid resume file");
    await expect(invalid.download("synthetic", "pdf", 1)).rejects.toThrow("not a valid resume file");
  });

});
