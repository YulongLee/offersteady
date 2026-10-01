import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { LibraryManager } from "./LibraryManager";
import { syntheticState } from "../../web/src/test-state";
import type { WebAppState } from "./domain";
import { materialUploadAdapter } from "./material-upload-adapter";
import { interviewAppAdapter } from "./app-adapter";

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });
it("does not begin polling when a retry completes after leaving the page", async () => {
  vi.useFakeTimers();
  const state = structuredClone(syntheticState) as unknown as WebAppState;
  state.knowledgeDocuments = state.knowledgeDocuments.slice(0, 1).map(doc => ({ ...doc, status: "failed" as const }));
  let resolveRetry!: (value: never) => void;
  vi.spyOn(materialUploadAdapter, "retryDocument").mockImplementation(() => new Promise(resolve => { resolveRetry = resolve; }));
  const load = vi.spyOn(interviewAppAdapter, "loadState").mockResolvedValue(state);
  const view = render(<MemoryRouter><LibraryManager state={state} setState={vi.fn()} /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Process again" }));
  view.unmount();
  await act(async () => { resolveRetry(undefined as never); await vi.advanceTimersByTimeAsync(100000); });
  expect(load).not.toHaveBeenCalled();
});
it("aborts an in-flight processing refresh and stops requests when the library closes", async () => {
  vi.useFakeTimers();
  const state = structuredClone(syntheticState) as unknown as WebAppState;
  state.knowledgeDocuments = state.knowledgeDocuments.slice(0, 1).map(doc => ({ ...doc, status: "failed" as const }));
  state.librarySources = [];
  vi.spyOn(materialUploadAdapter, "retryDocument").mockResolvedValue(undefined as never);
  let requestSignal: AbortSignal | undefined;
  let resolveLoad!: (state: WebAppState) => void;
  const load = vi.spyOn(interviewAppAdapter, "loadState").mockImplementation(signal => { requestSignal = signal; return new Promise(resolve => { resolveLoad = resolve; }); });
  function Harness() { const [current, setState] = useState(state); return <MemoryRouter><LibraryManager state={current} setState={setState} /></MemoryRouter>; }
  const view = render(<Harness />);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Process again" })); });
  await act(async () => { await vi.advanceTimersByTimeAsync(800); });
  expect(load).toHaveBeenCalledTimes(1);
  expect(requestSignal?.aborted).toBe(false);
  view.unmount();
  expect(requestSignal?.aborted).toBe(true);
  await act(async () => { resolveLoad(state); await vi.advanceTimersByTimeAsync(100000); });
  expect(load).toHaveBeenCalledTimes(1);
});
