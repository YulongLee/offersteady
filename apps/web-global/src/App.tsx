import { createContext, Suspense, useContext, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { BrowserRouter, Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import type { AnswerTaskSnapshot, CaptureState, ContextLibrarySource } from "@offersteady/protocol";
import { INTERVIEW_LANGUAGE_REGISTRY, interviewLanguageDefinition } from "@offersteady/protocol";
import { BriefcaseIcon, CaretDownIcon, ChartLineUpIcon, ChatCircleTextIcon, ClipboardTextIcon, CodeIcon, DatabaseIcon, DevicesIcon, GraduationCapIcon, IdentificationCardIcon, PaletteIcon, ScanIcon, UserFocusIcon } from "@phosphor-icons/react";

import type { IdleInterviewStatus, InterviewQuestion, LiveActionState, ProgrammingLanguage, QuestionStatus, RealtimeSessionUpdate, ScreenshotTask, SessionMode, SessionStatus, WebAppState } from "./domain";
import { runAdapterOperation } from "./api-client";
import { interviewAppAdapter } from "./app-adapter";
import { routes } from "./routes";
import { ContextPicker } from "./ContextPicker";
import { contextLevel, eligibleSource, managedLibrarySources, selectionSources, selectionValidity } from "./context-selection";
import { assetUrl } from "./assets";
import { interviewPlatforms } from "./platform-brands";
import { ConversationMonitor } from "./ConversationMonitor";
import { AnswerWorkspace, BillingPage, DownloadCenter, GuidePage, LibraryManager, PublicReviewPage } from "./route-components";
import { publicReviewCatalogue, publicReviewPage } from "./public-review-pages";
import { latestInterviewerTurnText } from "./conversation-turns";
import { ManualQuestionComposer } from "./ManualQuestionComposer";
import { AnswerActionBar } from "./AnswerActionBar";
import { MobileInterviewControls } from "./MobileInterviewControls";
import { ABSOLUTE_MAX_SPLIT_RATIO, ABSOLUTE_MIN_SPLIT_RATIO, clampSplitRatio, initialLiveWorkspaceView, isolateRealtimeSpeakerSession, noteNewAnswer, parseStoredSplitRatio, reconcileAnswerWorkspace, reconcileRealtimeSpeaker, resetTransientInterviewState, serializeSplitRatio, splitRatioBounds, splitRatioStorageKey } from "./live-workspace";
import { WorkspaceDivider } from "./WorkspaceDivider";
import { authClient } from "./auth-client";
import { materialUploadAdapter, saveMaterialDownload } from "./material-upload-adapter";
import { isInvalidRealtimeSessionStatus, realtimeReconnectAttemptAfterRecovery, realtimeRetryDelayMs } from "./realtime-recovery";
import { createLiveSessionLeaderCoordinator } from "./live-session-leader";
import { applyAppearancePreferences, persistAppearancePreferences, readAppearancePreferences, type AppearancePreferences } from "./appearance-preferences";
import { isFreshShortcutScreenshotAcceptance, SHORTCUT_SCREENSHOT_RECOVERY_POLL_INTERVAL_MS } from "./screenshot-shortcut-feedback";
import type { LiveAnswerStreamEvent } from "./live-answer-stream";
import { createAnswerStreamUpdateScheduler } from "./answer-stream-update-scheduler";
import { officialSocialContacts } from "./social-contacts";
import { companionUpdate, type CompanionUpdate } from "./platform";
import { globalEditionMetadata } from "./product-edition";
import globalScreenshotInstruction from "../../../ai/prompts/global-screenshot-instruction-v1.txt?raw";
import "./styles.css";
import { HomepageAdvantages } from "./HomepageAdvantages";
import { HomepageDownloads } from "./HomepageDownloads";
import homeCopy from "./homepage-commercial.json";
import "./homepage-commercial.css";


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
  const [loadAttempt, setLoadAttempt] = useState(0);
  const automaticRetryCount = useRef(0);

  useEffect(() => {
    if (!initialAuthenticated || !initialState?.account) return;
    if (authClient.readStoredSession()) return;
    const storedAccount = authClient.readStoredAccount();
    if (storedAccount?.id === initialState.account.id) return;
    authClient.bootstrapPrototypeIdentity(initialState.account);
  }, [initialAuthenticated, initialState]);

  useEffect(() => {
    if (initialState) return;
    const controller = new AbortController();
    const existing = authClient.readStoredSession();
    const initialize = async () => {
      if (existing) {
        try {
          await authClient.restore(controller.signal);
          setAuthenticatedState(true);
          return interviewAppAdapter.loadState(controller.signal);
        } catch (error) {
          if (controller.signal.aborted) throw error;
          authClient.clear();
          setAuthenticatedState(false);
          return interviewAppAdapter.loadState(controller.signal, { auth: false });
        }
      } else {
        setAuthenticatedState(false);
      }
      return interviewAppAdapter.loadState(controller.signal, { auth: false });
    };
    void initialize()
      .then(next => {
        setState(next);
        setLoadError("");
      })
      .catch(error => {
        if (controller.signal.aborted) return;
        setLoadError(error instanceof Error ? error.message : "后端页面状态加载失败");
      });
    return () => controller.abort();
  }, [initialState, loadAttempt]);

  useEffect(() => {
    if (initialState || state || !loadError) return;
    const delayMs = Math.min(10_000, 1_500 * 2 ** automaticRetryCount.current);
    automaticRetryCount.current += 1;
    const timer = window.setTimeout(() => {
      setLoadError("");
      setLoadAttempt(value => value + 1);
    }, delayMs);
    return () => window.clearTimeout(timer);
  }, [initialState, loadError, state]);

  const retryInitialLoad = () => {
    automaticRetryCount.current = 0;
    setLoadError("");
    setLoadAttempt(value => value + 1);
  };

  const setAuthenticated = (value: boolean) => {
    setAuthenticatedState(value);
  };

  const logout = async () => {
    await authClient.logout();
    setAuthenticated(false);
    try { setState(await interviewAppAdapter.loadState()); } catch { setState(current => current); }
  };

  if (!state && !loadError) return <RouteLoadingPage />;
  if (!state && loadError) return <IntegrationModeErrorPage message={loadError} onRetry={retryInitialLoad} />;

  if (!state) return <RouteLoadingPage />;
  return <PrototypeContext.Provider value={{ authenticated, setAuthenticated, state, setState: setState as React.Dispatch<React.SetStateAction<WebAppState>>, logout }}>{children}</PrototypeContext.Provider>;
}

const Logo = ({ compact = false }: { readonly compact?: boolean }) => <span className="logo-lockup"><img src={assetUrl("brand.app-icon")} width="44" height="44" decoding="async" alt="" /><strong>{compact ? "OfferSteady" : "OfferSteady AI Interview Assistant"}</strong></span>;

function PublicLayout() {
  const { authenticated } = usePrototype();
  return (
    <div className="public-shell">
      <header className="public-nav">
        <Link to={routes.landing} aria-label="OfferSteady home"><Logo compact /></Link>
        <nav aria-label="Public navigation"><a href="/features">Features</a><a href="/#product-tour">How it works</a><a href="/pricing">Pricing</a><a href="/download">Download</a><Link className="button ghost" to={authenticated ? routes.app : routes.login}>{authenticated ? "Open workspace" : "Sign in"}</Link></nav>
      </header>
      <Outlet />
    </div>
  );
}

function LandingPage() {
  const pricingPlans = publicReviewPage("pricing")?.plans ?? [];
  const freePlan = pricingPlans.find(plan => plan.name === "Free");
  const paidPlans = pricingPlans.filter(plan => plan.name !== "Free");
  const benefitIcons = [ChatCircleTextIcon, IdentificationCardIcon, ScanIcon, ClipboardTextIcon];
  return <main className="commercial-home">
    <section className="landing-hero">
      <div>
        <span className="kicker">YOUR AI INTERVIEW ASSISTANT</span>
        <h1>{publicReviewCatalogue.heroTitle}</h1>
        <p>{publicReviewCatalogue.productDescription}</p>
        <div className="hero-actions"><Link className="button primary large" to={routes.login}>Start free <span>→</span></Link><a className="text-link" href="#product-tour">See how it works <span aria-hidden="true">↗</span></a></div>
        <HomepageDownloads />
        <p className="hero-guidance-note">{publicReviewCatalogue.guidanceNotice}</p>
      </div>
      <div className="answer-demo" aria-label="Live answer preview">
        <div className="demo-top"><span><i className="online-dot" /> Interview guidance</span><span>Product preview</span></div>
        <small>Current question</small><h2>Tell me about a challenging project you led.</h2>
        <div className="demo-answer"><span className="advice-label">A place to start</span><ol><li>Set the context and goal in one sentence.</li><li>Focus on your decisions, actions, and trade-offs.</li><li>Close with a result you can verify.</li></ol><div className="source-pills"><span>Resume</span><span>Job description</span><span>Your experience</span></div></div>
      </div>
    </section>
    <section id="benefits" className="public-section" aria-labelledby="commercial-benefits-title">
      <div className="section-intro"><span className="kicker">BUILT FOR THE CONVERSATION</span><h2 id="commercial-benefits-title">{homeCopy.benefitsTitle}</h2><p>{homeCopy.benefitsIntro}</p></div>
      <div className="commercial-benefits">{homeCopy.benefits.map((benefit, index) => {
        const Icon = benefitIcons[index] ?? ChatCircleTextIcon;
        return <article key={benefit.label}><span><Icon size={28} weight="duotone" /></span><small>{benefit.label}</small><h3>{benefit.title}</h3><p>{benefit.body}</p></article>;
      })}</div>
    </section>
    {freePlan && paidPlans.length ? <section id="plans" className="public-section homepage-pricing" aria-labelledby="homepage-pricing-title">
      <div className="homepage-pricing-heading"><div><span className="kicker">YOUR SCHEDULE. YOUR PLAN.</span><h2 id="homepage-pricing-title">Pay for the time you need.</h2></div><p>{homeCopy.pricingIntro}</p></div>
      <article className="homepage-free-plan">
        <div><span>TRY IT FIRST</span><h3>{freePlan.name}</h3><p>{freePlan.description}</p></div>
        <div className="homepage-free-price"><strong>{freePlan.price}</strong><span>No credit card required</span></div>
        <ul>{freePlan.features.slice(0, 2).map(feature => <li key={feature}>✓ {feature}</li>)}</ul>
        <Link className="button primary" to={routes.login}>Start free <span>→</span></Link>
      </article>
      <div className="homepage-plan-grid" aria-label="OfferSteady paid plans">
        {paidPlans.map(plan => <article key={plan.name} className={`homepage-plan-card${plan.featured ? " featured" : ""}`}>
          <div className="homepage-plan-topline"><span>{plan.featured ? "WEEKLY ACCESS" : plan.name === "Pro Monthly" ? "MONTHLY SUBSCRIPTION" : "ONE-TIME PASS"}</span></div>
          <h3>{plan.name}</h3><p>{plan.description}</p>
          <div className="homepage-plan-price"><strong>{plan.price}</strong><span>{plan.term}</span></div>
          <ul>{plan.features.map(feature => <li key={feature}>✓ {feature}</li>)}</ul>
          <div className="plan-delivery"><p>{plan.billing}</p></div>
        </article>)}
      </div>
      <div className="commercial-plan-note"><p>{homeCopy.accessNote}</p><p>{homeCopy.checkoutNote}</p></div>
      <div className="homepage-pricing-actions"><Link className="button primary large" to={routes.pricing}>Compare all plans <span>→</span></Link><p>See full allowances, access periods and <Link to={routes.refundPolicy}>refund details</Link> before you choose.</p></div>
    </section> : null}
    <section id="product-tour" className="public-section" aria-labelledby="commercial-tour-title">
      <div className="section-intro"><span className="kicker">HOW IT WORKS</span><h2 id="commercial-tour-title">{homeCopy.tourTitle}</h2></div>
      <div className="commercial-steps">{homeCopy.steps.map((step, index) => <article key={step.title}><b>0{index + 1}</b><h3>{step.title}</h3><p>{step.body}</p></article>)}</div>
      <div className="commercial-videos">{homeCopy.videos.map(video => <article key={video.id}>
        <div className="global-product-film-frame"><video aria-label={video.label} controls muted playsInline preload="metadata" poster={video.poster}><source src={video.src} type="video/mp4" /></video></div>
        <h3 id={video.id}>{video.title}</h3><p>{video.description}</p>
      </article>)}</div>
    </section>
    <HomepageAdvantages compact />
    <section id="faq" className="public-section commercial-faq-layout" aria-labelledby="commercial-faq-title">
      <div className="section-intro"><span className="kicker">BEFORE YOU START</span><h2 id="commercial-faq-title">A few things worth knowing.</h2><p>Still have a question? <Link className="text-link" to={routes.contact}>Talk to us</Link></p></div>
      <div className="commercial-faq-list">{homeCopy.faqs.map(faq => <details key={faq.question}><summary>{faq.question}</summary><p>{faq.answer}</p><Link to={faq.href}>{faq.linkLabel} →</Link></details>)}</div>
    </section>
    <section className="commercial-closing" aria-labelledby="commercial-closing-title"><div><h2 id="commercial-closing-title">{homeCopy.closingTitle}</h2><p>{homeCopy.closingBody}</p></div><Link className="button primary large" to={routes.login}>Start free <span>→</span></Link></section>
    <footer className="public-footer">
      <div className="public-footer-main"><section className="footer-brand"><Logo compact /><p>AI interview guidance for preparation, live sessions, written assessments, and review.</p><span>Always verify suggestions and answer from your real experience.</span></section><nav className="footer-column"><h2>Product</h2><Link to={routes.features}>Features</Link><Link to={routes.interviewQuestions}>Interview topics</Link><Link to={routes.guides}>Guides</Link><Link to={routes.pricing}>Pricing</Link><Link to={routes.download}>Download</Link><Link to={routes.login}>Sign in</Link></nav><nav className="footer-column"><h2>Company &amp; legal</h2><Link to={routes.about}>About</Link><Link to={routes.contact}>Contact</Link><Link to={routes.security}>Security</Link><Link to={routes.terms}>Terms of Service</Link><Link to={routes.privacy}>Privacy Policy</Link><Link to={routes.refundPolicy}>Refund Policy</Link></nav><section className="footer-contact"><h2>Support</h2><p><a href="mailto:contact@oneshowailab.com">contact@oneshowailab.com</a></p><p>Never send passwords, verification codes, or complete identity documents to support.</p></section></div>
      <div className="public-footer-legal"><span>© 2026 OfferSteady</span><span>Operated by {publicReviewCatalogue.operator} · {publicReviewCatalogue.operatorLocation}</span></div>
    </footer>
  </main>;
}

function LoginPage() {
  const { authenticated, setAuthenticated, setState } = usePrototype();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<"login" | "registration" | "password_setup" | "password_reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [code, setCode] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState<"send" | "complete" | "login" | "">("");
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
  const resetMode = (nextMode: typeof mode) => {
    setMode(nextMode); setPassword(""); setConfirmPassword(""); setCode(""); setChallengeId(""); setCooldown(0); setMessage("");
  };
  const validEmail = () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setMessage("Enter a valid email address.");
      return null;
    }
    return normalizedEmail;
  };
  const requestCode = async () => {
    const normalizedEmail = validEmail();
    if (!normalizedEmail || mode === "login") return;
    setBusy("send");
    setMessage("");
    try {
      const response = await authClient.sendGlobalEmailCode(normalizedEmail, mode);
      setChallengeId(response.challengeId);
      setCooldown(response.cooldownSeconds);
      setMessage(`We sent a verification code to ${response.maskedEmail}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "We could not send the verification code.");
    } finally {
      setBusy("");
    }
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const normalizedEmail = validEmail();
    if (!normalizedEmail) return;
    if (mode === "login") {
      setBusy("login"); setMessage("");
      try { const session = await authClient.loginGlobal({ email: normalizedEmail, password }); enterWithAccount(session.account); }
      catch (error) { setMessage(error instanceof Error ? error.message : "Sign-in failed. Please try again."); }
      finally { setBusy(""); }
      return;
    }
    if (!challengeId) { await requestCode(); return; }
    if (password !== confirmPassword) { setMessage("Passwords do not match."); return; }
    setBusy("complete"); setMessage("");
    try { const session = await authClient.completeGlobalPasswordFlow({ mode, email: normalizedEmail, challengeId, code, password }); enterWithAccount(session.account); }
    catch (error) { setMessage(error instanceof Error ? error.message : "We could not complete this request."); }
    finally { setBusy(""); }
  };
  const heading = mode === "login" ? "Sign in to OfferSteady" : mode === "registration" ? "Create your account" : mode === "password_setup" ? "Set a password" : "Reset your password";
  const action = mode === "login" ? (busy === "login" ? "Signing in..." : "Sign in") : !challengeId ? (busy === "send" ? "Sending..." : "Send verification code") : busy === "complete" ? "Saving..." : mode === "registration" ? "Create account" : mode === "password_setup" ? "Set password" : "Reset password";
  return <main className="center-page"><section className="login-card"><Logo /><span className="prototype-badge">Global account</span><h1>{heading}</h1><p>{mode === "login" ? "Use your email and password to access your workspace." : "We will verify your email before saving a new password."}</p><form className="sms-login-form" onSubmit={submit}><label><span>Email address</span><input value={email} onChange={event => { setEmail(event.target.value); if (challengeId) { setChallengeId(""); setCode(""); } }} inputMode="email" autoComplete="email" placeholder="you@example.com" /></label>{mode === "login" ? <label><span>Password</span><input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" /></label> : challengeId ? <><label><span>Verification code</span><input value={code} onChange={event => setCode(event.target.value.replace(/\D/g, "").slice(0, 8))} inputMode="numeric" autoComplete="one-time-code" placeholder="Enter your code" /></label><label><span>New password</span><input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" aria-describedby="password-guidance" /></label><label><span>Confirm password</span><input type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} autoComplete="new-password" /></label><small id="password-guidance">Use at least 15 characters. Password managers and pasted passwords are supported.</small></> : null}<div className="sms-actions"><button className="button primary large full" type="submit" disabled={Boolean(busy)}>{action}</button>{mode !== "login" && challengeId ? <button className="button ghost full" type="button" disabled={cooldown > 0 || Boolean(busy)} onClick={() => { void requestCode(); }}>{cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}</button> : null}</div></form><div className="login-mode-actions">{mode === "login" ? <><button className="text-link" type="button" onClick={() => resetMode("registration")}>Create account</button><button className="text-link" type="button" onClick={() => resetMode("password_reset")}>Forgot password?</button><button className="text-link" type="button" onClick={() => resetMode("password_setup")}>Existing code-login user? Set a password</button></> : <button className="text-link" type="button" onClick={() => resetMode("login")}>Back to sign in</button>}</div>{message ? <p className="login-message" role="status">{message}</p> : null}<Link className="text-link login-back" to={routes.landing}>Back to home</Link><small className="login-legal-copy">By continuing, you agree to our <Link to={routes.terms}>Terms of Service</Link> and <Link to={routes.privacy}>Privacy Policy</Link>. Never share your password or verification code.</small></section></main>;
}

function ReferralLandingPage() {
  return <Navigate to={routes.landing} replace />;
}

function ProtectedRoute() {
  const { authenticated } = usePrototype();
  const location = useLocation();
  return authenticated ? <Outlet /> : <Navigate to={routes.login} state={{ from: location.pathname }} replace />;
}

const navItems = [
  { to: routes.app, label: "Interviews", icon: UserFocusIcon, end: true },
  { to: routes.writtenExams, label: "Written exams", icon: ClipboardTextIcon },
  { to: routes.library, label: "Materials", icon: DatabaseIcon },
  { to: routes.billing, label: "Plans & credits", icon: ChartLineUpIcon },
  { to: routes.guide, label: "Product guide", icon: ChatCircleTextIcon },
  { to: routes.devices, label: "Devices", icon: DevicesIcon },
  { to: routes.settings, label: "Settings", icon: PaletteIcon },
];

function WorkbenchNavigationItems({ mobile = false }: { readonly mobile?: boolean }) {
  return <>{navItems.map(item => {
    const Icon = item.icon;
    const content = <><span className="nav-icon" aria-hidden="true"><Icon size={17} weight="regular" /></span>{mobile ? <small>{item.label}</small> : item.label}</>;
    return <NavLink key={item.to} to={item.to} {...(item.end ? { end: true } : {})}>{content}</NavLink>;
  })}</>;
}

function AccountMenu({ compact = false, dropUp = false }: { readonly compact?: boolean; readonly dropUp?: boolean }) {
  const { logout, state } = usePrototype();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const initials = state.account.displayName.slice(0, 2).toUpperCase();
  const leaveAccount = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await logout();
      navigate(routes.login, { replace: true });
    } finally {
      setBusy(false);
    }
  };
  return <details className={`account-menu${compact ? " compact" : ""}${dropUp ? " drop-up" : ""}`}>
    <summary role="button" aria-label="Account menu" aria-haspopup="menu"><i>{initials}</i>{compact ? null : <span>{state.account.displayName}<small>Account</small></span>}</summary>
    <div className="account-menu-popover">
      <div><small>Signed in as</small><strong>{state.account.displayName}</strong></div>
      <button type="button" disabled={busy} onClick={() => void leaveAccount()}>Switch account</button>
      <button type="button" className="account-logout" disabled={busy} onClick={() => void leaveAccount()}>{busy ? "Signing out…" : "Sign out"}</button>
    </div>
  </details>;
}

function AppLayout() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar"><Link to={routes.app}><Logo compact /></Link><nav aria-label="Application navigation"><WorkbenchNavigationItems /></nav><div className="sidebar-foot"><span className="privacy-note">Audio is not stored by default</span><AccountMenu dropUp /></div></aside>
      <div className="app-content"><Outlet /></div>
      <nav className="mobile-nav" aria-label="Mobile application navigation"><WorkbenchNavigationItems mobile /><AccountMenu compact dropUp /></nav>
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

const sessionHomeRoute = (mode?: SessionMode) => mode === "written" ? routes.writtenExams : routes.app;

const sessionStatusLabel: Record<SessionStatus, string> = { preparing: "Preparing", ready: "Ready", active: "In progress", paused: "Paused", ended: "Completed", error: "Needs attention" };

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

const QUICK_ANSWER_MISSING_QUESTION_NOTICE = "未能识别到面试官的问题";

const extractLatestInterviewerQuestion = (speaker: WebAppState["speaker"]) => {
  return latestInterviewerTurnText(speaker.transcripts, speaker.pendingQuestion?.text ?? "");
};

function useDesktopLiveLayout() {
  const query = "(min-width: 721px)";
  const [desktop, setDesktop] = useState(() => typeof window.matchMedia === "function" ? window.matchMedia(query).matches : window.innerWidth > 720);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") { const update = () => setDesktop(window.innerWidth > 720); window.addEventListener("resize", update); return () => window.removeEventListener("resize", update); }
    const media = window.matchMedia(query); const update = () => setDesktop(media.matches); update(); media.addEventListener?.("change", update); return () => media.removeEventListener?.("change", update);
  }, []);
  return desktop;
}

function HomePage() {
  const { state, setState } = usePrototype();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const recentInterviews = state.interviews.filter(item => item.sessionMode !== "written").slice(0, 5);
  const materialSources = state.librarySources.filter(source => source.status !== "deleted" && source.status !== "disabled");
  const readyMaterials = materialSources.filter(source => source.status === "ready" && source.syncStatus !== "missing_artifacts");
  const processingMaterials = materialSources.filter(source => source.status === "processing");
  const materialCount = (kind: "resume" | "jd" | "knowledge") => materialSources.filter(source => source.kind === kind).length;
  const readyMaterialCount = (kind: "resume" | "jd" | "knowledge") => readyMaterials.filter(source => source.kind === kind).length;
  const active = recentInterviews.find(item => item.status !== "ended");
  const hour = new Date().getHours(); const greeting = Number.isFinite(hour) ? hour < 5 ? "Good evening" : hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening" : "Welcome";
  const deleteRecentInterview = async (interviewId: string) => {
    if (!window.confirm("Delete this interview and its questions, answers, and attachments?")) return;
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
  return <main className="app-page global-workbench"><PageHeader eyebrow={`${greeting} · INTERVIEW HOME`} title="Your interviews" detail={active ? "Continue where you left off or prepare a new interview." : "Create an interview, add relevant materials, and get ready before the call."} action={<Link className="button primary" to={routes.newInterview}>+ New interview</Link>} />
    {active ? <section className="continue-card"><div><span className="live-chip"><i /> {sessionStatusLabel[active.status]}</span><h2>{active.title}</h2><p>{[active.company, active.role].filter(Boolean).join(" · ")}</p><div className="progress-line"><i style={{ width: `${active.readiness}%` }} /></div><small>{active.readiness}% prepared · Resume, job description, and knowledge are selected per interview</small></div><div className="continue-actions"><Link className="button primary" to={interviewContinuationRoute(active)}>Continue interview</Link></div></section> : <EmptyState title="Create your first interview" detail="Set the role, choose your materials, and connect the desktop companion." action={<Link className="button primary" to={routes.newInterview}>Create interview</Link>} />}
    <section className="dashboard-grid"><div className="panel"><div className="panel-heading"><h2>Recent interviews</h2><span>{recentInterviews.length} of 5</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}{recentInterviews.length ? <div className="interview-list">{recentInterviews.map(item => <article key={item.id} className="recent-interview-row"><Link to={interviewContinuationRoute(item)}><span className={`status-icon ${item.status}`}>{item.status === "ended" ? "✓" : "↗"}</span><div><strong>{item.title}</strong><small>{item.updatedAt} · {sessionStatusLabel[item.status]}</small></div><span>→</span></Link><button type="button" disabled={deletingId === item.id} onClick={() => void deleteRecentInterview(item.id)}>{deletingId === item.id ? "Deleting…" : "Delete"}</button></article>)}</div> : <p className="panel-empty-copy">Your recent interviews will appear here.</p>}</div><div className="panel readiness-panel"><div className="panel-heading"><h2>Materials ready</h2><Link to={routes.library}>Manage</Link></div><div className="readiness-ring"><strong>{readyMaterials.length}</strong><span>ready</span></div><ul className="compact-list"><li><span>Resumes</span><b>{readyMaterialCount("resume")} of {materialCount("resume")} ready</b></li><li><span>Job descriptions</span><b>{readyMaterialCount("jd")} of {materialCount("jd")} ready</b></li><li><span>Knowledge files</span><b>{readyMaterialCount("knowledge")} of {materialCount("knowledge")} ready</b></li></ul>{processingMaterials.length ? <small>{processingMaterials.length} material{processingMaterials.length === 1 ? " is" : "s are"} processing</small> : null}</div></section>
  </main>;
}

function WrittenExamHomePage() {
  const { state, setState } = usePrototype();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const recentExams = state.interviews.filter(item => item.sessionMode === "written").slice(0, 5);
  const active = recentExams.find(item => item.status !== "ended");
  const deleteRecentExam = async (sessionId: string) => {
    if (!window.confirm("Delete this written exam and its screenshot-answer history?")) return;
    setDeleteError("");
    setDeletingId(sessionId);
    try {
      await runAdapterOperation(signal => interviewAppAdapter.deleteInterview(sessionId, signal));
      try {
        setState(await runAdapterOperation(signal => interviewAppAdapter.loadState(signal)));
      } catch {
        setState(current => ({ ...current, interviews: current.interviews.filter(item => item.id !== sessionId) }));
      }
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "删除失败，请稍后重试。");
    } finally {
      setDeletingId(null);
    }
  };
  return <main className="app-page global-workbench"><PageHeader eyebrow="WRITTEN EXAM HOME" title="Your written exams" detail="Use screenshot answers without microphone, system audio, or live transcription." action={<Link className="button primary" to={routes.newWrittenExam}>+ New written exam</Link>} />
    {active ? <section className="continue-card"><div><span className="live-chip"><i /> {sessionStatusLabel[active.status]}</span><h2>{active.title}</h2><p>{[active.company, active.role].filter(Boolean).join(" · ")}</p><div className="progress-line"><i style={{ width: `${active.readiness}%` }} /></div><small>Screenshot answers only · Audio stays off</small></div><div className="continue-actions"><Link className="button primary" to={interviewContinuationRoute(active)}>Continue written exam</Link></div></section> : <EmptyState title="Create your first written exam" detail="Connect the desktop companion and capture questions from your screen." action={<Link className="button primary" to={routes.newWrittenExam}>Create written exam</Link>} />}
    <section className="dashboard-grid"><div className="panel"><div className="panel-heading"><h2>Recent written exams</h2><span>{recentExams.length} of 5</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}{recentExams.length ? <div className="interview-list">{recentExams.map(item => <article key={item.id} className="recent-interview-row"><Link to={interviewContinuationRoute(item)}><span className={`status-icon ${item.status}`}>{item.status === "ended" ? "✓" : "↗"}</span><div><strong>{item.title}</strong><small>{item.updatedAt} · {sessionStatusLabel[item.status]}</small></div><span>→</span></Link><button type="button" disabled={deletingId === item.id} onClick={() => void deleteRecentExam(item.id)}>{deletingId === item.id ? "Deleting…" : "Delete"}</button></article>)}</div> : <p className="panel-empty-copy">Your recent written exams will appear here.</p>}</div><div className="panel readiness-panel written-exam-summary"><div className="panel-heading"><h2>How it works</h2></div><ul className="compact-list"><li><span>Session cost</span><b>30 credits</b></li><li><span>Answer method</span><b>Screenshot only</b></li><li><span>Audio capture</span><b>Off</b></li></ul></div></section>
  </main>;
}

function EmptyState({ title, detail, action }: { readonly title: string; readonly detail: string; readonly action?: ReactNode }) { return <section className="empty-state"><span>◇</span><h2>{title}</h2><p>{detail}</p>{action}</section>; }

function NewInterviewPage() {
  const navigate = useNavigate();
  const { state, setState } = usePrototype();
  const [form, setForm] = useState(() => {
    const latest = state.interviews.find(item => item.sessionMode !== "written");
    return latest
      ? { title: latest.title, role: latest.role, company: latest.company ?? "" }
      : { title: "", role: "", company: "" };
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.title.trim() || !form.role.trim()) { setError("请填写面试名称和目标岗位"); return; }
    setError("");
    setSaving(true);
    try {
      const draft = await runAdapterOperation(signal => interviewAppAdapter.createDraft({ ...form, interviewLanguage: state.account.defaultInterviewLanguage ?? "en-US" }, signal));
      setState(current => {
        const reset = resetTransientInterviewState(current);
        return {
          ...reset,
          interviews: [draft, ...current.interviews.filter(item => item.id !== draft.id)].slice(0, 5),
          contextSelections: { ...current.contextSelections, [draft.id]: { sessionId: draft.id, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null } },
        };
      });
      navigate(routes.prepare(draft.id), { state: { newlyCreatedInterview: true } });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建面试失败，请稍后重试。");
    } finally {
      setSaving(false);
    }
  };
  return <main className="app-page narrow"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="NEW INTERVIEW" title="创建一场面试" detail="先给这场面试一个清晰目标，资料可以在下一步补充。" /><form className="form-panel" onSubmit={submit}><label>面试名称<input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="例如：高级前端工程师一面" /></label><label>目标岗位<input value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} placeholder="例如：高级前端工程师" /></label><label>公司（可选）<input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} placeholder="例如：示例科技" /></label>{error ? <div className="inline-error" role="alert">{error}</div> : null}<div className="form-actions"><Link className="button ghost" to={routes.app}>取消</Link><button className="button primary" type="submit" disabled={saving}>{saving ? "创建中…" : "保存并准备 →"}</button></div><small className="saved-note">草稿只在你确认提交后保存。</small></form></main>;
}

function NewWrittenExamPage() {
  const navigate = useNavigate();
  const { state, setState } = usePrototype();
  const latest = state.interviews.find(item => item.sessionMode === "written");
  const [form, setForm] = useState(() => latest ? { title: latest.title, role: latest.role, company: latest.company ?? "" } : { title: "", role: "", company: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.title.trim() || !form.role.trim()) { setError("请填写笔试名称和目标岗位"); return; }
    setError("");
    setSaving(true);
    try {
      const draft = await runAdapterOperation(signal => interviewAppAdapter.createDraft({ ...form, sessionMode: "written", interviewLanguage: state.account.defaultInterviewLanguage ?? "en-US" }, signal));
      setState(current => {
        const reset = resetTransientInterviewState(current);
        return {
          ...reset,
          interviews: [draft, ...current.interviews.filter(item => item.id !== draft.id)].slice(0, 5),
          contextSelections: { ...current.contextSelections, [draft.id]: { sessionId: draft.id, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: Date.now() } },
        };
      });
      navigate(routes.prepare(draft.id), { state: { newlyCreatedInterview: true } });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建笔试失败，请稍后重试。");
    } finally {
      setSaving(false);
    }
  };
  return <main className="app-page narrow"><Link className="back-link" to={routes.writtenExams}>← Back to written exams</Link><PageHeader eyebrow="NEW WRITTEN EXAM" title="Create a written exam" detail="Written mode uses screenshot answers only; audio capture and live transcription stay off." /><form className="form-panel" onSubmit={submit}><label>Exam name<input value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} placeholder="e.g. Algorithms assessment" /></label><label>Target role<input value={form.role} onChange={event => setForm({ ...form, role: event.target.value })} placeholder="e.g. Software Engineer" /></label><label>Company (optional)<input value={form.company} onChange={event => setForm({ ...form, company: event.target.value })} placeholder="e.g. Example Inc." /></label>{error ? <div className="inline-error" role="alert">{error}</div> : null}<div className="form-actions"><Link className="button ghost" to={routes.writtenExams}>Cancel</Link><button className="button primary" type="submit" disabled={saving}>{saving ? "Creating…" : "Save and prepare →"}</button></div><small className="saved-note">Written exam access follows your selected membership plan.</small></form></main>;
}

function CompanionUpdateReminder({ update, onContinue }: { readonly update: CompanionUpdate; readonly onContinue: () => void }) {
  return <section className="companion-update-reminder" aria-label="伴随程序更新提醒">
    <span aria-hidden="true">↑</span>
    <div><strong>发现新版伴随程序 {update.release.version}</strong><small>当前版本 {update.currentVersion}，建议更新到与你设备匹配的最新版；本次也可以继续使用。</small></div>
    <div className="companion-update-actions"><a className="button primary" href={update.release.downloadUrl} download>立即下载</a><button className="button ghost" type="button" onClick={onContinue}>继续使用</button></div>
  </section>;
}

function CompanionUpdateRequired({ message }: { readonly message: string }) {
  return <div className="inline-error companion-update-required" role="alert"><span>{message}</span><Link className="button ghost" to={routes.devices}>Download latest companion</Link></div>;
}

function LanguagePicker({ value, saving, onChange }: { readonly value: import("@offersteady/protocol").InterviewLanguage; readonly saving: boolean; readonly onChange: (value: import("@offersteady/protocol").InterviewLanguage) => void }) {
  return <fieldset className="interview-language-picker" disabled={saving}><legend>Interview language</legend><p>Choose the language used for transcription, question detection, and AI answers in this session.</p><div className="interview-language-options">{INTERVIEW_LANGUAGE_REGISTRY.map(language => <label key={language.locale} className={value === language.locale ? "selected" : ""}><input type="radio" name="interview-language" value={language.locale} checked={value === language.locale} onChange={() => onChange(language.locale)} /><span><strong>{language.nativeLabel} <small>{language.label}</small></strong><small>{language.tier === "production" ? "Production support" : "Beta · quality validation in progress"}</small></span></label>)}</div>{saving ? <small role="status">Saving interview language…</small> : null}</fieldset>;
}

function PreparationPage() {
  const { id = "demo" } = useParams();
  const { state, setState } = usePrototype();
  const navigate = useNavigate();
  const location = useLocation();
  const newlyCreatedInterview = (location.state as { newlyCreatedInterview?: boolean } | null)?.newlyCreatedInterview === true;
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState("");
  const [materialConfirmError, setMaterialConfirmError] = useState("");
  const [confirmingMaterials, setConfirmingMaterials] = useState(false);
  const [machineCode, setMachineCode] = useState("");
  const [deviceBinding, setDeviceBinding] = useState<Awaited<ReturnType<typeof interviewAppAdapter.getDesktopDeviceBinding>> | null>(null);
  const [lastDevice, setLastDevice] = useState<Awaited<ReturnType<NonNullable<typeof interviewAppAdapter.getLastDesktopDevice>>> | null>(null);
  const [binding, setBinding] = useState(false);
  const [bindingError, setBindingError] = useState("");
  const [dismissedUpdateKey, setDismissedUpdateKey] = useState("");
  const [activeConflict, setActiveConflict] = useState<Awaited<ReturnType<typeof interviewAppAdapter.getActiveInterviewConflict>>["activeInterview"] | undefined>(undefined);
  const [conflictError, setConflictError] = useState("");
  const [resolvingConflict, setResolvingConflict] = useState(false);
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [languageError, setLanguageError] = useState("");
  const [savingProgramming, setSavingProgramming] = useState(false);
  const [programmingError, setProgrammingError] = useState("");
  const interview = state.interviews.find(item => item.id === id);
  const interviewTitle = interview?.title ?? "本场面试";
  const isWritten = interview?.sessionMode === "written";
  const interviewLanguage = interview?.interviewLanguage ?? "en-US";
  const programmingRequired = interview?.programmingRequired ?? false;
  const programmingLanguage = interview?.programmingLanguage ?? "python";
  const selection = state.contextSelections[id] ?? state.contextSelections.demo!;
  const managedSources = managedLibrarySources(state.librarySources, state.account.id);
  const validity = selectionValidity(managedSources, selection);
  const level = contextLevel(selection);
  const selectionReady = isWritten || validity === "valid";
  const machineReady = Boolean(deviceBinding);
  const conflictResolved = activeConflict === null;
  const canStart = selectionReady && machineReady && conflictResolved;
  const availableUpdate = useMemo(
    () => deviceBinding ? companionUpdate(deviceBinding.capabilities, state.releaseManifest) : null,
    [deviceBinding, state.releaseManifest],
  );
  const updateKey = availableUpdate && deviceBinding ? `${deviceBinding.bindingId}:${availableUpdate.release.id}` : "";
  const visibleUpdate = availableUpdate && updateKey !== dismissedUpdateKey ? availableUpdate : null;
  const complete = isWritten ? Number(machineReady) : Number(selectionReady) + Number(machineReady);
  const inputDiagnostic = machineReady
      ? "伴随程序已连接，正在后台准备音频与实时识别"
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
  const saveInterviewLanguage = async (nextLanguage: import("@offersteady/protocol").InterviewLanguage) => {
    if (savingLanguage || nextLanguage === interviewLanguage) return;
    setSavingLanguage(true);
    setLanguageError("");
    try {
      const updated = await runAdapterOperation(signal => interviewAppAdapter.updateInterviewLanguage(id, nextLanguage, signal));
      setState(current => ({
        ...current,
        interviews: current.interviews.map(item => item.id === id ? { ...item, ...updated } : item),
      }));
    } catch (error) {
      setLanguageError(error instanceof Error ? error.message : "面试语言保存失败，请重试。");
    } finally {
      setSavingLanguage(false);
    }
  };
  const saveInterviewProgramming = async (required: boolean, language: ProgrammingLanguage | null) => {
    if (savingProgramming) return;
    const normalizedLanguage = required ? language ?? "python" : null;
    if (required === programmingRequired && normalizedLanguage === (programmingRequired ? programmingLanguage : null)) return;
    setSavingProgramming(true);
    setProgrammingError("");
    try {
      const updated = await runAdapterOperation(signal => interviewAppAdapter.updateInterviewProgramming(id, required, normalizedLanguage, signal));
      setState(current => ({
        ...current,
        interviews: current.interviews.map(item => item.id === id ? { ...item, ...updated } : item),
      }));
    } catch (error) {
      setProgrammingError(error instanceof Error ? error.message : "编程设置保存失败，请重试。");
    } finally {
      setSavingProgramming(false);
    }
  };
  const downloadMaterial = async (source: ContextLibrarySource) => {
    setMaterialConfirmError("");
    try {
      const result = await runAdapterOperation(signal => materialUploadAdapter.downloadDocument(state.account.id, source.documentId ?? source.id, signal));
      saveMaterialDownload(result);
    } catch (error) {
      setMaterialConfirmError(error instanceof Error ? error.message : "资料下载失败，请稍后重试。");
    }
  };
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      runAdapterOperation(signal => interviewAppAdapter.getDesktopDeviceBinding(id, signal), controller.signal).catch(() => null),
      interviewAppAdapter.getLastDesktopDevice
        ? runAdapterOperation(signal => interviewAppAdapter.getLastDesktopDevice!(signal), controller.signal).catch(() => null)
        : Promise.resolve(null),
      runAdapterOperation(signal => interviewAppAdapter.getActiveInterviewConflict(id, signal), controller.signal),
    ]).then(([binding, recent, conflict]) => {
        setLastDevice(recent);
        setActiveConflict(conflict.activeInterview);
        setConflictError("");
        if (!binding) return;
        setDeviceBinding(binding);
        setMachineCode(binding.manualCode);
      })
      .catch(error => setConflictError(error instanceof Error ? error.message : "无法确认当前账号的面试状态，请稍后重试。"));
    return () => controller.abort();
  }, [id, newlyCreatedInterview]);
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
  useEffect(() => {
    // Keep the preparation page in sync when the Companion starts after the
    // page was opened. Previously the binding was fetched only once, leaving
    // a valid online Companion displayed as "待连接" until a manual refresh.
    let stopped = false;
    let inFlight = false;
    const refreshBinding = async () => {
      if (stopped || inFlight) return;
      inFlight = true;
      try {
        const next = await runAdapterOperation(signal => interviewAppAdapter.getDesktopDeviceBinding(id, signal));
        if (stopped) return;
        setDeviceBinding(next);
        if (next) {
          setMachineCode(next.manualCode);
          setBindingError("");
        }
      } catch (error) {
        if (!stopped) setBindingError(error instanceof Error ? error.message : "无法确认桌面助手连接状态，请稍后重试。");
      } finally {
        inFlight = false;
      }
    };
    const timer = window.setInterval(() => void refreshBinding(), 5_000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [id]);
  const connectDesktopDevice = async (reuseLastDevice = false) => {
    if (!conflictResolved) {
      setBindingError(activeConflict ? "请先处理正在进行中的面试。" : "正在确认账号的面试状态，请稍候。");
      return;
    }
    const code = machineCode.trim();
    if (!reuseLastDevice && !/^[0-9]{6}$/.test(code)) { setBindingError("请输入电脑伴随程序显示的 6 位机器码"); return; }
    setBinding(true); setBindingError("");
    try {
      const result = await runAdapterOperation(signal => interviewAppAdapter.bindDesktopDevice({
        interviewId: id,
        ...(reuseLastDevice ? { reuseLastDevice: true } : { manualCode: code }),
      }, signal));
      setDeviceBinding(result);
      setMachineCode(result.manualCode);
    } catch (error) {
      setBindingError(error instanceof Error ? error.message : "机器码验证失败，请确认电脑伴随程序已打开。");
    } finally {
      setBinding(false);
    }
  };
  const supersedePreviousInterview = async () => {
    if (!activeConflict || resolvingConflict) return;
    setResolvingConflict(true);
    setConflictError("");
    try {
      await runAdapterOperation(signal => interviewAppAdapter.supersedeActiveInterview({
        interviewId: id,
        expectedPreviousInterviewId: activeConflict.id,
      }, signal));
      setActiveConflict(null);
      setDeviceBinding(null);
      setBindingError("");
    } catch (error) {
      setConflictError(error instanceof Error ? error.message : "切换面试失败，请刷新后重试。");
      try {
        const refreshed = await runAdapterOperation(signal => interviewAppAdapter.getActiveInterviewConflict(id, signal));
        setActiveConflict(refreshed.activeInterview);
      } catch {
        // Preserve the visible conflict until the authoritative state can be loaded.
      }
    } finally {
      setResolvingConflict(false);
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
  if (isWritten) return <main className="app-page narrow written-preparation-page">
    <Link className="back-link" to={routes.writtenExams}>← 返回笔试模式</Link>
    <PageHeader eyebrow="WRITTEN EXAM" title={interviewTitle} detail="连接伴随助手后即可开始。" />
    <section className="panel written-preparation-card">
      <div className="panel-heading">
        <h2>连接伴随助手</h2>
        <span className={machineReady ? "written-connection-ready" : ""}>{machineReady ? "已连接" : "待连接"}</span>
      </div>
      {deviceBinding ? <div className="written-connected-device"><i>✓</i><span><strong>{deviceBinding.displayName}</strong><small>助手连接正常</small></span></div> : null}
      {activeConflict ? <div className="inline-error" role="alert">上一场会话仍在进行，请先结束上一场。<button className="button ghost" disabled={resolvingConflict} onClick={() => void supersedePreviousInterview()}>{resolvingConflict ? "正在切换…" : "结束上一场"}</button></div> : null}
      <div className="machine-code-panel written-machine-code-panel">
        <label><span>机器码</span><input inputMode="numeric" maxLength={6} value={machineCode} onChange={event => setMachineCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="输入 6 位机器码" /></label>
        <button className="button ghost" disabled={!conflictResolved || binding || machineReady && machineCode === deviceBinding?.manualCode} onClick={() => void connectDesktopDevice(false)}>{binding ? "连接中…" : "验证连接"}</button>
        {lastDevice ? <button className="button primary" disabled={!conflictResolved || binding || !lastDevice.online || deviceBinding?.deviceId === lastDevice.deviceId} onClick={() => void connectDesktopDevice(true)}>{deviceBinding?.deviceId === lastDevice.deviceId ? "上次设备已连接" : "连接上次设备"}</button> : null}
        {bindingError ? (bindingError.includes("Companion version") ? <CompanionUpdateRequired message={bindingError} /> : <div className="inline-error" role="alert">{bindingError}</div>) : null}
      </div>
      {visibleUpdate ? <CompanionUpdateReminder update={visibleUpdate} onContinue={() => setDismissedUpdateKey(updateKey)} /> : null}
      {startError ? <div className="inline-error written-start-error" role="alert">{startError}</div> : null}
      <div className="written-start-row">
        <small>Written exam access follows your membership plan</small>
        <button className="button primary" disabled={!canStart || starting} onClick={() => void startInterview()}>{starting ? "正在进入…" : "开始笔试 →"}</button>
      </div>
    </section>
  </main>;
  return <main className="app-page"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="PREPARATION" title={interviewTitle} detail="资料与“面试资料”页面保持一致，为本场按需选择。" action={<div className="completion"><strong>{complete}/2</strong><span>{canStart ? "可进入" : "准备中"}</span></div>} />
    <div className="prepare-grid"><section className="panel"><LanguagePicker value={interviewLanguage} saving={savingLanguage} onChange={saveInterviewLanguage} /><fieldset className="interview-language-picker legacy-language-picker" disabled><legend>Interview language</legend><p>English transcription, question detection, and AI answers are enabled for Global sessions.</p><div><label className="selected"><input type="radio" name="interview-language" value="en-US" checked readOnly /><span><strong>English Interview</strong><small>Supports US, UK, Australian, and Canadian English profiles</small></span></label></div>{savingLanguage ? <small role="status">Saving interview language…</small> : null}{languageError ? <div className="inline-error" role="alert">{languageError}</div> : null}</fieldset><fieldset className="programming-preference" disabled={savingProgramming}><legend>编程设置</legend><div className="programming-toggle-row"><span><strong>需要编程</strong><small>开启后，代码题会统一使用你选择的编程语言</small></span><label className="switch-control"><input type="checkbox" role="switch" checked={programmingRequired} onChange={event => void saveInterviewProgramming(event.target.checked, event.target.checked ? programmingLanguage : null)} /><span aria-hidden="true" /></label></div>{programmingRequired ? <div className="programming-language-options" role="radiogroup" aria-label="编程语言">{([['python', 'Python'], ['java', 'Java'], ['cpp', 'C++'], ['javascript', 'JavaScript'], ['typescript', 'TypeScript'], ['go', 'Go']] as const).map(([value, label]) => <label key={value} className={programmingLanguage === value ? "selected" : ""}><input type="radio" name="programming-language" value={value} checked={programmingLanguage === value} onChange={() => void saveInterviewProgramming(true, value)} /><span>{label}</span></label>)}</div> : null}{savingProgramming ? <small role="status">正在保存编程设置…</small> : null}{programmingError ? <div className="inline-error" role="alert">{programmingError}</div> : null}</fieldset><ContextPicker sources={managedSources} selection={selection} onSave={saveSelection} onDownload={downloadMaterial} />{confirmingMaterials ? <div className="context-warning" role="status">正在提交后端校验并保存本场资料…</div> : null}{materialConfirmError ? <div className="context-warning" role="alert">{materialConfirmError}</div> : null}</section>
      <aside className="panel check-panel"><div className="panel-heading"><h2>开始前检查</h2><span>{canStart ? "可进入" : !selectionReady ? "待确认资料" : "待绑定机器"}</span></div><ul className="check-list"><li className={selectionReady ? "done" : ""}><i>{selectionReady ? "✓" : "1"}</i><div><strong>本场资料</strong><span>{validity === "unconfirmed" ? "请选择资料或确认不使用资料" : validity === "attention-required" ? "所选资料已失效，请处理" : level === "none" ? "已确认不使用个人资料" : level === "personalized" ? "简历与 JD 已选择" : "已确认使用部分资料"}</span></div></li><li className={machineReady ? "done" : ""}><i>{machineReady ? "✓" : "2"}</i><div><strong>收音机器</strong><span>{deviceBinding ? `${deviceBinding.displayName} connected. Preparing the live session.` : inputDiagnostic}</span></div></li></ul>
        <div className="machine-code-panel">
          <strong className="connection-choice-title">连接桌面助手</strong>
          <label><span>{newlyCreatedInterview ? "输入机器码连接本场" : "重新输入机器码"}</span><input inputMode="numeric" maxLength={6} value={machineCode} onChange={event => setMachineCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="输入 6 位机器码" /></label>
          <button className="button ghost" disabled={!conflictResolved || binding || machineReady && machineCode === deviceBinding?.manualCode} onClick={() => void connectDesktopDevice(false)}>{binding ? "连接中…" : "验证并连接"}</button>
          <small>{deviceBinding ? `Connected for this session: ${deviceBinding.displayName}` : "输入助手显示的固定机器码，或直接连接当前账号上次使用的设备。"}</small>
          {bindingError ? (bindingError.includes("Companion version") ? <CompanionUpdateRequired message={bindingError} /> : <div className="inline-error" role="alert">{bindingError}</div>) : null}
          {lastDevice ? <><div className="connection-divider"><span>或使用上次设备</span></div><div className={`last-device-choice ${lastDevice.online ? "online" : "offline"}`}><span><b>{lastDevice.displayName}</b><small>{lastDevice.online ? `Device online · ${lastDevice.maskedManualCode}` : "设备离线，请先打开助手"}</small></span><button className="button primary" disabled={!conflictResolved || binding || !lastDevice.online || deviceBinding?.deviceId === lastDevice.deviceId} onClick={() => void connectDesktopDevice(true)}>{deviceBinding?.deviceId === lastDevice.deviceId ? "已连接本场" : "一键连接上次设备"}</button></div></> : null}
        </div>
        {visibleUpdate ? <CompanionUpdateReminder update={visibleUpdate} onContinue={() => setDismissedUpdateKey(updateKey)} /> : null}
        <div className="device-mini"><span className="device-glyph">⌘</span><div><strong>{deviceBinding?.displayName ?? state.preparation.device?.displayName ?? "电脑伴随程序"}</strong><small>{deviceBinding ? "本场设备已连接；系统权限沿用助手首次授权结果" : "当前仅缺少本场设备连接，不代表助手系统权限失效"}</small></div><Link to={routes.devices}>管理</Link></div>
        <div className="privacy-confirm preparation-disclosure"><span><strong>本场数据说明</strong><small>已选资料和转录仅用于生成回答建议；原始音频默认不保存，会话记录可在复盘中删除。麦克风和屏幕权限只由桌面助手首次申请，网页不会再次申请。</small></span></div>
        <div className="points-mini"><strong>Membership access</strong><span>Live Copilot and Screen Assist usage follows your selected plan.</span><Link to={routes.billing}>View plans and billing</Link><Link to={`${routes.guide}#quick-start`}>Preparation guide</Link></div>
        {startError ? <div className="inline-error" role="alert">{startError}</div> : null}<button className="button primary full" disabled={!canStart || starting} onClick={() => void startInterview()}>{starting ? "正在开始面试…" : "开始面试 →"}</button>{!selectionReady ? <small className="blocked-help">确认本场资料选择（可以为空）后继续。</small> : !machineReady ? <small className="blocked-help">请选择上次设备或输入机器码，为本场建立设备连接。</small> : level === "none" ? <small className="blocked-help context-disclosure">本场未使用个人资料。伴随程序会在后台准备音频，开始后直接切换到实时链路。</small> : <small className="blocked-help context-disclosure">伴随程序正在后台准备麦克风、电脑输出和识别服务；无需播放测试音或提前说话。</small>}
      </aside></div>
    {activeConflict ? <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="active-interview-conflict-title"><section className="sheet active-interview-conflict-sheet"><span className="conflict-kicker">单设备 · 单场面试</span><h2 id="active-interview-conflict-title">已有一场面试正在进行</h2><p>为避免旧页面和新页面同时占用语音链路，请先选择如何继续。</p><div className="active-interview-card"><span>进行中</span><strong>{activeConflict.title}</strong><small>结束上一场只会停止实时连接，历史记录和资料不会删除。</small></div>{conflictError ? <div className="inline-error" role="alert">{conflictError}</div> : null}<div className="sheet-actions conflict-actions"><button className="button primary" disabled={resolvingConflict} onClick={() => navigate(routes.live(activeConflict.id))}>继续上一场面试</button><button className="button ghost" disabled={resolvingConflict} onClick={() => void supersedePreviousInterview()}>{resolvingConflict ? "正在切换…" : "结束上一场，准备当前面试"}</button></div><Link className="conflict-return" to={routes.app}>暂不进入，返回面试首页</Link></section></div> : null}
  </main>;
}

function LivePage() {
  const { id = "demo" } = useParams();
  const { state, setState } = usePrototype();
  const navigate = useNavigate();
  const storageKey = splitRatioStorageKey(id);
  const [view, setView] = useState(() => initialLiveWorkspaceView(parseStoredSplitRatio(typeof window.sessionStorage?.getItem === "function" ? window.sessionStorage.getItem(storageKey) : null)));
  const [actionState, setActionState] = useState<Omit<LiveActionState, "pendingQuestion">>({ manualDraft: "", screenshotTask: null, quickAnswerStatus: "idle", quickAnswerMessage: "", screenshotAnswerStatus: "idle" });
  const [notice, setNotice] = useState("");
  const [cancellingAnswer, setCancellingAnswer] = useState(false);
  const [cancelAnswerError, setCancelAnswerError] = useState("");
  const [pageLeaseStatus, setPageLeaseStatus] = useState<"claiming" | "active" | "replaced">("claiming");
  const [captureControlPending, setCaptureControlPending] = useState<"pause" | "resume" | null>(null);
  const [realtimeDiagnosisNonce, setRealtimeDiagnosisNonce] = useState(0);
  const [idleStatus, setIdleStatus] = useState<IdleInterviewStatus | null>(null);
  const [continuingInterview, setContinuingInterview] = useState(false);
  const [autoAnswerSaving, setAutoAnswerSaving] = useState(false);
  const [splitBounds, setSplitBounds] = useState({ min: ABSOLUTE_MIN_SPLIT_RATIO, max: ABSOLUTE_MAX_SPLIT_RATIO });
  const [mobilePanel, setMobilePanel] = useState<"answer" | "conversation">("answer");
  const workspaceRef = useRef<HTMLDivElement>(null);
  const desktopLayout = useDesktopLiveLayout();
  const submittedCommands = useRef(new Set<string>());
  const attemptedAutoCandidates = useRef(new Set<string>());
  const previousLatestId = useRef(state.questions[0]?.id);
  const screenshotController = useRef<AbortController | null>(null);
  const manualAnswerController = useRef<AbortController | null>(null);
  const beginInstantScreenshotRef = useRef<() => void>(() => undefined);
  const activeShortcutScreenshotRequest = useRef<string | null>(null);
  const terminalShortcutScreenshotRequests = useRef(new Set<string>());
  const seenShortcutScreenshotNotifications = useRef(new Set<string>());
  const realtimeHealthyRef = useRef(false);
  const livePageMountedAtMs = useRef(Date.now());
  const pageInstanceId = useRef(globalThis.crypto?.randomUUID?.() ?? `page-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const liveInterview = state.interviews.find(item => item.id === id);
  const isWritten = liveInterview?.sessionMode === "written";
  const interviewTitle = liveInterview?.title ?? "本场面试";
  const interviewLanguage = liveInterview?.interviewLanguage ?? "en-US";
  const interviewLanguageLabel = interviewLanguageDefinition(interviewLanguage)?.nativeLabel ?? interviewLanguage;
  const active = state.questions[0] ?? emptyLiveQuestion;
  const screenshot = actionState.screenshotTask;
  const setScreenshot = (next: ScreenshotTask | null) => setActionState(current => ({
    ...current,
    screenshotTask: next,
    screenshotAnswerStatus: next
      ? next.stage === "completed" ? "success" : next.stage === "failed" ? "failed" : next.stage === "cancelled" ? "cancelled" : "processing"
      : current.screenshotAnswerStatus ?? "idle",
  }));
  const contextSelection = state.contextSelections[id] ?? { sessionId: id, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null };
  const selectedContextSources = selectionSources(managedLibrarySources(state.librarySources, state.account.id).filter(eligibleSource), contextSelection);
  useEffect(() => { if (typeof window.sessionStorage?.setItem === "function") window.sessionStorage.setItem(storageKey, serializeSplitRatio(view.splitRatio)); }, [storageKey, view.splitRatio]);
  useEffect(() => {
    if (!desktopLayout) return;
    const updateBounds = () => { const width = workspaceRef.current?.getBoundingClientRect().width ?? 0; if (!width) return; const next = width < 900 ? splitRatioBounds(width, 240, 300) : splitRatioBounds(width); setSplitBounds(next); setView(current => ({ ...current, splitRatio: clampSplitRatio(current.splitRatio, next) })); };
    updateBounds(); window.addEventListener("resize", updateBounds); const observer = typeof ResizeObserver === "function" ? new ResizeObserver(updateBounds) : null; if (workspaceRef.current) observer?.observe(workspaceRef.current); return () => { window.removeEventListener("resize", updateBounds); observer?.disconnect(); };
  }, [desktopLayout]);
  useEffect(() => {
    const nextLatestId = state.questions[0]?.id;
    if (!desktopLayout && previousLatestId.current && nextLatestId && previousLatestId.current !== nextLatestId) setMobilePanel("answer");
    setView(current => noteNewAnswer(current, previousLatestId.current, nextLatestId));
    previousLatestId.current = nextLatestId;
  }, [desktopLayout, state.questions]);
  useEffect(() => {
    if (!desktopLayout && state.activeAnswerTask && ["pending", "generating"].includes(state.activeAnswerTask.status)) setMobilePanel("answer");
  }, [desktopLayout, state.activeAnswerTask?.id, state.activeAnswerTask?.status]);
  useEffect(() => () => { screenshotController.current?.abort(); manualAnswerController.current?.abort(); }, []);
  useEffect(() => {
    setState(current => ({
      ...current,
      speaker: isolateRealtimeSpeakerSession(current.speaker, id),
      activeAnswerTask: current.activeAnswerTask?.interviewId === id ? current.activeAnswerTask : null,
    }));
  }, [id, setState]);
  useEffect(() => {
    const controller = new AbortController();
    let stopped = false;
    let inFlight = false;
    const syncWorkspace = async () => {
      if (stopped || inFlight || document.visibilityState !== "visible") return;
      inFlight = true;
      try {
        const snapshot = await runAdapterOperation(signal => interviewAppAdapter.loadInterviewWorkspace(id, signal), controller.signal);
        if (stopped) return;
        setState(current => ({
          ...current,
          ...reconcileAnswerWorkspace(
            { questions: current.questions, activeAnswerTask: current.activeAnswerTask },
            snapshot,
          ),
        }));
      } catch {
        // Keep the current page usable while a cross-device history refresh is temporarily unavailable.
      } finally {
        inFlight = false;
      }
    };
    void syncWorkspace();
    const refreshOnReturn = () => {
      if (document.visibilityState === "visible") void syncWorkspace();
    };
    document.addEventListener("visibilitychange", refreshOnReturn);
    window.addEventListener("focus", refreshOnReturn);
    return () => {
      stopped = true;
      controller.abort();
      document.removeEventListener("visibilitychange", refreshOnReturn);
      window.removeEventListener("focus", refreshOnReturn);
    };
  }, [id, setState]);
  useEffect(() => {
    if (pageLeaseStatus === "replaced") return;
    const controller = new AbortController();
    let stopped = false;
    const refreshIdleStatus = async () => {
      try {
        const next = await runAdapterOperation(signal => interviewAppAdapter.getInterviewIdleStatus(id, signal), controller.signal);
        if (stopped) return;
        setIdleStatus(next);
        if (next.state === "ended") {
          setState(current => ({
            ...current,
            captureState: "ready",
            interviews: current.interviews.map(item => item.id === id ? { ...item, status: "ended" } : item),
          }));
          navigate(routes.review(id), { replace: true });
        }
      } catch {
        // Realtime heartbeat continues to handle connectivity failures.
      }
    };
    void refreshIdleStatus();
    const timer = window.setInterval(() => void refreshIdleStatus(), 15_000);
    return () => { stopped = true; controller.abort(); window.clearInterval(timer); };
  }, [id, navigate, pageLeaseStatus, setState]);
  useEffect(() => {
    if (pageLeaseStatus === "replaced") return;
    const controller = new AbortController();
    let stopped = false;
    let inFlight = false;
    const syncShortcutAnswers = async () => {
      if (stopped || inFlight || realtimeHealthyRef.current || document.visibilityState !== "visible") return;
      inFlight = true;
      try {
        const updates = await runAdapterOperation(
          signal => interviewAppAdapter.loadDesktopShortcutScreenshotUpdates(id, signal),
          controller.signal,
        );
        if (stopped || updates.length === 0) return;
        const latest = updates[updates.length - 1]!;
        const latestAlreadyTerminal = terminalShortcutScreenshotRequests.current.has(latest.requestId);
        if ((latest.status === "requested" || latest.status === "processing") && !latestAlreadyTerminal) {
          activeShortcutScreenshotRequest.current = latest.requestId;
          setScreenshot(latest.screenshotTask);
        } else if (!latestAlreadyTerminal) {
          terminalShortcutScreenshotRequests.current.add(latest.requestId);
          if (activeShortcutScreenshotRequest.current === latest.requestId) {
            activeShortcutScreenshotRequest.current = null;
          }
          if (latest.status === "completed") {
            setActionState(current => ({ ...current, screenshotTask: null, screenshotAnswerStatus: "success" }));
          } else {
            setScreenshot(latest.screenshotTask);
          }
        }
        const results = updates.flatMap(update => update.result ? [update.result] : []);
        setState(current => {
          if (results.length === 0) return current;
          const newest = results.reduce((latest, result) => result.task.updatedAtMs > latest.task.updatedAtMs ? result : latest);
          return {
            ...current,
            ...reconcileAnswerWorkspace(
              { questions: current.questions, activeAnswerTask: current.activeAnswerTask },
              { questions: results.map(result => result.question), activeAnswerTask: newest.task },
            ),
          };
        });
      } catch {
        // Shortcut result synchronization is best-effort and must not interrupt live audio or manual answers.
      } finally {
        inFlight = false;
      }
    };
    void syncShortcutAnswers();
    const timer = window.setInterval(() => void syncShortcutAnswers(), SHORTCUT_SCREENSHOT_RECOVERY_POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      controller.abort();
      window.clearInterval(timer);
    };
  }, [id, pageLeaseStatus, setState]);
  useEffect(() => {
    let stopped = false;
    let heartbeatTimer: number | null = null;
    let heartbeatBindingId: string | null = null;
    let leaseGeneration: number | null = null;
    let lastBindingRefreshAt = 0;
    let reconnectTimer: number | null = null;
    let reconnectAttempt = 0;
    let invalidSessionSuspended = false;
    let realtimeSubscribeInFlight = false;
    let realtimeStreamHealthy = false;
    let realtimeLoadInFlight = false;
    let streamController: AbortController | null = null;
    const realtimeController = new AbortController();
    const coordinator = createLiveSessionLeaderCoordinator(
      `offersteady:live-session:${state.account.id}:${id}`,
      pageInstanceId.current,
    );
    let isRealtimeLeader = coordinator === null;
    const realtimeErrorStatus = (error: unknown) => {
      if (typeof error === "object" && error !== null && "status" in error && typeof error.status === "number") return error.status;
      const match = error instanceof Error ? error.message.match(/[（(](\d{3})[）)]/) : null;
      return match ? Number(match[1]) : null;
    };
    const pauseReplacedPage = () => {
      if (stopped) return;
      stopped = true;
      realtimeHealthyRef.current = false;
      setPageLeaseStatus("replaced");
      setNotice("");
      realtimeController.abort();
      streamController?.abort();
      manualAnswerController.current?.abort();
      screenshotController.current?.abort();
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (heartbeatTimer !== null) window.clearInterval(heartbeatTimer);
    };
    const applyRealtimeState = (realtime: RealtimeSessionUpdate, relay = true) => {
      if (stopped) return;
      const shortcut = realtime.shortcutScreenshotUpdate;
      const notificationId = shortcut?.notificationId;
      if (
        shortcut
        && notificationId
        && !seenShortcutScreenshotNotifications.current.has(notificationId)
        && !terminalShortcutScreenshotRequests.current.has(shortcut.requestId)
        && isFreshShortcutScreenshotAcceptance(shortcut.acceptedAtMs, livePageMountedAtMs.current)
      ) {
        seenShortcutScreenshotNotifications.current.add(notificationId);
        activeShortcutScreenshotRequest.current = shortcut.requestId;
        setScreenshot(shortcut.screenshotTask);
      }
      if (shortcut && shortcut.acceptedAtMs === undefined) {
        const alreadyTerminal = terminalShortcutScreenshotRequests.current.has(shortcut.requestId);
        if ((shortcut.status === "requested" || shortcut.status === "processing") && !alreadyTerminal) {
          activeShortcutScreenshotRequest.current = shortcut.requestId;
          setScreenshot(shortcut.screenshotTask);
        } else if (!alreadyTerminal) {
          terminalShortcutScreenshotRequests.current.add(shortcut.requestId);
          if (activeShortcutScreenshotRequest.current === shortcut.requestId) activeShortcutScreenshotRequest.current = null;
          if (shortcut.status === "completed") {
            setActionState(current => ({ ...current, screenshotTask: null, screenshotAnswerStatus: "success" }));
          } else if (shortcut.status === "cancelled") {
            setActionState(current => ({ ...current, screenshotTask: null, screenshotAnswerStatus: "cancelled" }));
          } else {
            setScreenshot(shortcut.screenshotTask);
          }
        }
      }
      setState(current => {
        const answerResults = [realtime.answerUpdate, shortcut?.result].filter((result): result is NonNullable<typeof result> => Boolean(result));
        const newestAnswer = answerResults.length > 0
          ? answerResults.reduce((latest, result) => result.task.updatedAtMs > latest.task.updatedAtMs ? result : latest)
          : null;
        const workspace = newestAnswer
          ? reconcileAnswerWorkspace(
              { questions: current.questions, activeAnswerTask: current.activeAnswerTask },
              {
                questions: answerResults.map(result => result.question),
                activeAnswerTask: newestAnswer.task,
              },
            )
          : { questions: current.questions, activeAnswerTask: current.activeAnswerTask };
        return {
          ...current,
          ...workspace,
          speaker: reconcileRealtimeSpeaker(current.speaker, realtime.speaker, id),
          ...(realtime.captureState ? { captureState: realtime.captureState } : {}),
        };
      });
      if (relay) coordinator?.publishState(realtime);
    };
    const sendHeartbeat = async () => {
      if (!isRealtimeLeader) return false;
      try {
        const now = Date.now();
        if (!heartbeatBindingId || now - lastBindingRefreshAt >= 30_000) {
          const binding = await runAdapterOperation(signal => interviewAppAdapter.getDesktopDeviceBinding(id, signal));
          if (binding?.bindingId) heartbeatBindingId = binding.bindingId;
          lastBindingRefreshAt = now;
        }
        const lease = await runAdapterOperation(signal => interviewAppAdapter.sendDesktopSessionHeartbeat({ interviewId: id, bindingId: heartbeatBindingId, page: "live", pageInstanceId: pageInstanceId.current }, signal));
        if (lease.pageInstanceId !== pageInstanceId.current || lease.leaseGeneration < 1) {
          pauseReplacedPage();
          return false;
        }
        leaseGeneration = lease.leaseGeneration;
        setPageLeaseStatus("active");
        return true;
      } catch (error) {
        if (isInvalidRealtimeSessionStatus(realtimeErrorStatus(error))) {
          pauseReplacedPage();
          return false;
        }
        heartbeatBindingId = null;
        // Realtime polling below will continue to surface backend connectivity issues without blocking manual answers.
        return false;
      }
    };
    const loadRealtime = async () => {
      if (!isRealtimeLeader || realtimeLoadInFlight || stopped || document.visibilityState !== "visible" || leaseGeneration === null) return false;
      realtimeLoadInFlight = true;
      try {
        const realtime = await runAdapterOperation(signal => interviewAppAdapter.loadRealtimeSession(
          id,
          signal,
          { pageInstanceId: pageInstanceId.current, leaseGeneration: leaseGeneration! },
        ));
        applyRealtimeState(realtime);
        return true;
      } catch {
        // Keep manual question and screenshot flows available when realtime sync is temporarily unavailable.
        return false;
      } finally {
        realtimeLoadInFlight = false;
      }
    };
    const scheduleReconnect = (status: number | null = null) => {
      if (stopped || realtimeController.signal.aborted) return;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      invalidSessionSuspended = isInvalidRealtimeSessionStatus(status);
      const delay = realtimeRetryDelayMs(status, reconnectAttempt);
      reconnectAttempt += 1;
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null;
        invalidSessionSuspended = false;
        void subscribeRealtime();
      }, delay);
    };
    const subscribeRealtime = async () => {
      if (!isRealtimeLeader || realtimeSubscribeInFlight || stopped || realtimeController.signal.aborted || leaseGeneration === null) return;
      const activeLeaseGeneration = leaseGeneration;
      const activeStreamController = new AbortController();
      streamController = activeStreamController;
      const abortStream = () => activeStreamController.abort();
      realtimeController.signal.addEventListener("abort", abortStream, { once: true });
      realtimeSubscribeInFlight = true;
      try {
        await runAdapterOperation(signal => interviewAppAdapter.subscribeRealtimeSession(id, (realtime, delivery) => {
          if (delivery?.type === "snapshot") {
            realtimeStreamHealthy = true;
            realtimeHealthyRef.current = true;
            invalidSessionSuspended = false;
            reconnectAttempt = realtimeReconnectAttemptAfterRecovery(reconnectAttempt, "stream-snapshot");
            if (reconnectTimer !== null) {
              window.clearTimeout(reconnectTimer);
              reconnectTimer = null;
            }
          }
          applyRealtimeState(realtime);
        }, signal, { pageInstanceId: pageInstanceId.current, leaseGeneration: activeLeaseGeneration }), activeStreamController.signal);
        realtimeStreamHealthy = false;
        realtimeHealthyRef.current = false;
        if (!stopped && !realtimeController.signal.aborted) scheduleReconnect();
      } catch (error) {
        if (stopped || realtimeController.signal.aborted) return;
        realtimeStreamHealthy = false;
        realtimeHealthyRef.current = false;
        const status = realtimeErrorStatus(error);
        if (isInvalidRealtimeSessionStatus(status)) {
          window.sessionStorage?.removeItem(`offersteady:realtime-cursor:${id}`);
          if (status === 409 || status === 410) pauseReplacedPage();
          else {
            setNotice("当前面试会话已失效，请从面试首页重新进入。");
            navigate(sessionHomeRoute(liveInterview?.sessionMode), { replace: true });
          }
          return;
        }
        const recovered = await loadRealtime();
        if (recovered) reconnectAttempt = realtimeReconnectAttemptAfterRecovery(reconnectAttempt, "fallback-snapshot");
        scheduleReconnect(status);
      } finally {
        realtimeSubscribeInFlight = false;
        realtimeController.signal.removeEventListener("abort", abortStream);
        if (streamController === activeStreamController) streamController = null;
      }
    };
    coordinator?.start({
      onLeadershipChange: leader => {
        isRealtimeLeader = leader;
        if (!leader) {
          realtimeStreamHealthy = false;
          realtimeHealthyRef.current = false;
          streamController?.abort();
          streamController = null;
          if (reconnectTimer !== null) {
            window.clearTimeout(reconnectTimer);
            reconnectTimer = null;
          }
          return;
        }
        void sendHeartbeat().then(claimed => {
          if (claimed) void subscribeRealtime();
        });
      },
      onState: realtime => {
        realtimeStreamHealthy = true;
        realtimeHealthyRef.current = true;
        applyRealtimeState(realtime, false);
      },
    }, document.visibilityState === "visible");
    heartbeatTimer = window.setInterval(() => void sendHeartbeat(), 15_000);
    const resumeRealtime = () => {
      if (stopped || !isRealtimeLeader || document.visibilityState !== "visible") return;
      void sendHeartbeat();
      if (invalidSessionSuspended) return;
      if (!realtimeStreamHealthy && !realtimeSubscribeInFlight) {
        if (reconnectTimer !== null) {
          window.clearTimeout(reconnectTimer);
          reconnectTimer = null;
        }
        reconnectAttempt = 0;
        void subscribeRealtime();
      }
    };
    const handleVisibilityChange = () => {
      coordinator?.setEligible(document.visibilityState === "visible");
      if (document.visibilityState === "visible") resumeRealtime();
    };
    const handlePageHide = () => coordinator?.setEligible(false);
    const handlePageShow = () => {
      coordinator?.setEligible(document.visibilityState === "visible");
      if (document.visibilityState === "visible") resumeRealtime();
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", handlePageHide);
    window.addEventListener("pageshow", handlePageShow);
    window.addEventListener("focus", resumeRealtime);
    window.addEventListener("online", resumeRealtime);
    if (isRealtimeLeader) {
      void sendHeartbeat().then(claimed => {
        if (!claimed || stopped) return;
        void subscribeRealtime();
      });
    }
    return () => {
      stopped = true;
      realtimeHealthyRef.current = false;
      realtimeController.abort();
      streamController?.abort();
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (heartbeatTimer !== null) window.clearInterval(heartbeatTimer);
      coordinator?.stop();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", handlePageHide);
      window.removeEventListener("pageshow", handlePageShow);
      window.removeEventListener("focus", resumeRealtime);
      window.removeEventListener("online", resumeRealtime);
    };
  }, [id, navigate, realtimeDiagnosisNonce, setState, state.account.id]);
  const scopedAdvice = {
    ...active.advice,
    detail: selectedContextSources.length ? active.advice.detail : "当前没有选择个人资料。请使用通用结构组织回答，并只补充你能够核对的真实经历、职责和结果。",
    sourceTypes: selectedContextSources.map(source => source.kind === "resume" ? "简历" as const : source.kind === "jd" ? "JD" as const : "知识库" as const),
    inference: "",
    uncertain: selectedContextSources.length === 0,
    provenance: { selectionRevision: contextSelection.revision, usedSources: selectedContextSources.map(source => ({ sourceId: source.id, sourceVersion: source.version, displayName: source.displayName, kind: source.kind })) },
  };
  const syncBilling = async () => {
    try {
      const refreshed = await interviewAppAdapter.loadState();
      setState(current => ({ ...current, billing: refreshed.billing }));
    } catch {
      // The completed task remains usable; the next state refresh will reconcile billing.
    }
  };
  const activeTaskFor = (question: InterviewQuestion, usageId: string): AnswerTaskSnapshot => ({ id: `answer:${question.id}:${Date.now()}`, interviewId: id, userId: state.account.id, billingUsageId: usageId, questionId: question.id, question: question.text, revision: 1, status: "generating", partialText: "正在整理回答结构…", updatedAtMs: Date.now() });
  const pendingManualQuestion = (text: string, questionId: string, input: InterviewQuestion["input"] = "manual"): InterviewQuestion => ({
    ...active,
    id: questionId,
    text,
    input,
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
  const submitManualText = async (
    text: string,
    replaceQuestionId?: string,
    frozenQuestion?: { readonly questionId: string; readonly questionRevision: number; readonly clickedAtMs: number; readonly prefetchRevision: number; readonly triggerMode?: "manual" | "auto" },
  ) => {
    const trimmed = text.trim(); if (!trimmed) return;
    const clickedAtMs = frozenQuestion?.clickedAtMs ?? Date.now();
    const command = frozenQuestion?.triggerMode === "auto" ? `auto:${id}:${frozenQuestion.questionId}` : `manual:${id}:${trimmed}`; if (submittedCommands.current.has(command)) return;
    submittedCommands.current.add(command); setNotice("");
    setActionState(current => ({ ...current, quickAnswerStatus: "processing", quickAnswerMessage: "" }));
    const pendingId = replaceQuestionId ?? `manual-pending-${Date.now()}`;
    const pendingQuestion = pendingManualQuestion(trimmed, pendingId, frozenQuestion?.triggerMode === "auto" ? "desktop-audio" : "manual");
    const pendingTask: AnswerTaskSnapshot = { id: `pending:${pendingId}`, interviewId: id, userId: state.account.id, billingUsageId: `pending:${pendingId}`, questionId: pendingId, question: trimmed, revision: 1, status: "generating", partialText: "正在调用当前对话模型生成回答…", clickedAtMs, updatedAtMs: Date.now() };
    setState(current => ({ ...current, questions: replaceQuestionId ? current.questions.map(item => item.id === replaceQuestionId ? pendingQuestion : item) : [pendingQuestion, ...current.questions], activeAnswerTask: pendingTask }));
    setActionState(current => ({ ...current, manualDraft: "" }));
    setView(current => ({ ...current, viewingAnswerId: null, newAnswerAvailable: false }));
    type StreamUpdate = Parameters<NonNullable<Parameters<typeof interviewAppAdapter.submitManualAnswer>[2]>>[0];
    let firstAnswerTiming: LiveAnswerStreamEvent["timing"];
    const applyStreamUpdate = (update: StreamUpdate) => {
      setState(current => ({
        ...current,
        ...reconcileAnswerWorkspace(
          {
            questions: current.questions.filter(item => item.id !== pendingId && item.id !== update.result.question.id),
            activeAnswerTask: current.activeAnswerTask,
          },
          { questions: [update.result.question], activeAnswerTask: update.result.task },
          { preferIncomingTask: true },
        ),
      }));
      const renderedText = update.result.task.partialText ?? update.result.task.completedText ?? "";
      if (
        update.event.type === "chunk"
        && renderedText.trim()
        && update.result.task.clickedAtMs
        && interviewAppAdapter.acknowledgeAnswerFirstRender
      ) {
        const acknowledge = () => interviewAppAdapter.acknowledgeAnswerFirstRender?.({
          interviewId: id,
          taskId: update.result.task.id,
          clickedAtMs: update.result.task.clickedAtMs!,
          ...(update.event.receivedAtMs === undefined ? {} : { browserEventReceiveAtMs: update.event.receivedAtMs }),
          browserRenderAtMs: Date.now(),
          renderedTextLength: renderedText.length,
          timing: update.event.timing,
        });
        if (typeof requestAnimationFrame === "function") requestAnimationFrame(() => requestAnimationFrame(acknowledge));
        else window.setTimeout(acknowledge, 0);
      }
    };
    const streamUpdateScheduler = createAnswerStreamUpdateScheduler<StreamUpdate>({
      apply: applyStreamUpdate,
      isFirstVisible: update => update.event.type === "chunk" && Boolean(update.event.chunk?.text.trim()),
    });
    try {
      manualAnswerController.current?.abort();
      const controller = new AbortController();
      manualAnswerController.current = controller;
      const result = await runAdapterOperation(signal => interviewAppAdapter.submitManualAnswer({ interviewId: id, question: trimmed, idempotencyKey: command, ...frozenQuestion, clickedAtMs }, signal, update => {
        firstAnswerTiming ??= update.event.timing;
        const enrichedUpdate = firstAnswerTiming && !update.event.timing
          ? { ...update, event: { ...update.event, timing: firstAnswerTiming } }
          : update;
        streamUpdateScheduler.push(enrichedUpdate, ["completed", "failed", "cancelled"].includes(update.event.type));
      }), controller.signal);
      streamUpdateScheduler.flush();
      setState(current => ({
        ...current,
        ...reconcileAnswerWorkspace(
          { questions: current.questions.filter(item => item.id !== pendingId && item.id !== result.question.id), activeAnswerTask: current.activeAnswerTask },
          { questions: [result.question], activeAnswerTask: result.task },
          { preferIncomingTask: true },
        ),
      }));
      setActionState(current => ({ ...current, quickAnswerStatus: result.task.status === "failed" ? "failed" : result.task.status === "completed" ? "success" : "processing", quickAnswerMessage: result.task.status === "failed" ? result.task.partialText ?? "快答失败，可重试" : "" }));
      if (result.task.status === "completed") void syncBilling();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (error instanceof Error && error.message === "请求已取消") return;
      const message = error instanceof Error ? error.message : "回答生成失败，请稍后重试。";
      setNotice(message);
      setActionState(current => ({ ...current, quickAnswerStatus: "failed", quickAnswerMessage: message }));
      setState(current => ({ ...current, questions: current.questions.map(item => item.id === pendingId ? failedManualQuestion(item, message) : item), activeAnswerTask: current.activeAnswerTask?.questionId === pendingId ? { ...current.activeAnswerTask, status: "failed", partialText: message, updatedAtMs: Date.now() } : current.activeAnswerTask }));
    } finally {
      streamUpdateScheduler.dispose();
      manualAnswerController.current = null;
      submittedCommands.current.delete(command);
    }
  };
  useEffect(() => {
    const candidate = state.speaker.autoAnswerQuestion;
    const enabledAtMs = liveInterview?.autoAnswerEnabledAtMs ?? null;
    const taskBusy = Boolean(state.activeAnswerTask && ["pending", "generating"].includes(state.activeAnswerTask.status));
    if (
      !liveInterview?.autoAnswerEnabled
      || !enabledAtMs
      || !candidate
      || (candidate.createdAtMs ?? 0) < enabledAtMs
      || candidate.answerTaskId
      || candidate.state !== "auto-confirmed"
      || state.speaker.mode !== "dual-channel"
      || !["capturing", "reconnecting"].includes(state.captureState)
      || pageLeaseStatus !== "active"
      || taskBusy
      || attemptedAutoCandidates.current.has(candidate.id)
    ) return;
    attemptedAutoCandidates.current.add(candidate.id);
    void submitManualText(candidate.text, undefined, {
      questionId: candidate.id,
      questionRevision: candidate.revision,
      clickedAtMs: Date.now(),
      prefetchRevision: candidate.revision,
      triggerMode: "auto",
    });
  }, [
    liveInterview?.autoAnswerEnabled,
    liveInterview?.autoAnswerEnabledAtMs,
    pageLeaseStatus,
    state.activeAnswerTask?.id,
    state.activeAnswerTask?.status,
    state.captureState,
    state.speaker.autoAnswerQuestion?.id,
    state.speaker.autoAnswerQuestion?.answerTaskId,
    state.speaker.mode,
  ]);
  const toggleAutoAnswer = async (enabled: boolean) => {
    if (autoAnswerSaving || pageLeaseStatus === "replaced") return;
    setAutoAnswerSaving(true);
    setNotice("");
    try {
      const updated = await runAdapterOperation(signal => interviewAppAdapter.updateInterviewAutoAnswer(id, enabled, signal));
      attemptedAutoCandidates.current.clear();
      setState(current => ({
        ...current,
        interviews: current.interviews.map(item => item.id === id ? { ...item, ...updated } : item),
      }));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "自动回答设置保存失败，请稍后重试。");
    } finally {
      setAutoAnswerSaving(false);
    }
  };
  const latestInterviewerQuestion = () => extractLatestInterviewerQuestion(state.speaker);
  const latestInterviewerText = latestInterviewerQuestion();
  const submitManual = () => {
    const fallback = latestInterviewerQuestion();
    const question = actionState.manualDraft.trim() || fallback;
    if (!question) { setNotice(QUICK_ANSWER_MISSING_QUESTION_NOTICE); return; }
    const source = [...state.speaker.transcripts]
      .reverse()
      .find(item => item.sourceKind === "system" || item.role === "interviewer");
    const candidate = state.speaker.pendingQuestion;
    const revision = candidate?.revision ?? source?.revision;
    const questionId = candidate?.id ?? source?.id;
    void submitManualText(
      question,
      undefined,
      questionId && revision ? {
        questionId,
        questionRevision: revision,
        clickedAtMs: Date.now(),
        prefetchRevision: revision,
      } : undefined,
    );
  };
  useEffect(() => {
    if (latestInterviewerText && notice === QUICK_ANSWER_MISSING_QUESTION_NOTICE) setNotice("");
  }, [latestInterviewerText, notice]);
  const setCapture = (captureState: CaptureState, status: SessionStatus) => setState(current => ({
    ...current,
    captureState,
    interviews: current.interviews.map(item => item.id === id ? { ...item, status } : item),
  }));
  const controlCapture = async (action: "pause" | "resume") => {
    if (captureControlPending || pageLeaseStatus === "replaced") return;
    setCaptureControlPending(action);
    setNotice("");
    try {
      const captureState = await runAdapterOperation(signal => interviewAppAdapter.controlInterviewCapture(id, action, signal));
      setCapture(captureState, captureState === "paused" ? "paused" : "active");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : action === "pause" ? "暂停收音失败，请稍后重试。" : "恢复收音失败，请稍后重试。");
    } finally {
      setCaptureControlPending(null);
    }
  };
  const continueIdleInterview = async () => {
    if (continuingInterview) return;
    setContinuingInterview(true);
    try {
      const next = await runAdapterOperation(signal => interviewAppAdapter.continueInterviewSession(id, signal));
      setIdleStatus(next);
    } finally {
      setContinuingInterview(false);
    }
  };
  const finishInterview = async () => {
    if (!window.confirm(isWritten
      ? "End this written exam? Its answer history will remain available."
      : "End this interview? Audio capture will stop and the review will open.")) return;
    try {
      await runAdapterOperation(signal => interviewAppAdapter.endInterviewSession(id, signal));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : isWritten ? "结束笔试失败，请稍后重试。" : "结束面试失败，请稍后重试。");
      return;
    }
    setCapture("ready", "ended");
    navigate(routes.review(id));
  };
  const updateQuestionStatus = (questionId: string, status: QuestionStatus) => {
    const question = state.questions.find(item => item.id === questionId);
    if (!question) return;
    if (question.status === "cancelled" && status === "generating") {
      if (question.input === "manual") { void submitManualText(question.text, questionId); return; }
      const usageId = `retry:${questionId}:${Date.now()}`;
      const task: AnswerTaskSnapshot = { id: `answer:${questionId}:${Date.now()}`, interviewId: id, userId: state.account.id, billingUsageId: usageId, questionId, question: question.text, revision: 1, status: "generating", partialText: "正在重新整理回答…", updatedAtMs: Date.now() };
      setState(current => ({ ...current, questions: current.questions.map(item => item.id === questionId ? { ...item, status } : item), activeAnswerTask: task }));
      return;
    }
    setState(current => ({ ...current, questions: current.questions.map(item => item.id === questionId ? { ...item, status } : item) }));
  };
  const screenshotInstruction = globalScreenshotInstruction.trim();
  const submitScreenshot = async () => {
    const usageId = `screenshot:remote:${Date.now()}`;
    const placeholderId = `shot-pending-${Date.now()}`;
    const placeholderQuestion: InterviewQuestion = {
      ...active,
      id: placeholderId,
      text: "请根据当前截图直接回答",
      input: "screenshot",
      askedAt: "刚刚",
      status: "generating",
      advice: {
        outline: [],
        detail: "正在识别当前截图并生成回答…",
        sourceTypes: [],
        inference: "",
        uncertain: false,
        provenance: { selectionRevision: 0, usedSources: [] },
      },
    };
    const placeholderTask = activeTaskFor(placeholderQuestion, usageId);
    setState(current => ({ ...current, questions: [placeholderQuestion, ...current.questions], activeAnswerTask: placeholderTask }));
    setView(current => ({ ...current, viewingAnswerId: null, newAnswerAvailable: false }));
    try {
      const result = await runAdapterOperation(signal => interviewAppAdapter.submitScreenshotAnswer({
        interviewId: id,
        instruction: screenshotInstruction,
      }, signal, task => setScreenshot(task), streamed => {
        setState(current => ({
          ...current,
          ...reconcileAnswerWorkspace(
            {
              questions: current.questions.filter(item => item.id !== placeholderId),
              activeAnswerTask: current.activeAnswerTask?.questionId === placeholderId ? null : current.activeAnswerTask,
            },
            { questions: [streamed.question], activeAnswerTask: streamed.task },
            { preferIncomingTask: true },
          ),
        }));
      }), screenshotController.current?.signal);
      setState(current => ({
        ...current,
        ...reconcileAnswerWorkspace(
          {
            questions: current.questions.filter(item => item.id !== placeholderId),
            activeAnswerTask: current.activeAnswerTask?.questionId === placeholderId ? null : current.activeAnswerTask,
          },
          { questions: [result.question], activeAnswerTask: result.task },
          { preferIncomingTask: true },
        ),
      }));
      setActionState(current => ({ ...current, screenshotTask: null, screenshotAnswerStatus: "success" }));
      if (result.task.status === "completed") void syncBilling();
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
    if (task.stage === "generating") return null;
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
  const cancelScreenshot = async () => {
    const shortcutRequestId = activeShortcutScreenshotRequest.current;
    if (shortcutRequestId) {
      terminalShortcutScreenshotRequests.current.add(shortcutRequestId);
      activeShortcutScreenshotRequest.current = null;
      setActionState(current => ({ ...current, screenshotTask: null, screenshotAnswerStatus: "cancelled" }));
      try {
        await runAdapterOperation(signal => interviewAppAdapter.cancelDesktopShortcutScreenshot(shortcutRequestId, signal));
      } catch (error) {
        terminalShortcutScreenshotRequests.current.delete(shortcutRequestId);
        screenshotFailure(error instanceof Error ? error.message : "取消截屏回答失败，请稍后重试。");
      }
      return;
    }
    screenshotController.current?.abort();
    screenshotController.current = null;
    setActionState(current => ({ ...current, screenshotTask: null, screenshotAnswerStatus: "cancelled" }));
    setState(current => {
      const task = current.activeAnswerTask;
      if (!task || !task.billingUsageId.startsWith("screenshot:remote:") || (task.status !== "queued" && task.status !== "generating")) return current;
      return {
        ...current,
        activeAnswerTask: { ...task, status: "cancelled", revision: task.revision + 1, updatedAtMs: Date.now() },
        questions: current.questions.map(question => question.id === task.questionId ? { ...question, status: "cancelled" } : question),
      };
    });
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
  beginInstantScreenshotRef.current = beginInstantScreenshot;
  useEffect(() => {
    const handleScreenshotShortcut = (event: KeyboardEvent) => {
      if (
        pageLeaseStatus === "replaced" ||
        event.repeat ||
        event.altKey ||
        event.metaKey ||
        !event.ctrlKey ||
        !event.shiftKey ||
        event.code !== "Space"
      ) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      beginInstantScreenshotRef.current();
    };
    window.addEventListener("keydown", handleScreenshotShortcut, { capture: true });
    return () => window.removeEventListener("keydown", handleScreenshotShortcut, { capture: true });
  }, [pageLeaseStatus]);
  const dismissPending = () => setState(current => ({ ...current, speaker: { ...current.speaker, pendingQuestion: null } }));
  const confirmPending = () => {
    const candidate = state.speaker.pendingQuestion; if (!candidate) return;
    setState(current => ({ ...current, speaker: { ...current.speaker, pendingQuestion: null } }));
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
      const taskInput = state.questions.find(question => question.id === task.questionId)?.input;
      setActionState(current => ({
        ...current,
        screenshotTask: taskInput === "screenshot" ? null : current.screenshotTask,
        ...(taskInput === "screenshot" ? { screenshotAnswerStatus: "cancelled" as const } : {}),
        ...(taskInput === "manual" ? { quickAnswerStatus: "cancelled" as const, quickAnswerMessage: "" } : {}),
      }));
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
      if (result.outcome === "cancelled" || result.outcome === "already-cancelled") {
        const taskInput = state.questions.find(question => question.id === result.task.questionId)?.input;
        if (taskInput === "manual") setActionState(current => ({ ...current, quickAnswerStatus: "cancelled", quickAnswerMessage: "" }));
        if (taskInput === "screenshot") setActionState(current => ({ ...current, screenshotTask: null, screenshotAnswerStatus: "cancelled" }));
        setState(current => {
        const hasFrontendReserve = !result.task.billingUsageId.startsWith("live-answer:") && !result.task.billingUsageId.startsWith("pending:");
        return { ...current, activeAnswerTask: result.task, questions: current.questions.map(question => question.id === result.task.questionId ? { ...question, status: "cancelled" } : question), billing: result.billingReleased && hasFrontendReserve && !current.billing.activePass ? { ...current.billing, balance: current.billing.balance + current.billing.rates.answerPoints, ledger: [{ id: `release-${result.task.billingUsageId}`, userId: current.account.id, kind: "usage_release", points: current.billing.rates.answerPoints, createdAtMs: Date.now(), referenceId: result.task.billingUsageId, description: "回答已终止，积分预留已释放" }, ...current.billing.ledger] } : current.billing };
        });
      }
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
  const missingQuestionNotice = notice === QUICK_ANSWER_MISSING_QUESTION_NOTICE;
  const captureActive = state.captureState === "capturing" || state.captureState === "reconnecting";
  const captureStatus = pageLeaseStatus === "replaced" ? "已在其他页面继续" : captureActive ? "正在收音" : state.captureState === "paused" ? "收音已暂停" : state.captureState === "permission-required" ? "采集能力不可用" : state.captureState === "error" ? "设备连接异常" : "已连接，未采集";
  const captureButton = captureActive
    ? <button className="button warning live-session-control" disabled={pageLeaseStatus === "replaced" || captureControlPending !== null} onClick={() => void controlCapture("pause")}>{captureControlPending === "pause" ? "暂停中…" : "暂停收音"}</button>
    : <button className="button primary live-session-control" disabled={pageLeaseStatus === "replaced" || captureControlPending !== null || (state.captureState !== "ready" && state.captureState !== "paused")} onClick={() => state.captureState === "paused" ? void controlCapture("resume") : setCapture("capturing", "active")}>{captureControlPending === "resume" ? "恢复中…" : state.captureState === "paused" ? "恢复收音" : "开始面试"}</button>;
  const changeManualDraft = (value: string) => {
    setActionState(current => ({ ...current, manualDraft: value, quickAnswerStatus: "idle", quickAnswerMessage: "" }));
    if (value.trim() && notice === QUICK_ANSWER_MISSING_QUESTION_NOTICE) setNotice("");
  };
  const conversationPanel = <ConversationMonitor state={state} onConfirmQuestion={pageLeaseStatus === "replaced" ? dismissPending : confirmPending} onDismissQuestion={dismissPending} />;
  const answerPanel = <AnswerWorkspace answers={state.questions} viewingAnswerId={view.viewingAnswerId} newAnswerAvailable={view.newAnswerAvailable} activeTask={state.activeAnswerTask} cancelling={cancellingAnswer} cancelError={cancelAnswerError} interviewLanguage={interviewLanguage} onStop={() => void stopAnswer()} onView={answerId => setView(current => ({ ...current, viewingAnswerId: answerId, newAnswerAvailable: answerId ? current.newAnswerAvailable : false }))} onRetry={updateQuestionStatus} />;

  if (isWritten) return <main className={`live-page focused-live-page${desktopLayout ? " desktop-live-page" : " mobile-live-page"}`}><header className="live-top"><Link to={routes.writtenExams} aria-label="返回笔试模式"><Logo /></Link><div className="live-session-heading"><strong>{interviewTitle}</strong><span><i className="online-dot" /> 桌面助手已连接 · 截屏回答可用</span><small className="live-language-badge">笔试模式</small></div><div className="live-top-actions"><Link className="live-balance" to={routes.billing}>积分与会员</Link><AccountMenu compact /><button className="button danger live-session-control" disabled={pageLeaseStatus === "replaced"} onClick={() => void finishInterview()}>结束笔试</button></div></header>{notice ? <div className="global-live-alert" role="alert"><strong>{notice}</strong><button type="button" onClick={() => setNotice("")}>关闭</button></div> : null}{pageLeaseStatus === "replaced" ? <div className="global-live-alert replaced-page-alert" role="status"><strong>本场笔试已在其他页面继续</strong><Link className="button primary" to={routes.writtenExams}>返回笔试模式</Link></div> : null}<div className="written-exam-workspace"><section className="answer-column">{answerPanel}<AnswerActionBar manualDraft="" screenshotTask={actionState.screenshotTask} screenshotOnly screenshotAnswerStatus={actionState.screenshotAnswerStatus ?? "idle"} disabled={pageLeaseStatus === "replaced"} onQuickAnswer={() => undefined} onScreenshot={beginInstantScreenshot} /></section></div>{screenshot && pageLeaseStatus !== "replaced" ? <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="screenshot-dialog-title"><section className="sheet"><h2 id="screenshot-dialog-title">{screenshotStageTitle(screenshot)}</h2>{screenshotStageDetail(screenshot) ? <p>{screenshotStageDetail(screenshot)}</p> : null}{screenshot.stage === "failed" ? <div className="sheet-actions split-actions"><button className="button ghost full" onClick={dismissScreenshotFailure}>删除本次失败</button><button className="button primary full" onClick={beginInstantScreenshot}>重新截屏</button></div> : <button className="button primary full" onClick={() => void cancelScreenshot()}>取消</button>}</section></div> : null}<footer className="session-bar"><div><i className="online-dot" /><strong>笔试进行中</strong></div><div><small>仅在你主动发起时截屏并生成回答</small></div></footer></main>;

  return <main className={`live-page focused-live-page${desktopLayout ? " desktop-live-page" : " mobile-live-page"}`}>
    <header className="live-top">
      <Link to={routes.app} aria-label="返回面试首页"><Logo /></Link>
      <div className="live-session-heading"><strong>{interviewTitle}</strong><span><i className={captureActive ? "recording-dot" : "online-dot"} /> {desktopLayout ? `This device · ${captureStatus}` : captureStatus}</span><small className="live-language-badge">{interviewLanguageLabel}</small></div>
      {desktopLayout ? <div className="live-top-actions"><div className="live-auto-answer"><span>自动回答</span><label className="switch-control"><input type="checkbox" role="switch" aria-label="自动回答" checked={liveInterview?.autoAnswerEnabled ?? false} disabled={autoAnswerSaving || pageLeaseStatus === "replaced"} onChange={event => void toggleAutoAnswer(event.target.checked)} /><span aria-hidden="true" /></label></div><Link className="live-balance" to={routes.billing}>积分与会员</Link><details className="live-contact-menu"><summary>联系我们</summary><div className="live-contact-popover" aria-label="官方社交账号">{officialSocialContacts.map(contact => <p key={contact.id}><small>{contact.label}</small><strong>{contact.account}</strong></p>)}</div></details><span>18:24</span><AccountMenu compact />{captureButton}<button className="button danger live-session-control" disabled={pageLeaseStatus === "replaced"} onClick={() => void finishInterview()}>结束面试</button></div> : <div className="mobile-live-top-actions"><div className="live-auto-answer mobile"><span>自动</span><label className="switch-control"><input type="checkbox" role="switch" aria-label="自动回答" checked={liveInterview?.autoAnswerEnabled ?? false} disabled={autoAnswerSaving || pageLeaseStatus === "replaced"} onChange={event => void toggleAutoAnswer(event.target.checked)} /><span aria-hidden="true" /></label></div>{captureButton}<details className="mobile-live-more"><summary aria-label="更多面试操作">•••</summary><div><Link to={routes.billing}>积分与会员</Link><Link to={routes.settings}>用户设置</Link><section className="mobile-live-contact-list" aria-label="官方社交账号">{officialSocialContacts.map(contact => <p key={contact.id}><small>{contact.label}</small><strong>{contact.account}</strong></p>)}</section><button className="danger" disabled={pageLeaseStatus === "replaced"} onClick={() => void finishInterview()}>结束面试</button></div></details></div>}
    </header>
    {idleStatus?.state === "warning" ? <div className="global-live-alert" role="status"><strong>本场面试即将因空闲自动结束</strong><span>连续 20 分钟没有音频、回答或截图活动会释放当前设备连接，历史记录仍会保留。</span><button className="button primary" disabled={continuingInterview} onClick={() => void continueIdleInterview()}>{continuingInterview ? "正在继续…" : "继续本场面试"}</button></div> : null}
    {pageLeaseStatus === "replaced" ? <div className="global-live-alert replaced-page-alert" role="status"><strong>本场面试已在其他页面继续</strong><span>当前页面已停止收音同步、实时订阅和回答请求；已显示内容仍可查看。关闭此页或返回面试首页即可。</span><Link className="button primary" to={routes.app}>返回面试首页</Link></div> : null}
    {state.captureState === "permission-required" || state.captureState === "error" ? <div className="global-live-alert" role="status"><strong>{state.captureState === "permission-required" ? "助手采集能力不可用" : "桌面设备连接异常"}</strong><span>{state.captureState === "permission-required" ? "请在桌面助手中检查首次授权状态；网页不会申请麦克风或屏幕权限，手动输入仍可使用。" : "可以运行诊断，当前仍可使用手动问题和截图。"}</span><button onClick={() => state.captureState === "permission-required" ? setCapture("ready", "ready") : setRealtimeDiagnosisNonce(current => current + 1)}>{state.captureState === "permission-required" ? "关闭提示" : "重新诊断"}</button></div> : null}
    {notice ? <div className="global-live-alert" role="status"><strong>{notice}</strong><span>{missingQuestionNotice ? "请等待面试官问题识别完成，或在左侧手动输入问题后再使用快答。" : billingNotice ? "当前任务未启动，请检查积分或会员权益。" : "当前回答没有成功启动，请根据上方原因重试。"}</span>{billingNotice ? <Link className="button primary" to={routes.billing}>前往积分与会员</Link> : null}</div> : null}
    {desktopLayout ? <div ref={workspaceRef} className={`live-grid focused-live-grid${pageLeaseStatus === "replaced" ? " live-grid-readonly" : ""}`} style={{ gridTemplateColumns: `minmax(240px, ${view.splitRatio}fr) 12px minmax(300px, ${100 - view.splitRatio}fr)` }}><section className="conversation-column">{conversationPanel}<ManualQuestionComposer manualDraft={actionState.manualDraft} disabled={pageLeaseStatus === "replaced"} onChange={changeManualDraft} /></section><WorkspaceDivider containerRef={workspaceRef} ratio={view.splitRatio} bounds={splitBounds} onChange={splitRatio => setView(current => ({ ...current, splitRatio }))} /><section className="answer-column">{answerPanel}<AnswerActionBar manualDraft={actionState.manualDraft} latestInterviewerQuestion={latestInterviewerText} screenshotTask={actionState.screenshotTask} quickAnswerStatus={actionState.quickAnswerStatus ?? "idle"} quickAnswerMessage={actionState.quickAnswerMessage ?? ""} screenshotAnswerStatus={actionState.screenshotAnswerStatus ?? "idle"} disabled={pageLeaseStatus === "replaced"} onQuickAnswer={submitManual} onScreenshot={beginInstantScreenshot} /></section></div> : <div className={`mobile-live-workspace${pageLeaseStatus === "replaced" ? " live-grid-readonly" : ""}`}><nav className="mobile-live-tabs" role="tablist" aria-label="面试内容"><button role="tab" aria-selected={mobilePanel === "answer"} className={mobilePanel === "answer" ? "active" : ""} onClick={() => setMobilePanel("answer")}>回答{state.activeAnswerTask && ["pending", "generating"].includes(state.activeAnswerTask.status) ? <span>生成中</span> : null}</button><button role="tab" aria-selected={mobilePanel === "conversation"} className={mobilePanel === "conversation" ? "active" : ""} onClick={() => setMobilePanel("conversation")}>对话<span>{state.speaker.transcripts.length}</span></button></nav><section className={`mobile-live-panel ${mobilePanel}`} role="tabpanel">{mobilePanel === "answer" ? answerPanel : conversationPanel}</section><MobileInterviewControls manualDraft={actionState.manualDraft} latestInterviewerQuestion={latestInterviewerText} screenshotTask={actionState.screenshotTask} quickAnswerStatus={actionState.quickAnswerStatus ?? "idle"} quickAnswerMessage={actionState.quickAnswerMessage ?? ""} screenshotAnswerStatus={actionState.screenshotAnswerStatus ?? "idle"} disabled={pageLeaseStatus === "replaced"} onChange={changeManualDraft} onQuickAnswer={() => { setMobilePanel("answer"); submitManual(); }} onScreenshot={() => { setMobilePanel("answer"); beginInstantScreenshot(); }} /></div>}
    {screenshot && pageLeaseStatus !== "replaced" ? <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="screenshot-dialog-title"><section className="sheet"><h2 id="screenshot-dialog-title">{screenshotStageTitle(screenshot)}</h2>{screenshotStageDetail(screenshot) ? <p>{screenshotStageDetail(screenshot)}</p> : null}{screenshot.stage === "failed" ? <div className="sheet-actions split-actions"><button className="button ghost full" onClick={dismissScreenshotFailure}>删除本次失败</button><button className="button primary full" onClick={beginInstantScreenshot}>重新截屏</button></div> : <button className="button primary full" onClick={() => void cancelScreenshot()}>取消</button>}</section></div> : null}
    {desktopLayout ? <footer className="session-bar"><div><i className={captureActive ? "recording-dot" : "online-dot"} /><strong>{captureActive ? "面试进行中" : state.captureState === "paused" ? "面试已暂停" : "等待开始面试"}</strong></div><div><small>{captureActive ? "正在持续接收面试官与我的实时对话" : "开始面试后会在头部右侧管理本场状态"}</small></div></footer> : null}
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
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewLoadError, setReviewLoadError] = useState("");
  const [wordExportState, setWordExportState] = useState<"idle" | "generating" | "success" | "error">("idle");
  const interview = state.interviews.find(item => item.id === id);
  const isWritten = interview?.sessionMode === "written";
  useEffect(() => {
    const controller = new AbortController();
    setReviewLoading(true);
    setReviewLoadError("");
    void Promise.all([
      runAdapterOperation(signal => interviewAppAdapter.loadInterviewReview(id, signal), controller.signal),
      runAdapterOperation(signal => interviewAppAdapter.loadInterviewWorkspace(id, signal), controller.signal)
        .catch(error => {
          if (error instanceof DOMException && error.name === "AbortError") throw error;
          return null;
        }),
    ])
      .then(([review, workspace]) => {
        setState(current => ({
          ...current,
          review: { ...current.review, ...review, screenshots: current.review.screenshots },
          questions: workspace ? [...workspace.questions] : current.questions,
          activeAnswerTask: workspace ? workspace.activeAnswerTask : current.activeAnswerTask,
        }));
        setReviewStatus(review.status);
      })
      .catch(error => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setReviewLoadError(error instanceof Error ? error.message : "复盘对话加载失败，请稍后重试。");
      })
      .finally(() => setReviewLoading(false));
    return () => controller.abort();
  }, [id, setState]);
  const downloadReview = async () => {
    if (wordExportState === "generating") return;
    const title = state.review.title || interview?.title || "面试复盘";
    setWordExportState("generating");
    try {
      const { createInterviewReviewWordBlob, downloadInterviewReviewWord, interviewReviewWordFilename } = await import("./interview-review-word-export");
      const blob = await createInterviewReviewWordBlob(state.review, state.questions, interview);
      downloadInterviewReviewWord(interviewReviewWordFilename(title, state.review.endedAtMs), blob);
      setWordExportState("success");
    } catch {
      setWordExportState("error");
    }
  };
  const deleteShot = async (shotId: string) => { setDeleteError(""); setDeletingShotId(shotId); try { await runAdapterOperation(signal => interviewAppAdapter.deleteScreenshot(shotId, signal)); setState(current => ({ ...current, review: { ...current.review, screenshots: current.review.screenshots.filter(item => item.id !== shotId) } })); } catch { setDeleteError("截图删除失败，记录仍然保留，请重试。"); } finally { setDeletingShotId(null); } };
  const deleteInterview = async () => { if (!window.confirm(isWritten ? "Delete this written exam and all screenshot-answer history?" : "Delete this interview, its questions, answers, and session attachments? Reusable materials will remain.")) return; setDeleteError(""); setDeletingInterview(true); try { await runAdapterOperation(signal => interviewAppAdapter.deleteInterview(id, signal)); setState(current => ({ ...current, interviews: current.interviews.filter(item => item.id !== id), questions: [] })); navigate(sessionHomeRoute(interview?.sessionMode)); } catch { setDeleteError(isWritten ? "The written exam could not be deleted. Existing records were not changed." : "The interview could not be deleted. Existing records were not changed."); } finally { setDeletingInterview(false); } };
  if (isWritten) {
    const writtenQuestions = state.questions.filter(question => question.input === "screenshot");
    return <main className="app-page narrow written-result-page">
      <Link className="back-link" to={routes.writtenExams}>← 返回笔试模式</Link>
      <PageHeader eyebrow="WRITTEN EXAM RESULT" title={interview.title} detail="本场答题记录已保留，可随时从最近笔试重新查看。" action={<Link className="button primary" to={routes.writtenExams}>完成</Link>} />
      {reviewLoadError ? <div className="inline-error" role="status">{reviewLoadError}</div> : null}
      <section className="panel written-result-card">
        <div className="panel-heading"><h2>本场答题记录</h2><span>{writtenQuestions.length} 题</span></div>
        {reviewLoading ? <p className="review-loading">正在加载答题记录…</p> : writtenQuestions.length ? <div className="written-result-list">{[...writtenQuestions].reverse().map((question, index) => <article key={question.id}><header><span>第 {index + 1} 题</span><small>{question.askedAt}</small></header><h3>{question.text}</h3><div><strong>回答</strong><p>{question.advice.detail}</p></div></article>)}</div> : <EmptyState title="本场暂无答题记录" detail="本场笔试已经结束，没有保存成功的截屏回答。" />}
      </section>
      <div className="written-result-actions">
        {deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}
        <button className="button danger" disabled={deletingInterview} onClick={() => void deleteInterview()}>{deletingInterview ? "正在删除…" : "删除本场笔试"}</button>
      </div>
    </main>;
  }
  return <main className="app-page"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="INTERVIEW REVIEW" title="本场面试复盘" detail="整理语音转写与 AI 回答建议，不对你的能力作自动评分。" action={<div className="review-header-actions"><button type="button" className="button primary" onClick={() => void downloadReview()} disabled={reviewLoading || wordExportState === "generating"}>{wordExportState === "generating" ? "正在生成 Word…" : "下载 Word"}</button><div className="review-meta"><strong>{state.review.duration}</strong><span>{state.review.transcripts.length} 条对话 · {state.questions.length} 个问题</span></div></div>} />
    <p className={`review-download-note${wordExportState === "error" ? " error-text" : ""}`} role={wordExportState === "error" ? "alert" : undefined}>{wordExportState === "error" ? "Word 生成失败，请重试。当前复盘内容不会丢失。" : wordExportState === "success" ? "Word 已生成并开始下载，请妥善保管本场面试对话。" : "Word 文件包含本场面试对话，仅在你的浏览器本地生成，请妥善保管。"}</p>{reviewLoadError ? <div className="inline-error" role="status">{reviewLoadError}</div> : null}
    <div className="review-grid"><div className="review-main"><section className="panel"><div className="panel-heading"><h2>真实对话记录</h2><span>语音转写</span></div>{reviewLoading ? <p className="review-loading">正在加载本场对话…</p> : state.review.transcripts.length ? <div className="review-transcript-list">{state.review.transcripts.map(item => <article key={item.id} className={`review-transcript ${item.role}`}><header><strong>{item.speakerLabel}</strong><time dateTime={new Date(item.occurredAtMs).toISOString()}>{new Date(item.occurredAtMs).toLocaleTimeString(globalEditionMetadata().locale, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}</time></header><p>{item.text}</p></article>)}</div> : <EmptyState title="没有可用的对话转写" detail="旧场次或未成功收音的场次可能没有持久语音转写，已有问题与 AI 建议仍可查看。" />}</section><section className="panel"><div className="panel-heading"><h2>问题与 AI 回答建议</h2><span>生成建议，不代表实际作答</span></div>{state.questions.length ? <div className="review-timeline">{[...state.questions].reverse().map((question, index) => <article key={question.id}><i>{index + 1}</i><div><small>{question.askedAt} · {question.input === "screenshot" ? "截图题" : question.input === "manual" ? "手动输入" : "音频转写"}</small><h3>{question.text}</h3><p>{question.advice.outline.join("; ")}</p><div className="source-pills"><small>资料 v{question.advice.provenance.selectionRevision}</small>{question.advice.provenance.usedSources.map(source => <span key={source.sourceId}>{source.displayName}</span>)}</div></div></article>)}</div> : <EmptyState title="没有可复盘的问题" detail="本场面试没有已确认的问题记录。" />}</section></div>
      <aside><section className="panel review-summary"><div className="panel-heading"><h2>AI 整理摘要</h2><span className={reviewStatus}>{reviewStatus === "complete" ? "已生成" : reviewStatus === "failed" ? "生成失败" : "处理中"}</span></div>{reviewStatus === "complete" ? <><p>{state.review.summary}</p><div className="evidence-box"><span>说明</span><p>这是基于本场记录的生成建议，与原始问题记录分开保存。</p></div></> : reviewStatus === "failed" ? <div className="inline-error">摘要生成失败，原始记录仍可查看。<button onClick={() => setReviewStatus("complete")}>重试</button></div> : <p>正在整理本场已确认问题…</p>}</section><section className="panel data-panel"><div className="panel-heading"><h2>数据与附件</h2><span>可删除</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}<ul className="compact-list"><li><span>简历与知识库</span><b>作为可复用资料保留</b></li><li><span>对话转写</span><b>随会话保存并删除</b></li><li><span>问题与 AI 建议</span><b>随会话保存</b></li>{state.review.screenshots.map(shot => <li key={shot.id}><span>{shot.name}</span><button disabled={deletingShotId === shot.id} onClick={() => void deleteShot(shot.id)}>{deletingShotId === shot.id ? "删除中…" : "删除截图"}</button></li>)}</ul><button className="button danger full" disabled={deletingInterview} onClick={() => void deleteInterview()}>{deletingInterview ? "正在删除…" : "删除整场面试"}</button></section></aside></div>
  </main>;
}

function LibraryPage() { const { state, setState } = usePrototype(); return <LibraryManager state={state} setState={setState} />; }

function BillingRoutePage() { const { state } = usePrototype(); return <BillingPage state={state} />; }
function GuideRoutePage() { const { state } = usePrototype(); return <GuidePage support={state.billing.support} />; }

function DevicesPage() {
  const { state } = usePrototype();
  return <main className="app-page"><PageHeader eyebrow="DESKTOP COMPANION" title="电脑伴随程序" detail="下载与你电脑匹配的伴随助手，并查看安装与系统授权说明。" /><DownloadCenter manifest={state.releaseManifest} /></main>;
}

function PasswordSettingsCard() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirmPassword) { setMessage("Passwords do not match."); return; }
    setBusy(true); setMessage("");
    try {
      await authClient.changeGlobalPassword({ currentPassword, newPassword });
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      setMessage("Password updated. Other signed-in devices have been signed out.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "We could not update your password.");
    } finally { setBusy(false); }
  };
  return <section className="panel"><h2>Password</h2><p>Change your password without waiting for an email. Other active sessions will be signed out.</p><form className="sms-login-form settings-password-form" onSubmit={submit}><label><span>Current password</span><input type="password" autoComplete="current-password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} /></label><label><span>New password</span><input type="password" autoComplete="new-password" value={newPassword} onChange={event => setNewPassword(event.target.value)} /></label><label><span>Confirm new password</span><input type="password" autoComplete="new-password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} /></label><small>Use at least 15 characters.</small><button className="button primary" disabled={busy} type="submit">{busy ? "Updating..." : "Update password"}</button></form>{message ? <p className="login-message" role="status">{message}</p> : null}</section>;
}

function SettingsPage() {
  const { state, setState } = usePrototype();
  const [appearance, setAppearance] = useState<AppearancePreferences>(() => readAppearancePreferences());
  const [language, setLanguage] = useState<import("@offersteady/protocol").InterviewLanguage>(state.account.defaultInterviewLanguage ?? "en-US");
  const [languageSaving, setLanguageSaving] = useState(false);
  const [languageError, setLanguageError] = useState("");
  const updateAppearance = (patch: Partial<AppearancePreferences>) => {
    const next = { ...appearance, ...patch };
    setAppearance(next);
    applyAppearancePreferences(next);
    persistAppearancePreferences(next);
  };
  const saveLanguage = async (next: import("@offersteady/protocol").InterviewLanguage) => {
    const previous = language;
    setLanguage(next); setLanguageSaving(true); setLanguageError("");
    try {
      const account = await runAdapterOperation(signal => interviewAppAdapter.updateDefaultInterviewLanguage(next, signal));
      setState(current => ({ ...current, account }));
    } catch (error) {
      setLanguage(previous); setLanguageError(error instanceof Error ? error.message : "Could not save your interview language.");
    } finally { setLanguageSaving(false); }
  };
  return <main className="app-page"><PageHeader eyebrow="SETTINGS" title="设置" detail="查看真实的数据行为和辅助功能。" /><div className="settings-list"><PasswordSettingsCard /><section className="panel"><h2>Interview language</h2><p className="panel-empty-copy">Choose the default language for new Global interview sessions. You can still change a draft before it starts.</p><label className="setting-row"><span><strong>Default interview language</strong><small>Used for transcription, question detection, and AI answers</small></span><select aria-label="Default interview language" value={language} disabled={languageSaving} onChange={event => void saveLanguage(event.target.value as import("@offersteady/protocol").InterviewLanguage)}>{INTERVIEW_LANGUAGE_REGISTRY.map(item => <option key={item.locale} value={item.locale}>{item.nativeLabel} · {item.label}{item.tier === "beta" ? " (Beta)" : ""}</option>)}</select></label>{languageError ? <div className="inline-error" role="alert">{languageError}</div> : null}</section><section className="panel"><h2>数据与隐私</h2><div className="setting-row"><span><strong>原始音频</strong><small>完成当前转写后不保留</small></span><b>默认不保存</b></div><div className="setting-row"><span><strong>面试记录</strong><small>请在对应复盘页查看、管理和删除记录。</small></span><Link to={`${routes.guide}#privacy-support`}>查看数据说明</Link></div></section><section className="panel"><h2>辅助功能</h2><label className="setting-row"><span><strong>减少动态效果</strong><small>减少波形与状态动画</small></span><input type="checkbox" /></label><label className="setting-row"><span><strong>回答字号</strong><small>只影响实时回答区域</small></span><select aria-label="回答字号" value={appearance.answerFontSize} onChange={event => updateAppearance({ answerFontSize: event.target.value as AppearancePreferences["answerFontSize"] })}><option value="normal">标准</option><option value="large">较大</option></select></label><label className="setting-row"><span><strong>页面主题</strong><small>明亮模式提高页面整体亮度，适合光线充足的环境</small></span><select aria-label="页面主题" value={appearance.theme} onChange={event => updateAppearance({ theme: event.target.value as AppearancePreferences["theme"] })}><option value="dark">深色</option><option value="bright">明亮</option></select></label></section></div></main>;
}

function RouteErrorPage() { return <main className="center-page"><EmptyState title="页面暂时无法加载" detail="没有输出任何敏感内容。请返回应用首页重试。" action={<Link className="button primary" to={routes.app}>返回首页</Link>} /></main>; }
function IntegrationModeErrorPage({ message, onRetry }: { readonly message: string; readonly onRetry: () => void }) { return <main className="center-page"><EmptyState title="后端页面状态暂时无法加载" detail={`${message}. This page retries automatically, and your session resumes when the service recovers.`} action={<button className="button primary" type="button" onClick={onRetry}>立即重试</button>} /></main>; }
function NotFoundPage() { return <main className="center-page"><EmptyState title="没有找到这个页面" detail="检查地址，或回到面试首页继续。" action={<Link className="button primary" to={routes.app}>返回首页</Link>} /></main>; }
function RouteLoadingPage() { return <main className="route-loading-page" role="status" aria-label="页面加载中" />; }

export function AppRoutes() {
  return <Routes><Route element={<PublicLayout />}><Route path={routes.landing} element={<LandingPage />} /><Route path={routes.login} element={<LoginPage />} /><Route path={routes.invite()} element={<ReferralLandingPage />} />{publicReviewCatalogue.pages.map(page => <Route key={page.slug} path={`/${page.slug}`} element={<PublicReviewPage slug={page.slug} />} />)}</Route><Route path="/billing/success" element={<Navigate to="/app/billing" replace />} /><Route element={<ProtectedRoute />}><Route path="/app" element={<AppLayout />}><Route index element={<HomePage />} /><Route path="written-exams" element={<WrittenExamHomePage />} /><Route path="interviews/new" element={<NewInterviewPage />} /><Route path="written-exams/new" element={<NewWrittenExamPage />} /><Route path="interviews/:id/prepare" element={<PreparationPage />} /><Route path="interviews/:id/review" element={<ReviewPage />} /><Route path="library" element={<LibraryPage />} /><Route path="billing" element={<BillingRoutePage />} /><Route path="guide" element={<GuideRoutePage />} /><Route path="devices" element={<DevicesPage />} /><Route path="settings" element={<SettingsPage />} /></Route><Route path="/app/interviews/:id/live" element={<LivePage />} /></Route><Route path="/error" element={<RouteErrorPage />} /><Route path="*" element={<NotFoundPage />} /></Routes>;
}

function DocumentTitleManager() {
  const { pathname } = useLocation();
  useEffect(() => {
    const reviewPage = publicReviewPage(pathname.replace(/^\//, ""));
    const landingMetadata = pathname === routes.landing ? {
      title: "OfferSteady | AI Interview Assistant",
      description: homeCopy.metaDescription,
      canonical: "https://offersteady.com/",
    } : null;
    if (pathname === routes.landing) {
      document.title = "OfferSteady | AI Interview Assistant";
    } else if (reviewPage) {
      document.title = reviewPage.title;
    } else {
      document.title = "OfferSteady AI Interview Assistant";
    }
    const metadata = reviewPage ? { title: reviewPage.title, description: reviewPage.description, canonical: `https://offersteady.com/${reviewPage.slug}` } : landingMetadata;
    if (metadata) {
      let description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      if (!description) { description = document.createElement("meta"); description.name = "description"; document.head.append(description); }
      description.content = metadata.description;
      let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
      if (!canonical) { canonical = document.createElement("link"); canonical.rel = "canonical"; document.head.append(canonical); }
      canonical.href = metadata.canonical;
    }
  }, [pathname]);
  return null;
}

export interface AppProps { readonly initialAuthenticated?: boolean; readonly initialState?: WebAppState }

export function App({ initialAuthenticated, initialState }: AppProps) {
  return <BrowserRouter><DocumentTitleManager /><PrototypeProvider initialAuthenticated={initialAuthenticated} initialState={initialState}><Suspense fallback={<RouteLoadingPage />}><AppRoutes /></Suspense></PrototypeProvider></BrowserRouter>;
}
