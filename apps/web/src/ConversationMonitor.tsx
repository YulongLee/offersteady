import { useEffect, useMemo, useRef } from "react";
import type { WebAppState } from "./domain";

interface Props {
  readonly state: WebAppState;
  readonly onConfirmQuestion: () => void;
  readonly onDismissQuestion: () => void;
}

const relativeTime = (milliseconds: number) => `${String(Math.floor(milliseconds / 60_000)).padStart(2, "0")}:${String(Math.floor(milliseconds / 1_000) % 60).padStart(2, "0")}`;
const normalizeTranscriptText = (text: string) => text.replace(/\s+/g, "").replace(/[，。！？、；：,.!?;:~～…·]/g, "");

export function ConversationMonitor({ state, onConfirmQuestion, onDismissQuestion }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const transcripts = useMemo(() => {
    const cleanSegments = state.speaker.transcripts.filter(segment => normalizeTranscriptText(segment.text));
    const latestById = new Map<string, (typeof state.speaker.transcripts)[number]>();
    for (const segment of cleanSegments) {
      const current = latestById.get(segment.id);
      if (!current || segment.revision > current.revision) latestById.set(segment.id, segment);
    }
    const ordered = [...latestById.values()].sort((a, b) => a.startedAtMs - b.startedAtMs);
    const collapsed: typeof ordered = [];
    for (const segment of ordered) {
      const previous = collapsed.at(-1);
      if (previous) {
        const previousText = normalizeTranscriptText(previous.text);
        const currentText = normalizeTranscriptText(segment.text);
        const closeInTime = Math.abs(segment.startedAtMs - previous.endedAtMs) <= 4_000;
        const sameRole = previous.role === segment.role;
        const sameOrContaining = previousText && currentText && (
          previousText === currentText
          || previousText.includes(currentText)
          || currentText.includes(previousText)
        );
        if (sameRole && closeInTime && sameOrContaining) {
          collapsed[collapsed.length - 1] = segment.revision >= previous.revision ? segment : previous;
          continue;
        }
      }
      collapsed.push(segment);
    }
    return collapsed;
  }, [state.speaker.transcripts]);
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
        return <article key={segment.id} className={`conversation-turn ${role}`}><time>{relativeTime(segment.startedAtMs)}</time><div><div className="conversation-turn-meta"><strong>{role === "candidate" ? "我" : "面试官"}</strong><small>{segment.isFinal ? "已确认" : "转写中"}{segment.overlap ? " · 声音重叠" : ""}</small></div><p>{segment.text}</p>{pendingSegmentIds.has(segment.id) && state.speaker.pendingQuestion ? <div className="inline-question-confirm"><span>问题内容不清晰</span><strong>{state.speaker.pendingQuestion.text}</strong><small>确认文本后才会生成回答，与角色判断无关。</small><div><button onClick={onDismissQuestion}>忽略</button><button className="confirm" onClick={onConfirmQuestion}>确认问题</button></div></div> : null}</div></article>;
      })}
    </div>
  </section>;
}
