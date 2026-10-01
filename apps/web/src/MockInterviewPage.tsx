import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { authClient } from "./auth-client";
import { mockRequest, mockSocketUrl, MockVoicePlayer, type MockQuote, type MockResume, type MockSession } from "./mock-interview-client";
import { MockPlaybackIndicator } from "./MockPlaybackIndicator";
import { mockReportDimensionLabels as labels, mockReportDisclosure } from "./mock-interview-report";
import "./mock-interview.css";

export const mockPhaseLabel: Record<MockSession["state"]["phase"], string> = {
  preparing: "面试准备", generating_question: "面试官正在出题", speaking: "听听面试官的问题",
  listening: "轮到你回答", paused: "已暂停 · 不计分钟费", generating_report: "正在整理面试报告", completed: "本场练习已结束",
};
const errorText = (error: unknown) => error instanceof Error ? error.message : "操作暂时不可用，请重试。";
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
    if (!row || socket.current?.readyState !== WebSocket.OPEN) { setError("连接已断开，请重新连接后操作。"); return; }
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
    return () => { disposed = true; current.current = null; setSession(null); };
  }, [id]);

  const needsConnection = Boolean(id && session && session.state.phase !== "completed");
  useEffect(() => {
    if (!id || !needsConnection) return;
    const auth = authClient.readStoredSession();
    if (!auth) { setError("请先重新登录。"); return; }
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
          setError(message.message); setBusy(false);
          if (message.type === "speech_unavailable") { voice.current.stop(); setPlaying(false); }
        }
      } catch (cause) { voice.current.stop(); setPlaying(false); setError(errorText(cause)); command("pause"); }
    };
    connection.onclose = () => {
      clearInterval(heartbeat); clearTimeout(settleTimer.current); voice.current.close(); setSettlingAudio(false);
      microphoneReady.current = false; pendingListen.current = null; setWaitingForMicrophone(false);
      if (!disposed) { setConnected(false); setPlaying(false); setError("面试连接已断开，收音与计费已暂停。请重新连接。"); }
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
    if (!auth) throw new Error("请重新登录");
    await mockRequest(`/realtime-speech/sessions/${id}/desktop-binding`, { userId: auth.account.id, manualCode: machineCode });
    setBindingNotice("机器码已绑定，正在检查助手状态…");
    // Request an immediate readiness refresh instead of waiting for the next
    // periodic heartbeat. This does not start capture or minute billing.
    if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(JSON.stringify({ action: "heartbeat" }));
  });
  const create = () => action(async () => {
    if (!quote) return;
    if (quote.entryPoints && !window.confirm(`本场创建扣 ${quote.entryPoints} 积分，朗读与回答每开始一分钟扣 ${quote.minutePoints} 积分。确认创建？`)) return;
    createKey.current ??= crypto.randomUUID();
    const row = await mockRequest<MockSession>("/mock-interviews", { idempotencyKey: createKey.current,
      title: target.trim() ? `${target.trim()} · 模拟面试` : "模拟面试", targetRole: target,
      expectedBillingClass: quote.billingClass });
    createKey.current = null;
    navigate(`/app/mock-interviews/${row.sessionId}`);
  });

  if (enabled === false) return <main className="app-page mock-page"><h1>模拟面试尚未开放</h1><p>正式开放前，原有面试功能不受影响。</p><Link to="/app">返回面试模式</Link></main>;
  if (!id) return <main className="app-page mock-page">
    <header className="mock-page-heading"><div><span className="eyebrow">AI PRACTICE</span><h1>把下一次面试，提前练一遍。</h1><p>围绕你的简历展开，最多 10 道问题。按自己的节奏回答，结束后获得反馈。</p></div><span className="mock-pill">已保存 {quote?.savedCount ?? "—"} / 2</span></header>
    {error && <p role="alert" className="mock-alert">{error}</p>}
    <section className="mock-create-grid"><div className="mock-portrait"><img src="/assets/mock-interview/interviewer-v1.png" alt="原创虚拟 AI 面试官形象" /><div><span className="mock-pill">AI 模拟面试官</span><h2>一次对话，一次更充分的准备。</h2></div></div>
      <div className="mock-panel"><span className="eyebrow">开始练习</span><h2>这次，想准备什么岗位？</h2><label>目标岗位 <span>选填</span><input value={target} maxLength={80} onChange={e => { setTarget(e.target.value); createKey.current = null; }} placeholder="例如：后端开发工程师" /></label>
      <div className="mock-price"><strong>{quote?.entryPoints === 0 ? "本场免费" : "100 积分 / 场"}</strong><p>{quote?.entryPoints === 0 ? `时间会员今日剩余 ${quote.dailyFreeRemaining} 次免费创建，本场分钟费也免费。` : "另收 5 积分 / 分钟，仅累计题目朗读与回答时间，每开始一分钟计费。"}</p></div>
      <ul className="mock-notes"><li>创建后选择一份已解析简历，连接现有正式版桌面助手，无需为此升级助手。</li><li>每天按北京时间重置会员 3 次免费额度，超出后按积分收费。</li><li>准备、出题等待、暂停、断线及报告生成不计分钟费。</li><li>结束自动保存问答和报告，最多 2 场；不保存原始音频。不自动覆盖旧记录。</li><li>主动取消不退创建费；系统故障导致一题都无法完成时，退本场积分或恢复免费次数。</li></ul>
      <button className="button primary" disabled={busy || !quote || quote.savedCount >= 2} onClick={() => void create()}>{busy ? "正在创建…" : quote && quote.savedCount >= 2 ? "请先手动删除旧记录" : "创建模拟面试 →"}</button></div></section>
    <section className="mock-history"><h2>我的模拟面试</h2>{sessions.length === 0 && <p>你的每一次练习，都会从这里开始。</p>}{sessions.map(row => <article key={row.sessionId} className="mock-panel"><div><h3>{row.title}</h3><p>{mockPhaseLabel[row.state.phase]} · {new Date(row.createdAtMs).toLocaleString("zh-CN")}</p></div><Link className="button" to={`/app/mock-interviews/${row.sessionId}`}>{row.state.phase === "completed" ? "查看报告" : "继续面试"}</Link>{row.state.phase === "completed" && <button className="button" disabled={busy} onClick={() => void action(async () => { if (!window.confirm("删除本场问答和报告？不会退还已使用积分或免费次数。")) return; await mockRequest(`/mock-interviews/${row.sessionId}`, undefined, "DELETE"); await reload(); })}>删除</button>}</article>)}</section>
  </main>;
  if (!session) return <main className="app-page mock-page"><h1>正在恢复面试…</h1>{error && <p role="alert">{error}</p>}</main>;
  const phase = session.state.phase;
  const question = session.state.rounds.at(-1);
  return <main className="app-page mock-page"><header className="mock-page-heading"><div><Link to="/app/mock-interviews">← 我的模拟面试</Link><h1>{session.title}</h1><p>{session.billingClass === "daily_pass_free" ? "本场全程免费" : `创建 100 积分 · 已计 ${session.billedMinutes} 分钟 / ${session.billedMinutes * 5} 积分`} · {session.interacting ? "正在计时" : "当前不计分钟费"}{session.refunded ? " · 本场已退还" : ""}</p></div><span className="mock-pill">{mockPhaseLabel[phase]}</span></header>
    {error && <p role="alert" className="mock-alert">{error}</p>}
    {phase !== "completed" && !connected && <button className="button" onClick={() => setReconnect(n => n + 1)}>重新连接</button>}
    {session.error === "mock_minute_insufficient_balance" && <p role="alert" className="mock-alert">积分不足，本场已暂停且不再计时。请补充积分后继续，或结束并保存已有回答。</p>}
    {phase === "completed" ? <MockReportView session={session} /> : <div className="mock-workbench"><aside className={`mock-portrait ${playing ? "is-speaking" : ""}`}><img src="/assets/mock-interview/interviewer-v1.png" alt="AI 模拟面试官" /><div><span className="mock-pill">AI 模拟面试官 · 非真人</span><h2>{mockPhaseLabel[phase]}</h2><MockPlaybackIndicator player={voice.current} phase={phase} /><p>基于你的简历与你对话，不代表真实招聘结果。</p></div></aside><section className="mock-panel mock-conversation">
      {phase === "preparing" ? <><span className="eyebrow">开始前检查</span><h2>让这场面试围绕你展开</h2><label>选择已解析的简历<select aria-label="选择简历" value={session.resumeId ?? ""} disabled={busy || !connected} onChange={e => void action(async () => { const doc = resumes.find(r => r.documentId === e.target.value); if (doc) update(await mockRequest<MockSession>(`/mock-interviews/${id}/resume`, { version: session.state.version, documentId: doc.documentId, documentVersionId: doc.documentVersionId })); })}><option value="">请选择简历</option>{resumes.map(doc => <option key={doc.documentId} value={doc.documentId}>{doc.displayName}</option>)}</select></label>{resumes.length === 0 && <p><Link to="/app/library">先去资料页上传并解析简历</Link></p>}<label>桌面助手机器码<input inputMode="numeric" maxLength={6} value={machineCode} onChange={e => setMachineCode(e.target.value.replace(/\D/g, ""))} placeholder="6 位机器码" /></label><p className="mock-muted">现有正式版助手即可，无需为模拟面试升级。请开启麦克风权限和系统自动校时，建议佩戴耳机。</p><p className="mock-muted">仅使用麦克风，不使用系统声音。助手在提问期间可能仍采集上传，服务器会丢弃非回答时段的音频，不转写、不保存。</p><button className="button" disabled={busy || !connected || machineCode.length !== 6} onClick={() => void bindDevice()}>验证并连接</button><p role="status" aria-label="助手连接状态">{!connected ? "页面连接未就绪，请重新连接。" : bindingNotice || preparation?.message || (desktopConnected ? "● 助手已连接，开始后连接收音通道" : "请打开桌面助手，输入机器码后验证并连接。")}</p><button className="button primary" disabled={!connected || !desktopConnected || !session.resumeId || busy} onClick={() => void voice.current.unlock().then(() => command("start")).catch(cause => setError(errorText(cause)))}>开始模拟面试 →</button></> : <>
      <div className="mock-question-meta"><span>问题 {session.state.rounds.length} / 10</span><span>{desktopConnected ? "麦克风助手在线" : "助手未连接"}</span></div>{question && <h2 className="mock-question">{question.question}</h2>}
      {(phase === "generating_question" || phase === "generating_report") && <div role="status" className="mock-wait"><span className="mock-spinner" />{mockPhaseLabel[phase]}<small>等待期间不计分钟费，请不要重复创建。</small></div>}
      {session.error === "generation_unavailable" && <button className="button" disabled={!connected} onClick={() => command("retry")}>重试生成</button>}
      {waitingForMicrophone && phase === "speaking" && <p role="status" className="mock-wait">正在等待助手收音通道连接，等待期间不计分钟费。请保持助手运行，显示“轮到你回答”后再开口。</p>}
      {settlingAudio && phase === "speaking" && <p role="status" className="mock-wait">正在准备收音，请稍候片刻，显示“轮到你回答”后再开口。此阶段不计分钟费。</p>}
      {phase === "speaking" && <div className="mock-actions"><button className="button primary" disabled={!connected || playing || waitingForMicrophone || settlingAudio} onClick={() => { pendingListen.current = null; playingQuestion.current = question?.question_id ?? null; voice.current.stop(); playbackAcknowledged.current = false; setPlaying(true); void voice.current.unlock().then(() => command("speak")).catch(cause => setError(errorText(cause))); }}>朗读问题</button><button className="button" disabled={!connected || waitingForMicrophone || settlingAudio} onClick={() => { voice.current.stop(); playingQuestion.current = null; if (question) prepareListening(question.question_id); }}>我已读完，开始回答</button></div>}
      {(phase === "listening" || phase === "paused") && <><label>你的回答<textarea aria-label="你的回答" rows={8} value={draft} maxLength={8000} onChange={e => { edited.current = true; setEditing(true); draftText.current = e.target.value; setDraft(e.target.value); }} placeholder="请对着麦克风回答，也可在这里校正转写。" /></label><p className="mock-muted">{editing ? "已进入文字校正，新的转写不会覆盖你的修改。" : "思考和停顿不会自动进入下一题。确认回答后再提交。"}</p></>}
      <div className="mock-actions">{phase === "listening" && <><button className="button primary" disabled={!connected || !draft.trim()} onClick={() => { answerId.current ??= crypto.randomUUID(); command("submit", { answer: draft.trim(), submissionId: answerId.current }); }}>回答完成 →</button><button className="button" onClick={() => command("pause")} disabled={!connected}>暂停</button><button className="button" onClick={() => command("replay")} disabled={!connected}>重新听题</button></>}{phase === "paused" && <button className="button primary" disabled={!connected || !desktopConnected} onClick={() => command("resume")}>继续本题</button>}</div>
      </>}
      <footer className="mock-end"><p>结束后自动保存报告。不足 10 题将标注为部分练习。</p><button className="button" disabled={!connected || phase === "generating_report"} onClick={() => { if (window.confirm("结束本场练习并生成报告？主动结束不退创建费。")) { voice.current.stop(); command("end"); } }}>结束面试</button></footer>
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
