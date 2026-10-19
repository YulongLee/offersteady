import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import snapshot from "./test/resume-optimizer-http-wire.json";
import { BackendResumeOptimizerClient, resumeOptimizerClient } from "./resume-optimizer-client";
import { ResumeOptimizerPage } from "./ResumeOptimizerPage";
import { syntheticState } from "../../web/src/test-state";
import type { WebAppState } from "./domain";
const responses = snapshot.responses;
const saved = responses.saveAs.body.data!.document;
const completed = responses.completedDetail.body.data!;
type WireResponse = { readonly status: number; readonly headers: Record<string, string>; readonly body?: unknown; readonly bodyBase64?: string };
function fromWire(wire: WireResponse) {
  const body = wire.bodyBase64 ? Uint8Array.from(atob(wire.bodyBase64), c => c.charCodeAt(0)) : JSON.stringify(wire.body);
  return new Response(body, { status: wire.status, headers: wire.headers });
}
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
describe("actual Global FastAPI and service wire compatibility", () => {
  it("binds real source aliases, readiness, member quota and nullable initial result fields", async () => {
    expect(snapshot.actualFastApiRouter && snapshot.actualService && snapshot.actualLocalPostgres).toBe(true);
    expect(snapshot.providerCalls).toBe(0);
    expect(snapshot.webSource).toMatchObject({ kind: "resume", status: "ready", selectable: true, documentId: snapshot.sourceInput.sourceDocumentId, documentVersionId: snapshot.sourceInput.sourceVersionId });
    expect(snapshot.savedWebSource).toMatchObject({ kind: "resume", status: "processing", selectable: false, documentId: saved.documentId, documentVersionId: saved.documentVersionId });
    const fetch = vi.fn(async (_url: unknown, init?: RequestInit) => fromWire(init?.method === "POST" ? responses.create : responses.capabilities));
    const client = new BackendResumeOptimizerClient("/", fetch);
    const caps = await client.capabilities(); expect(caps).toMatchObject({ enabled: true, eligible: true, dailyLimit: 1, dailyRemaining: 1, timezone: "UTC", activeJobId: null });
    const job = await client.create(responses.create.requestBody as never);
    expect(job).toMatchObject({ status: "queued", review: null, initialDraftMarkdown: null, draftMarkdown: null, savedDocumentId: null, errorMessage: null, jdDocumentId: null, jdVersionId: null });
    expect(JSON.parse(String(fetch.mock.calls[1]![1]?.body))).toEqual(responses.create.requestBody);
  });
  it("reads actual completion/revision/evidence and independent DocumentRecordResponse aliases", async () => {
    const client = new BackendResumeOptimizerClient("/", async (_url, init) => fromWire(init?.method === "POST" ? responses.saveAs : responses.completedDetail));
    const detail = await client.get(completed.jobId);
    expect(detail.revision).toBe(2); expect(detail.review!.dimensions).toHaveLength(4); expect(detail.review!.overallScore).toBe(72); expect(detail.review!.roleMatchingAssessed).toBe(false);
    for (const dimension of detail.review!.dimensions) for (const evidence of dimension.evidence) expect(detail.sourceText).toContain(evidence.quote);
    const result = await client.saveAs(detail.jobId, 3);
    expect(result.document).toMatchObject({ documentId: saved.documentId, documentVersionId: saved.documentVersionId, documentKind: "resume", status: "processing_requested" });
    expect(responses.saveAsReplay.body.data!.document.documentId).toBe(saved.documentId);
  });
  it("accepts real authenticated DOCX/PDF HTTP attachments and exact backend content types", async () => {
    for (const format of ["docx", "pdf"] as const) {
      const wire = responses[`export_${format}`];
      expect(wire.headers["cache-control"]).toBe("private, no-store");
      const client = new BackendResumeOptimizerClient("/", async () => fromWire(wire));
      const result = await client.download(completed.jobId, format, 3);
      expect(result.filename).toBe(`optimized-resume.${format}`);
      expect(result.blob.size).toBeGreaterThan(1000);
      expect(Array.from(new Uint8Array(await result.blob.slice(0, 4).arrayBuffer()))).toEqual(format === "pdf" ? [37, 80, 68, 70] : [80, 75, 3, 4]);
    }
  });
  it("gives actionable fixed-format guidance for the actual unsupported-glyph error without exposing input", async () => {
    expect(responses.exportUnavailable.status).toBe(422);
    expect(responses.exportUnavailable.body.error!.details!.errorCode).toBe("resume_optimizer_export_unavailable");
    const client = new BackendResumeOptimizerClient("/", async () => fromWire(responses.exportUnavailable));
    await expect(client.download(completed.jobId, "pdf", 4)).rejects.toMatchObject({ code: "resume_optimizer_export_unavailable", message: "We couldn’t prepare this format. Try Word, or remove unsupported characters and retry. Your saved draft is unchanged." });
  });
  it("keeps an actual completed draft and confirmation after save-as storage failure, then retries successfully", async () => {
    const state = structuredClone(syntheticState) as unknown as WebAppState;
    state.account = { ...state.account, id: "owner" }; state.librarySources = [snapshot.webSource] as unknown as WebAppState["librarySources"];
    let attempts = 0; let savedCopy = false;
    const fetch = vi.fn(async (input: unknown, init?: RequestInit) => {
      const url = new URL(String(input), "http://127.0.0.1");
      if (url.pathname.endsWith("/capabilities")) return fromWire(responses.afterCompletionCapabilities);
      if (url.pathname.endsWith("/jobs")) return fromWire(responses.list);
      if (url.pathname.endsWith("/save-as")) { attempts += 1; savedCopy = attempts > 1; return fromWire(attempts === 1 ? responses.saveAsFailure : responses.saveAs); }
      if (url.pathname.endsWith(`/jobs/${completed.jobId}`)) return fromWire(savedCopy ? responses.afterSaveAs : responses.draft);
      if (url.pathname === "/api/v1/web/state") return new Response(JSON.stringify({ success: true, data: { ...state, librarySources: [...state.librarySources, snapshot.savedWebSource] } }), { headers: { "Content-Type": "application/json" } });
      throw new Error("Unexpected synthetic request");
    });
    vi.stubGlobal("fetch", fetch);
    render(<MemoryRouter><ResumeOptimizerPage state={state} setState={vi.fn()} /></MemoryRouter>);
    await screen.findByText("Your reviews");
    const button = Array.from(document.querySelectorAll<HTMLButtonElement>(".resume-history button")).find(button => button.textContent?.includes("Ready"))!;
    fireEvent.click(button); await screen.findByText("Compare, edit and make it yours");
    expect(screen.getByText("Parsed source resume")).toBeInTheDocument();
    expect(screen.getByText("Parsed source; table layouts simplified.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /I have checked this saved draft/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Save a separate resume in Materials/ }));
    fireEvent.click(screen.getByRole("button", { name: "Save as new resume" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(screen.getByLabelText("Your optimized draft")).toHaveValue(responses.draft.body.data!.draftMarkdown);
    expect(screen.getByRole("checkbox", { name: /I have checked this saved draft/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Save a separate resume in Materials/ })).toBeChecked();
    await waitFor(() => expect(screen.getByRole("button", { name: "Save as new resume" })).toBeEnabled());
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Save as new resume" })));
    await screen.findByText(/A separate resume was saved to Materials/);
    expect(attempts).toBe(2); expect(state.librarySources).toHaveLength(1);
    const writes = fetch.mock.calls.filter(call => String(call[0]).endsWith("/save-as"));
    expect(JSON.parse(String(writes[0]![1]?.body))).toEqual(responses.saveAs.requestBody);
    expect(JSON.parse(String(writes[0]![1]?.body))).toEqual(JSON.parse(String(writes[1]![1]?.body)));
    expect(resumeOptimizerClient).toBeDefined();
  });
  it("accepts actual normalized table rows and clearly rejects unsupported markup before quota use", async () => {
    const table = responses.tableSourceCreate.body.data!;
    expect(table.sourceText).toContain("Team | Count"); expect(table.sourceText).toContain("Reports | 12"); expect(table.sourceText).not.toContain("<table");
    expect(responses.afterUnsupportedCapabilities.body.data!.dailyRemaining).toBe(1);
    expect(responses.sourceMarkupUnsupported.status).toBe(422);
    const client = new BackendResumeOptimizerClient("/", async () => fromWire(responses.sourceMarkupUnsupported));
    await expect(client.create(responses.sourceMarkupUnsupported.requestBody as never)).rejects.toMatchObject({ code: "resume_optimizer_source_markup_unsupported", message: expect.stringContaining("plain-text or Markdown") });
  });

});
