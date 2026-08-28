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

const TRANSCRIPT_SMOOTHING_MAX_LAG_MS = 300;
const TRANSCRIPT_SMOOTHING_FRAME_MS = 32;
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

export const firstAdaptiveTranscriptText = (current: string, target: string) => {
  if (current === target || !target.startsWith(current)) return target;
  const currentLength = graphemes(current).length;
  return graphemes(target).slice(0, currentLength + 1).join("");
};

export const nextAdaptiveTranscriptText = (
  current: string,
  target: string,
  elapsedMs: number,
  maxLagMs = TRANSCRIPT_SMOOTHING_MAX_LAG_MS,
) => {
  if (current === target || !target.startsWith(current) || elapsedMs >= maxLagMs) return target;
  const currentUnits = graphemes(current);
  const targetUnits = graphemes(target);
  const remaining = targetUnits.length - currentUnits.length;
  if (remaining <= 0) return target;
  const remainingFrames = Math.max(1, Math.floor((maxLagMs - Math.max(0, elapsedMs)) / TRANSCRIPT_SMOOTHING_FRAME_MS));
  const step = Math.max(1, Math.ceil(remaining / remainingFrames));
  return targetUnits.slice(0, currentUnits.length + step).join("");
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
      if (timestamp - lastStepAtRef.current < TRANSCRIPT_SMOOTHING_FRAME_MS) return true;
      lastStepAtRef.current = timestamp;
      const next = nextAdaptiveTranscriptText(current, target, timestamp - targetStartedAtRef.current);
      updateVisibleText(next);
      return next !== target;
    };
  }

  useLayoutEffect(() => {
    const job = frameJobRef.current!;
    const target = nextProgressiveTranscriptText(targetTextRef.current, text, segment.isFinal);
    targetTextRef.current = target;
    if (segment.isFinal || !active || !transcriptSmoothingEnabled()) {
      cancelTranscriptFrameJob(job);
      updateVisibleText(target);
      return;
    }
    const now = window.performance.now();
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
