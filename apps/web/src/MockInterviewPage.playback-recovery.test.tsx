import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { MockInterviewPage } from "./MockInterviewPage";
import { authClient } from "./auth-client";
import { mockRequest, type MockSession } from "./mock-interview-client";

vi.mock("./mock-interview-client", async original => ({
  ...await original<typeof import("./mock-interview-client")>(), mockRequest: vi.fn(),
}));
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it("pauses interrupted queued audio and recovers the same question without automatic listening", async () => {
  let context: any;
  const sources: any[] = [];
  vi.stubGlobal("requestAnimationFrame", vi.fn(() => 1));
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  vi.stubGlobal("AudioContext", class {
    state = "running"; currentTime = 1; destination = {}; onstatechange: (() => void) | null = null;
    resume = vi.fn(async () => { this.state = "running"; this.onstatechange?.(); });
    close = vi.fn(async () => { this.state = "closed"; });
    createAnalyser = () => ({ fftSize: 0, getFloatTimeDomainData: vi.fn(), disconnect: vi.fn() });
    createBuffer = (_c: number, length: number, rate: number) => ({ duration: length / rate, getChannelData: () => new Float32Array(length) });
    createBufferSource = () => {
      const source = { buffer: null, onended: null, connect: vi.fn(), disconnect: vi.fn(), start: vi.fn(), stop: vi.fn() };
      sources.push(source); return source;
    };
    constructor() { context = this; }
  });
  const sockets: any[] = [];
  vi.stubGlobal("WebSocket", class {
    static OPEN = 1; readyState = 1; onmessage: any; onopen: any; onclose: any;
    send = vi.fn(); close = vi.fn(); constructor() { sockets.push(this); }
  });
  vi.spyOn(authClient, "readStoredSession").mockReturnValue({ accessToken: "synthetic", account: { id: "synthetic" } } as ReturnType<typeof authClient.readStoredSession>);
  const row: MockSession = { sessionId: "synthetic", title: "合成播放恢复", targetRole: "", billingClass: "points", refunded: false,
    createdAtMs: 1, resumeId: "synthetic-resume", resumeVersion: "v1", error: null, billableMs: 0, billedMinutes: 0, interacting: false, partial: true, report: null,
    state: { phase: "speaking", version: 4, capture_epoch: null, rounds: [{ question_id: "q1", question: "合成问题", answer: null, submission_id: null }] } };
  vi.mocked(mockRequest).mockImplementation(async path => path.endsWith("capabilities") ? { enabled: true } : row);
  render(<MemoryRouter initialEntries={["/app/mock-interviews/synthetic"]}><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
  await waitFor(() => expect(sockets).toHaveLength(1));
  const emit = (message: object) => act(() => sockets[0].onmessage({ data: JSON.stringify(message) }));
  const state = (phase: MockSession["state"]["phase"], version: number) => emit({ type: "state", session: { ...row, state: { ...row.state, phase, version } }, desktopConnected: true, microphoneConnected: true });
  const commands = () => sockets[0].send.mock.calls.map(([raw]: [string]) => JSON.parse(raw).action);
  state("speaking", 4);
  await waitFor(() => expect(commands()).toEqual(["speak"]));
  emit({ type: "audio", questionId: "q1", pcm: "AAA=" });
  emit({ type: "audio_end", questionId: "q1" });
  const oldEnded = sources[0].onended;
  vi.useFakeTimers();
  act(() => { context.state = "suspended"; context.onstatechange(); context.onstatechange(); });
  expect(commands()).toEqual(["speak", "playback_started", "pause"]);
  expect(sources[0].stop).toHaveBeenCalledOnce();
  expect(sources[0].buffer).toBeNull();
  state("paused", 5);
  expect(screen.getByRole("status", { name: "网页声音状态" })).toHaveTextContent("请点击继续本题后恢复朗读");
  act(() => { oldEnded?.(); vi.advanceTimersByTime(10_000); });
  expect(commands()).not.toContain("listen");
  fireEvent.click(screen.getByRole("button", { name: "继续本题" }));
  state("speaking", 6);
  await act(async () => {});
  expect(commands()).toEqual(["speak", "playback_started", "pause", "resume", "speak"]);
  expect(screen.queryByRole("status", { name: "网页声音状态" })).not.toBeInTheDocument();
});
