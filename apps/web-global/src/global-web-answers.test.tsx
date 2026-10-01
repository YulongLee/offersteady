import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { BackendPreviewInterviewAdapter } from "./backend-adapter";
import { syntheticState } from "../../web/src/test-state";
import { WebAnswerSources } from "./WebAnswerSources";
import { useWebAnswerControl, WebAnswerToggle } from "./WebAnswerControl";
import type { WebAppState, SubmitManualAnswerResult } from "./domain";

beforeEach(() => {
  window.localStorage.setItem("offersteady.auth.access_token", "synthetic-token");
  window.localStorage.setItem("offersteady.auth.refresh_token", "synthetic-refresh");
  window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user", displayName: "Synthetic", createdAtMs: 1, bindings: [] }));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const access = (eligible = true, available = true) => vi.stubGlobal("fetch", vi.fn(async (input: unknown) =>
  new Response(JSON.stringify(String(input).includes("/status") ? { webSearchEnabled: true, webSearchAvailable: available } : { features: { webAnswer: eligible } }),
    { headers: { "content-type": "application/json" } })));
function Control({ id = "session" }: { id?: string }) {
  const mode = useWebAnswerControl(id, false);
  return <WebAnswerToggle {...mode} onChange={mode.change} />;
}
it("does not offer an unconfigured provider even if the rollout flag is on", async () => {
  access(true, false);
  render(<Control />);
  await waitFor(() => expect(screen.getByRole("switch")).toHaveAttribute("title", "Web answers are not available in this environment"));
  expect(screen.getByRole("switch")).toBeDisabled();
});
it("starts off, gates membership, and resets on another session", async () => {
  access(false);
  const first = render(<Control />);
  await waitFor(() => expect(screen.getByRole("switch")).toHaveAttribute("title", expect.stringContaining("7 days")));
  expect(screen.getByRole("switch")).toBeDisabled();
  first.unmount();
  access();
  const { rerender } = render(<Control />);
  await waitFor(() => expect(screen.getByRole("switch")).toBeEnabled());
  expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "false");
  fireEvent.click(screen.getByRole("switch"));
  expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  rerender(<Control id="another-session" />);
  await waitFor(() => expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "false"));
});
it("renders honest fallback and rejects unsafe source URLs", () => {
  render(<WebAnswerSources provenance={{ selectionRevision: 0, usedSources: [], webSearchStatus: "fallback",
    webSources: [{ title: "Safe source", url: "https://example.invalid/docs" }, { title: "Unsafe", url: "javascript:alert(1)" }] }} />);
  expect(screen.getByRole("status")).toHaveTextContent("Web search unavailable");
  expect(screen.getByRole("link", { name: "Safe source" })).toHaveAttribute("rel", "noopener noreferrer");
  expect(screen.queryByRole("link", { name: "Unsafe" })).not.toBeInTheDocument();
});
it("sends an opt-in flag and carries server source status", async () => {
  const task = { taskId: "synthetic", sessionId: "session", ownerUserId: "user", question: "Cache?",
    answerText: "Quick Answer\nUse a cache.\n\n---\n\nDetailed Answer\nVerify eviction.", status: "completed", updatedAtMs: 5,
    webSearchStatus: "succeeded", webSources: [{ title: "Reference", url: "https://example.invalid/docs" }] };
  const fetcher = vi.fn(async () => new Response(`data: ${JSON.stringify({ type: "completed", task })}\n\n`));
  const adapter = new BackendPreviewInterviewAdapter("http://synthetic.invalid", fetcher);
  const result = await adapter.submitManualAnswer({ interviewId: "session", question: "Cache?", idempotencyKey: "synthetic", webSearchEnabled: true }, undefined, vi.fn());
  expect(JSON.parse((fetcher.mock.calls[0] as unknown as [unknown, RequestInit])[1].body as string).webSearchEnabled).toBe(true);
  expect(result.question.advice.provenance.webSearchStatus).toBe("succeeded");
  expect(result.question.advice.provenance.webSources).toEqual(task.webSources);
});
it("turning web off keeps quick text, rejects late web events and permits the next ordinary answer", async () => {
  access();
  Object.defineProperty(window, "innerWidth", { configurable: true, value: 1280 });
  vi.spyOn(interviewAppAdapter, "sendDesktopSessionHeartbeat").mockImplementation(async command => ({
    pageInstanceId: command.pageInstanceId ?? null, leaseGeneration: 1, leaseExpiresAtMs: Date.now()+60_000,
  }));
  const state = structuredClone(syntheticState) as unknown as WebAppState;
  state.interviews = state.interviews.map(item => ({ ...item, interviewLanguage: "en-US" }));
  const first: SubmitManualAnswerResult = {
    question: { id: "web-task", text: "Cache?", askedAt: "Now", input: "manual", status: "streaming", quickAnswerCompleted: true,
      advice: { outline: [], detail: "Quick Answer\nRetained quick text.", sourceTypes: [], inference: "", uncertain: false,
        provenance: { selectionRevision: 0, usedSources: [], webSearchStatus: "pending" } } },
    task: { id: "web-task", questionId: "web-task", interviewId: "demo", userId: "user", billingUsageId: "live-answer:web-task",
      question: "Cache?", revision: 1, status: "generating", partialText: "Quick Answer\nRetained quick text.", quickAnswerCompleted: true, updatedAtMs: Date.now() },
  };
  let late!: (value: Parameters<NonNullable<Parameters<typeof interviewAppAdapter.submitManualAnswer>[2]>>[0]) => void;
  let finish!: (value: SubmitManualAnswerResult) => void;
  const submit = vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockImplementationOnce((command, _signal, update) => {
    expect(command.webSearchEnabled).toBe(true);
    late = update!;
    update?.({ result: first, event: { type: "quick-completed" } });
    return new Promise(resolve => { finish = resolve; });
  }).mockImplementationOnce(async command => {
    expect(command.webSearchEnabled).toBe(false);
    return { question: { ...first.question, id: "standard-task", status: "confirmed", advice: { ...first.question.advice, detail: "New standard answer." } },
      task: { ...first.task, id: "standard-task", questionId: "standard-task", status: "completed", updatedAtMs: Date.now()+1 } };
  });
  vi.spyOn(interviewAppAdapter, "cancelAnswer").mockResolvedValue({ outcome: "cancelled", task: { ...first.task, status: "cancelled" }, billingReleased: true });
  window.history.replaceState({}, "", "/app/interviews/demo/live");
  render(<App initialAuthenticated initialState={state} />);
  const toggle = screen.getByRole("switch", { name: "Web answers" });
  await waitFor(() => expect(toggle).toBeEnabled());
  fireEvent.click(toggle);
  fireEvent.change(screen.getByRole("textbox", { name: /interviewer.*question/i }), { target: { value: "Cache?" } });
  fireEvent.click(screen.getByRole("button", { name: "Quick Answer" }));
  expect(screen.getByText("Retained quick text.")).toBeInTheDocument();
  fireEvent.click(toggle);
  await waitFor(() => expect(interviewAppAdapter.cancelAnswer).toHaveBeenCalledTimes(1));
  await act(async () => {
    const stale = { ...first, question: { ...first.question, advice: { ...first.question.advice, detail: "Late web result must not appear." } } };
    late({ result: stale, event: { type: "completed" } }); finish(stale);
  });
  expect(screen.queryByText("Late web result must not appear.")).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("textbox", { name: /interviewer.*question/i }), { target: { value: "Cache?" } });
  fireEvent.click(screen.getByRole("button", { name: "Quick Answer" }));
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("New standard answer.")).toBeInTheDocument();
});
