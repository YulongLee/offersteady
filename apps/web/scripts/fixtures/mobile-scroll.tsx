// Isolated browser review only. This file is never an application entry point.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AnswerWorkspace } from "../../src/AnswerWorkspace";
import { ConversationMonitor } from "../../src/ConversationMonitor";
import { MobileInterviewControls } from "../../src/MobileInterviewControls";
import { MockInterviewPage } from "../../src/MockInterviewPage";
import type { MockSession } from "../../src/mock-interview-client";
import { syntheticState } from "../../src/test-state";
import "../../src/styles.css";

const noop = () => undefined;
const sample = syntheticState.speaker.transcripts[0]!;
const turn = (index: number) => ({
  ...sample, id: `scroll-turn-${index}`, utteranceId: `scroll-utterance-${index}`,
  role: index % 2 ? "candidate" as const : "interviewer" as const,
  sourceKind: index % 2 ? "microphone" as const : "system" as const,
  text: `合成对话 ${index + 1}。请结合需求说明设计方法、验证结果和下一步改进。`,
  startedAtMs: index * 10_000, endedAtMs: index * 10_000 + 5_000,
  revision: 1, isFinal: true,
});
const initialState = {
  ...structuredClone(syntheticState),
  speaker: { ...syntheticState.speaker, transcripts: Array.from({ length: 60 }, (_, i) => turn(i)), pendingQuestion: null },
};
const answer = {
  ...syntheticState.questions[0]!, id: "scroll-answer", status: "confirmed" as const,
  advice: { ...syntheticState.questions[0]!.advice,
    detail: Array.from({ length: 60 }, (_, i) => `第 ${i + 1} 段合成回答。先明确目标，再验证边界条件，最后检查实际结果。`).join("\n\n"),
  },
};

function LiveFixture() {
  const [panel, setPanel] = useState("answer");
  const [state, setState] = useState(initialState);
  const [draft, setDraft] = useState("");
  return <main className="live-page focused-live-page mobile-live-page">
    <header className="live-top"><span>返回</span><div className="live-session-heading"><strong>合成手机滚动检查</strong></div><button id="append-turn" onClick={() => setState(previous => ({
      ...previous, speaker: { ...previous.speaker, transcripts: [...previous.speaker.transcripts, turn(previous.speaker.transcripts.length)] },
    }))}>新增转写</button></header>
    <div className="mobile-live-workspace">
      <nav className="mobile-live-tabs" role="tablist">
        <button role="tab" aria-selected={panel === "answer"} onClick={() => setPanel("answer")}>回答</button>
        <button role="tab" aria-selected={panel === "conversation"} onClick={() => setPanel("conversation")}>对话</button>
      </nav>
      <section className={`mobile-live-panel ${panel}`} role="tabpanel">
        {panel === "answer"
          ? <AnswerWorkspace answers={[answer]} viewingAnswerId={null} activeTask={null} newAnswerAvailable={false} cancelling={false} cancelError="" onView={noop} onRetry={noop} onStop={noop} />
          : <ConversationMonitor state={state} onConfirmQuestion={noop} onDismissQuestion={noop} />}
      </section>
      <MobileInterviewControls manualDraft={draft} screenshotTask={null} onChange={setDraft} onQuickAnswer={noop} onScreenshot={noop} />
    </div>
  </main>;
}

const scenario = new URLSearchParams(location.search).get("scenario") ?? "live";
const mockSession: MockSession = {
  sessionId: "scroll-mock", title: "合成模拟面试", targetRole: "开发工程师", billingClass: "daily_pass_free",
  refunded: false, createdAtMs: 1, resumeId: null, resumeVersion: null, error: null,
  billableMs: 0, billedMinutes: 0, interacting: false, partial: true,
  state: { phase: scenario === "mock-report" ? "completed" : scenario === "mock-prepare" ? "preparing" : "listening",
    version: 1, capture_epoch: null, rounds: Array.from({ length: scenario === "mock-report" ? 10 : 1 }, (_, i) => ({
      question_id: `mock-q${i}`, question: "请介绍你会如何验证手机页面的滚动和主要操作？",
      answer: "合成回答。明确测试范围，覆盖视口和长内容，检查内容末尾和操作可达性。".repeat(12), submission_id: `mock-a${i}`,
    })),
  },
  report: { summary: "合成练习报告。", overall_score: 80, dimensions: { clarity: 80 }, feedback: [], practice_priorities: ["继续练习"] },
};
// No API, audio, model or payment requests leave this fixture.
window.fetch = async input => {
  const path = new URL(input instanceof Request ? input.url : String(input), location.origin).pathname;
  const data = path.endsWith("/capabilities") ? { enabled: true }
    : path === "/api/v1/mock-interviews/scroll-mock" ? mockSession
      : path === "/api/v1/documents" ? [] : undefined;
  if (data === undefined) throw new Error(`Unexpected review request: ${path}`);
  return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
};

createRoot(document.getElementById("root")!).render(scenario === "live" ? <LiveFixture />
  : <MemoryRouter initialEntries={["/app/mock-interviews/scroll-mock"]}><div className="app-shell"><div className="app-content">
    <Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes>
  </div></div></MemoryRouter>);
