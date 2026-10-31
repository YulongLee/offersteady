import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { authClient } from "./auth-client";
import { mockRequest, mockSocketUrl, nextMockQuoteRefreshDelay, MockPlaybackError, MockVoicePlayer, type MockQuote, type MockResume, type MockSession } from "./mock-interview-client";
import { MockPlaybackIndicator } from "./MockPlaybackIndicator";
import { mockReportDimensionLabels as labels, mockReportDisclosure } from "./mock-interview-report";
import "./mock-interview.css";

export const mockPhaseLabel: Record<MockSession["state"]["phase"], string> = {
  preparing: "面试准备", generating_question: "面试官正在出题", speaking: "听听面试官的问题",
  listening: "轮到你回答", paused: "已暂停", generating_report: "正在整理面试报告", completed: "本场练习已结束",
};
const errorText = (error: unknown) => error instanceof Error ? error.message : "操作暂时不可用，请重试。";
const playbackRecoveryMessage = (phase: MockSession["state"]["phase"]) => phase === "preparing"
  ? "网页声音尚未就绪，请再次点击开始模拟面试重试。"
  : phase === "paused" ? "网页声音已暂停，请点击继续本题后恢复朗读。"
  : new MockPlaybackError().message;
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
  const [microphoneCheckExpired, setMicrophoneCheckExpired] = useState(false);
  const [rechecking, setRechecking] = useState(false);
  const recheckTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const recheckLocked = useRef(false);
  const readinessError = useRef<string | null>(null);
  const desktopReady = useRef(false);
  const [playbackNotice, setPlaybackNotice] = useState("");
  const playbackRecoveryNeeded = useRef(false);
  const [playbackUnlocking, setPlaybackUnlocking] = useState<"auto" | "manual" | null>(null);
  const playbackSequence = useRef(0);
  const playbackAttempt = useRef<{ sequence: number; manual: boolean; questionId: string | undefined; action: "speak" | "start" } | null>(null);
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
  const actionGeneration = useRef(0);
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [playing, setPlaying] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const current = useRef<MockSession | null>(null);
  const edited = useRef(false);
  const draftText = useRef("");
  const capturePrefix = useRef("");
  const voice = useRef(new MockVoicePlayer());
  const createKey = useRef<string | null>(null);
  const quoteRequest = useRef(0);
  const answerId = useRef<string | null>(null);
  const playingQuestion = useRef<string | null>(null);
  const playbackAcknowledged = useRef(false);
  const [reconnect, setReconnect] = useState(0);

  const cancelPlaybackIntent = () => {
    playbackSequence.current++;
    playbackAttempt.current = null;
    setPlaybackUnlocking(null);
  };
  const cancelListeningIntent = () => {
    clearTimeout(settleTimer.current); settleTimer.current = undefined;
    pendingListen.current = null;
    setWaitingForMicrophone(false); setSettlingAudio(false);
  };
  const invalidateActions = () => {
    actionGeneration.current++;
    setBusy(false);
  };

  const update = (row: MockSession) => {
    const old = current.current;
    if (old?.sessionId !== row.sessionId || old?.state.phase !== row.state.phase || old?.state.rounds.at(-1)?.question_id !== row.state.rounds.at(-1)?.question_id || old?.resumeId !== row.resumeId || old?.resumeVersion !== row.resumeVersion) {
      cancelPlaybackIntent();
      setPlaybackNotice(row.state.phase === "paused" && playbackRecoveryNeeded.current ? playbackRecoveryMessage("paused") : "");
      if (row.state.phase !== "paused") playbackRecoveryNeeded.current = false;
    }
    if (old?.state.rounds.at(-1)?.question_id !== row.state.rounds.at(-1)?.question_id) {
      voice.current.stop(); setPlaying(false); playingQuestion.current = null; playbackAcknowledged.current = false;
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
    if (!row || socket.current?.readyState !== WebSocket.OPEN) { setError("连接已断开，请重新连接后操作。"); return; }
    if (["pause", "end", "listen", "replay", "resume", "submit"].includes(action)) {
      cancelPlaybackIntent(); cancelListeningIntent(); invalidateActions();
    }
    setError(""); readinessError.current = null;
    socket.current.send(JSON.stringify({ action, version: row.state.version,
      ...(["listen", "replay", "speak", "playback_started", "playback_waiting", "submit"].includes(action) ? { questionId: row.state.rounds.at(-1)?.question_id } : {}), ...extra }));
  };
  const requestPlayback = (action: "start" | "speak", manual: boolean) => {
    const row = current.current;
    const connection = socket.current;
    const phase = action === "start" ? "preparing" : "speaking";
    if (!row || row.state.phase !== phase || connection?.readyState !== WebSocket.OPEN) return;
    const questionId = row.state.rounds.at(-1)?.question_id;
    const pending = playbackAttempt.current;
    if (pending?.manual && pending.action === action && pending.questionId === questionId) return;
    const sequence = ++playbackSequence.current;
    playbackAttempt.current = { sequence, manual, questionId, action };
    playbackRecoveryNeeded.current = false;
    setPlaybackUnlocking(manual ? "manual" : "auto");
    setPlaybackNotice(manual ? "" : "正在准备网页声音。如果没有播放，请点击朗读问题恢复。");
    if (action === "speak") {
      pendingListen.current = null;
      playingQuestion.current = questionId ?? null;
      voice.current.stop(); playbackAcknowledged.current = false; setPlaying(false);
    }
    const valid = () => sequence === playbackSequence.current && socket.current === connection
      && connection.readyState === WebSocket.OPEN && current.current?.sessionId === row.sessionId
      && current.current.state.phase === phase && current.current.state.rounds.at(-1)?.question_id === questionId
      && (action !== "start" || (current.current.resumeId === row.resumeId && current.current.resumeVersion === row.resumeVersion));
    // Keep this invocation synchronous with the click, including when an older
    // automatic resume is pending and the user supplies the missing gesture.
    void voice.current.unlock().then(() => {
      if (!valid()) return;
      playbackAttempt.current = null; setPlaybackUnlocking(null); setPlaybackNotice("");
      if (action === "start" && (!desktopReady.current || !current.current?.resumeId)) return;
      if (action === "speak") setPlaying(true);
      command(action);
    }).catch(() => {
      if (!valid()) return;
      playbackAttempt.current = null; setPlaybackUnlocking(null); setPlaying(false);
      playbackRecoveryNeeded.current = true;
      setPlaybackNotice(playbackRecoveryMessage(phase));
    });
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
  voice.current.onPlaybackUnavailable = () => {
    const row = current.current;
    if (row?.state.phase !== "speaking" || !playingQuestion.current
        || playingQuestion.current !== row.state.rounds.at(-1)?.question_id) return;
    voice.current.stop(); setPlaying(false); playingQuestion.current = null;
    playbackAcknowledged.current = false; playbackRecoveryNeeded.current = true;
    command("pause");
    setPlaybackNotice(playbackRecoveryMessage("paused"));
  };

  const reload = useCallback(async () => {
    const request = ++quoteRequest.current;
    const data = await mockRequest<{ sessions: MockSession[]; quote: MockQuote }>("/mock-interviews");
    if (request !== quoteRequest.current) return;
    setSessions(data.sessions); setQuote(data.quote);
  }, []);

  useEffect(() => {
    if (id || enabled !== true) return;
    let disposed = false;
    const refresh = () => { void reload().catch(cause => { if (!disposed) setError(errorText(cause)); }); };
    const timer = quote ? setTimeout(refresh, nextMockQuoteRefreshDelay(quote)) : undefined;
    const recover = () => { if (document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", recover);
    return () => { disposed = true; clearTimeout(timer); document.removeEventListener("visibilitychange", recover); };
  }, [id, enabled, quote, reload]);

  useEffect(() => {
    let disposed = false;
    setError(""); readinessError.current = null;
    void mockRequest<{ enabled: boolean }>("/mock-interviews/capabilities").then(async capability => {
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
      } else await reload();
    }).catch(cause => { if (!disposed) setError(errorText(cause)); });
    return () => { disposed = true; invalidateActions(); quoteRequest.current++; current.current = null; setSession(null); };
  }, [id, reload]);

  useEffect(() => {
    setMicrophoneCheckExpired(false);
    if (!id || !connected || session?.state.phase !== "preparing" || preparation?.code !== "mock_microphone_checking") return;
    const timer = setTimeout(() => setMicrophoneCheckExpired(true), 30_000);
    return () => clearTimeout(timer);
  }, [id, connected, session?.state.phase, preparation?.code]);

  useEffect(() => () => {
    clearTimeout(recheckTimer.current); recheckLocked.current = false;
    setRechecking(false); setBindingNotice(""); setPreparation(null);
  }, [id, reconnect]);

  const needsConnection = Boolean(id && session && session.sessionId === id && session.state.phase !== "completed");
  useEffect(() => {
    if (!id || !needsConnection) return;
    const auth = authClient.readStoredSession();
    if (!auth) { setError("请先重新登录。"); return; }
    let disposed = false;
    let stateReceived = false;
    let heartbeat: ReturnType<typeof setInterval> | undefined;
    const connection = new WebSocket(mockSocketUrl(id));
    socket.current = connection;
    connection.onopen = () => {
      if (disposed || socket.current !== connection) return;
      connection.send(JSON.stringify({ accessToken: auth.accessToken }));
      heartbeat = setInterval(() => {
        if (!disposed && socket.current === connection && connection.readyState === WebSocket.OPEN) connection.send(JSON.stringify({ action: "heartbeat" }));
      }, 5000);
    };
    connection.onmessage = event => {
      if (disposed) return;
      try {
        const message = JSON.parse(String(event.data));
        if (message.type === "state") {
          const previousPhase = current.current?.state.phase;
          const previousQuestion = current.current?.state.rounds.at(-1)?.question_id;
          microphoneReady.current = (message.microphoneConnected ?? message.desktopConnected) === true;
          desktopReady.current = message.desktopConnected === true && message.preparation?.ready !== false;
          setPreparation(message.preparation ?? null);
          setBindingNotice("");
          if (message.preparation?.ready === true && readinessError.current) {
            const stale = readinessError.current; readinessError.current = null;
            setError(previous => previous === stale ? "" : previous);
          }
          setConnected(true); setDesktopConnected(message.desktopConnected === true); update(message.session);
          if (pendingListen.current && microphoneReady.current) beginListening(pendingListen.current);
          if (message.session.state.phase === "speaking" && (!stateReceived || previousPhase !== "speaking" || previousQuestion !== message.session.state.rounds.at(-1)?.question_id)) {
            voice.current.stop(); playbackAcknowledged.current = false;
            playingQuestion.current = message.session.state.rounds.at(-1)?.question_id ?? null;
            requestPlayback("speak", false);
          }
          stateReceived = true;
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
          readinessError.current = ["mock_microphone_checking", "mock_microphone_required"].includes(message.code) ? message.message : null;
          setError(message.message); setBusy(false);
          if (message.type === "speech_unavailable") { cancelPlaybackIntent(); voice.current.stop(); setPlaying(false); playingQuestion.current = null; }
          else if (current.current?.state.phase === "speaking") setPlaying(false);
        }
      } catch (cause) {
        voice.current.stop(); setPlaying(false); playingQuestion.current = null;
        command("pause");
        if (cause instanceof MockPlaybackError) { playbackRecoveryNeeded.current = true; setPlaybackNotice(playbackRecoveryMessage(current.current?.state.phase ?? "speaking")); }
        else setError(errorText(cause));
      }
    };
    connection.onclose = () => {
      if (disposed) return;
      invalidateActions();
      clearInterval(heartbeat); clearTimeout(settleTimer.current); voice.current.close(); setSettlingAudio(false);
      microphoneReady.current = false; pendingListen.current = null; setWaitingForMicrophone(false);
      desktopReady.current = false; cancelPlaybackIntent(); setPlaybackNotice("");
      playbackRecoveryNeeded.current = false;
      readinessError.current = null;
      clearTimeout(recheckTimer.current); recheckLocked.current = false; setRechecking(false); setBindingNotice("");
      if (!disposed) { setConnected(false); setPlaying(false); setError("面试连接已断开，收音已暂停。请重新连接；本场结束时间保持不变。"); }
    };
    return () => { disposed = true; invalidateActions(); cancelPlaybackIntent(); cancelListeningIntent(); playbackRecoveryNeeded.current = false; setPlaybackNotice(""); clearInterval(heartbeat); voice.current.close(); connection.close(); socket.current = null; microphoneReady.current = false; desktopReady.current = false; setConnected(false); };
  }, [id, needsConnection, reconnect]);

  const action = async (run: (isCurrent: () => boolean) => Promise<void>) => {
    const generation = actionGeneration.current;
    const connection = socket.current;
    const isCurrent = () => generation === actionGeneration.current && socket.current === connection;
    setBusy(true); setError(""); readinessError.current = null;
    try { await run(isCurrent); }
    catch (cause) { if (isCurrent()) setError(errorText(cause)); }
    finally { if (isCurrent()) setBusy(false); }
  };
  const selectResume = (documentId: string) => action(async isCurrent => {
    const row = current.current;
    const doc = resumes.find(item => item.documentId === documentId);
    if (!row || row.state.phase !== "preparing" || !doc) return;
    const selected = await mockRequest<MockSession>(`/mock-interviews/${row.sessionId}/resume`, {
      version: row.state.version, documentId: doc.documentId, documentVersionId: doc.documentVersionId,
    });
    const latest = current.current;
    if (!isCurrent() || latest?.sessionId !== row.sessionId || latest.state.phase !== "preparing"
        || selected.sessionId !== row.sessionId || selected.state.phase !== "preparing"
        || selected.state.version < latest.state.version) return;
    update(selected);
  });
  const recheckMicrophone = () => {
    if (recheckLocked.current || current.current?.state.phase !== "preparing" || socket.current?.readyState !== WebSocket.OPEN) return;
    recheckLocked.current = true; setRechecking(true);
    setBindingNotice("正在重新检查麦克风…");
    socket.current.send(JSON.stringify({ action: "heartbeat" }));
    recheckTimer.current = setTimeout(() => {
      recheckLocked.current = false; setRechecking(false);
      setBindingNotice(previous => previous === "正在重新检查麦克风…" ? "" : previous);
    }, 2000);
  };
  const bindDevice = () => action(async isCurrent => {
    cancelPlaybackIntent();
    setBindingNotice("");
    const row = current.current;
    if (!row || row.state.phase !== "preparing") return;
    const auth = authClient.readStoredSession();
    if (!auth) throw new Error("请重新登录");
    await mockRequest(`/realtime-speech/sessions/${id}/desktop-binding`, { userId: auth.account.id, manualCode: machineCode });
    if (!isCurrent() || current.current?.sessionId !== row.sessionId || current.current.state.phase !== "preparing") return;
    setBindingNotice("机器码已绑定，正在检查助手状态…");
    // Request an immediate readiness refresh instead of waiting for the next
    // periodic heartbeat. This does not start capture or minute billing.
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ action: "heartbeat" }));
  });
  const create = () => action(async isCurrent => {
    if (!quote) return;
    if (quote.entryPoints && !window.confirm(`本场一次性扣 ${quote.entryPoints} 积分，开始后 ${quote.durationLimitMinutes} 分钟自动结束。确认创建？`)) return;
    createKey.current ??= crypto.randomUUID();
    let row: MockSession;
    try {
      row = await mockRequest<MockSession>("/mock-interviews", { idempotencyKey: createKey.current,
        title: target.trim() ? `${target.trim()} · 模拟面试` : "模拟面试", targetRole: target,
        expectedBillingClass: quote.billingClass });
    } catch (cause) {
      // A lost response can follow a successful charge. Keep the creation key
      // for retries, while refreshing any quote invalidated by quota or date.
      try { if (isCurrent()) await reload(); } catch { /* Preserve the original actionable error. */ }
      throw cause;
    }
    if (!isCurrent()) return;
    createKey.current = null;
    navigate(`/app/mock-interviews/${row.sessionId}`);
  });

  if (enabled === false) return <main className="app-page mock-page"><h1>模拟面试尚未开放</h1><p>正式开放前，原有面试功能不受影响。</p><Link to="/app">返回面试模式</Link></main>;
  if (!id) return <main className="app-page mock-page">
    <header className="mock-page-heading"><div><span className="eyebrow">AI PRACTICE</span><h1>把下一次面试，提前练一遍。</h1><p>围绕你的简历展开，最多 10 道问题。按自己的节奏回答，结束后获得反馈。</p></div><span className="mock-pill">已保存 {quote?.savedCount ?? "—"} / 2</span></header>
    {error && <p role="alert" className="mock-alert">{error}</p>}
    <section className="mock-create-grid"><div className="mock-portrait"><img src="/assets/mock-interview/interviewer-v1.png" alt="原创虚拟 AI 面试官形象" /><div><span className="mock-pill">AI 模拟面试官</span><h2>一次对话，一次更充分的准备。</h2></div></div>
      <div className="mock-panel"><span className="eyebrow">开始练习</span><h2>这次，想准备什么岗位？</h2><label>目标岗位 <span>选填</span><input value={target} maxLength={80} disabled={busy} onChange={e => { setTarget(e.target.value); createKey.current = null; }} placeholder="例如：后端开发工程师" /></label>
      <div className="mock-price"><strong>{quote?.entryPoints === 0 ? "本场免费" : "100 积分 / 场"}</strong><p>{quote?.entryPoints === 0 ? `有效会员今日剩余 ${quote.dailyFreeRemaining} 场免费模拟面试。` : "每场一次性扣 100 积分，朗读、回答和报告不额外收费。"}</p></div>
      <ul className="mock-notes"><li>创建后选择一份已解析简历，连接现有正式版桌面助手，无需为此升级助手。</li><li>所有有效会员每天免费 {quote?.dailyFreeLimit ?? 1} 场，北京时间 00:00 更新；当天免费次数用完后，100 积分 / 场。</li><li>开始后 {quote?.durationLimitMinutes ?? 60} 分钟自动结束；准备阶段不计时，暂停、出题等待和断线不延长结束时间。</li><li>结束自动保存问答和报告，最多 2 场；不保存原始音频。不自动覆盖旧记录。</li><li>主动取消不退创建费；系统故障导致一题都无法完成时，退本场积分或恢复免费次数。</li></ul>
      <button className="button primary" disabled={busy || !quote || quote.savedCount >= 2} onClick={() => void create()}>{busy ? "正在创建…" : quote && quote.savedCount >= 2 ? "请先手动删除旧记录" : "创建模拟面试 →"}</button></div></section>
    <section className="mock-history"><h2>我的模拟面试</h2>{sessions.length === 0 && <p>你的每一次练习，都会从这里开始。</p>}{sessions.map(row => <article key={row.sessionId} className="mock-panel"><div><h3>{row.title}</h3><p>{mockPhaseLabel[row.state.phase]} · {new Date(row.createdAtMs).toLocaleString("zh-CN")}</p></div><Link className="button" to={`/app/mock-interviews/${row.sessionId}`}>{row.state.phase === "completed" ? "查看报告" : "继续面试"}</Link>{row.state.phase === "completed" && <button className="button" disabled={busy} onClick={() => void action(async isCurrent => { if (!window.confirm("删除本场问答和报告？不会退还已使用积分或免费次数。")) return; await mockRequest(`/mock-interviews/${row.sessionId}`, undefined, "DELETE"); if (isCurrent()) await reload(); })}>删除</button>}</article>)}</section>
  </main>;
  if (!session) return <main className="app-page mock-page"><h1>正在恢复面试…</h1>{error && <p role="alert">{error}</p>}</main>;
  const phase = session.state.phase;
  const question = session.state.rounds.at(-1);
  return <main className="app-page mock-page"><header className="mock-page-heading"><div><Link to="/app/mock-interviews">← 我的模拟面试</Link><h1>{session.title}</h1><p>{session.billingClass === "daily_pass_free" ? "本场全程免费" : "创建费用 100 积分"}{session.refunded ? " · 本场已退还" : ""}</p><p>{session.deadlineAtMs ? <>本场结束时间：{new Date(session.deadlineAtMs).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false })}（北京时间） · 暂停、等待和重连不延长</> : <>开始后 {session.durationLimitMinutes ?? 60} 分钟自动结束，准备阶段不计时。</>}</p></div><span className="mock-pill">{mockPhaseLabel[phase]}</span></header>
    {error && <p role="alert" className="mock-alert">{error}</p>}
    {playbackNotice && <p role="status" aria-label="网页声音状态" className="mock-alert">{playbackNotice}</p>}
    {phase !== "completed" && !connected && <button className="button" onClick={() => setReconnect(n => n + 1)}>重新连接</button>}
    {session.endReason === "time_limit" && <p role="status" className="mock-alert">已达到本场 {session.durationLimitMinutes ?? 60} 分钟时限，模拟面试已自动结束。已提交的回答将保存在报告中。</p>}
    {phase === "completed" ? <MockReportView session={session} /> : <div className="mock-workbench"><aside className={`mock-portrait ${playing ? "is-speaking" : ""}`}><img src="/assets/mock-interview/interviewer-v1.png" alt="AI 模拟面试官" /><div><span className="mock-pill">AI 模拟面试官 · 非真人</span><h2>{mockPhaseLabel[phase]}</h2><MockPlaybackIndicator player={voice.current} phase={phase} /></div></aside><section className="mock-panel mock-conversation">
      {phase === "preparing" ? <><span className="eyebrow">开始前检查</span><h2>让这场面试围绕你展开</h2><label>选择已解析的简历<select aria-label="选择简历" value={session.resumeId ?? ""} disabled={busy || !connected} onChange={e => void selectResume(e.target.value)}><option value="">请选择简历</option>{resumes.map(doc => <option key={doc.documentId} value={doc.documentId}>{doc.displayName}</option>)}</select></label>{resumes.length === 0 && <p><Link to="/app/library">先去资料页上传并解析简历</Link></p>}<label>桌面助手机器码<input inputMode="numeric" maxLength={6} value={machineCode} onChange={e => setMachineCode(e.target.value.replace(/\D/g, ""))} placeholder="6 位机器码" /></label><button className="button" disabled={busy || !connected || machineCode.length !== 6} onClick={() => void bindDevice()}>验证并连接</button><p role="status" aria-label="助手连接状态">{!connected ? "页面连接未就绪，请重新连接。" : bindingNotice || (preparation?.code === "mock_microphone_checking" && microphoneCheckExpired ? "麦克风状态尚未确认，请重新检查。" : preparation?.message) || (desktopConnected ? "● 助手已连接，开始后连接收音通道" : "请打开桌面助手，输入机器码后验证并连接。")}</p>{["mock_microphone_checking", "mock_microphone_required"].includes(preparation?.code ?? "") && <button className="button" disabled={!connected || rechecking || busy} onClick={recheckMicrophone}>{rechecking ? "正在重新检查…" : "重新检查麦克风"}</button>}<button className="button primary" disabled={!connected || !desktopConnected || preparation?.ready === false || !session.resumeId || busy || playbackUnlocking === "manual"} onClick={() => requestPlayback("start", true)}>开始模拟面试 →</button><details className="mock-instructions mock-muted"><summary>使用说明</summary><p>现有正式版助手即可，仅使用麦克风，建议佩戴耳机。原始音频不保存，非回答时段的音频不转写。旧版助手可能在提问时继续采集上传，服务器会丢弃非回答时段的音频。</p></details></> : <>
      <div className="mock-question-meta"><span>问题 {session.state.rounds.length} / 10</span><span>{desktopConnected ? "麦克风助手在线" : "助手未连接"}</span></div>{question && <h2 className="mock-question">{question.question}</h2>}
      {(phase === "generating_question" || phase === "generating_report") && <div role="status" className="mock-wait"><span className="mock-spinner" />{mockPhaseLabel[phase]}<small>请稍候，不额外收费，无需重复创建。</small></div>}
      {session.error === "generation_unavailable" && <button className="button" disabled={!connected} onClick={() => command("retry")}>重试生成</button>}
      {waitingForMicrophone && phase === "speaking" && <p role="status" className="mock-wait">正在等待助手收音通道连接。请保持助手运行，显示“轮到你回答”后再开口。</p>}
      {settlingAudio && phase === "speaking" && <p role="status" className="mock-wait">正在准备收音，请稍候片刻，显示“轮到你回答”后再开口。</p>}
      {phase === "speaking" && <div className="mock-actions"><button className="button primary" disabled={!connected || playing || playbackUnlocking === "manual" || waitingForMicrophone || settlingAudio} onClick={() => requestPlayback("speak", true)}>朗读问题</button><button className="button" disabled={!connected || waitingForMicrophone || settlingAudio} onClick={() => { cancelPlaybackIntent(); playbackRecoveryNeeded.current = false; setPlaybackNotice(""); voice.current.stop(); setPlaying(false); playingQuestion.current = null; if (question) prepareListening(question.question_id); }}>我已读完，开始回答</button></div>}
      {(phase === "listening" || phase === "paused") && <><label>你的回答<textarea aria-label="你的回答" rows={8} value={draft} maxLength={8000} onChange={e => { edited.current = true; setEditing(true); draftText.current = e.target.value; setDraft(e.target.value); }} placeholder="请对着麦克风回答，也可在这里校正转写。" /></label><p className="mock-muted">{editing ? "已进入文字校正，新的转写不会覆盖你的修改。" : "思考和停顿不会自动进入下一题。确认回答后再提交。"}</p></>}
      <div className="mock-actions">{phase === "listening" && <><button className="button primary" disabled={!connected || !draft.trim()} onClick={() => { answerId.current ??= crypto.randomUUID(); command("submit", { answer: draft.trim(), submissionId: answerId.current }); }}>回答完成 →</button><button className="button" onClick={() => command("pause")} disabled={!connected}>暂停</button><button className="button" onClick={() => command("replay")} disabled={!connected}>重新听题</button></>}{phase === "paused" && <button className="button primary" disabled={!connected || !desktopConnected} onClick={() => command("resume")}>继续本题</button>}</div>
      </>}
      <footer className="mock-end"><p>结束后自动保存报告。不足 10 题将标注为部分练习。</p><button className="button" disabled={!connected || phase === "generating_report"} onClick={() => { if (window.confirm("结束本场练习并生成报告？主动结束不退创建费。")) { cancelPlaybackIntent(); playbackRecoveryNeeded.current = false; setPlaybackNotice(""); voice.current.stop(); setPlaying(false); playingQuestion.current = null; command("end"); } }}>结束面试</button></footer>
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
      setExportError("Word 下载失败，请重试。在线报告不受影响。");
    } finally {
      exportPending.current = false;
      setExporting(false);
    }
  };
  return <section className="mock-report">
    {session.state.phase === "completed" && report && <div className="mock-report-actions">
      <button className="button primary" disabled={exporting} aria-busy={exporting} onClick={() => void downloadReport()}>{exporting ? "正在生成 Word…" : "下载 Word"}</button>
      <span className="mock-muted">包含评分、逐题问答与改进建议 · 下载不额外扣费</span>
    </div>}
    {exportError && <p role="alert" className="mock-alert">{exportError}</p>}
    <div className="mock-panel mock-report-summary"><div className="mock-score">{report?.overall_score ?? "—"}<small>{report?.overall_score == null ? "有效回答不足，不评分" : "/ 100"}</small></div><div><span className="eyebrow">{session.partial ? "部分练习报告" : "面试练习报告"}</span><h2>复盘，让下一次更好。</h2><p>{report?.summary}</p><p className="mock-muted">{mockReportDisclosure}</p></div></div>
    {report?.dimensions && <div className="mock-dimensions">{Object.entries(report.dimensions).map(([key, value]) => <div className="mock-panel" key={key}><span>{labels[key] ?? key}</span><strong>{value}</strong><meter min={0} max={100} value={value} aria-label={labels[key] ?? key} /></div>)}</div>}
    {session.state.rounds.map((round, index) => { const feedback = report?.feedback.find(item => item.question_id === round.question_id); return <article className="mock-panel" key={round.question_id}><span className="eyebrow">问题 {index + 1}</span><h3>{round.question}</h3><p className="mock-answer">{round.answer ?? "本题未提交回答，不计分。"}</p>{feedback && <><h4>回答中的证据</h4><blockquote>{feedback.answer_quote}</blockquote><h4>做得好的地方</h4><p>{feedback.strength}</p><h4>可以提升</h4><p>{feedback.improvement}</p><h4>回答建议</h4><p>{feedback.suggestion}</p></>}</article>; })}
    {!!report?.practice_priorities.length && <section className="mock-panel"><h3>下一次练习重点</h3><ul>{report.practice_priorities.map((tip, index) => <li key={index}>{tip}</li>)}</ul></section>}
    <Link className="button" to="/app/mock-interviews">返回我的模拟面试</Link>
  </section>;
}
