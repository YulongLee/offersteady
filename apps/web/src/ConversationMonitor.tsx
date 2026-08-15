import { useEffect, useMemo, useRef, useState } from "react";
import type { WebAppState } from "./domain";
import { projectConversationTurns } from "./conversation-turns";

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
export const nextProgressiveTranscriptText = (current: string, target: string, step = 2) => {
  if (current === target) return current;
  if (target.startsWith(current)) return target.slice(0, current.length + Math.max(1, step));
  let commonPrefixLength = 0;
  while (
    commonPrefixLength < current.length
    && commonPrefixLength < target.length
    && current[commonPrefixLength] === target[commonPrefixLength]
  ) commonPrefixLength += 1;
  return target.slice(0, Math.min(target.length, commonPrefixLength + Math.max(1, step)));
};

export const STALE_TRANSCRIPT_MS = 8_000;
export type TranscriptPresentationState = "final" | "transcribing" | "stale";
export const transcriptPresentationState = (
  segment: { readonly isFinal: boolean; readonly publishedAtMs?: number; readonly endedAtMs: number },
  nowMs = Date.now(),
): TranscriptPresentationState => {
  if (segment.isFinal) return "final";
  const lastRevisionAtMs = segment.publishedAtMs ?? segment.endedAtMs;
  if (lastRevisionAtMs >= 1_000_000_000_000 && nowMs - lastRevisionAtMs >= STALE_TRANSCRIPT_MS) return "stale";
  return "transcribing";
};

function ProgressiveTranscriptText({ text, active }: { readonly text: string; readonly active: boolean }) {
  const [visibleText, setVisibleText] = useState(text);
  const targetText = useRef(text);
  targetText.current = text;

  useEffect(() => {
    if (!active) {
      setVisibleText(text);
      return;
    }
    const timer = window.setInterval(() => {
      setVisibleText(current => nextProgressiveTranscriptText(current, targetText.current));
    }, 32);
    return () => window.clearInterval(timer);
  }, [active, text]);

  return <p className={active ? "is-streaming" : "is-final"}>{visibleText}{active ? <span className="transcript-caret" aria-hidden="true" /> : null}</p>;
}

export function ConversationMonitor({ state, onConfirmQuestion, onDismissQuestion }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const transcripts = useMemo(() => projectConversationTurns(state.speaker.transcripts), [state.speaker.transcripts]);
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (!transcripts.some(segment => !segment.isFinal)) return;
    const timer = window.setInterval(() => setNowMs(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, [transcripts]);
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
    <header><div><span className="kicker">LIVE CONVERSATION</span><h2 id="conversation-title">实时对话</h2></div><span className="conversation-mode"><i className={state.speaker.mode === "dual-channel" ? "online-dot" : "recording-dot"} />{state.speaker.mode === "dual-channel" ? "双通道 · 两角色" : "仅手动提问"}</span></header>
    {state.speaker.degradation ? <div className="source-degradation" role="status"><strong>音频来源无法区分</strong><span>自动回答已暂停，请检查桌面程序或使用右侧手动提问。</span></div> : null}
    {!state.speaker.degradation && state.speaker.runtimeNotice ? <div className="source-degradation" role="status"><strong>当前 session 尚未收到实时对话</strong><span>{state.speaker.runtimeNotice.message}</span></div> : null}
    <div className="conversation-list" ref={viewport} onScroll={event => { const node = event.currentTarget; followLatest.current = node.scrollHeight - node.scrollTop - node.clientHeight < 48; }}>
      {transcripts.length === 0 ? <div className="conversation-empty"><strong>等待当前面试的实时对话</strong><span>{state.speaker.runtimeNotice?.message ?? "桌面伴随助手连上当前 session 后，这里会按“面试官 / 我”实时显示转录。"}</span></div> : null}
      {transcripts.map(segment => {
        const role = segment.role;
        const hasPendingQuestion = segment.sourceSegmentIds.some(id => pendingSegmentIds.has(id));
        const presentation = transcriptPresentationState(segment, nowMs);
        return <article key={segment.id} className={`conversation-turn ${role}`}><time>{formatTranscriptTimestamp(segment.startedAtMs)}</time><div><div className="conversation-turn-meta"><strong>{role === "candidate" ? "我" : "面试官"}</strong><small>{presentation === "final" ? "已确认" : presentation === "stale" ? "识别未完成" : "转写中"}{segment.overlap ? " · 声音重叠" : ""}</small></div><ProgressiveTranscriptText text={segment.text} active={presentation === "transcribing"} />{hasPendingQuestion && state.speaker.pendingQuestion ? <div className="inline-question-confirm"><span>问题内容不清晰</span><strong>{state.speaker.pendingQuestion.text}</strong><small>确认文本后才会生成回答，与角色判断无关。</small><div><button onClick={onDismissQuestion}>忽略</button><button className="confirm" onClick={onConfirmQuestion}>确认问题</button></div></div> : null}</div></article>;
      })}
    </div>
  </section>;
}
