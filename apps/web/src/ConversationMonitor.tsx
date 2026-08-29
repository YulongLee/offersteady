import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { SpeakerTranscriptSegment } from "@offersteady/protocol";
import type { WebAppState } from "./domain";
import { projectConversationTurns } from "./conversation-turns";
import { SubtitleDiagnosticsOverlay } from "./SubtitleDiagnosticsOverlay";
import { recordSubtitleRevisionStage, subtitleRevisionDiagnosticsEnabled } from "./realtime-subtitle-diagnostics";

interface Props {
  readonly state: WebAppState;
  readonly onConfirmQuestion: () => void;
  readonly onDismissQuestion: () => void;
}

export const formatTranscriptTimestamp = (milliseconds: number) => {
  if (milliseconds >= 1_000_000_000_000) {
    const timestamp = new Date(milliseconds);
    return `[${String(timestamp.getHours()).padStart(2, "0")}:${String(timestamp.getMinutes()).padStart(2, "0")}:${String(timestamp.getSeconds()).padStart(2, "0")}]`;
  }
  return `[${String(Math.floor(milliseconds / 60_000)).padStart(2, "0")}:${String(Math.floor(milliseconds / 1_000) % 60).padStart(2, "0")}]`;
};

export const TRANSCRIPT_RESERVOIR_MIN_LAG_MS = 800;
export const TRANSCRIPT_RESERVOIR_MAX_LAG_MS = 1_000;
export const TRANSCRIPT_FINAL_TAIL_MIN_MS = 150;
export const TRANSCRIPT_FINAL_TAIL_MAX_MS = 250;
const TRANSCRIPT_RESERVOIR_DEFAULT_REVISION_INTERVAL_MS = 520;
const TRANSCRIPT_RESERVOIR_MIN_REVISION_INTERVAL_MS = 120;
const TRANSCRIPT_RESERVOIR_MAX_REVISION_INTERVAL_MS = 1_200;
const TRANSCRIPT_RESERVOIR_MIN_STEP_MS = 28;
const TRANSCRIPT_RESERVOIR_MAX_STEP_MS = 400;
type TranscriptFrameJob = (timestamp: number) => boolean;
const transcriptFrameJobs = new Set<TranscriptFrameJob>();
let transcriptFrameHandle: number | null = null;

const requestTranscriptFrame = () => {
  if (transcriptFrameHandle !== null || transcriptFrameJobs.size === 0) return;
  let requestIsSynchronous = true;
  transcriptFrameHandle = -1;
  const handle = window.requestAnimationFrame(timestamp => {
    transcriptFrameHandle = null;
    runTranscriptFrameJobs(timestamp, requestIsSynchronous);
  });
  requestIsSynchronous = false;
  if (transcriptFrameHandle === -1) transcriptFrameHandle = handle;
};

const runTranscriptFrameJobs = (timestamp: number, synchronousFallback = false) => {
  for (const job of [...transcriptFrameJobs]) {
    if (!job(timestamp)) transcriptFrameJobs.delete(job);
  }
  if (synchronousFallback && transcriptFrameJobs.size > 0) {
    for (const job of [...transcriptFrameJobs]) {
      if (!job(Number.MAX_SAFE_INTEGER)) transcriptFrameJobs.delete(job);
    }
  }
  requestTranscriptFrame();
};

const scheduleTranscriptFrameJob = (job: TranscriptFrameJob) => {
  transcriptFrameJobs.add(job);
  requestTranscriptFrame();
};

const cancelTranscriptFrameJob = (job: TranscriptFrameJob) => {
  transcriptFrameJobs.delete(job);
  if (transcriptFrameJobs.size === 0 && transcriptFrameHandle !== null) {
    window.cancelAnimationFrame(transcriptFrameHandle);
    transcriptFrameHandle = null;
  }
};

const transcriptSmoothingEnabled = () => {
  if (import.meta.env.VITE_REALTIME_SUBTITLE_SMOOTHING === "false") return false;
  if (typeof window === "undefined" || typeof document === "undefined") return false;
  if ((window as Window & { __offersteadyDisableSubtitleSmoothing?: boolean }).__offersteadyDisableSubtitleSmoothing) return false;
  if (document.visibilityState !== "visible") return false;
  if (typeof window.requestAnimationFrame !== "function") return false;
  return typeof window.matchMedia !== "function" || !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
};

const graphemes = (value: string) => Array.from(value);

export const adaptiveTranscriptReservoirLag = (observedRevisionIntervalMs: number) => Math.min(
  TRANSCRIPT_RESERVOIR_MAX_LAG_MS,
  Math.max(
    TRANSCRIPT_RESERVOIR_MIN_LAG_MS,
    Math.round(observedRevisionIntervalMs * 1.25),
  ),
);

export const finalTranscriptTailDuration = (addedGraphemes: number) => Math.min(
  TRANSCRIPT_FINAL_TAIL_MAX_MS,
  Math.max(
    TRANSCRIPT_FINAL_TAIL_MIN_MS,
    Math.round(TRANSCRIPT_FINAL_TAIL_MIN_MS + Math.max(0, addedGraphemes - 1) * 12.5),
  ),
);

export const firstAdaptiveTranscriptText = (current: string, target: string) => {
  if (current === target || !target.startsWith(current)) return target;
  const currentLength = graphemes(current).length;
  return graphemes(target).slice(0, currentLength + 1).join("");
};

export const nextAdaptiveTranscriptText = (
  current: string,
  target: string,
  elapsedMs: number,
  maxLagMs = TRANSCRIPT_RESERVOIR_MAX_LAG_MS,
  observedRevisionIntervalMs = TRANSCRIPT_RESERVOIR_DEFAULT_REVISION_INTERVAL_MS,
  elapsedSinceLastStepMs = Number.POSITIVE_INFINITY,
) => {
  if (current === target || !target.startsWith(current) || elapsedMs >= maxLagMs) return target;
  const currentUnits = graphemes(current);
  const targetUnits = graphemes(target);
  const remaining = targetUnits.length - currentUnits.length;
  if (remaining <= 0) return target;
  const expectedIntervalMs = Math.min(
    TRANSCRIPT_RESERVOIR_MAX_REVISION_INTERVAL_MS,
    Math.max(TRANSCRIPT_RESERVOIR_MIN_REVISION_INTERVAL_MS, observedRevisionIntervalMs),
  );
  const desiredDrainDeadlineMs = Math.min(maxLagMs, adaptiveTranscriptReservoirLag(expectedIntervalMs));
  const remainingDrainMs = Math.max(1, desiredDrainDeadlineMs - Math.max(0, elapsedMs));
  const cadenceMs = Math.min(
    TRANSCRIPT_RESERVOIR_MAX_STEP_MS,
    Math.max(TRANSCRIPT_RESERVOIR_MIN_STEP_MS, remainingDrainMs / remaining),
  );
  if (elapsedSinceLastStepMs < cadenceMs) return current;
  const remainingSteps = Math.max(1, Math.floor(remainingDrainMs / cadenceMs));
  const catchUpStep = Math.max(1, Math.ceil(remaining / remainingSteps));
  const elapsedStep = Number.isFinite(elapsedSinceLastStepMs)
    ? Math.max(1, Math.floor(elapsedSinceLastStepMs / cadenceMs))
    : 1;
  const step = Math.max(catchUpStep, elapsedStep);
  return targetUnits.slice(0, currentUnits.length + step).join("");
};

export const nextFinalTranscriptTailText = (
  start: string,
  target: string,
  elapsedMs: number,
  durationMs: number,
) => {
  if (start === target || !target.startsWith(start) || elapsedMs >= durationMs) return target;
  const startUnits = graphemes(start);
  const targetUnits = graphemes(target);
  const added = targetUnits.length - startUnits.length;
  if (added <= 0) return target;
  const revealed = Math.max(1, Math.ceil(added * Math.max(0, elapsedMs) / Math.max(1, durationMs)));
  return targetUnits.slice(0, startUnits.length + revealed).join("");
};

export const nextProgressiveTranscriptText = (current: string, target: string, isFinal = false) => {
  if (isFinal) return target;
  const compactLength = (value: string) => value
    .replace(/\s+/g, "")
    .replace(/[，。！？、；：,.!?;:~～…·\-—_]+/g, "")
    .length;
  if (compactLength(target) < compactLength(current)) return current;
  return target;
};

export type TranscriptPresentationState = "final" | "transcribing" | "confirming" | "stale";
export const transcriptPresentationState = (
  segment: { readonly isFinal: boolean; readonly turnState?: "speaking" | "tail" | "committing"; readonly terminalState?: "final" | "incomplete" },
): TranscriptPresentationState => {
  if (segment.isFinal) return segment.terminalState === "incomplete" ? "stale" : "final";
  if (segment.turnState === "committing") return "confirming";
  return "transcribing";
};
export const transcriptPresentationLabel = (presentation: TranscriptPresentationState) =>
  presentation === "final" ? "已确认"
    : presentation === "stale" ? "识别未完成"
      : presentation === "confirming" ? "已转写"
        : "转写中";

export function ProgressiveTranscriptText({ segment, active }: { readonly segment: SpeakerTranscriptSegment; readonly active: boolean }) {
  const text = segment.text;
  const [visibleText, setVisibleText] = useState(segment.isFinal || !active ? text : "");
  const visibleTextRef = useRef(visibleText);
  const targetTextRef = useRef(text);
  const targetStartedAtRef = useRef(0);
  const lastStepAtRef = useRef(0);
  const lastRevisionAtRef = useRef(0);
  const revisionIntervalRef = useRef(TRANSCRIPT_RESERVOIR_DEFAULT_REVISION_INTERVAL_MS);
  const animationModeRef = useRef<"partial" | "final-tail">("partial");
  const animationStartTextRef = useRef(visibleText);
  const animationDurationRef = useRef(TRANSCRIPT_RESERVOIR_MIN_LAG_MS);
  const frameJobRef = useRef<TranscriptFrameJob | null>(null);
  const lastPaintedEventId = useRef<string | null>(null);
  const performance = segment.performance;
  const renderStartedAtMs = useMemo(() => Date.now(), [performance?.eventId, visibleText]);

  const updateVisibleText = (value: string) => {
    visibleTextRef.current = value;
    setVisibleText(value);
  };

  if (frameJobRef.current === null) {
    frameJobRef.current = timestamp => {
      const target = targetTextRef.current;
      const current = visibleTextRef.current;
      if (current === target) return false;
      if (!transcriptSmoothingEnabled()) {
        updateVisibleText(target);
        return false;
      }
      const elapsedMs = timestamp - targetStartedAtRef.current;
      const next = animationModeRef.current === "final-tail"
        ? nextFinalTranscriptTailText(
          animationStartTextRef.current,
          target,
          elapsedMs,
          animationDurationRef.current,
        )
        : nextAdaptiveTranscriptText(
          current,
          target,
          elapsedMs,
          TRANSCRIPT_RESERVOIR_MAX_LAG_MS,
          revisionIntervalRef.current,
          timestamp - lastStepAtRef.current,
        );
      if (next === current) return true;
      lastStepAtRef.current = timestamp;
      updateVisibleText(next);
      return next !== target;
    };
  }

  useLayoutEffect(() => {
    const job = frameJobRef.current!;
    const target = nextProgressiveTranscriptText(targetTextRef.current, text, segment.isFinal);
    targetTextRef.current = target;
    const current = visibleTextRef.current;
    const smoothingEnabled = transcriptSmoothingEnabled();
    const smoothFinalTail = segment.isFinal && target.startsWith(current) && target !== current;
    if (!smoothingEnabled || (!active && !smoothFinalTail)) {
      cancelTranscriptFrameJob(job);
      updateVisibleText(target);
      return;
    }
    const now = window.performance.now();
    if (smoothFinalTail) {
      animationModeRef.current = "final-tail";
      animationStartTextRef.current = current;
      animationDurationRef.current = finalTranscriptTailDuration(
        graphemes(target).length - graphemes(current).length,
      );
      targetStartedAtRef.current = now;
      lastStepAtRef.current = now;
      const firstFrame = firstAdaptiveTranscriptText(current, target);
      updateVisibleText(firstFrame);
      if (firstFrame === target) cancelTranscriptFrameJob(job);
      else scheduleTranscriptFrameJob(job);
      return;
    }
    animationModeRef.current = "partial";
    animationStartTextRef.current = current;
    if (lastRevisionAtRef.current > 0) {
      const observedInterval = Math.min(
        TRANSCRIPT_RESERVOIR_MAX_REVISION_INTERVAL_MS,
        Math.max(TRANSCRIPT_RESERVOIR_MIN_REVISION_INTERVAL_MS, now - lastRevisionAtRef.current),
      );
      revisionIntervalRef.current = revisionIntervalRef.current * 0.65 + observedInterval * 0.35;
    }
    lastRevisionAtRef.current = now;
    animationDurationRef.current = adaptiveTranscriptReservoirLag(revisionIntervalRef.current);
    targetStartedAtRef.current = now;
    lastStepAtRef.current = now;
    const firstFrame = firstAdaptiveTranscriptText(visibleTextRef.current, target);
    updateVisibleText(firstFrame);
    if (firstFrame === target) cancelTranscriptFrameJob(job);
    else scheduleTranscriptFrameJob(job);
  }, [active, segment.isFinal, text]);

  useEffect(() => () => {
    if (frameJobRef.current) cancelTranscriptFrameJob(frameJobRef.current);
  }, []);

  useLayoutEffect(() => {
    if (visibleText !== text) return;
    const eventId = performance?.eventId;
    const traceId = performance?.traceId;
    if (!eventId || !traceId || lastPaintedEventId.current === eventId) return;
    const identity = {
      sessionId: segment.sessionId,
      channel: performance.channel ?? segment.sourceKind,
      utteranceId: performance.utteranceId ?? performance.segmentId ?? segment.id,
      segmentId: performance.segmentId ?? segment.id,
      revision: segment.revision,
      eventId,
      traceId,
      textLength: text.length,
    };
    if (subtitleRevisionDiagnosticsEnabled()) {
      recordSubtitleRevisionStage(identity, "react-render", renderStartedAtMs, { renderedTextLength: visibleText.length });
    }
    const reactCommitAtMs = Date.now();
    if (subtitleRevisionDiagnosticsEnabled()) {
      recordSubtitleRevisionStage(identity, "react-commit", reactCommitAtMs, { renderedTextLength: visibleText.length });
    }
    const handle = window.requestAnimationFrame(() => {
      const browserPaintAtMs = Date.now();
      lastPaintedEventId.current = eventId;
      if (subtitleRevisionDiagnosticsEnabled()) {
        recordSubtitleRevisionStage(identity, "paint", browserPaintAtMs, { renderedTextLength: visibleText.length });
      }
      window.dispatchEvent(new CustomEvent("offersteady:realtime-transcript-rendered", {
        detail: {
          sessionId: segment.sessionId,
          traceId,
          eventId,
          browserStreamChunkReceivedAtMs: performance.browserStreamChunkReceivedAtMs,
          browserEventParsedAtMs: performance.browserEventParsedAtMs,
          transcriptStoreUpdateStartAtMs: performance.transcriptStoreUpdateStartAtMs,
          transcriptStoreUpdateCompleteAtMs: performance.transcriptStoreUpdateCompleteAtMs,
          browserEventReceiveAtMs: performance.browserEventReceiveAtMs,
          browserStateUpdateAtMs: performance.browserStateUpdateAtMs,
          reactRenderStartAtMs: renderStartedAtMs,
          reactCommitAtMs,
          browserPaintAtMs,
          browserRenderAtMs: browserPaintAtMs,
          renderedRevision: segment.revision,
          renderedTextLength: visibleText.length,
          visibilityState: document.visibilityState,
        },
      }));
    });
    return () => window.cancelAnimationFrame(handle);
  }, [performance, renderStartedAtMs, segment.id, segment.revision, segment.sessionId, text, visibleText]);

  return <p className={active ? "is-streaming" : "is-final"}>{visibleText}{active ? <span className="transcript-caret" aria-hidden="true" /> : null}</p>;
}

export function ConversationMonitor({ state, onConfirmQuestion, onDismissQuestion }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const transcripts = useMemo(() => projectConversationTurns(state.speaker.transcripts), [state.speaker.transcripts]);
  useEffect(() => { const node = viewport.current; if (node && followLatest.current) node.scrollTop = node.scrollHeight; }, [transcripts.length, transcripts.at(-1)?.revision]);
  useEffect(() => {
    const latest = transcripts.at(-1);
    if (!latest) return;
    const publishedAtMs = latest.publishedAtMs ?? latest.endedAtMs;
    if (!publishedAtMs) return;
    const frontendRenderMs = Math.max(0, Date.now() - publishedAtMs);
    const runtime = ((globalThis as typeof globalThis & {
      __offersteadyRealtimeMetrics?: {
        latestFrontendRenderMs?: number;
        latestSegmentId?: string;
        renderedAtMs?: number;
      };
    }).__offersteadyRealtimeMetrics ??= {});
    runtime.latestFrontendRenderMs = frontendRenderMs;
    runtime.latestSegmentId = latest.id;
    runtime.renderedAtMs = Date.now();
  }, [transcripts]);
  const pendingSegmentIds = new Set(state.speaker.pendingQuestion?.sourceSegmentIds ?? []);
  return <section className={`conversation-monitor ${transcripts.length === 0 ? "is-empty" : "has-transcripts"}`} aria-labelledby="conversation-title">
    <SubtitleDiagnosticsOverlay />
    <header><div><span className="kicker">LIVE CONVERSATION</span><h2 id="conversation-title">实时对话</h2></div><span className="conversation-mode"><i className={state.speaker.mode === "dual-channel" ? "online-dot" : "recording-dot"} />{state.speaker.mode === "dual-channel" ? "双通道 · 两角色" : "仅手动提问"}</span></header>
    {state.speaker.degradation ? <div className="source-degradation" role="status"><strong>音频来源无法区分</strong><span>面试官问题识别已暂停，请检查桌面程序或使用右侧手动提问。</span></div> : null}
    {!state.speaker.degradation && state.speaker.runtimeNotice ? <div className="source-degradation" role="status"><strong>当前 session 尚未收到实时对话</strong><span>{state.speaker.runtimeNotice.message}</span></div> : null}
    <div className="conversation-list" ref={viewport} onScroll={event => { const node = event.currentTarget; followLatest.current = node.scrollHeight - node.scrollTop - node.clientHeight < 48; }}>
      {transcripts.length === 0 ? <div className="conversation-empty"><strong>等待当前面试的实时对话</strong><span>{state.speaker.runtimeNotice?.message ?? "桌面伴随助手连上当前 session 后，这里会按“面试官 / 我”实时显示转录。"}</span></div> : null}
      {transcripts.map(segment => {
        const role = segment.role;
        const hasPendingQuestion = segment.sourceSegmentIds.some(id => pendingSegmentIds.has(id));
        const presentation = transcriptPresentationState(segment);
        return <article key={segment.id} className={`conversation-turn ${role}`}><time>{formatTranscriptTimestamp(segment.startedAtMs)}</time><div><div className="conversation-turn-meta"><strong>{role === "candidate" ? "我" : "面试官"}</strong><small>{transcriptPresentationLabel(presentation)}{segment.overlap ? " · 声音重叠" : ""}</small></div><ProgressiveTranscriptText segment={segment} active={presentation === "transcribing"} />{hasPendingQuestion && state.speaker.pendingQuestion ? <div className="inline-question-confirm"><span>问题内容不清晰</span><strong>{state.speaker.pendingQuestion.text}</strong><small>确认文本后可点击“快答”生成回答；确认本身不会开始回答或扣费。</small><div><button onClick={onDismissQuestion}>忽略</button><button className="confirm" onClick={onConfirmQuestion}>确认问题</button></div></div> : null}</div></article>;
      })}
    </div>
  </section>;
}
