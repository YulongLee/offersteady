import { createContext, Suspense, useContext, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { BrowserRouter, Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import type { AnswerTaskSnapshot, CaptureState } from "@offersteady/protocol";

import type { InterviewQuestion, LiveActionState, QuestionStatus, ScreenshotTask, SessionStatus, WebAppState } from "./domain";
import { runAdapterOperation } from "./api-client";
import { interviewAppAdapter, runtimeConfig } from "./app-adapter";
import { DownloadCenter } from "./DownloadCenter";
import { LibraryManager } from "./LibraryManager";
import { routes } from "./routes";
import { ContextPicker } from "./ContextPicker";
import { contextLevel, eligibleSource, managedLibrarySources, selectionSources, selectionValidity } from "./context-selection";
import { BillingPage } from "./BillingPage";
import { GuidePage } from "./GuidePage";
import { assetUrl } from "./assets";
import { ConversationMonitor } from "./ConversationMonitor";
import { AnswerWorkspace } from "./AnswerWorkspace";
import { ManualQuestionComposer } from "./ManualQuestionComposer";
import { AnswerActionBar } from "./AnswerActionBar";
import { ABSOLUTE_MAX_SPLIT_RATIO, ABSOLUTE_MIN_SPLIT_RATIO, clampSplitRatio, initialLiveWorkspaceView, noteNewAnswer, parseStoredSplitRatio, serializeSplitRatio, splitRatioBounds, splitRatioStorageKey } from "./live-workspace";
import { WorkspaceDivider } from "./WorkspaceDivider";
import { authClient } from "./auth-client";
import "./styles.css";

interface PrototypeContextValue {
  authenticated: boolean;
  setAuthenticated(value: boolean): void;
  state: WebAppState;
  setState: React.Dispatch<React.SetStateAction<WebAppState>>;
  logout(): Promise<void>;
}

const PrototypeContext = createContext<PrototypeContextValue | null>(null);

const usePrototype = () => {
  const value = useContext(PrototypeContext);
  if (!value) throw new Error("Prototype context is unavailable");
  return value;
};

function PrototypeProvider({ children, initialAuthenticated, initialState }: { readonly children: ReactNode; readonly initialAuthenticated?: boolean | undefined; readonly initialState?: WebAppState | undefined }) {
  const [authenticated, setAuthenticatedState] = useState(() => initialAuthenticated ?? Boolean(authClient.readStoredSession()));
  const [state, setState] = useState<WebAppState | null>(() => initialState ? structuredClone(initialState) : null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!initialAuthenticated || !initialState?.account) return;
    if (authClient.readStoredSession()) return;
    const storedAccount = authClient.readStoredAccount();
    if (storedAccount?.id === initialState.account.id) return;
    authClient.bootstrapPrototypeIdentity(initialState.account);
  }, [initialAuthenticated, initialState]);

  useEffect(() => {
    const controller = new AbortController();
    if (!initialState) {
      const existing = authClient.readStoredSession();
      interviewAppAdapter.loadState(controller.signal, { auth: !existing })
        .then(next => {
          setState(existing ? { ...next, account: existing.account } : next);
          setLoadError("");
        })
        .catch(error => {
          setLoadError(error instanceof Error ? error.message : "后端页面状态加载失败");
        });
    }
    return () => controller.abort();
  }, [initialState]);

  useEffect(() => {
    if (initialState) return;
    const controller = new AbortController();
    const existing = authClient.readStoredSession();
    if (!existing) return () => controller.abort();
    void authClient.restore(controller.signal)
      .then(restored => {
        setAuthenticatedState(true);
        setState(current => current ? { ...current, account: restored.account } : current);
        return interviewAppAdapter.loadState(controller.signal);
      })
      .then(next => {
        setState(next);
        setLoadError("");
      })
      .catch(() => {
        if (authClient.readStoredSession()) {
          setAuthenticatedState(true);
          setState(current => current ? { ...current, account: existing.account } : current);
          return;
        }
        setAuthenticatedState(false);
      });
    return () => controller.abort();
  }, [initialState]);

  const setAuthenticated = (value: boolean) => {
    setAuthenticatedState(value);
  };

  const logout = async () => {
    await authClient.logout();
    setAuthenticated(false);
    try { setState(await interviewAppAdapter.loadState()); } catch { setState(current => current); }
  };

  if (!state && !loadError) return <RouteLoadingPage />;
  if (!state && loadError) return <IntegrationModeErrorPage message={loadError} />;

  if (!state) return <RouteLoadingPage />;
  return <PrototypeContext.Provider value={{ authenticated, setAuthenticated, state, setState: setState as React.Dispatch<React.SetStateAction<WebAppState>>, logout }}>{children}</PrototypeContext.Provider>;
}

const Logo = () => <span className="logo-lockup"><img src={assetUrl("brand.app-icon")} alt="" /><strong>面试稳</strong></span>;

function PublicLayout() {
  const { authenticated } = usePrototype();
  return (
    <div className="public-shell">
      <header className="public-nav">
        <Link to={routes.landing} aria-label="面试稳首页"><Logo /></Link>
        <nav aria-label="公开导航"><a href="#workflow">使用方式</a><a href="#privacy">隐私边界</a><Link className="button ghost" to={authenticated ? routes.app : routes.login}>{authenticated ? "进入应用" : "登录"}</Link></nav>
      </header>
      <Outlet />
    </div>
  );
}

function LandingPage() {
  const { state } = usePrototype(); const passes = state.billing.catalog.filter(item => item.kind === "time_pass");
  return (
    <main>
      <section className="landing-hero">
        <div>
          <span className="kicker">AI INTERVIEW COPILOT</span>
          <h1>AI 面试助手，<br />助你更从容地冲刺 Offer。</h1>
          <p>实时理解面试问题，结合你的简历、岗位要求和个人资料，快速生成清晰回答思路。语音、手动输入和截图题都支持。</p>
          <div className="hero-actions"><Link className="button primary large" to={routes.login}>免费使用 <span>→</span></Link><a className="text-link" href="#pricing-value">看看怎么收费</a></div>
          <div className="free-grant"><strong>200 点</strong><span>新用户体验额度<br />无需先付费</span></div>
          <div className="trust-list"><span>✓ 实时辅助</span><span>✓ 个性化回答</span><span>✓ 按自己的节奏使用</span></div>
        </div>
        <div className="answer-demo" aria-label="实时回答区域预览">
          <div className="demo-top"><span><i className="online-dot" /> 面试进行中</span><span>18:24</span></div>
          <small>当前问题</small><h2>请介绍一个最有挑战的项目</h2>
          <div className="demo-answer"><span className="advice-label">回答建议</span><ol><li>一句话交代项目背景与目标</li><li>聚焦你的职责与技术决策</li><li>用简历中可核对的结果收尾</li></ol><div className="source-pills"><span>简历</span><span>JD</span><span>知识库</span></div></div>
        </div>
      </section>
      <section id="workflow" className="public-section">
        <div className="section-intro"><span className="kicker">YOUR INTERVIEW RHYTHM</span><h2>从准备到现场，少一点慌乱</h2></div>
        <div className="workflow-grid"><article><b>01 · PERSONAL</b><h3>理解你的真实经历</h3><p>每场面试单独选择简历、JD 和知识材料，减少无关内容，也不替你虚构经历。</p></article><article><b>02 · REAL-TIME</b><h3>听懂问题，也看懂截图</h3><p>支持授权语音、手动输入和截图题；系统优先聚焦面试官问题，来源不清时会暂停自动回答并提示你改用手动输入。</p></article><article><b>03 · TRACEABLE</b><h3>知道建议从哪里来</h3><p>每条回答显示实际使用的资料名称与版本，资料和模型推断保持清晰分离。</p></article></div>
        <div className="advantage-strip"><div><strong>电脑端</strong><span>macOS 双芯片已规划，Windows 版本按签名状态逐步开放</span></div><div><strong>手机端</strong><span>同步查看回答和会话状态，不被单一设备绑住</span></div><div><strong>你的数据</strong><span>资料可管理、可删除，原始音频默认不保存</span></div></div>
      </section>
      <section id="pricing-value" className="public-section pricing-value"><div className="section-intro"><span className="kicker">FLEXIBLE & FAIR</span><h2>按你的面试节奏选择</h2><p>偶尔使用按点结算，面试密集期选择按天会员。新用户赠送 200 点体验额度，再按实际面试节奏购买。</p></div><div className="public-pricing-grid"><article><span>灵活按次</span><h3>积分使用</h3><strong>回答 5 点起</strong><p>知识材料 20 点起，完整 Token 规则可在积分页查看。</p><Link to={routes.login}>免费开始 →</Link></article><article className="featured"><span>短期高频</span><h3>按天会员</h3><strong>3 天 ¥{((passes.find(item => item.durationDays === 3)?.priceCents ?? 0) / 100).toFixed(2)} 起</strong><p>{passes.map(item => `${item.durationDays}天`).join(" / ")}；15 天和 30 天各含 2 份知识材料额度。</p><Link to={routes.login}>领取 200 点 →</Link></article></div></section>
      <section id="value-proof" className="public-section value-proof"><div className="section-intro"><span className="kicker">WHY OFFERSTEADY</span><h2>从听懂问题，到组织答案，现场更从容。</h2><p>结合你的简历、目标岗位和知识材料，快速抓住问题重点，生成清晰、贴合你的回答思路。</p></div><div className="value-proof-grid"><article><span>01</span><h3>实时抓住问题重点</h3><p>区分面试官与候选人的对话，让你把注意力放在真正需要回答的问题上。</p></article><article><span>02</span><h3>回答更贴合你的经历</h3><p>按场选择简历、JD 和知识材料，快速整理更相关的表达结构。</p></article><article><span>03</span><h3>按求职节奏灵活使用</h3><p>偶尔面试按点使用，密集面试选择短期会员，不必承担长期订阅。</p></article></div><div id="privacy" className="value-trust"><p>AI 内容为回答建议，重要经历请以真实情况为准；资料和会话记录可管理、可删除。</p><details><summary>查看使用与隐私说明</summary><p>原始音频默认不保存；简历、JD、截图和会话记录提供删除入口。请遵守面试规则并以真实经历作答。</p></details></div></section>
      <footer className="public-footer"><Logo /><span>© 2026 面试稳 · OneShow AI Lab</span></footer>
    </main>
  );
}

function LoginPage() {
  const { authenticated, setAuthenticated, setState } = usePrototype();
  const navigate = useNavigate();
  const location = useLocation();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [code, setCode] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState<"send" | "verify" | "">("");
  const [message, setMessage] = useState("");
  const destination = (location.state as { from?: string } | null)?.from ?? routes.app;
  const enter = () => { setAuthenticated(true); navigate(destination, { replace: true }); };
  const enterWithAccount = (account: WebAppState["account"]) => {
    setState(current => ({ ...current, account }));
    void interviewAppAdapter.loadState().then(next => setState(next)).catch(() => undefined);
    enter();
  };
  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setTimeout(() => setCooldown(value => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(id);
  }, [cooldown]);
  if (authenticated) return <Navigate to={destination} replace />;
  const sendCode = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("send");
    setMessage("");
    try {
      const response = await authClient.sendSmsCode(phoneNumber);
      setChallengeId(response.challengeId);
      setCooldown(response.cooldownSeconds);
      setMessage(`验证码已发送至 ${response.maskedPhone}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "验证码发送失败");
    } finally {
      setBusy("");
    }
  };
  const verifyCode = async (event: FormEvent) => {
    event.preventDefault();
    if (!challengeId) {
      setMessage("请先获取验证码");
      return;
    }
    setBusy("verify");
    setMessage("");
    try {
      const session = await authClient.verifySmsLogin({ phoneNumber, challengeId, code });
      enterWithAccount(session.account);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "登录失败，请稍后重试");
    } finally {
      setBusy("");
    }
  };
  return <main className="center-page"><section className="login-card"><Logo /><span className="prototype-badge">免费使用 · 新用户赠 200 点</span><h1>开始你的面试准备</h1><p>使用手机号验证码完成登录或注册，同一个账号可以管理资料、积分和不同设备上的面试。</p><form className="sms-login-form" onSubmit={challengeId ? verifyCode : sendCode}><label><span>手机号</span><input value={phoneNumber} onChange={event => setPhoneNumber(event.target.value)} inputMode="tel" autoComplete="tel" placeholder="请输入手机号" /></label>{challengeId ? <label><span>验证码</span><input value={code} onChange={event => setCode(event.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="请输入验证码" /></label> : null}<div className="sms-actions"><button className="button primary large full" type="submit" disabled={Boolean(busy)}>{busy === "verify" ? "登录中..." : challengeId ? "登录 / 注册" : busy === "send" ? "发送中..." : "获取验证码"}</button>{challengeId ? <button className="button ghost full" type="button" disabled={cooldown > 0 || Boolean(busy)} onClick={event => { void sendCode(event as unknown as FormEvent); }}>{cooldown > 0 ? `${cooldown}s 后重发` : "重新发送验证码"}</button> : null}</div></form>{message ? <p className="login-message">{message}</p> : null}<Link className="text-link login-back" to={routes.landing}>返回首页</Link><small>登录即表示你同意账号服务与隐私说明。验证码只用于账号识别和登录校验。</small></section></main>;
}

function ProtectedRoute() {
  const { authenticated } = usePrototype();
  const location = useLocation();
  return authenticated ? <Outlet /> : <Navigate to={routes.login} state={{ from: location.pathname }} replace />;
}

const navItems = [
  { to: routes.app, label: "面试", icon: "◫", end: true },
  { to: routes.library, label: "资料", icon: "◇" },
  { to: routes.billing, label: "积分", icon: "点" },
  { to: routes.guide, label: "使用说明", icon: "?" },
  { to: routes.devices, label: "设备", icon: "⌘" },
  { to: routes.settings, label: "设置", icon: "○" },
];

function AppLayout() {
  const { logout, state } = usePrototype();
  const initials = state.account.displayName.slice(0, 2).toUpperCase();
  return (
    <div className="app-shell">
      <aside className="app-sidebar"><Link to={routes.app}><Logo /></Link><nav aria-label="应用导航">{navItems.map(item => <NavLink key={item.to} to={item.to} {...(item.end ? { end: true } : {})}><span>{item.icon}</span>{item.label}</NavLink>)}</nav><div className="sidebar-foot"><span className="privacy-note">音频默认不保存</span><button className="user-chip" onClick={() => void logout()} aria-label="退出登录"><i>{initials}</i><span>{state.account.displayName}<small>退出登录</small></span></button></div></aside>
      <div className="app-content"><Outlet /></div>
      <nav className="mobile-nav" aria-label="移动端应用导航">{navItems.map(item => <NavLink key={item.to} to={item.to} {...(item.end ? { end: true } : {})}><span>{item.icon}</span><small>{item.label}</small></NavLink>)}</nav>
    </div>
  );
}

function PageHeader({ eyebrow, title, detail, action }: { readonly eyebrow: string; readonly title: string; readonly detail?: string; readonly action?: ReactNode }) {
  return <header className="page-header"><div><span className="kicker">{eyebrow}</span><h1>{title}</h1>{detail ? <p>{detail}</p> : null}</div>{action}</header>;
}

export const interviewContinuationRoute = (interview: Pick<WebAppState["interviews"][number], "id" | "status">) => interview.status === "ended"
  ? routes.review(interview.id)
  : interview.status === "active" || interview.status === "paused" || interview.status === "error"
    ? routes.live(interview.id)
    : routes.prepare(interview.id);

const sessionStatusLabel: Record<SessionStatus, string> = { preparing: "准备中", ready: "待开始", active: "进行中", paused: "已暂停", ended: "已结束", error: "待恢复" };

const emptyLiveQuestion: InterviewQuestion = {
  id: "empty-live-question",
  askedAt: "等待中",
  text: "等待面试问题",
  input: "manual",
  status: "listening",
  advice: {
    outline: [],
    detail: "当前还没有来自后端的面试问题记录。",
    sourceTypes: [],
    inference: "",
    uncertain: true,
    provenance: { selectionRevision: 0, usedSources: [] },
  },
};

const normalizeQuickAnswerText = (text: string) => text.replace(/\s+/g, " ").trim();

const extractLatestInterviewerQuestion = (speaker: WebAppState["speaker"]) => {
  const latestBySegment = new Map<string, WebAppState["speaker"]["transcripts"][number]>();
  for (const segment of speaker.transcripts) {
    const current = latestBySegment.get(segment.id);
    if (!current || segment.revision > current.revision) latestBySegment.set(segment.id, segment);
  }
  const interviewerSegments = [...latestBySegment.values()]
    .filter(segment => (segment.sourceKind === "system" || segment.role === "interviewer") && segment.text.trim())
    .sort((left, right) => right.endedAtMs - left.endedAtMs);
  const detectedQuestion = normalizeQuickAnswerText(speaker.pendingQuestion?.text ?? "");
  if (interviewerSegments.length === 0) return detectedQuestion;
  const latest = interviewerSegments[0]!;
  const latestCandidateEndedAt = [...speaker.transcripts]
    .filter(segment => segment.role === "candidate" && segment.isFinal && segment.endedAtMs <= latest.startedAtMs)
    .sort((left, right) => right.endedAtMs - left.endedAtMs)[0]?.endedAtMs ?? -Infinity;
  const eligibleFinalSegments = interviewerSegments.filter(segment => segment.isFinal && segment.endedAtMs > latestCandidateEndedAt);
  const latestFinal = eligibleFinalSegments[0];
  const newestPartial = !latest.isFinal && (!latestFinal || latest.endedAtMs > latestFinal.endedAtMs) ? latest : null;
  const merged = latestFinal ? [latestFinal] : [];
  for (const segment of eligibleFinalSegments.filter(segment => segment.id !== latestFinal?.id)) {
    if (segment.endedAtMs <= latestCandidateEndedAt) break;
    const gap = (merged[merged.length - 1]?.startedAtMs ?? latest.startedAtMs) - segment.endedAtMs;
    if (gap > 12_000) break;
    if (merged.length >= 4) break;
    merged.push(segment);
  }
  if (newestPartial && newestPartial.endedAtMs > latestCandidateEndedAt) merged.unshift(newestPartial);
  const ordered = merged.sort((left, right) => left.startedAtMs - right.startedAtMs);
  const mergedTexts: string[] = [];
  for (const segment of ordered) {
    const text = normalizeQuickAnswerText(segment.text);
    if (!text) continue;
    const previous = mergedTexts.at(-1);
    if (previous && (previous.includes(text) || text.includes(previous))) {
      mergedTexts[mergedTexts.length - 1] = text.length >= previous.length ? text : previous;
      continue;
    }
    mergedTexts.push(text);
  }
  if (detectedQuestion) {
    const duplicateIndex = mergedTexts.findIndex(text => text.includes(detectedQuestion) || detectedQuestion.includes(text));
    if (duplicateIndex >= 0) {
      const current = mergedTexts[duplicateIndex]!;
      mergedTexts[duplicateIndex] = detectedQuestion.length >= current.length ? detectedQuestion : current;
    } else {
      mergedTexts.push(detectedQuestion);
    }
  }
  return mergedTexts.join(" ").trim();
};

function useDesktopLiveLayout() {
  const query = "(min-width: 1051px)";
  const [desktop, setDesktop] = useState(() => typeof window.matchMedia === "function" ? window.matchMedia(query).matches : window.innerWidth > 1050);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") { const update = () => setDesktop(window.innerWidth > 1050); window.addEventListener("resize", update); return () => window.removeEventListener("resize", update); }
    const media = window.matchMedia(query); const update = () => setDesktop(media.matches); update(); media.addEventListener?.("change", update); return () => media.removeEventListener?.("change", update);
  }, []);
  return desktop;
}

function HomePage() {
  const { state, setState } = usePrototype();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const recentInterviews = state.interviews.slice(0, 5);
  const materialSources = state.librarySources.filter(source => source.status !== "deleted" && source.status !== "disabled");
  const readyMaterials = materialSources.filter(source => source.status === "ready" && source.syncStatus !== "missing_artifacts");
  const processingMaterials = materialSources.filter(source => source.status === "processing");
  const materialCount = (kind: "resume" | "jd" | "knowledge") => materialSources.filter(source => source.kind === kind).length;
  const readyMaterialCount = (kind: "resume" | "jd" | "knowledge") => readyMaterials.filter(source => source.kind === kind).length;
  const active = recentInterviews.find(item => item.status !== "ended");
  const hour = new Date().getHours(); const greeting = Number.isFinite(hour) ? hour < 5 ? "夜深了" : hour < 11 ? "早上好" : hour < 14 ? "中午好" : hour < 18 ? "下午好" : "晚上好" : "你好";
  const title = active ? "继续这场面试" : "准备好下一场面试了吗？";
  const deleteRecentInterview = async (interviewId: string) => {
    if (!window.confirm("确认删除这场面试？对应问题、回答与附件会一起删除。")) return;
    setDeleteError("");
    setDeletingId(interviewId);
    try {
      await runAdapterOperation(signal => interviewAppAdapter.deleteInterview(interviewId, signal));
      try {
        const next = await runAdapterOperation(signal => interviewAppAdapter.loadState(signal));
        setState(next);
      } catch {
        setState(current => ({ ...current, interviews: current.interviews.filter(item => item.id !== interviewId) }));
      }
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "删除失败，请稍后重试。");
    } finally {
      setDeletingId(null);
    }
  };
  return <main className="app-page"><PageHeader eyebrow={`${greeting} · INTERVIEW HOME`} title={title} detail={active ? "资料、设备和面试状态都在这里，接着上次的进度继续。" : "创建面试并选择对应资料，让每个回答更贴近目标岗位。"} action={<Link className="button primary" to={routes.newInterview}>＋ 新建面试</Link>} />
    {active ? <section className="continue-card"><div><span className="live-chip"><i /> {sessionStatusLabel[active.status]}</span><h2>{active.title}</h2><p>{active.company} · {active.role}</p><div className="progress-line"><i style={{ width: `${active.readiness}%` }} /></div><small>准备完成 {active.readiness}% · 简历、JD 与知识库按本场选择</small></div><div className="continue-actions"><Link className="button primary" to={interviewContinuationRoute(active)}>继续面试</Link></div></section> : <EmptyState title="创建第一场面试" detail="用合成资料走完准备、现场和复盘流程。" action={<Link className="button primary" to={routes.newInterview}>开始创建</Link>} />}
    <section className="dashboard-grid"><div className="panel"><div className="panel-heading"><h2>最近面试</h2><span>{recentInterviews.length} / 5 场</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}<div className="interview-list">{recentInterviews.map(item => <article key={item.id} className="recent-interview-row"><Link to={interviewContinuationRoute(item)}><span className={`status-icon ${item.status}`}>{item.status === "ended" ? "✓" : "↗"}</span><div><strong>{item.title}</strong><small>{item.updatedAt} · {sessionStatusLabel[item.status]}</small></div><span>→</span></Link><button type="button" disabled={deletingId === item.id} onClick={() => void deleteRecentInterview(item.id)}>{deletingId === item.id ? "删除中…" : "删除"}</button></article>)}</div></div><div className="panel readiness-panel"><div className="panel-heading"><h2>通用资料</h2><Link to={routes.library}>管理</Link></div><div className="readiness-ring"><strong>{readyMaterials.length}</strong><span>份已就绪</span></div><ul className="compact-list"><li><span>简历</span><b>{readyMaterialCount("resume")} / {materialCount("resume")} 份可用</b></li><li><span>职位 JD</span><b>{readyMaterialCount("jd")} / {materialCount("jd")} 份可用</b></li><li><span>知识材料</span><b>{readyMaterialCount("knowledge")} / {materialCount("knowledge")} 份可用</b></li></ul>{processingMaterials.length ? <small>{processingMaterials.length} 份资料正在后台处理中</small> : null}</div></section>
  </main>;
}

function EmptyState({ title, detail, action }: { readonly title: string; readonly detail: string; readonly action?: ReactNode }) { return <section className="empty-state"><span>◇</span><h2>{title}</h2><p>{detail}</p>{action}</section>; }

function NewInterviewPage() {
  const navigate = useNavigate();
  const { setState } = usePrototype();
  const [form, setForm] = useState(() => {
    if (typeof window.sessionStorage?.getItem !== "function") return { title: "", role: "", company: "" };
    const saved = window.sessionStorage.getItem("offersteady.last-draft");
    if (!saved) return { title: "", role: "", company: "" };
    try { return JSON.parse(saved) as { title: string; role: string; company: string }; } catch { return { title: "", role: "", company: "" }; }
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.title.trim() || !form.role.trim()) { setError("请填写面试名称和目标岗位"); return; }
    setError("");
    setSaving(true);
    try {
      const draft = await runAdapterOperation(signal => interviewAppAdapter.createDraft(form, signal));
      setState(current => ({ ...current, interviews: [draft, ...current.interviews.filter(item => item.id !== draft.id)].slice(0, 5), contextSelections: { ...current.contextSelections, [draft.id]: { sessionId: draft.id, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null } } }));
      if (typeof window.sessionStorage?.setItem === "function") window.sessionStorage.setItem("offersteady.last-draft", JSON.stringify(form));
      navigate(routes.prepare(draft.id));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建面试失败，请稍后重试。");
    } finally {
      setSaving(false);
    }
  };
  return <main className="app-page narrow"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="NEW INTERVIEW" title="创建一场面试" detail="先给这场面试一个清晰目标，资料可以在下一步补充。" /><form className="form-panel" onSubmit={submit}><label>面试名称<input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="例如：高级前端工程师一面" /></label><label>目标岗位<input value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} placeholder="例如：高级前端工程师" /></label><label>公司（可选）<input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} placeholder="例如：示例科技" /></label>{error ? <div className="inline-error" role="alert">{error}</div> : null}<div className="form-actions"><Link className="button ghost" to={routes.app}>取消</Link><button className="button primary" type="submit" disabled={saving}>{saving ? "创建中…" : "保存并准备 →"}</button></div><small className="saved-note">草稿只在你确认提交后保存。</small></form></main>;
}

function PreparationPage() {
  const { id = "demo" } = useParams();
  const { state, setState } = usePrototype();
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState("");
  const [materialConfirmError, setMaterialConfirmError] = useState("");
  const [confirmingMaterials, setConfirmingMaterials] = useState(false);
  const [machineCode, setMachineCode] = useState("");
  const [deviceBinding, setDeviceBinding] = useState<Awaited<ReturnType<typeof interviewAppAdapter.getDesktopDeviceBinding>> | null>(() => state.preparation.device?.connected ? {
    bindingId: `state-device:${state.preparation.device.deviceId}`,
    sessionId: id,
    deviceId: state.preparation.device.deviceId,
    manualCode: "000000",
    displayName: state.preparation.device.displayName,
    capabilities: { microphone: state.preparation.device.capabilities.microphone, systemAudio: state.preparation.device.capabilities.systemAudio },
    status: "bound",
    boundAtMs: Date.now(),
    lastSeenAtMs: state.preparation.device.lastSeenAtMs,
  } : null);
  const [binding, setBinding] = useState(false);
  const [bindingError, setBindingError] = useState("");
  const selection = state.contextSelections[id] ?? state.contextSelections.demo!;
  const managedSources = managedLibrarySources(state.librarySources, state.account.id);
  const validity = selectionValidity(managedSources, selection);
  const level = contextLevel(selection);
  const selectionReady = validity === "valid";
  const machineReady = Boolean(deviceBinding);
  const audioReady = Boolean(machineReady && (deviceBinding?.capabilities.microphone === true || deviceBinding?.capabilities.microphone === "granted") && (deviceBinding?.capabilities.systemAudio === true || deviceBinding?.capabilities.systemAudio === "granted"));
  const canStart = selectionReady && machineReady;
  const complete = Number(selectionReady) + Number(machineReady);
  const inputDiagnostic = audioReady
      ? "已绑定本场收音机器，进入后会同步面试官和我的对话"
      : state.preparation.device?.connected
      ? "本地端会继续检查收音、系统音频和问题检测"
      : "请输入桌面伴随程序中的 6 位机器码，绑定本场收音机器";
  const saveSelection = async (next: typeof selection) => {
    if (confirmingMaterials) return;
    setConfirmingMaterials(true);
    setMaterialConfirmError("");
    try {
      const confirmed = await runAdapterOperation(signal => interviewAppAdapter.confirmInterviewMaterials(next, signal));
      setState(current => ({
        ...current,
        contextSelections: { ...current.contextSelections, [id]: confirmed },
        interviews: current.interviews.map(item => item.id === id ? { ...item, readiness: confirmed.confirmedAtMs ? 100 : 0 } : item),
      }));
    } catch (error) {
      setMaterialConfirmError(error instanceof Error ? error.message : "确认本场资料失败，请稍后重试。");
    } finally {
      setConfirmingMaterials(false);
    }
  };
  useEffect(() => {
    const controller = new AbortController();
    void runAdapterOperation(signal => interviewAppAdapter.getDesktopDeviceBinding(id, signal), controller.signal)
      .then(binding => {
        if (!binding) return;
        setDeviceBinding(binding);
        setMachineCode(binding.manualCode);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [id]);
  useEffect(() => {
    if (!deviceBinding) return;
    let stopped = false;
    const heartbeat = async () => {
      try {
        await runAdapterOperation(signal => interviewAppAdapter.sendDesktopSessionHeartbeat({
          interviewId: id,
          bindingId: deviceBinding.bindingId,
          page: "preparation",
        }, signal));
      } catch {
        // Heartbeat is retried in the background; do not replace user-facing bind/start errors.
      }
    };
    void heartbeat();
    const timer = window.setInterval(() => void heartbeat(), 3000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [id, deviceBinding?.bindingId]);
  const bindMachineCode = async () => {
    const code = machineCode.trim();
    if (!/^[0-9]{6}$/.test(code)) { setBindingError("请输入电脑伴随程序显示的 6 位机器码"); return; }
    setBinding(true); setBindingError("");
    try {
      const result = await runAdapterOperation(signal => interviewAppAdapter.bindDesktopDevice({ interviewId: id, manualCode: code }, signal));
      setDeviceBinding(result);
    } catch (error) {
      setBindingError(error instanceof Error ? error.message : "机器码验证失败，请确认电脑伴随程序已打开。");
    } finally {
      setBinding(false);
    }
  };
  const startInterview = async () => {
    if (!canStart || starting) return;
    setStarting(true); setStartError("");
    try {
      const started = await runAdapterOperation(signal => interviewAppAdapter.startInterviewSession(id, signal));
      setState(current => ({ ...current, interviews: current.interviews.map(item => item.id === id ? { ...item, ...started, status: "active" } : item) }));
      navigate(routes.live(id));
    } catch (error) {
      setStartError(error instanceof Error ? error.message : "开始面试失败，请稍后重试。");
    } finally {
      setStarting(false);
    }
  };
  return <main className="app-page"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="PREPARATION" title="高级前端工程师面试" detail="资料与“面试资料”页面保持一致，为本场按需选择。" action={<div className="completion"><strong>{complete}/2</strong><span>可进入</span></div>} />
    <div className="prepare-grid"><section className="panel"><ContextPicker sources={managedSources} selection={selection} onSave={saveSelection} />{confirmingMaterials ? <div className="context-warning" role="status">正在提交后端校验并保存本场资料…</div> : null}{materialConfirmError ? <div className="context-warning" role="alert">{materialConfirmError}</div> : null}</section>
      <aside className="panel check-panel"><div className="panel-heading"><h2>开始前检查</h2><span>{canStart ? "可进入" : !selectionReady ? "待确认资料" : "待绑定机器"}</span></div><ul className="check-list"><li className={selectionReady ? "done" : ""}><i>{selectionReady ? "✓" : "1"}</i><div><strong>本场资料</strong><span>{validity === "unconfirmed" ? "请选择资料或确认不使用资料" : validity === "attention-required" ? "所选资料已失效，请处理" : level === "none" ? "已确认不使用个人资料" : level === "personalized" ? "简历与 JD 已选择" : "已确认使用部分资料"}</span></div></li><li className={machineReady ? "done" : ""}><i>{machineReady ? "✓" : "2"}</i><div><strong>收音机器</strong><span>{inputDiagnostic}</span></div></li></ul>
        <div className="machine-code-panel">
          <label><span>机器码验证</span><input inputMode="numeric" maxLength={6} value={machineCode} onChange={event => setMachineCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="输入 6 位机器码" /></label>
          <button className="button ghost" disabled={binding || machineReady && machineCode === deviceBinding?.manualCode} onClick={() => void bindMachineCode()}>{binding ? "验证中…" : machineReady ? "重新验证" : "验证并绑定"}</button>
          <small>{deviceBinding ? `已绑定：${deviceBinding.displayName} · ${deviceBinding.manualCode}` : "打开电脑伴随程序，复制其中的 6 位验证码后输入。"}</small>
          {bindingError ? <div className="inline-error" role="alert">{bindingError}</div> : null}
        </div>
        <div className="device-mini"><span className="device-glyph">⌘</span><div><strong>{deviceBinding?.displayName ?? state.preparation.device?.displayName ?? "电脑伴随程序"}</strong><small>{deviceBinding ? "已绑定到本场面试；进入后会同步本机音频和屏幕监控状态" : "未绑定前不能开始面试，避免收音机器和面试场次不一致"}</small></div><Link to={routes.devices}>管理</Link></div>
        <div className="privacy-confirm preparation-disclosure"><span><strong>本场数据说明</strong><small>已选资料和转录仅用于生成回答建议；原始音频默认不保存，会话记录可在复盘中删除。启用音频或上传截图时会分别确认。</small></span></div>
        <div className="points-mini"><strong>{state.billing.balance} 点</strong><span>回答 5 点 · 截图 15 点</span><Link to={routes.billing}>查看收费说明</Link><Link to={`${routes.guide}#quick-start`}>准备流程说明</Link></div>
        {startError ? <div className="inline-error" role="alert">{startError}</div> : null}<button className="button primary full" disabled={!canStart || starting} onClick={() => void startInterview()}>{starting ? "正在开始面试…" : "开始面试 →"}</button>{!selectionReady ? <small className="blocked-help">确认本场资料选择（可以为空）后继续。</small> : !machineReady ? <small className="blocked-help">请输入并验证电脑伴随程序的 6 位机器码，确保本场面试使用同一台收音机器。</small> : level === "none" ? <small className="blocked-help context-disclosure">本场未使用个人资料，回答将更通用，也不会自动读取其他资料。进入面试不会自动开始收音。</small> : <small className="blocked-help context-disclosure">本地端会在连接后检查音频与问题检测；进入面试后，实时对话会按“面试官 / 我”展示双通道转录。</small>}
      </aside></div>
  </main>;
}

function LivePage() {
  const { id = "demo" } = useParams();
  const { state, setState } = usePrototype();
  const navigate = useNavigate();
  const storageKey = splitRatioStorageKey(id);
  const [view, setView] = useState(() => initialLiveWorkspaceView(parseStoredSplitRatio(typeof window.sessionStorage?.getItem === "function" ? window.sessionStorage.getItem(storageKey) : null)));
  const [actionState, setActionState] = useState<Omit<LiveActionState, "pendingQuestion">>({ manualDraft: "", screenshotTask: null });
  const [notice, setNotice] = useState("");
  const [cancellingAnswer, setCancellingAnswer] = useState(false);
  const [cancelAnswerError, setCancelAnswerError] = useState("");
  const [splitBounds, setSplitBounds] = useState({ min: ABSOLUTE_MIN_SPLIT_RATIO, max: ABSOLUTE_MAX_SPLIT_RATIO });
  const workspaceRef = useRef<HTMLDivElement>(null);
  const desktopLayout = useDesktopLiveLayout();
  const submittedCommands = useRef(new Set<string>());
  const previousLatestId = useRef(state.questions[0]?.id);
  const screenshotController = useRef<AbortController | null>(null);
  const manualAnswerController = useRef<AbortController | null>(null);
  const active = state.questions[0] ?? emptyLiveQuestion;
  const screenshot = actionState.screenshotTask;
  const setScreenshot = (next: ScreenshotTask | null) => setActionState(current => ({ ...current, screenshotTask: next }));
  const contextSelection = state.contextSelections[id] ?? { sessionId: id, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null };
  const selectedContextSources = selectionSources(managedLibrarySources(state.librarySources, state.account.id).filter(eligibleSource), contextSelection);
  useEffect(() => { if (typeof window.sessionStorage?.setItem === "function") window.sessionStorage.setItem(storageKey, serializeSplitRatio(view.splitRatio)); }, [storageKey, view.splitRatio]);
  useEffect(() => {
    if (!desktopLayout) return;
    const updateBounds = () => { const width = workspaceRef.current?.getBoundingClientRect().width ?? 0; if (!width) return; const next = splitRatioBounds(width); setSplitBounds(next); setView(current => ({ ...current, splitRatio: clampSplitRatio(current.splitRatio, next) })); };
    updateBounds(); window.addEventListener("resize", updateBounds); const observer = typeof ResizeObserver === "function" ? new ResizeObserver(updateBounds) : null; if (workspaceRef.current) observer?.observe(workspaceRef.current); return () => { window.removeEventListener("resize", updateBounds); observer?.disconnect(); };
  }, [desktopLayout]);
  useEffect(() => { const nextLatestId = state.questions[0]?.id; setView(current => noteNewAnswer(current, previousLatestId.current, nextLatestId)); previousLatestId.current = nextLatestId; }, [state.questions]);
  useEffect(() => () => { screenshotController.current?.abort(); manualAnswerController.current?.abort(); }, []);
  useEffect(() => {
    let stopped = false;
    let heartbeatBindingId: string | null = null;
    let reconnectTimer: number | null = null;
    let realtimeLoadInFlight = false;
    const realtimeController = new AbortController();
    const applyRealtimeState = (realtime: Pick<WebAppState, "speaker"> & Partial<Pick<WebAppState, "captureState">>) => {
      if (stopped) return;
      setState(current => ({
        ...current,
        speaker: realtime.speaker,
        ...(realtime.captureState ? { captureState: realtime.captureState } : {}),
      }));
    };
    const sendHeartbeat = async () => {
      try {
        if (!heartbeatBindingId || document.visibilityState === "visible") {
          const binding = await runAdapterOperation(signal => interviewAppAdapter.getDesktopDeviceBinding(id, signal));
          if (binding?.bindingId) heartbeatBindingId = binding.bindingId;
        }
        await runAdapterOperation(signal => interviewAppAdapter.sendDesktopSessionHeartbeat({ interviewId: id, bindingId: heartbeatBindingId, page: "live" }, signal));
      } catch {
        // Realtime polling below will continue to surface backend connectivity issues without blocking manual answers.
      }
    };
    const loadRealtime = async () => {
      if (realtimeLoadInFlight || stopped || document.visibilityState !== "visible") return;
      realtimeLoadInFlight = true;
      try {
        const realtime = await runAdapterOperation(signal => interviewAppAdapter.loadRealtimeSession(id, signal));
        applyRealtimeState(realtime);
      } catch {
        // Keep manual question and screenshot flows available when realtime sync is temporarily unavailable.
      } finally {
        realtimeLoadInFlight = false;
      }
    };
    const scheduleReconnect = () => {
      if (stopped || realtimeController.signal.aborted) return;
      reconnectTimer = window.setTimeout(() => { void subscribeRealtime(); }, 250);
    };
    const subscribeRealtime = async () => {
      try {
        await runAdapterOperation(signal => interviewAppAdapter.subscribeRealtimeSession(id, applyRealtimeState, signal), realtimeController.signal);
        if (!stopped && !realtimeController.signal.aborted) scheduleReconnect();
      } catch {
        if (stopped || realtimeController.signal.aborted) return;
        await loadRealtime();
        scheduleReconnect();
      }
    };
    void sendHeartbeat();
    const heartbeatTimer = window.setInterval(() => void sendHeartbeat(), 3000);
    const realtimePollTimer = window.setInterval(() => void loadRealtime(), 1000);
    const sendForegroundHeartbeat = () => {
      if (!stopped && document.visibilityState === "visible") void sendHeartbeat();
    };
    document.addEventListener("visibilitychange", sendForegroundHeartbeat);
    window.addEventListener("focus", sendForegroundHeartbeat);
    window.addEventListener("online", sendForegroundHeartbeat);
    void loadRealtime();
    void subscribeRealtime();
    return () => {
      stopped = true;
      realtimeController.abort();
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      window.clearInterval(heartbeatTimer);
      window.clearInterval(realtimePollTimer);
      document.removeEventListener("visibilitychange", sendForegroundHeartbeat);
      window.removeEventListener("focus", sendForegroundHeartbeat);
      window.removeEventListener("online", sendForegroundHeartbeat);
    };
  }, [id, setState]);
  const scopedAdvice = {
    ...active.advice,
    detail: selectedContextSources.length ? active.advice.detail : "当前没有选择个人资料。请使用通用结构组织回答，并只补充你能够核对的真实经历、职责和结果。",
    sourceTypes: selectedContextSources.map(source => source.kind === "resume" ? "简历" as const : source.kind === "jd" ? "JD" as const : "知识库" as const),
    inference: "",
    uncertain: selectedContextSources.length === 0,
    provenance: { selectionRevision: contextSelection.revision, usedSources: selectedContextSources.map(source => ({ sourceId: source.id, sourceVersion: source.version, displayName: source.displayName, kind: source.kind })) },
  };
  const charge = (points: number, reference: string) => {
    if (submittedCommands.current.has(reference)) return false;
    if (state.billing.activePass) { submittedCommands.current.add(reference); return true; }
    if (state.billing.balance < points) { setNotice("积分不足，请先购买积分或开通会员"); return false; }
    submittedCommands.current.add(reference);
    setState(current => ({ ...current, billing: { ...current.billing, balance: current.billing.balance - points, ledger: [{ id: `usage-${reference}`, userId: current.account.id, kind: "usage_reserve", points: -points, createdAtMs: Date.now(), referenceId: reference, description: "回答积分预留" }, ...current.billing.ledger] } }));
    return true;
  };
  const activeTaskFor = (question: InterviewQuestion, usageId: string): AnswerTaskSnapshot => ({ id: `answer:${question.id}:${Date.now()}`, interviewId: id, userId: state.account.id, billingUsageId: usageId, questionId: question.id, question: question.text, revision: 1, status: "generating", partialText: "正在整理回答结构…", updatedAtMs: Date.now() });
  const pendingManualQuestion = (text: string, questionId: string): InterviewQuestion => ({
    ...active,
    id: questionId,
    text,
    input: "manual",
    askedAt: "刚刚",
    status: "generating",
    advice: {
      ...scopedAdvice,
      detail: "正在调用当前对话模型生成回答…",
      outline: [],
      inference: "",
      uncertain: selectedContextSources.length === 0,
    },
  });
  const failedManualQuestion = (question: InterviewQuestion, message = "回答生成失败，请稍后重试。"): InterviewQuestion => ({
    ...question,
    status: "failed",
    advice: {
      ...question.advice,
      outline: [],
      detail: message,
      inference: "",
      uncertain: true,
    },
  });
  const submitManualText = async (text: string, replaceQuestionId?: string) => {
    const trimmed = text.trim(); if (!trimmed) return;
    const command = `manual:${id}:${trimmed}`; if (submittedCommands.current.has(command)) return;
    submittedCommands.current.add(command); setNotice("");
    const pendingId = replaceQuestionId ?? `manual-pending-${Date.now()}`;
    const pendingQuestion = pendingManualQuestion(trimmed, pendingId);
    const pendingTask: AnswerTaskSnapshot = { id: `pending:${pendingId}`, interviewId: id, userId: state.account.id, billingUsageId: `pending:${pendingId}`, questionId: pendingId, question: trimmed, revision: 1, status: "generating", partialText: "正在调用当前对话模型生成回答…", updatedAtMs: Date.now() };
    setState(current => ({ ...current, questions: replaceQuestionId ? current.questions.map(item => item.id === replaceQuestionId ? pendingQuestion : item) : [pendingQuestion, ...current.questions], activeAnswerTask: pendingTask }));
    setActionState(current => ({ ...current, manualDraft: "" }));
    setView(current => current.viewingAnswerId ? { ...current, newAnswerAvailable: true } : current);
    try {
      manualAnswerController.current?.abort();
      const controller = new AbortController();
      manualAnswerController.current = controller;
      const result = await runAdapterOperation(signal => interviewAppAdapter.submitManualAnswer({ interviewId: id, question: trimmed, idempotencyKey: command }, signal, ({ result: update }) => {
        setState(current => ({
          ...current,
          questions: [update.question, ...current.questions.filter(item => item.id !== pendingId && item.id !== update.question.id)],
          activeAnswerTask: update.task,
        }));
      }), controller.signal);
      setState(current => ({ ...current, questions: [result.question, ...current.questions.filter(item => item.id !== pendingId && item.id !== result.question.id)], activeAnswerTask: result.task }));
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (error instanceof Error && error.message === "请求已取消") return;
      const message = error instanceof Error ? error.message : "回答生成失败，请稍后重试。";
      setNotice(message);
      setState(current => ({ ...current, questions: current.questions.map(item => item.id === pendingId ? failedManualQuestion(item, message) : item), activeAnswerTask: current.activeAnswerTask?.questionId === pendingId ? { ...current.activeAnswerTask, status: "failed", partialText: message, updatedAtMs: Date.now() } : current.activeAnswerTask }));
    } finally {
      manualAnswerController.current = null;
      submittedCommands.current.delete(command);
    }
  };
  const latestInterviewerQuestion = () => extractLatestInterviewerQuestion(state.speaker);
  const latestInterviewerText = latestInterviewerQuestion();
  const submitManual = () => {
    const fallback = latestInterviewerQuestion();
    const question = actionState.manualDraft.trim() || fallback;
    if (!question) { setNotice("还没有可用于快答的面试官问题，请先输入问题或等待实时对话同步。"); return; }
    void submitManualText(question);
  };
  const setCapture = (captureState: CaptureState, status: SessionStatus) => setState(current => current.captureState === captureState ? current : ({ ...current, captureState, interviews: current.interviews.map(item => item.id === id ? { ...item, status } : item) }));
  const updateQuestionStatus = (questionId: string, status: QuestionStatus) => {
    const question = state.questions.find(item => item.id === questionId);
    if (!question) return;
    if (question.status === "cancelled" && status === "generating") {
      if (question.input === "manual") { void submitManualText(question.text, questionId); return; }
      const usageId = `retry:${questionId}:${Date.now()}`; if (!charge(state.billing.rates.answerPoints, usageId)) return;
      const task: AnswerTaskSnapshot = { id: `answer:${questionId}:${Date.now()}`, interviewId: id, userId: state.account.id, billingUsageId: usageId, questionId, question: question.text, revision: 1, status: "generating", partialText: "正在重新整理回答…", updatedAtMs: Date.now() };
      setState(current => ({ ...current, questions: current.questions.map(item => item.id === questionId ? { ...item, status } : item), activeAnswerTask: task }));
      return;
    }
    setState(current => ({ ...current, questions: current.questions.map(item => item.id === questionId ? { ...item, status } : item) }));
  };
  const screenshotInstruction = (latestQuestion: string) => latestQuestion.trim()
    ? `请结合当前截图，直接回答这道题。如果截图内容与问题存在差异，以截图内容为准。面试官最近的问题是：${latestQuestion.trim()}`
    : "请直接识别当前截图中的题目、代码或系统设计内容，并给出可直接使用的中文回答。";
  const submitScreenshot = async () => {
    const usageId = `screenshot:remote:${Date.now()}`; if (!charge(state.billing.rates.screenshotAnswerPoints, usageId)) return;
    const latestQuestion = latestInterviewerQuestion();
    const instruction = screenshotInstruction(latestQuestion);
    const placeholderId = `shot-pending-${Date.now()}`;
    const placeholderQuestion: InterviewQuestion = {
      ...active,
      id: placeholderId,
      text: latestQuestion.trim() || "请根据当前截图直接回答",
      input: "screenshot",
      askedAt: "刚刚",
      status: "generating",
      advice: scopedAdvice,
    };
    const placeholderTask = activeTaskFor(placeholderQuestion, usageId);
    setState(current => ({ ...current, questions: [placeholderQuestion, ...current.questions], activeAnswerTask: placeholderTask }));
    try {
      const result = await runAdapterOperation(signal => interviewAppAdapter.submitScreenshotAnswer({
        interviewId: id,
        instruction,
      }, signal, task => setScreenshot(task)), screenshotController.current?.signal);
      setState(current => ({
        ...current,
        questions: current.questions.map(item => item.id === placeholderId ? result.question : item),
        activeAnswerTask: result.task,
      }));
      setActionState(current => ({ ...current, screenshotTask: null }));
      setView(current => current.viewingAnswerId ? { ...current, newAnswerAvailable: true } : current);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (error instanceof Error && error.message === "请求已取消") return;
      const message = error instanceof Error ? error.message : "截屏回答失败，请稍后重试。";
      setState(current => ({
        ...current,
        questions: current.questions.map(item => item.id === placeholderId ? { ...item, status: "failed", advice: { ...item.advice, detail: message, uncertain: true } } : item),
        activeAnswerTask: current.activeAnswerTask?.questionId === placeholderId ? { ...current.activeAnswerTask, status: "failed", partialText: message, updatedAtMs: Date.now() } : current.activeAnswerTask,
      }));
      screenshotFailure(message, "共享屏幕截取");
    }
  };
  const screenshotFailure = (message: string, name = screenshot?.name ?? "当前屏幕截取") => {
    setScreenshot({ name, stage: "failed", errorMessage: message });
  };
  const screenshotStageTitle = (task: ScreenshotTask) => {
    if (task.stage === "failed") return "截屏回答失败";
    if (task.stage === "waiting-desktop") return "等待本地助手";
    if (task.stage === "uploading") return "正在上传截图";
    if (task.stage === "uploaded") return "截图已上传";
    if (task.stage === "recognizing") return "正在识别截图";
    if (task.stage === "generating") return "正在生成答案";
    if (task.stage === "completed") return "截屏回答已完成";
    if (task.stage === "cancelled") return "截屏回答已取消";
    return "正在截取当前屏幕";
  };
  const screenshotStageDetail = (task: ScreenshotTask) => {
    if (task.stage === "failed") return task.errorMessage || "截屏回答失败，请稍后重试。";
    if (task.stage === "waiting-desktop") return "网页端已创建截屏任务，正在等待本地助手接收。";
    if (task.stage === "uploading") return "本地助手已接收任务，正在截取并上传压缩后的全屏截图。";
    if (task.stage === "uploaded") return "截图已上传到后端，正在准备交给视觉模型识别。";
    if (task.stage === "recognizing") return "正在识别截图中的题目、代码或系统设计内容。";
    if (task.stage === "generating") return "视觉模型正在生成答案，耗时主要取决于模型 API。";
    if (task.stage === "completed") return "截图回答已完成，答案会显示在右侧回答区。";
    if (task.stage === "cancelled") return "本次截屏回答已取消。";
    return "正在截取你选择的共享屏幕，不会跳转到上传页面。";
  };
  const captureErrorMessage = (error: unknown) => {
    if (error instanceof DOMException && error.name === "AbortError") return "";
    if (error instanceof DOMException && error.name === "NotAllowedError") return "共享屏幕截取未获授权，请检查电脑伴随程序权限后重试。";
    if (error instanceof Error && error.message) return error.message;
    return "共享屏幕暂时无法截取，请重试。";
  };
  const cancelScreenshot = () => {
    screenshotController.current?.abort();
    screenshotController.current = null;
    setScreenshot(null);
  };
  const beginInstantScreenshot = () => {
    if (screenshot && screenshot.stage !== "failed" && screenshot.stage !== "completed" && screenshot.stage !== "cancelled") {
      setScreenshot({ ...screenshot });
      return;
    }
    setNotice("");
    screenshotController.current?.abort();
    const controller = new AbortController();
    screenshotController.current = controller;
    setScreenshot({ name: "共享屏幕截取", stage: "capturing" });
    window.setTimeout(() => {
      void Promise.resolve()
        .then(() => {
          if (controller.signal.aborted) return;
          setScreenshot({ name: "共享屏幕截取", stage: "recognizing" });
          return submitScreenshot();
        })
        .then(() => {
          screenshotController.current = null;
        })
        .catch(error => {
          if (controller.signal.aborted || (error instanceof DOMException && error.name === "AbortError")) {
            screenshotController.current = null;
            return;
          }
          screenshotController.current = null;
          screenshotFailure(captureErrorMessage(error));
        });
    }, 0);
  };
  const dismissPending = () => setState(current => ({ ...current, speaker: { ...current.speaker, pendingQuestion: null } }));
  const confirmPending = () => {
    const candidate = state.speaker.pendingQuestion; if (!candidate || !charge(state.billing.rates.answerPoints, candidate.id)) return;
    const question: InterviewQuestion = { ...active, id: candidate.id, text: candidate.text, askedAt: "刚刚", input: "desktop-audio", status: "generating", advice: scopedAdvice };
    const task = activeTaskFor(question, candidate.id);
    setState(current => ({ ...current, questions: current.questions.some(item => item.id === candidate.id) ? current.questions : [question, ...current.questions], speaker: { ...current.speaker, pendingQuestion: null }, activeAnswerTask: task }));
    setView(current => current.viewingAnswerId ? { ...current, newAnswerAvailable: true } : current);
  };
  const stopAnswer = async () => {
    const task = state.activeAnswerTask;
    if (!task || (task.status !== "queued" && task.status !== "generating") || cancellingAnswer) return;
    const releaseReservedPoints = (usageId: string, points: number, description: string) => setState(current => current.billing.activePass ? current : ({
      ...current,
      billing: {
        ...current.billing,
        balance: current.billing.balance + points,
        ledger: [{
          id: `release-${usageId}`,
          userId: current.account.id,
          kind: "usage_release",
          points,
          createdAtMs: Date.now(),
          referenceId: usageId,
          description,
        }, ...current.billing.ledger],
      },
    }));
    const markLocallyCancelled = (description?: { readonly usageId: string; readonly points: number; readonly text: string }) => {
      setScreenshot(null);
      setState(current => ({
        ...current,
        activeAnswerTask: { ...task, status: "cancelled", revision: task.revision + 1, updatedAtMs: Date.now() },
        questions: current.questions.map(question => question.id === task.questionId ? { ...question, status: "cancelled" } : question),
      }));
      if (description) releaseReservedPoints(description.usageId, description.points, description.text);
    };
    if (task.billingUsageId.startsWith("pending:")) {
      manualAnswerController.current?.abort();
      markLocallyCancelled();
      return;
    }
    if (task.billingUsageId.startsWith("screenshot:remote:")) {
      screenshotController.current?.abort();
      screenshotController.current = null;
      markLocallyCancelled({
        usageId: task.billingUsageId,
        points: state.billing.rates.screenshotAnswerPoints,
        text: "截图回答已终止，积分预留已释放",
      });
      return;
    }
    manualAnswerController.current?.abort();
    setCancellingAnswer(true); setCancelAnswerError("");
    try {
      const result = await runAdapterOperation(signal => interviewAppAdapter.cancelAnswer({ interviewId: id, answerTaskId: task.id, expectedRevision: task.revision, idempotencyKey: `cancel:${task.id}:${task.revision}` }, task, signal));
      if (result.outcome === "cancelled" || result.outcome === "already-cancelled") setState(current => {
        const hasFrontendReserve = !result.task.billingUsageId.startsWith("live-answer:") && !result.task.billingUsageId.startsWith("pending:");
        return { ...current, activeAnswerTask: result.task, questions: current.questions.map(question => question.id === result.task.questionId ? { ...question, status: "cancelled" } : question), billing: result.billingReleased && hasFrontendReserve && !current.billing.activePass ? { ...current.billing, balance: current.billing.balance + current.billing.rates.answerPoints, ledger: [{ id: `release-${result.task.billingUsageId}`, userId: current.account.id, kind: "usage_release", points: current.billing.rates.answerPoints, createdAtMs: Date.now(), referenceId: result.task.billingUsageId, description: "回答已终止，积分预留已释放" }, ...current.billing.ledger] } : current.billing };
      });
      else setCancelAnswerError(result.outcome === "stale-revision" ? "回答状态刚刚发生变化，请重试。" : "回答已经完成，无法终止。");
    } catch { setCancelAnswerError("终止回答失败，当前回答状态未改变，请重试。"); }
    finally { setCancellingAnswer(false); }
  };
  const dismissScreenshotFailure = () => {
    screenshotController.current?.abort();
    screenshotController.current = null;
    setScreenshot(null);
    setState(current => {
      const task = current.activeAnswerTask;
      if (!task || task.status !== "failed" || !task.billingUsageId.startsWith("screenshot:remote:")) return current;
      return { ...current, activeAnswerTask: null };
    });
  };
  const billingNotice = notice.includes("积分") || notice.includes("会员") || notice.toLowerCase().includes("billing");
  return <main className="live-page focused-live-page"><header className="live-top"><Link to={routes.app}><Logo /></Link><div><strong>高级前端工程师面试</strong><span><i className={state.captureState === "capturing" ? "recording-dot" : "online-dot"} /> {state.captureState === "capturing" ? "这台 Mac · 正在收音" : state.captureState === "paused" ? "收音已暂停" : state.captureState === "reconnecting" ? "Mac 正在重连" : state.captureState === "permission-required" ? "需要音频权限" : state.captureState === "error" ? "设备连接异常" : "这台 Mac · 已连接，未采集"}</span></div><div className="live-top-actions"><Link className="live-balance" to={routes.billing}>积分</Link><span>18:24</span>{state.captureState === "capturing" ? <button className="button warning live-session-control" onClick={() => setCapture("paused", "paused")}>暂停收音</button> : <button className="button primary live-session-control" disabled={state.captureState !== "ready" && state.captureState !== "paused"} onClick={() => setCapture("capturing", "active")}>{state.captureState === "paused" ? "恢复收音" : "开始面试"}</button>}<button className="button danger live-session-control" onClick={() => { if (window.confirm("确认结束本场面试？结束后将停止采集并进入复盘。")) { setCapture("ready", "ended"); navigate(routes.review(id)); } }}>结束面试</button></div></header>
    {state.captureState === "reconnecting" || state.captureState === "permission-required" || state.captureState === "error" ? <div className="global-live-alert" role="status"><strong>{state.captureState === "reconnecting" ? "设备正在重连" : state.captureState === "permission-required" ? "需要麦克风与系统音频权限" : "桌面设备连接异常"}</strong><span>{state.captureState === "reconnecting" ? "恢复前可能存在音频缺口，不会伪装为持续同步。" : state.captureState === "permission-required" ? "请在 Mac 伴随程序中完成系统授权，或改用手动输入。" : "可以运行诊断，当前仍可使用手动问题和截图。"}</span><button onClick={() => setCapture("ready", "ready")}>{state.captureState === "permission-required" ? "已完成授权" : "重新诊断"}</button></div> : null}
    {notice ? <div className="global-live-alert" role="status"><strong>{notice}</strong><span>{billingNotice ? "当前任务未启动，请检查积分或会员权益。" : "当前回答没有成功启动，请根据上方原因重试。"}</span>{billingNotice ? <Link className="button primary" to={routes.billing}>前往积分页</Link> : null}</div> : null}
    <div ref={workspaceRef} className="live-grid focused-live-grid" style={desktopLayout ? { gridTemplateColumns: `minmax(320px, ${view.splitRatio}fr) 12px minmax(420px, ${100 - view.splitRatio}fr)` } : undefined}><section className="conversation-column"><ConversationMonitor state={state} onConfirmQuestion={confirmPending} onDismissQuestion={dismissPending} /><ManualQuestionComposer manualDraft={actionState.manualDraft} onChange={value => setActionState(current => ({ ...current, manualDraft: value }))} /></section>{desktopLayout ? <WorkspaceDivider containerRef={workspaceRef} ratio={view.splitRatio} bounds={splitBounds} onChange={splitRatio => setView(current => ({ ...current, splitRatio }))} /> : null}<section className="answer-column"><AnswerWorkspace answers={state.questions} viewingAnswerId={view.viewingAnswerId} newAnswerAvailable={view.newAnswerAvailable} activeTask={state.activeAnswerTask} cancelling={cancellingAnswer} cancelError={cancelAnswerError} onStop={() => void stopAnswer()} onView={answerId => setView(current => ({ ...current, viewingAnswerId: answerId, newAnswerAvailable: answerId ? current.newAnswerAvailable : false }))} onRetry={updateQuestionStatus} /><AnswerActionBar manualDraft={actionState.manualDraft} latestInterviewerQuestion={latestInterviewerText} screenshotTask={actionState.screenshotTask} onQuickAnswer={submitManual} onScreenshot={beginInstantScreenshot} /></section></div>{screenshot ? <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="screenshot-dialog-title"><section className="sheet"><h2 id="screenshot-dialog-title">{screenshotStageTitle(screenshot)}</h2><p>{screenshotStageDetail(screenshot)}</p>{screenshot.stage === "failed" ? <div className="sheet-actions split-actions"><button className="button ghost full" onClick={dismissScreenshotFailure}>删除本次失败</button><button className="button primary full" onClick={beginInstantScreenshot}>重新截屏</button></div> : <button className="button primary full" onClick={cancelScreenshot}>取消</button>}</section></div> : null}
    <footer className="session-bar"><div><i className={state.captureState === "capturing" ? "recording-dot" : "online-dot"} /><strong>{state.captureState === "capturing" ? "面试进行中" : state.captureState === "paused" ? "面试已暂停" : "等待开始面试"}</strong></div><div><small>{state.captureState === "capturing" ? "正在持续接收面试官与我的实时对话" : "开始面试后会在头部右侧管理本场状态"}</small></div></footer>
  </main>;
}

function ReviewPage() {
  const { id = "review" } = useParams();
  const { state, setState } = usePrototype();
  const navigate = useNavigate();
  const [reviewStatus, setReviewStatus] = useState(state.review.status);
  const [deleteError, setDeleteError] = useState("");
  const [deletingShotId, setDeletingShotId] = useState<string | null>(null);
  const [deletingInterview, setDeletingInterview] = useState(false);
  const deleteShot = async (shotId: string) => { setDeleteError(""); setDeletingShotId(shotId); try { await runAdapterOperation(signal => interviewAppAdapter.deleteScreenshot(shotId, signal)); setState(current => ({ ...current, review: { ...current.review, screenshots: current.review.screenshots.filter(item => item.id !== shotId) } })); } catch { setDeleteError("截图删除失败，记录仍然保留，请重试。"); } finally { setDeletingShotId(null); } };
  const deleteInterview = async () => { if (!window.confirm("删除整场面试及其问题、回答和会话附件？可复用简历与知识库仍会保留。")) return; setDeleteError(""); setDeletingInterview(true); try { await runAdapterOperation(signal => interviewAppAdapter.deleteInterview(id, signal)); setState(current => ({ ...current, interviews: current.interviews.filter(item => item.id !== id), questions: [] })); navigate(routes.app); } catch { setDeleteError("整场面试删除失败，现有记录未改变，请重试。"); } finally { setDeletingInterview(false); } };
  return <main className="app-page"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="INTERVIEW REVIEW" title="本场面试复盘" detail="整理已确认记录，不对你的能力作自动评分。" action={<div className="review-meta"><strong>{state.review.duration}</strong><span>{state.questions.length} 个问题</span></div>} />
    <div className="review-grid"><section className="panel"><div className="panel-heading"><h2>问题与回答记录</h2><span>原始记录</span></div>{state.questions.length ? <div className="review-timeline">{[...state.questions].reverse().map((question, index) => <article key={question.id}><i>{index + 1}</i><div><small>{question.askedAt} · {question.input === "screenshot" ? "截图题" : question.input === "manual" ? "手动输入" : "音频转写"}</small><h3>{question.text}</h3><p>{question.advice.outline.join("；")}</p><div className="source-pills"><small>资料 v{question.advice.provenance.selectionRevision}</small>{question.advice.provenance.usedSources.map(source => <span key={source.sourceId}>{source.displayName}</span>)}</div></div></article>)}</div> : <EmptyState title="没有可复盘的问题" detail="本场面试没有已确认的问题记录。" />}</section>
      <aside><section className="panel review-summary"><div className="panel-heading"><h2>AI 整理摘要</h2><span className={reviewStatus}>{reviewStatus === "complete" ? "已生成" : reviewStatus === "failed" ? "生成失败" : "处理中"}</span></div>{reviewStatus === "complete" ? <><p>{state.review.summary}</p><div className="evidence-box"><span>说明</span><p>这是基于本场记录的生成建议，与原始问题记录分开保存。</p></div></> : reviewStatus === "failed" ? <div className="inline-error">摘要生成失败，原始记录仍可查看。<button onClick={() => setReviewStatus("complete")}>重试</button></div> : <p>正在整理本场已确认问题…</p>}</section><section className="panel data-panel"><div className="panel-heading"><h2>数据与附件</h2><span>可删除</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}<ul className="compact-list"><li><span>简历与知识库</span><b>作为可复用资料保留</b></li><li><span>问题与回答</span><b>随会话保存</b></li>{state.review.screenshots.map(shot => <li key={shot.id}><span>{shot.name}</span><button disabled={deletingShotId === shot.id} onClick={() => void deleteShot(shot.id)}>{deletingShotId === shot.id ? "删除中…" : "删除截图"}</button></li>)}</ul><button className="button danger full" disabled={deletingInterview} onClick={() => void deleteInterview()}>{deletingInterview ? "正在删除…" : "删除整场面试"}</button></section></aside></div>
  </main>;
}

function LibraryPage() { const { state, setState } = usePrototype(); return <LibraryManager state={state} setState={setState} />; }

function BillingRoutePage() { const { state, setState } = usePrototype(); return <BillingPage state={state} setState={setState} />; }

function DevicesPage() {
  const { state } = usePrototype();
  return <main className="app-page"><PageHeader eyebrow="DESKTOP COMPANION" title="电脑伴随程序" detail="根据系统和芯片选择安装包；实际收音能力以连接后的检测结果为准。" /><div className="device-page-grid"><DownloadCenter manifest={state.releaseManifest} /><section className="panel"><div className="panel-heading"><h2>已连接设备</h2><span className="success-text">● 在线</span></div><div className="paired-device"><span className="device-glyph">⌘</span><div><strong>{state.preparation.device?.displayName}</strong><small>{state.preparation.device?.capabilities.platformVersion} · 麦克风与系统音频权限正常</small></div><button className="button ghost">诊断</button></div><div className="privacy-box"><strong>当前没有收音</strong><p>伴随程序不会因为打开网页而自动开始。Windows 预览版若不支持系统音频，会明确降级到麦克风、手动输入和截图。</p></div></section></div></main>;
}

function SettingsPage() { return <main className="app-page"><PageHeader eyebrow="SETTINGS" title="设置" detail="查看真实的数据行为和辅助功能。" /><div className="settings-list"><section className="panel"><h2>数据与隐私</h2><div className="setting-row"><span><strong>原始音频</strong><small>完成当前转写后不保留</small></span><b>默认不保存</b></div><div className="setting-row"><span><strong>面试记录</strong><small>请在对应复盘页查看、管理和删除记录。</small></span><Link to={`${routes.guide}#privacy-support`}>查看数据说明</Link></div></section><section className="panel"><h2>辅助功能</h2><label className="setting-row"><span><strong>减少动态效果</strong><small>减少波形与状态动画</small></span><input type="checkbox" /></label><label className="setting-row"><span><strong>回答字号</strong><small>只影响实时回答区域</small></span><select aria-label="回答字号" defaultValue="normal"><option value="normal">标准</option><option value="large">较大</option></select></label></section></div></main>; }

function RouteErrorPage() { return <main className="center-page"><EmptyState title="页面暂时无法加载" detail="没有输出任何敏感内容。请返回应用首页重试。" action={<Link className="button primary" to={routes.app}>返回首页</Link>} /></main>; }
function IntegrationModeErrorPage({ message }: { readonly message: string }) { return <main className="center-page"><EmptyState title="后端页面状态无法加载" detail={`${message}。当前页面只读取后端 API，请检查服务状态或接口契约。`} action={<a className="button primary" href={runtimeConfig.apiBaseUrl} target="_blank" rel="noreferrer">检查后端服务</a>} /></main>; }
function NotFoundPage() { return <main className="center-page"><EmptyState title="没有找到这个页面" detail="检查地址，或回到面试首页继续。" action={<Link className="button primary" to={routes.app}>返回首页</Link>} /></main>; }
function RouteLoadingPage() { return <main className="center-page" role="status"><EmptyState title="正在安全加载" detail="面试内容将在身份与数据状态确认后显示。" /></main>; }

export function AppRoutes() {
  return <Routes><Route element={<PublicLayout />}><Route path={routes.landing} element={<LandingPage />} /><Route path={routes.login} element={<LoginPage />} /></Route><Route element={<ProtectedRoute />}><Route path="/app" element={<AppLayout />}><Route index element={<HomePage />} /><Route path="interviews/new" element={<NewInterviewPage />} /><Route path="interviews/:id/prepare" element={<PreparationPage />} /><Route path="interviews/:id/review" element={<ReviewPage />} /><Route path="library" element={<LibraryPage />} /><Route path="billing" element={<BillingRoutePage />} /><Route path="guide" element={<GuidePage />} /><Route path="devices" element={<DevicesPage />} /><Route path="settings" element={<SettingsPage />} /></Route><Route path="/app/interviews/:id/live" element={<LivePage />} /></Route><Route path="/error" element={<RouteErrorPage />} /><Route path="*" element={<NotFoundPage />} /></Routes>;
}

export interface AppProps { readonly initialAuthenticated?: boolean; readonly initialState?: WebAppState }

export function App({ initialAuthenticated, initialState }: AppProps) {
  useEffect(() => { document.title = "面试稳"; }, []);
  return <BrowserRouter><PrototypeProvider initialAuthenticated={initialAuthenticated} initialState={initialState}><Suspense fallback={<RouteLoadingPage />}><AppRoutes /></Suspense></PrototypeProvider></BrowserRouter>;
}
