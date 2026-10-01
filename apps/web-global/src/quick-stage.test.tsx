import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { syntheticState } from "../../web/src/test-state";
import { AnswerWorkspace } from "./AnswerWorkspace";
import { BackendPreviewInterviewAdapter } from "./backend-adapter";
import { mergeAnswerTask, reconcileAnswerWorkspace } from "./live-workspace";
import type { InterviewQuestion, WebAppState, SubmitManualAnswerResult } from "./domain";
import type { AnswerTaskSnapshot } from "@offersteady/protocol";

const question: InterviewQuestion = {
  id: "synthetic", askedAt: "Now", text: "How do you design a cache?", input: "manual",
  status: "streaming", quickAnswerCompleted: true,
  advice: { outline: [], detail: "Quick Answer\n**Use a bounded cache.**", sourceTypes: [], inference: "", uncertain: false,
    provenance: { selectionRevision: 0, usedSources: [], sourceCount: 0, noPersonalMaterialUsed: true } },
};
const task: AnswerTaskSnapshot = {
  id: "synthetic", questionId: "synthetic", interviewId: "session", userId: "user", billingUsageId: "usage",
  question: question.text, revision: 1, status: "generating", partialText: question.advice.detail,
  quickAnswerCompleted: true, updatedAtMs: 5,
};
const props = { answers: [question], viewingAnswerId: null, newAnswerAvailable: false, activeTask: task,
  cancelling: false, cancelError: "", interviewLanguage: "en-US" as const, onView: vi.fn(), onRetry: vi.fn(), onStop: vi.fn() };

it("finishes quick formatting while detail is still busy", () => {
  const { container } = render(<AnswerWorkspace {...props} />);
  expect(container.querySelector(".simple-answer")).toHaveAttribute("aria-busy", "false");
  expect(container.querySelector(".simple-answer strong")).toHaveTextContent("Use a bounded cache.");
  expect(container.querySelector(".detailed-answer")).toHaveAttribute("aria-busy", "true");
  expect(screen.getByText("Quick answer complete · Adding detail")).toBeInTheDocument();
});

it.each(["failed", "cancelled"] as const)("retains completed quick text when detail is %s", status => {
  render(<AnswerWorkspace {...props} answers={[{ ...question, status }]} activeTask={{ ...task, status }} />);
  expect(screen.getByText("Use a bounded cache.")).toBeInTheDocument();
  if (status === "failed") expect(screen.getByText("Detailed answer failed; quick answer retained")).toBeInTheDocument();
});

it("keeps quick completion on stale snapshots, but not a different task", () => {
  const stale = { ...task, quickAnswerCompleted: false, updatedAtMs: 4 };
  expect(mergeAnswerTask(task, stale)?.quickAnswerCompleted).toBe(true);
  expect(mergeAnswerTask(task, { ...stale, id: "next", questionId: "next", updatedAtMs: 6 })?.quickAnswerCompleted).toBe(false);
  const merged = reconcileAnswerWorkspace({ questions: [question], activeAnswerTask: task },
    { questions: [{ ...question, quickAnswerCompleted: false }], activeAnswerTask: stale });
  expect(merged.questions[0]?.quickAnswerCompleted).toBe(true);
});

beforeEach(() => {
  window.localStorage.setItem("offersteady.auth.access_token", "synthetic-token");
  window.localStorage.setItem("offersteady.auth.refresh_token", "synthetic-refresh");
  window.localStorage.setItem("offersteady.auth.account", JSON.stringify({ id: "user", displayName: "Synthetic", createdAtMs: 1, bindings: [] }));
});

afterEach(() => vi.restoreAllMocks());

it.each([1280, 390])("retains quick text after detail disconnect in the live page at %s px", async width => {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  let rejectDetail!: (error: Error) => void;
  const result: SubmitManualAnswerResult = { question, task: { ...task, updatedAtMs: Date.now() } };
  vi.spyOn(interviewAppAdapter, "submitManualAnswer").mockImplementation((_command, _signal, update) => {
    update?.({ result, event: { type: "quick-completed" } });
    return new Promise((_resolve, reject) => { rejectDetail = reject; });
  });
  const state = structuredClone(syntheticState) as unknown as WebAppState;
  state.interviews = state.interviews.map(item => ({ ...item, interviewLanguage: "en-US" }));
  window.history.replaceState({}, "", "/app/interviews/demo/live");
  const { container } = render(<App initialAuthenticated initialState={state} />);
  fireEvent.change(screen.getByRole("textbox", { name: /interviewer.*question/i }), { target: { value: question.text } });
  fireEvent.click(screen.getByRole("button", { name: "Quick Answer" }));
  expect(container.querySelector(".simple-answer")).toHaveAttribute("aria-busy", "false");
  expect(container.querySelector(".detailed-answer")).toHaveAttribute("aria-busy", "true");
  await act(async () => rejectDetail(new Error("Synthetic detail interruption")));
  expect(screen.getByText("Detailed answer failed; quick answer retained")).toBeInTheDocument();
  expect(container.querySelector(".simple-answer strong")).toHaveTextContent("Use a bounded cache.");
  expect(container.querySelector('.answer-workspace [aria-busy="true"]')).not.toBeInTheDocument();
});

it.each([false, true])("carries the new field and recognizes stream completion: %s", async terminal => {
  const eventTask = { taskId: "synthetic", sessionId: "session", ownerUserId: "user", question: question.text,
    answerText: question.advice.detail, quickAnswerCompleted: true, status: "streaming", updatedAtMs: 5 };
  const events = [{ type: "quick-completed", task: eventTask }, ...(terminal ? [{ type: "completed", task: { ...eventTask, status: "completed" } }] : [])];
  const fetcher = vi.fn(async () => new Response(events.map(event => `data: ${JSON.stringify(event)}\n\n`).join(""), { status: 200 }));
  const adapter = new BackendPreviewInterviewAdapter("http://synthetic.invalid", fetcher);
  const update = vi.fn();
  const result = adapter.submitManualAnswer({ interviewId: "session", question: question.text, idempotencyKey: "synthetic" }, undefined, update);
  if (terminal) await expect(result).resolves.toHaveProperty("task.status", "completed");
  else await expect(result).rejects.toThrow("stream was interrupted");
  expect(update.mock.calls[0]?.[0].result.question.quickAnswerCompleted).toBe(true);
  expect(update.mock.calls[0]?.[0].result.task.quickAnswerCompleted).toBe(true);
});
