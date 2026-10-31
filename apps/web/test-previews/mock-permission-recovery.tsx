// Test-only entry, excluded from production Vite inputs. No real network, microphone or playback.
import "../src/legacy-browser-polyfills";
import "../src/styles.css";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { authClient } from "../src/auth-client";
import { MockInterviewPage } from "../src/MockInterviewPage";
import type { MockSession } from "../src/mock-interview-client";

const row: MockSession = {
  sessionId: "synthetic-mock-permission", title: "模拟面试 · 权限恢复测试", targetRole: "后端开发",
  billingClass: "daily_pass_free", refunded: false, createdAtMs: 1793318400000,
  resumeId: "synthetic-resume", resumeVersion: "synthetic-v1", error: null,
  billableMs: 0, billedMinutes: 0, interacting: false, partial: true, report: null,
  durationLimitMinutes: 60, startedAtMs: null, deadlineAtMs: null,
  state: { phase: "preparing", version: 1, rounds: [], capture_epoch: null },
};
let permission = "unknown";
const actions: string[] = [];
const receipt = () => {
  document.getElementById("qa-receipt")!.textContent = JSON.stringify({
    syntheticOnly: true, permission, sessionId: row.sessionId,
    selectedResume: row.resumeId, providerCalls: 0, actualAudioCalls: 0, actions,
  }, null, 2);
};
// In-memory synthetic auth only: never inspect or replace the user's stored account.
authClient.readStoredSession = () => ({ accessToken: "synthetic-local-only", refreshToken: "synthetic-local-only",
  account: { id: "synthetic-owner", displayName: "合成测试账号", createdAtMs: 1, bindings: [] } });
globalThis.fetch = async (input, init) => {
  const url = new URL(String(input), location.origin);
  if (!([location.origin, "http://127.0.0.1:8000"].includes(url.origin))) throw new Error("Synthetic preview blocks external requests.");
  const method = init?.method ?? "GET";
  const path = url.pathname;
  let data: unknown;
  if (method === "GET" && path === "/api/v1/mock-interviews/capabilities") data = { enabled: true };
  else if (method === "GET" && path === `/api/v1/mock-interviews/${row.sessionId}`) data = row;
  else if (method === "GET" && path === "/api/v1/documents") data = [{ documentId: "synthetic-resume", displayName: "合成测试简历.pdf", documentVersionId: "synthetic-v1", status: "ready", indexState: "indexed" }];
  else throw new Error("Synthetic preview blocks this API operation.");
  return new Response(JSON.stringify({ success: true, data, error: null, requestId: "synthetic-local", meta: { apiVersion: "v1", timestamp: "2026-10-30T00:00:00Z" } }), { headers: { "Content-Type": "application/json" } });
};
const sockets = new Set<SyntheticSocket>();
class SyntheticSocket {
  static OPEN = 1;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  private timer: ReturnType<typeof setTimeout>;
  constructor(_url: string) {
    sockets.add(this);
    this.timer = setTimeout(() => this.onopen?.(), 10);
  }
  emit() {
    if (this.readyState !== 1) return;
    const ready = permission === "granted";
    const code = ready ? "mock_ready" : permission === "denied" ? "mock_microphone_required" : permission === "offline" ? "mock_desktop_unavailable" : "mock_microphone_checking";
    const message = ready ? "助手已就绪，可以开始模拟面试。" : permission === "denied" ? "助手当前上报麦克风权限未开启。请在系统设置中允许麦克风后重新检查。" : permission === "offline" ? "请先连接在线的桌面助手。" : "正在检查麦克风，请保持助手运行，等待权限状态同步。";
    this.onmessage?.({ data: JSON.stringify({ type: "state", session: row, desktopConnected: ready,
      microphoneConnected: false, preparation: { ready, code, message } }) });
  }
  send(raw: string) {
    const message = JSON.parse(raw);
    if (message.accessToken) { this.emit(); return; }
    actions.push(String(message.action)); receipt();
    if (message.action === "heartbeat") this.emit();
    // Intentionally do not generate questions, capture, charge or contact services.
  }
  close() { clearTimeout(this.timer); this.readyState = 3; sockets.delete(this); this.onclose?.(); }
}
globalThis.WebSocket = SyntheticSocket as unknown as typeof WebSocket;
globalThis.AudioContext = class {
  state = "suspended";
  onstatechange: (() => void) | null = null;
  async resume() { this.state = "running"; this.onstatechange?.(); }
  async close() { this.state = "closed"; }
} as unknown as typeof AudioContext;
document.querySelectorAll<HTMLButtonElement>("[data-permission]").forEach(button => button.addEventListener("click", () => {
  permission = button.dataset.permission!;
  sockets.forEach(socket => socket.emit()); receipt();
}));
receipt();
createRoot(document.getElementById("root")!).render(<MemoryRouter initialEntries={[`/app/mock-interviews/${row.sessionId}`]}><Routes><Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} /></Routes></MemoryRouter>);
