// Dev-only visual harness. No server mutation, real credentials or user records.
import React from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { MockInterviewPage } from "../src/MockInterviewPage";
import { authClient } from "../src/auth-client";
import "../src/styles.css";

const reportMode = new URLSearchParams(location.search).get("view") === "report";
const workbenchMode = new URLSearchParams(location.search).get("view") === "workbench";
const preparationMode = new URLSearchParams(location.search).get("view") === "preparation";
const session = { sessionId: "mock-synthetic", title: "后端工程师 · 模拟面试", targetRole: "后端工程师",
  billingClass: "daily_pass_free", refunded: false, createdAtMs: 1790340000000, resumeId: "synthetic-resume", resumeVersion: "v1",
  error: null, billableMs: 240000, billedMinutes: 0, interacting: false, partial: true,
  state: { phase: reportMode ? "completed" : preparationMode ? "preparing" : "listening", version: 3, capture_epoch: "synthetic-epoch", rounds: [{ question_id: "q1",
    question: "你在订单项目中使用了幂等设计。如果两个相同请求同时到达，你会怎样避免重复扣减库存？",
    answer: reportMode ? "我会先用业务幂等键标记请求，再利用数据库唯一约束保证并发安全。失败时返回原请求结果。" : null, submission_id: reportMode ? "a1" : null }] },
  report: reportMode ? { summary: "部分报告（已回答 1/10 题）。你能抓住并发场景的核心，可以进一步解释事务和重试之间的关系。",
    overall_score: 78, dimensions: { relevance: 85, clarity: 80, depth: 75, evidence: 72 },
    feedback: [{ question_id: "q1", answer_quote: "利用数据库唯一约束保证并发安全", strength: "使用数据库约束作为并发一致性的最后保障。",
      improvement: "尚未说明失败重试与库存更新如何放在同一个事务边界内。", suggestion: "按请求标识、事务处理、冲突返回的顺序组织回答，再补充【请补充真实例子】。" }], practice_priorities: ["准备一个真实的并发请求案例，说明失败后的恢复过程。"] } : null };
authClient.readStoredSession = () => ({ accessToken: "synthetic-preview-only", refreshToken: "synthetic", account: { id: "synthetic", displayName: "合成测试", createdAtMs: 0, bindings: [] } });
const originalFetch = window.fetch.bind(window);
window.fetch = async (input, init) => {
  const path = String(input);
  if (!path.includes("/api/v1/")) return originalFetch(input, init);
  let data: unknown;
  if (path.endsWith("/capabilities")) data = { enabled: true };
  else if (path.includes("/documents")) data = [{ documentId: "synthetic-resume", documentVersionId: "v1", displayName: "合成后端工程师简历.pdf", status: "ready", indexState: "indexed" }];
  else if (path.endsWith("/mock-synthetic")) data = session;
  else data = { sessions: [], quote: { activeTimeMember: true, dailyFreeRemaining: 2, entryPoints: 0, minutePoints: 0, billingClass: "daily_pass_free", savedCount: 0, savedLimit: 2 } };
  return new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
};
let previewSocket: { emit: (message: unknown) => void } | null = null;
// A quiet, deliberately synthetic test tone exercises the real PCM playback path.
// This is not the production TTS voice and never opens a microphone or network socket.
function syntheticQuestionAudio() {
  const samples = new Uint8Array(24000 * 2 * 5);
  const view = new DataView(samples.buffer);
  for (let index = 0; index < samples.length / 2; index++) {
    const seconds = index / 24000;
    const envelope = Math.min(1, seconds * 8, (5 - seconds) * 8) * (0.5 + 0.5 * Math.sin(seconds * 9));
    view.setInt16(index * 2, Math.round(2200 * envelope * Math.sin(2 * Math.PI * 220 * seconds)), true);
  }
  let binary = "";
  for (let offset = 0; offset < samples.length; offset += 8192) binary += String.fromCharCode(...samples.subarray(offset, offset + 8192));
  return btoa(binary);
}
function previewPhase(phase: string) {
  session.state.phase = phase;
  session.state.version++;
  previewSocket?.emit({ type: "state", session, desktopConnected: true });
}
if (workbenchMode || preparationMode) {
  class PreviewSocket {
    static OPEN = 1;
    readyState = 1;
    onopen: (() => void) | null = null;
    onmessage: ((event: { data: string }) => void) | null = null;
    onclose: (() => void) | null = null;
    constructor() { previewSocket = this; setTimeout(() => this.onopen?.(), 0); }
    emit(message: unknown) { if (this.readyState === 1) this.onmessage?.({ data: JSON.stringify(message) }); }
    send(payload: string) {
      const message = JSON.parse(payload);
      if (message.accessToken) setTimeout(() => this.emit({ type: "state", session, desktopConnected: true, microphoneConnected: !preparationMode }), 0);
      if (message.action === "speak") {
        this.emit({ type: "audio", questionId: "q1", pcm: syntheticQuestionAudio() });
        this.emit({ type: "audio_end", questionId: "q1" });
      }
      if (message.action === "listen") previewPhase("listening");
      if (message.action === "pause") previewPhase("paused");
      if (message.action === "resume") previewPhase("listening");
      if (message.action === "replay") previewPhase("speaking");
    }
    close() { this.readyState = 3; previewSocket = null; this.onclose?.(); }
  }
  window.WebSocket = PreviewSocket as unknown as typeof WebSocket;
}
const entry = reportMode || workbenchMode || preparationMode ? "/app/mock-interviews/mock-synthetic" : "/app/mock-interviews";
createRoot(document.getElementById("root")!).render(<><div style={{ padding: "12px 24px", color: "#e5c38c", background: "#292217", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}><span>本地合成界面验收 · 不连接生产服务，不计费</span>{workbenchMode && <><button className="button" onClick={() => { previewPhase("listening"); previewPhase("speaking"); }}>播放声波演示（合成测试音）</button><button className="button" onClick={() => previewPhase("paused")}>停止演示</button><small>仅演示声波，非正式面试官语音</small></>}</div><MemoryRouter initialEntries={[entry]}><Routes><Route path="/app/mock-interviews" element={<MockInterviewPage />} /><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter></>);
