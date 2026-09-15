import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { AnswerTaskSnapshot, CaptureState } from "@offersteady/protocol";
import type { IdleInterviewStatus, InterviewQuestion, LiveActionState, QuestionStatus, RealtimeSessionUpdate, ScreenshotTask, SessionMode, SessionStatus, WebAppState } from "./domain";
import { runAdapterOperation } from "./api-client";
import { interviewAppAdapter } from "./app-adapter";
import { routes } from "./routes";
import { eligibleSource, managedLibrarySources, selectionSources } from "./context-selection";
import { ConversationMonitor } from "./ConversationMonitor";
import { AnswerWorkspace } from "./route-components";
import { latestInterviewerTurnText } from "./conversation-turns";
import { ManualQuestionComposer } from "./ManualQuestionComposer";
import { AnswerActionBar } from "./AnswerActionBar";
import { MobileInterviewControls } from "./MobileInterviewControls";
import { ABSOLUTE_MAX_SPLIT_RATIO, ABSOLUTE_MIN_SPLIT_RATIO, clampSplitRatio, initialLiveWorkspaceView, isolateRealtimeSpeakerSession, noteNewAnswer, parseStoredSplitRatio, reconcileAnswerWorkspace, reconcileRealtimeSpeaker, serializeSplitRatio, splitRatioBounds, splitRatioStorageKey } from "./live-workspace";
import { WorkspaceDivider } from "./WorkspaceDivider";
import { isInvalidRealtimeSessionStatus, realtimeReconnectAttemptAfterRecovery, realtimeRetryDelayMs } from "./realtime-recovery";
import { createLiveSessionLeaderCoordinator } from "./live-session-leader";
import { isFreshShortcutScreenshotAcceptance, SHORTCUT_SCREENSHOT_RECOVERY_POLL_INTERVAL_MS } from "./screenshot-shortcut-feedback";
import type { LiveAnswerStreamEvent } from "./live-answer-stream";
import { officialSocialContacts } from "./social-contacts";
import { usePrototype } from "./app-context";

const sessionHomeRoute = (mode?: SessionMode) => mode === "written" ? routes.writtenExams : routes.app;

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

export function LivePage({ brand, accountMenu }: { readonly brand: ReactNode; readonly accountMenu: ReactNode }) {
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
  const interviewLanguageLabel = (liveInterview?.interviewLanguage ?? "zh-CN") === "en-US" ? "English Interview" : "中文面试";
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
    let pendingStreamUpdate: Parameters<NonNullable<Parameters<typeof interviewAppAdapter.submitManualAnswer>[2]>>[0] | null = null;
    let firstAnswerTiming: LiveAnswerStreamEvent["timing"];
    let streamRenderTimer: number | null = null;
    const applyStreamUpdate = (update: NonNullable<typeof pendingStreamUpdate>) => {
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
        if (typeof requestAnimationFrame === "function") requestAnimationFrame(acknowledge);
        else window.setTimeout(acknowledge, 0);
      }
    };
    const flushStreamUpdate = () => {
      if (streamRenderTimer !== null) window.clearTimeout(streamRenderTimer);
      streamRenderTimer = null;
      if (!pendingStreamUpdate) return;
      const update = pendingStreamUpdate;
      pendingStreamUpdate = null;
      applyStreamUpdate(update);
    };
    try {
      manualAnswerController.current?.abort();
      const controller = new AbortController();
      manualAnswerController.current = controller;
      const result = await runAdapterOperation(signal => interviewAppAdapter.submitManualAnswer({ interviewId: id, question: trimmed, idempotencyKey: command, ...frozenQuestion, clickedAtMs }, signal, update => {
        firstAnswerTiming ??= update.event.timing;
        pendingStreamUpdate = firstAnswerTiming && !update.event.timing
          ? { ...update, event: { ...update.event, timing: firstAnswerTiming } }
          : update;
        if (["completed", "failed", "cancelled"].includes(update.event.type)) flushStreamUpdate();
        else if (streamRenderTimer === null) streamRenderTimer = window.setTimeout(flushStreamUpdate, 16);
      }), controller.signal);
      flushStreamUpdate();
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
      if (streamRenderTimer !== null) window.clearTimeout(streamRenderTimer);
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
    if (!window.confirm(isWritten ? "确认结束本场笔试？结束后仍可查看本场答题记录。" : "确认结束本场面试？结束后将停止采集并进入复盘。")) return;
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
  const screenshotInstruction = "请只依据当前截图识别其中的题目、代码或系统设计内容，并给出可直接使用的中文回答。不要使用实时对话、面试官最近的问题或其他会话信息。";
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
  const answerPanel = <AnswerWorkspace answers={state.questions} viewingAnswerId={view.viewingAnswerId} newAnswerAvailable={view.newAnswerAvailable} activeTask={state.activeAnswerTask} cancelling={cancellingAnswer} cancelError={cancelAnswerError} interviewLanguage={liveInterview?.interviewLanguage ?? "zh-CN"} onStop={() => void stopAnswer()} onView={answerId => setView(current => ({ ...current, viewingAnswerId: answerId, newAnswerAvailable: answerId ? current.newAnswerAvailable : false }))} onRetry={updateQuestionStatus} />;

  if (isWritten) return <main className={`live-page focused-live-page${desktopLayout ? " desktop-live-page" : " mobile-live-page"}`}><header className="live-top"><Link to={routes.writtenExams} aria-label="返回笔试模式">{brand}</Link><div className="live-session-heading"><strong>{interviewTitle}</strong><span><i className="online-dot" /> 桌面助手已连接 · 截屏回答可用</span><small className="live-language-badge">笔试模式</small></div><div className="live-top-actions"><Link className="live-balance" to={routes.billing}>积分与会员</Link>{accountMenu}<button className="button danger live-session-control" disabled={pageLeaseStatus === "replaced"} onClick={() => void finishInterview()}>结束笔试</button></div></header>{notice ? <div className="global-live-alert" role="alert"><strong>{notice}</strong><button type="button" onClick={() => setNotice("")}>关闭</button></div> : null}{pageLeaseStatus === "replaced" ? <div className="global-live-alert replaced-page-alert" role="status"><strong>本场笔试已在其他页面继续</strong><Link className="button primary" to={routes.writtenExams}>返回笔试模式</Link></div> : null}<div className="written-exam-workspace"><section className="answer-column">{answerPanel}<AnswerActionBar manualDraft="" screenshotTask={actionState.screenshotTask} screenshotOnly screenshotAnswerStatus={actionState.screenshotAnswerStatus ?? "idle"} disabled={pageLeaseStatus === "replaced"} onQuickAnswer={() => undefined} onScreenshot={beginInstantScreenshot} /></section></div>{screenshot && pageLeaseStatus !== "replaced" ? <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="screenshot-dialog-title"><section className="sheet"><h2 id="screenshot-dialog-title">{screenshotStageTitle(screenshot)}</h2>{screenshotStageDetail(screenshot) ? <p>{screenshotStageDetail(screenshot)}</p> : null}{screenshot.stage === "failed" ? <div className="sheet-actions split-actions"><button className="button ghost full" onClick={dismissScreenshotFailure}>删除本次失败</button><button className="button primary full" onClick={beginInstantScreenshot}>重新截屏</button></div> : <button className="button primary full" onClick={() => void cancelScreenshot()}>取消</button>}</section></div> : null}<footer className="session-bar"><div><i className="online-dot" /><strong>笔试进行中</strong></div><div><small>仅在你主动发起时截屏并生成回答</small></div></footer></main>;

  return <main className={`live-page focused-live-page${desktopLayout ? " desktop-live-page" : " mobile-live-page"}`}>
    <header className="live-top">
      <Link to={routes.app} aria-label="返回面试首页">{brand}</Link>
      <div className="live-session-heading"><strong>{interviewTitle}</strong><span><i className={captureActive ? "recording-dot" : "online-dot"} /> {desktopLayout ? `这台设备 · ${captureStatus}` : captureStatus}</span><small className="live-language-badge">{interviewLanguageLabel}</small></div>
      {desktopLayout ? <div className="live-top-actions"><div className="live-auto-answer"><span>自动回答</span><label className="switch-control"><input type="checkbox" role="switch" aria-label="自动回答" checked={liveInterview?.autoAnswerEnabled ?? false} disabled={autoAnswerSaving || pageLeaseStatus === "replaced"} onChange={event => void toggleAutoAnswer(event.target.checked)} /><span aria-hidden="true" /></label></div><Link className="live-balance" to={routes.billing}>积分与会员</Link><details className="live-contact-menu"><summary>联系我们</summary><div className="live-contact-popover" aria-label="官方社交账号">{officialSocialContacts.map(contact => <p key={contact.id}><small>{contact.label}</small><strong>{contact.account}</strong></p>)}</div></details><span>18:24</span>{accountMenu}{captureButton}<button className="button danger live-session-control" disabled={pageLeaseStatus === "replaced"} onClick={() => void finishInterview()}>结束面试</button></div> : <div className="mobile-live-top-actions"><div className="live-auto-answer mobile"><span>自动</span><label className="switch-control"><input type="checkbox" role="switch" aria-label="自动回答" checked={liveInterview?.autoAnswerEnabled ?? false} disabled={autoAnswerSaving || pageLeaseStatus === "replaced"} onChange={event => void toggleAutoAnswer(event.target.checked)} /><span aria-hidden="true" /></label></div>{captureButton}<details className="mobile-live-more"><summary aria-label="更多面试操作">•••</summary><div><Link to={routes.billing}>积分与会员</Link><Link to={routes.settings}>用户设置</Link><section className="mobile-live-contact-list" aria-label="官方社交账号">{officialSocialContacts.map(contact => <p key={contact.id}><small>{contact.label}</small><strong>{contact.account}</strong></p>)}</section><button className="danger" disabled={pageLeaseStatus === "replaced"} onClick={() => void finishInterview()}>结束面试</button></div></details></div>}
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
