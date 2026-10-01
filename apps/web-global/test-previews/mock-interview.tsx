// Development-only visual fixture. No microphone, production API, account or charge.
import { createRoot } from "react-dom/client";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { MockInterviewPage } from "../src/MockInterviewPage";
import { authClient } from "../src/auth-client";
import "../src/styles.css";

const view = new URLSearchParams(location.search).get("view");
const session = { sessionId: "synthetic", title: "Backend Engineer · Mock interview", targetRole: "Backend Engineer",
  billingClass: "daily_pass_free", refunded: false, createdAtMs: 1790654400000, resumeId: "synthetic-resume", resumeVersion: "v1",
  error: null, billableMs: 60000, billedMinutes: 0, interacting: false, partial: true,
  state: { phase: view === "report" ? "completed" : view === "preparation" ? "preparing" : "listening",
    version: 3, capture_epoch: "synthetic-epoch", rounds: [{ question_id: "q1",
      question: "Your resume mentions an ordering service. How would you prevent duplicate writes when two identical requests arrive together?",
      answer: "I would use a business idempotency key and a database unique constraint, then return the original result on retry.", submission_id: "a1" }] },
  report: { summary: "Partial report (1/10 questions answered). You identified a concurrency safeguard. Explain how the transaction and retry policy work together.",
    overall_score: 78, dimensions: { relevance: 85, clarity: 80, depth: 75, evidence: 72 },
    feedback: [{ question_id: "q1", answer_quote: "a database unique constraint", strength: "Names a concrete concurrency safeguard.",
      improvement: "Explain the transaction boundary and failure recovery.", suggestion: "Add [your actual responsibility], [specific steps], and [verified results]. Do not invent metrics." }],
    practice_priorities: ["Describe a real concurrency example and its failure recovery."] } };
authClient.readStoredSession = () => ({ accessToken: "synthetic-only", refreshToken: "synthetic",
  account: { id: "synthetic", displayName: "Synthetic", createdAtMs: 0, bindings: [] } });
window.fetch = async input => {
  const path = String(input);
  const data = path.endsWith("/capabilities") ? { enabled: true }
    : path.includes("/documents") ? [{ documentId: "synthetic-resume", documentVersionId: "v1", displayName: "Synthetic resume.pdf", status: "ready", indexState: "indexed" }]
    : path.endsWith("/synthetic") ? session
    : { sessions: [], quote: { eligible: true, activeTimeMember: true, dailyLimit: 3, timezone: "UTC",
        dailyFreeRemaining: 2, entryPoints: 0, minutePoints: 0, billingClass: "daily_pass_free", savedCount: 0, savedLimit: 2 } };
  return new Response(JSON.stringify(data), { headers: { "content-type": "application/json" } });
};
class SyntheticSocket {
  static OPEN = 1; readyState = 1;
  onopen: (() => void) | null = null; onmessage: ((event: { data: string }) => void) | null = null;
  constructor() { setTimeout(() => this.onopen?.(), 0); }
  send(payload: string) { if (JSON.parse(payload).accessToken) setTimeout(() => {
    if (this.readyState === 1) this.onmessage?.({ data: JSON.stringify({ type: "state", session, desktopConnected: true, microphoneConnected: true,
      preparation: { ready: true, code: "mock_ready" } }) });
  }, 0); }
  close() { this.readyState = 3; }
}
window.WebSocket = SyntheticSocket as unknown as typeof WebSocket;
const entry = view ? "/app/mock-interviews/synthetic" : "/app/mock-interviews";
createRoot(document.getElementById("root")!).render(<>
  <div style={{ padding: "12px 24px", color: "#e5c38c", background: "#292217" }}>Synthetic preview · No production connection or charge</div>
  <MemoryRouter initialEntries={[entry]}><Routes>
    <Route path="/app/mock-interviews" element={<MockInterviewPage />} />
    <Route path="/app/mock-interviews/:id" element={<MockInterviewPage />} />
  </Routes></MemoryRouter>
</>);
