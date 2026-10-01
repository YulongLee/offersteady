import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { authClient } from "./auth-client";
import { globalApiErrorMessage } from "./global-errors";
import { mockPreparationMessage } from "./mock-interview-errors";
import { mockRequest, mockSocketUrl, MockVoicePlayer, type MockQuote, type MockResume, type MockSession } from "./mock-interview-client";
import { MockPlaybackIndicator } from "./MockPlaybackIndicator";
import { mockReportDimensionLabels as labels, mockReportDisclosure } from "./mock-interview-report";
import "./mock-interview.css";

export const mockPhaseLabel: Record<MockSession["state"]["phase"], string> = {
  preparing: "Preparation", generating_question: "Preparing your next question", speaking: "Listen to the interviewer",
  listening: "Your turn to answer", paused: "Paused", generating_report: "Preparing your report", completed: "Practice complete",
};
const errorText = (error: unknown) => error instanceof Error ? error.message : "This action is temporarily unavailable. Please try again.";
export function MockInterviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<MockSession[]>([]);
  const [quote, setQuote] = useState<MockQuote | null>(null);
  const [session, setSession] = useState<MockSession | null>(null);
  const [resumes, setResumes] = useState<MockResume[]>([]);
  const [target, setTarget] = useState("");
  const [machineCode, setMachineCode] = useState("");
  const [desktopConnected, setDesktopConnected] = useState(false);
  const [preparation, setPreparation] = useState<{ ready: boolean; code: string; message: string } | null>(null);
  const [bindingNotice, setBindingNotice] = useState("");
  const [waitingForMicrophone, setWaitingForMicrophone] = useState(false);
  const [settlingAudio, setSettlingAudio] = useState(false);
  const settleTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const microphoneReady = useRef(false);
  const pendingListen = useRef<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [draft, setDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [playing, setPlaying] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const current = useRef<MockSession | null>(null);
  const edited = useRef(false);
  const draftText = useRef("");
  const capturePrefix = useRef("");
  const voice = useRef(new MockVoicePlayer());
  const createKey = useRef<string | null>(null);
  const answerId = useRef<string | null>(null);
  const playingQuestion = useRef<string | null>(null);
  const playbackAcknowledged = useRef(false);
  const [reconnect, setReconnect] = useState(0);

  const update = (row: MockSession) => {
    const old = current.current;
    if (old?.state.rounds.at(-1)?.question_id !== row.state.rounds.at(-1)?.question_id) {
      setDraft(""); edited.current = false; setEditing(false); answerId.current = null;
      draftText.current = ""; capturePrefix.current = "";
    }
    if (row.state.capture_epoch && row.state.capture_epoch !== old?.state.capture_epoch) {
      // A pause/replay opens a fresh ASR epoch, not a fresh answer. Preserve the
      // confirmed-on-screen draft while avoiding duplicate partial appends.
      capturePrefix.current = draftText.current;
    }
    if (row.state.phase !== "speaking") {
      voice.current.stop(); setPlaying(false); playingQuestion.current = null;
      pendingListen.current = null; setWaitingForMicrophone(false);
      clearTimeout(settleTimer.current); setSettlingAudio(false);
    }
    current.current = row;
    setSession(row);
  };

  const command = (action: string, extra: Record<string, unknown> = {}) => {
    const row = current.current;
    if (!row || socket.current?.readyState !== WebSocket.OPEN) { setError("Connection lost. Reconnect before continuing."); return; }
    setError("");
    socket.current.send(JSON.stringify({ action, version: row.state.version,
      ...(["listen", "replay", "speak", "playback_started", "playback_waiting", "submit"].includes(action) ? { questionId: row.state.rounds.at(-1)?.question_id } : {}), ...extra }));
  };
  const beginListening = (questionId: string) => {
    if (current.current?.state.phase !== "speaking" || current.current.state.rounds.at(-1)?.question_id !== questionId) return;
    pendingListen.current = questionId;
    setWaitingForMicrophone(!microphoneReady.current);
    if (microphoneReady.current) {
      pendingListen.current = null;
      command("listen");
    }
  };
  const prepareListening = (questionId: string) => {
    // The shipped companion's VAD can retain an utterance tail for 1200 ms.
    // Let that segment close before inviting a new answer; no minute clock is
    // active during this transition. Do not change the companion's VAD itself.
    clearTimeout(settleTimer.current);
    pendingListen.current = null;
    setSettlingAudio(true);
    if (playbackAcknowledged.current) { playbackAcknowledged.current = false; command("playback_waiting"); }
    settleTimer.current = setTimeout(() => {
      setSettlingAudio(false);
      beginListening(questionId);
    }, 1500);
  };
  voice.current.onIdle = () => {
    if (playbackAcknowledged.current && current.current?.state.phase === "speaking") {
      playbackAcknowledged.current = false;
      command("playback_waiting");
    }
  };

  const reload = async () => {
    const data = await mockRequest<{ sessions: MockSession[]; quote: MockQuote }>("/mock-interviews");
    setSessions(data.sessions); setQuote(data.quote);
  };

  useEffect(() => {
    let disposed = false;
    void mockRequest<{ enabled: boolean }>("/mock-interviews/capabilities").then(async capability => {
      if (disposed) return;
      if (disposed) return;
      setEnabled(capability.enabled);
      if (!capability.enabled) return;
      if (id) {
        const row = await mockRequest<MockSession>(`/mock-interviews/${encodeURIComponent(id)}`);
        if (disposed) return;
        update(row);
        if (row.state.phase === "preparing") {
          const docs = await mockRequest<MockResume[]>("/documents?documentKind=resume");
          if (!disposed) setResumes(docs.filter(doc => doc.status === "ready" && doc.indexState === "indexed" && doc.documentVersionId));
        }
      } else {
        const data = await mockRequest<{ sessions: MockSession[]; quote: MockQuote }>("/mock-interviews");
        if (!disposed) { setSessions(data.sessions); setQuote(data.quote); }
      }
    }).catch(cause => { if (!disposed) setError(errorText(cause)); });
    return () => { disposed = true; current.current = null; setSession(null); };
  }, [id]);

  const needsConnection = Boolean(id && session && session.state.phase !== "completed");
  useEffect(() => {
    if (!id || !needsConnection) return;
    const auth = authClient.readStoredSession();
    if (!auth) { setError("Please sign in again."); return; }
    let disposed = false;
    let heartbeat: ReturnType<typeof setInterval> | undefined;
    const connection = new WebSocket(mockSocketUrl(id));
    socket.current = connection;
    connection.onopen = () => {
      connection.send(JSON.stringify({ accessToken: auth.accessToken }));
      heartbeat = setInterval(() => {
        if (connection.readyState === WebSocket.OPEN) connection.send(JSON.stringify({ action: "heartbeat" }));
      }, 5000);
    };
    connection.onmessage = event => {
      if (disposed) return;
      try {
        const message = JSON.parse(String(event.data));
        if (message.type === "state") {
          const previousPhase = current.current?.state.phase;
          microphoneReady.current = (message.microphoneConnected ?? message.desktopConnected) === true;
          setPreparation(message.preparation ?? null);
          setBindingNotice("");
          setConnected(true); setDesktopConnected(message.desktopConnected === true); update(message.session);
          if (pendingListen.current && microphoneReady.current) beginListening(pendingListen.current);
          if (message.session.state.phase === "speaking" && previousPhase !== "speaking") {
            voice.current.stop(); playbackAcknowledged.current = false;
            playingQuestion.current = message.session.state.rounds.at(-1)?.question_id ?? null;
            void voice.current.unlock().then(() => { if (!disposed) command("speak"); }).catch(cause => setError(errorText(cause)));
          }
        } else if (message.type === "transcript") {
          if (!edited.current && message.epoch === current.current?.state.capture_epoch) {
            draftText.current = [capturePrefix.current, String(message.text)].filter(Boolean).join(" ").slice(0, 8000);
            setDraft(draftText.current);
          }
        } else if (message.type === "audio" && message.questionId === playingQuestion.current) {
          voice.current.append(message.pcm);
          if (!playbackAcknowledged.current) {
            playbackAcknowledged.current = true;
            command("playback_started");
          }
          setPlaying(true);
        } else if (message.type === "audio_end" && message.questionId === playingQuestion.current) {
          voice.current.finish(() => {
            setPlaying(false);
            if (!disposed) prepareListening(message.questionId);
          });
        } else if (message.type === "error" || message.type === "speech_unavailable") {
          setError(message.type === "speech_unavailable" ? "Voice playback is unavailable. Retry or read the question and choose Ready to answer." : globalApiErrorMessage(message.code, 400)); setBusy(false);
          if (message.type === "speech_unavailable") { voice.current.stop(); setPlaying(false); }
        }
      } catch (cause) { voice.current.stop(); setPlaying(false); setError(errorText(cause)); command("pause"); }
    };
    connection.onclose = () => {
      if (disposed) return;
      clearInterval(heartbeat); clearTimeout(settleTimer.current); voice.current.close(); setSettlingAudio(false);
      microphoneReady.current = false; pendingListen.current = null; setWaitingForMicrophone(false);
      if (!disposed) { setConnected(false); setPlaying(false); setError("Connection lost. Microphone capture is paused. Please reconnect."); }
    };
    return () => { disposed = true; clearInterval(heartbeat); clearTimeout(settleTimer.current); voice.current.close(); connection.close(); socket.current = null; microphoneReady.current = false; pendingListen.current = null; setConnected(false); };
  }, [id, needsConnection, reconnect]);

  const action = async (run: () => Promise<void>) => {
    setBusy(true); setError("");
    try { await run(); } catch (cause) { setError(errorText(cause)); } finally { setBusy(false); }
  };
  const bindDevice = () => action(async () => {
    setBindingNotice("");
    const auth = authClient.readStoredSession();
    if (!auth) throw new Error("Please sign in again.");
    await mockRequest(`/realtime-speech/sessions/${id}/desktop-binding`, { userId: auth.account.id, manualCode: machineCode });
    setBindingNotice("Device linked. Checking companion readiness…");
    // Request an immediate readiness refresh instead of waiting for the next
    // periodic heartbeat. This does not start capture or minute billing.
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ action: "heartbeat" }));
  });
  const create = () => action(async () => {
    if (!quote) return;
    createKey.current ??= crypto.randomUUID();
    const row = await mockRequest<MockSession>("/mock-interviews", { idempotencyKey: createKey.current,
      title: target.trim() ? `${target.trim()} · Mock interview` : "Mock interview", targetRole: target,
      expectedBillingClass: quote.billingClass });
    createKey.current = null;
    navigate(`/app/mock-interviews/${row.sessionId}`);
  });

  if (enabled === false) return <main className="app-page mock-page"><h1>Mock interviews are not available yet</h1><p>Your existing interview tools are still available.</p><Link to="/app">Back to interviews</Link></main>;
  if (!id) return <main className="app-page mock-page">
    <header className="mock-page-heading"><div><span className="eyebrow">AI PRACTICE</span><h1>Practice for your next interview.</h1><p>Up to 10 English questions based on your resume. Answer at your own pace, then review your feedback.</p></div><span className="mock-pill">Saved {quote?.savedCount ?? "—"} / 2</span></header>
    {error && <p role="alert" className="mock-alert">{error}</p>}
    <section className="mock-create-grid"><div className="mock-portrait"><img src="/assets/mock-interview/interviewer-v1.png" alt="Virtual AI interviewer" /><div><span className="mock-pill">AI interviewer</span><h2>A conversation to help you prepare.</h2></div></div>
      <div className="mock-panel"><span className="eyebrow">START PRACTICING</span><h2>Which role are you preparing for?</h2><label>Target role <span>Optional</span><input value={target} maxLength={80} onChange={e => { setTarget(e.target.value); createKey.current = null; }} placeholder="e.g. Backend Engineer" /></label>
      <div className="mock-price"><strong>{quote?.eligible ? "Included with your membership" : "7-day or longer membership required"}</strong><p>{quote?.eligible ? `${quote.dailyFreeRemaining} of 3 sessions remaining today · resets at 00:00 UTC` : "An active weekly, monthly or longer membership unlocks mock interviews."}</p><Link to="/app/billing">View plans and membership</Link></div>
      <ul className="mock-notes"><li>Select a parsed resume and connect your existing desktop companion. No companion upgrade is needed.</li><li>Create up to 3 sessions per day. The allowance resets at 00:00 UTC; once used, try again the next day.</li><li>Included with an active membership originally purchased for 7 days or longer. No entry or per-minute charge.</li><li>Completed sessions are saved automatically, up to 2 records including sessions in progress. Old records are never overwritten. Raw audio is not saved.</li><li>Cancelling or deleting a session does not restore its daily allowance. A system failure before any completed answer restores that allowance.</li></ul>
      <button className="button primary" disabled={busy || !quote || !quote.eligible || quote.dailyFreeRemaining <= 0 || quote.savedCount >= 2} onClick={() => void create()}>{busy ? "Creating…" : quote && quote.savedCount >= 2 ? "Delete an old record first" : quote && !quote.eligible ? "Membership required" : quote && quote.dailyFreeRemaining <= 0 ? "Daily limit reached · try tomorrow" : "Create mock interview →"}</button></div></section>
    <section className="mock-history"><h2>My mock interviews</h2>{sessions.length === 0 && <p>Your practice sessions will appear here.</p>}{sessions.map(row => <article key={row.sessionId} className="mock-panel"><div><h3>{row.title}</h3><p>{mockPhaseLabel[row.state.phase]} · {new Date(row.createdAtMs).toLocaleString("en-US")}</p></div><Link className="button" to={`/app/mock-interviews/${row.sessionId}`}>{row.state.phase === "completed" ? "View report" : "Continue practice"}</Link>{row.state.phase === "completed" && <button className="button" disabled={busy} onClick={() => void action(async () => { if (!window.confirm("Delete this session and report? This does not restore the daily allowance.")) return; await mockRequest(`/mock-interviews/${row.sessionId}`, undefined, "DELETE"); await reload(); })}>Delete</button>}</article>)}</section>
  </main>;
  if (!session) return <main className="app-page mock-page"><h1>Loading your practice…</h1>{error && <p role="alert">{error}</p>}</main>;
  const phase = session.state.phase;
  const question = session.state.rounds.at(-1);
  return <main className="app-page mock-page"><header className="mock-page-heading"><div><Link to="/app/mock-interviews">← My mock interviews</Link><h1>{session.title}</h1><p>Included with your membership · No per-minute charge{session.refunded ? " · Daily allowance restored" : ""}</p></div><span className="mock-pill">{mockPhaseLabel[phase]}</span></header>
    {error && <p role="alert" className="mock-alert">{error}</p>}
    {phase !== "completed" && !connected && <button className="button" onClick={() => setReconnect(n => n + 1)}>Reconnect</button>}
    {phase === "completed" ? <MockReportView session={session} /> : <div className="mock-workbench"><aside className={`mock-portrait ${playing ? "is-speaking" : ""}`}><img src="/assets/mock-interview/interviewer-v1.png" alt="AI interviewer" /><div><span className="mock-pill">AI interviewer · Not a real person</span><h2>{mockPhaseLabel[phase]}</h2><MockPlaybackIndicator player={voice.current} phase={phase} /><p>Practice based on your resume. This is not a hiring decision.</p></div></aside><section className="mock-panel mock-conversation">
      {phase === "preparing" ? <><span className="eyebrow">PRE-START CHECK</span><h2>Make this interview about you</h2><label>Select a parsed resume<select aria-label="Select resume" value={session.resumeId ?? ""} disabled={busy || !connected} onChange={e => void action(async () => { const doc = resumes.find(r => r.documentId === e.target.value); if (doc) update(await mockRequest<MockSession>(`/mock-interviews/${id}/resume`, { version: session.state.version, documentId: doc.documentId, documentVersionId: doc.documentVersionId })); })}><option value="">Choose a resume</option>{resumes.map(doc => <option key={doc.documentId} value={doc.documentId}>{doc.displayName}</option>)}</select></label>{resumes.length === 0 && <p><Link to="/app/library">Upload and process a resume in Materials first</Link></p>}<label>Companion machine code<input inputMode="numeric" maxLength={6} value={machineCode} onChange={e => setMachineCode(e.target.value.replace(/\D/g, ""))} placeholder="6-digit machine code" /></label><p className="mock-muted">Use your existing companion. Enable microphone access and automatic system time. Headphones are recommended.</p><p className="mock-muted">Only microphone audio is used. Your companion may still upload while questions play; the server discards audio outside your answer turn without transcribing or saving it.</p><button className="button" disabled={busy || !connected || machineCode.length !== 6} onClick={() => void bindDevice()}>Verify and connect</button><p role="status" aria-label="Companion connection status">{!connected ? "The page is not connected. Please reconnect." : bindingNotice || (preparation ? mockPreparationMessage(preparation.code) : "") || (desktopConnected ? "● Companion ready. Microphone streaming connects when you start." : "Open your companion, enter the machine code, then verify and connect.")}</p><button className="button primary" disabled={!connected || !desktopConnected || !session.resumeId || busy} onClick={() => void voice.current.unlock().then(() => command("start")).catch(cause => setError(errorText(cause)))}>Start mock interview →</button></> : <>
      <div className="mock-question-meta"><span>Question {session.state.rounds.length} / 10</span><span>{desktopConnected ? "Microphone companion online" : "Companion disconnected"}</span></div>{question && <h2 className="mock-question">{question.question}</h2>}
      {(phase === "generating_question" || phase === "generating_report") && <div role="status" className="mock-wait"><span className="mock-spinner" />{mockPhaseLabel[phase]}<small>Please wait. Do not create another session.</small></div>}
      {session.error === "generation_unavailable" && <button className="button" disabled={!connected} onClick={() => command("retry")}>Retry</button>}
      {waitingForMicrophone && phase === "speaking" && <p role="status" className="mock-wait">Waiting for the microphone channel. Keep your companion running and speak when you see Your turn to answer.</p>}
      {settlingAudio && phase === "speaking" && <p role="status" className="mock-wait">Preparing microphone capture. Wait until Your turn to answer appears.</p>}
      {phase === "speaking" && <div className="mock-actions"><button className="button primary" disabled={!connected || playing || waitingForMicrophone || settlingAudio} onClick={() => { pendingListen.current = null; playingQuestion.current = question?.question_id ?? null; voice.current.stop(); playbackAcknowledged.current = false; setPlaying(true); void voice.current.unlock().then(() => command("speak")).catch(cause => setError(errorText(cause))); }}>Play question</button><button className="button" disabled={!connected || waitingForMicrophone || settlingAudio} onClick={() => { voice.current.stop(); playingQuestion.current = null; if (question) prepareListening(question.question_id); }}>Ready to answer</button></div>}
      {(phase === "listening" || phase === "paused") && <><label>Your answer<textarea aria-label="Your answer" rows={8} value={draft} maxLength={8000} onChange={e => { edited.current = true; setEditing(true); draftText.current = e.target.value; setDraft(e.target.value); }} placeholder="Answer into your microphone. You can also correct the transcript here." /></label><p className="mock-muted">{editing ? "Editing mode: incoming transcripts will not overwrite your changes." : "Take time to think. Only Answer complete advances to the next question."}</p></>}
      <div className="mock-actions">{phase === "listening" && <><button className="button primary" disabled={!connected || !draft.trim()} onClick={() => { answerId.current ??= crypto.randomUUID(); command("submit", { answer: draft.trim(), submissionId: answerId.current }); }}>Answer complete →</button><button className="button" onClick={() => command("pause")} disabled={!connected}>Pause</button><button className="button" onClick={() => command("replay")} disabled={!connected}>Replay question</button></>}{phase === "paused" && <button className="button primary" disabled={!connected || !desktopConnected} onClick={() => command("resume")}>Resume question</button>}</div>
      </>}
      <footer className="mock-end"><p>Your report is saved automatically. Fewer than 10 completed answers are marked as partial practice.</p><button className="button" disabled={!connected || phase === "generating_report"} onClick={() => { if (window.confirm("Finish this practice and generate a report? The daily allowance will not be restored.")) { voice.current.stop(); command("end"); } }}>Finish practice</button></footer>
    </section></div>}
  </main>;
}

export function MockReportView({ session }: { session: MockSession }) {
  const report = session.report;
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const exportPending = useRef(false);
  const downloadReport = async () => {
    if (exportPending.current || session.state.phase !== "completed" || !report) return;
    exportPending.current = true;
    setExporting(true);
    setExportError(null);
    try {
      const { downloadMockInterviewWord } = await import("./mock-interview-word-export");
      await downloadMockInterviewWord(session);
    } catch {
      setExportError("Word download failed. Please retry; your online report is still available.");
    } finally {
      exportPending.current = false;
      setExporting(false);
    }
  };
  return <section className="mock-report">
    {session.state.phase === "completed" && report && <div className="mock-report-actions">
      <button className="button primary" disabled={exporting} aria-busy={exporting} onClick={() => void downloadReport()}>{exporting ? "Preparing Word…" : "Download Word"}</button>
      <span className="mock-muted">Scores, questions, answers and suggestions · No download charge</span>
    </div>}
    {exportError && <p role="alert" className="mock-alert">{exportError}</p>}
    <div className="mock-panel mock-report-summary"><div className="mock-score">{report?.overall_score ?? "—"}<small>{report?.overall_score == null ? "Not enough answered questions to score" : "/ 100"}</small></div><div><span className="eyebrow">{session.partial ? "Partial practice report" : "Practice report"}</span><h2>Review. Reflect. Improve.</h2><p>{report?.summary}</p><p className="mock-muted">{mockReportDisclosure}</p></div></div>
    {report?.dimensions && <div className="mock-dimensions">{Object.entries(report.dimensions).map(([key, value]) => <div className="mock-panel" key={key}><span>{labels[key] ?? key}</span><strong>{value}</strong><meter min={0} max={100} value={value} aria-label={labels[key] ?? key} /></div>)}</div>}
    {session.state.rounds.map((round, index) => { const feedback = report?.feedback.find(item => item.question_id === round.question_id); return <article className="mock-panel" key={round.question_id}><span className="eyebrow">Question {index + 1}</span><h3>{round.question}</h3><p className="mock-answer">{round.answer ?? "No answer was submitted for this question. It is not scored."}</p>{feedback && <><h4>Evidence from your answer</h4><blockquote>{feedback.answer_quote}</blockquote><h4>What went well</h4><p>{feedback.strength}</p><h4>What to improve</h4><p>{feedback.improvement}</p><h4>Suggested approach</h4><p>{feedback.suggestion}</p></>}</article>; })}
    {!!report?.practice_priorities.length && <section className="mock-panel"><h3>Next practice priorities</h3><ul>{report.practice_priorities.map((tip, index) => <li key={index}>{tip}</li>)}</ul></section>}
    <Link className="button" to="/app/mock-interviews">Back to my mock interviews</Link>
  </section>;
}
