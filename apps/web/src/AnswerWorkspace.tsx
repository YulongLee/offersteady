import type { AnswerTaskSnapshot } from "@offersteady/protocol";
import { memo, useState } from "react";
import type { InterviewLanguage, InterviewQuestion, QuestionStatus } from "./domain";
import { AnswerMarkdown } from "./AnswerMarkdown";
import { answerPage } from "./live-workspace";

interface Props {
  readonly answers: readonly InterviewQuestion[];
  readonly viewingAnswerId: string | null;
  readonly newAnswerAvailable: boolean;
  readonly activeTask: AnswerTaskSnapshot | null;
  readonly cancelling: boolean;
  readonly cancelError: string;
  readonly cancelledWebAnswerIds?: ReadonlySet<string>;
  readonly interviewLanguage?: InterviewLanguage;
  readonly onView: (id: string | null) => void;
  readonly onRetry: (id: string, status: QuestionStatus) => void;
  readonly onStop: () => void;
}

const statusLabel: Record<QuestionStatus, string> = { listening: "正在聆听", transcribing: "正在转写", confirmed: "问题已确认", generating: "正在思考", streaming: "正在生成", uncertain: "需要确认", failed: "生成失败", offline: "连接离线", cancelled: "回答已终止" };

const cleanSectionText = (value: string) => value
  .replace(/^\s*(简要回答|简单回答|详细回答|Quick Answer|Detailed Answer)\s*[:：]?\s*/i, "")
  .trim();

const splitAnswerSections = (detail: string) => {
  const [simpleRaw, ...detailParts] = detail.split(/\n\s*---\s*\n/);
  const simple = cleanSectionText(simpleRaw || detail);
  const detailed = cleanSectionText(detailParts.join("\n---\n"));
  return { simple, detailed, hasDetailedSection: detailParts.length > 0 };
};

const AnswerContent = memo(function AnswerContent({ content, streaming }: { readonly content: string; readonly streaming: boolean }) {
  return streaming
    ? <div className="answer-stream-text">{content}</div>
    : <AnswerMarkdown content={content} />;
});

export function AnswerWorkspace({ answers, viewingAnswerId, newAnswerAvailable, activeTask, cancelling, cancelError, cancelledWebAnswerIds, interviewLanguage = "zh-CN", onView, onRetry, onStop }: Props) {
  const [mobileExpanded, setMobileExpanded] = useState(false);
  const english = interviewLanguage === "en-US";
  const page = answerPage(answers, viewingAnswerId);
  const taskActive = activeTask?.status === "queued" || activeTask?.status === "generating";
  if (!page) return <section className="answer-workspace empty-state" aria-labelledby="answer-title"><h2 id="answer-title">{english ? "Answer" : "回答"}</h2><p>{english ? "Confirm the interviewer's question or enter one manually to see the answer here." : "确认面试官问题或手动输入问题后，答案会显示在这里。"}</p></section>;
  const shown = page.answer;
  const fixedCount = shown.advice.provenance.fixedSourceCount ?? shown.advice.provenance.usedSources.filter(source => source.contextRole === "fixed").length;
  const retrievedCount = shown.advice.provenance.retrievedSourceCount ?? shown.advice.provenance.usedSources.filter(source => source.contextRole === "retrieved").length;
  const unavailableSources = shown.advice.provenance.unavailableSources ?? [];
  const webSources = shown.advice.provenance.webSources ?? [];
  const webSearchStatus = shown.advice.provenance.webSearchStatus;
  const answerSections = splitAnswerSections(shown.advice.detail);
  const shownTaskActive = Boolean(taskActive && activeTask?.questionId === shown.id);
  const answerStreaming = page.isLatest && (shownTaskActive || shown.status === "generating" || shown.status === "streaming");
  const quickCompleted = shown.quickAnswerCompleted === true
    || (activeTask?.questionId === shown.id && activeTask.quickAnswerCompleted === true)
    || answerSections.hasDetailedSection;
  const simpleStreaming = answerStreaming && !quickCompleted;
  const detailStreaming = answerStreaming && quickCompleted;
  const detailFailed = quickCompleted && shown.status === "failed";
  const webSearchNotice = webSearchStatus === "succeeded"
    ? (english ? "Web context added" : "已加入联网资料")
    : webSearchStatus === "fallback" || webSearchStatus === "unavailable"
      ? (english ? "Web search unavailable; local answer shown" : "联网暂不可用，已回退本地回答")
      : webSearchStatus === "pending" && detailStreaming
        ? (english ? "Checking public web sources…" : "正在查询公开资料…")
        : "";
  const minimalSourceSummary = shown.advice.provenance.usedSources.length
    ? english ? `Answer sources · Fixed ${fixedCount} · Knowledge ${retrievedCount}` : `回答依据 · 固定资料 ${fixedCount} · 知识库 ${retrievedCount}`
    : english ? "No personal materials used" : "未使用个人资料";
  const preserveCancelledText = shown.status === "cancelled" && cancelledWebAnswerIds?.has(shown.id) && Boolean(answerSections.simple);
  return <section className={`answer-workspace${mobileExpanded ? " mobile-answer-expanded" : ""}`} aria-labelledby="answer-title" aria-live="polite">
    <header className="answer-workspace-head"><div><span className="kicker">ANSWER</span><h2 id="answer-title">{english ? "Answer" : "回答"}</h2></div><div className="answer-pagination"><button className="mobile-answer-size-toggle" aria-pressed={mobileExpanded} onClick={() => setMobileExpanded(value => !value)}>{mobileExpanded ? (english ? "Restore height" : "恢复回答框高度") : (english ? "Expand answer" : "扩大回答框")}</button><button disabled={!page.previousId} title={page.previousId ? (english ? "View previous answer" : "查看上一条历史答案") : (english ? "This is the earliest answer" : "已经是最早答案")} onClick={() => onView(page.previousId)}>← {english ? "Previous" : "上一条"}</button><span>{page.index + 1} / {page.total}</span><button disabled={!page.nextId} title={page.nextId ? (english ? "View next answer" : "查看下一条较新答案") : (english ? "This is the latest answer" : "已经是最新答案")} onClick={() => onView(page.nextId)}>{english ? "Next" : "下一条"} →</button>{!page.isLatest || newAnswerAvailable ? <button className="latest-answer" onClick={() => onView(null)}>{english ? (newAnswerAvailable ? "New answer · Latest" : "Back to latest") : (newAnswerAvailable ? "有新答案 · 回到最新" : "回到最新")}</button> : null}</div></header>
    {taskActive ? <div className="answer-task-control" role="status"><span>{shownTaskActive && quickCompleted ? (english ? "Quick answer complete · Adding detail" : "简单回答已完成 · 详细回答正在生成") : viewingAnswerId ? "最新回答仍在生成" : "当前回答正在生成"}</span><button className="stop-answer" disabled={cancelling} onClick={onStop}>{cancelling ? "正在终止…" : "终止回答"}</button></div> : null}
    {cancelError ? <div className="answer-cancel-error" role="alert">{cancelError}</div> : null}
    <div className="question-block"><div><span className="question-state"><i /> {page.isLatest ? statusLabel[shown.status] : "历史答案"}</span><small>{shown.askedAt} · {shown.input === "desktop-audio" ? "桌面音频" : shown.input === "manual" ? "手动输入" : "截图"}</small></div><h1>{shown.text}</h1></div>
    {shown.status === "cancelled" ? <div className="cancelled-answer" role="status"><strong>回答已终止</strong><span>未完成内容不会作为可用建议；面试与收音仍在继续。</span><button onClick={() => onRetry(shown.id, "generating")}>重新回答</button></div> : null}
    {preserveCancelledText ? <div className="advice-card"><p>{english ? "Web mode is off. Text generated before stopping is retained below; the answer is incomplete." : "联网已关闭。以下保留停止前已生成的内容，回答尚未完成。"}</p><AnswerContent content={answerSections.simple} streaming={false} /></div> : null}
    {shown.status === "offline" || shown.status === "failed" || shown.status === "uncertain" ? <div className={`recovery-banner ${shown.status}`} role="status"><div><strong>{shown.status === "offline" ? "实时连接已断开" : shown.status === "failed" ? (detailFailed ? (english ? "Detailed answer failed; quick answer retained" : "详细回答生成失败，简单回答已保留") : "回答生成失败") : "问题内容需要确认"}</strong><span>{shown.status === "offline" ? "当前不再宣称内容正在同步。" : "原始问题仍被保留，可安全重试。"}</span></div><button onClick={() => onRetry(shown.id, shown.status === "offline" ? "confirmed" : "generating")}>{shown.status === "offline" ? "重新连接" : "重试"}</button></div> : null}
    {shown.status !== "cancelled" ? <div className="advice-card"><div className="advice-heading"><span className="advice-label">{english ? "AI Answer" : "AI 回答"}</span><span className="confidence">{english ? (shown.advice.uncertain ? "Limited evidence" : "Ready to use") : (shown.advice.uncertain ? "资料较少" : "可直接参考")}</span></div><div className="answer-body structured-answer" aria-label={english ? "Answer body" : "回答正文"}><section className="answer-section simple-answer" aria-busy={simpleStreaming}><div className="answer-section-title"><span>{english ? "Quick Answer" : "简单回答"}</span><small>{quickCompleted && answerStreaming ? (english ? "Quick answer complete" : "简单回答已完成") : (english ? "Say this first" : "先说这段")}</small></div><AnswerContent content={answerSections.simple} streaming={simpleStreaming} /></section>{answerSections.detailed || answerStreaming ? <section className="answer-section detailed-answer" aria-busy={detailStreaming}><div className="answer-section-title"><span>{english ? "Detailed Answer" : "详细回答"}</span><small>{english ? (retrievedCount > 0 ? `Knowledge sources ${retrievedCount}` : detailStreaming ? "Adding detail" : "No knowledge source") : (retrievedCount > 0 ? `已引用知识库 ${retrievedCount}` : detailStreaming ? "正在补充" : "未引用知识库")}</small></div>{answerSections.detailed ? <AnswerContent content={answerSections.detailed} streaming={answerStreaming} /> : <p className="answer-placeholder">{!quickCompleted ? (english ? "Detailed answer follows the quick answer." : "简单回答完成后补充详细回答") : webSearchStatus === "pending" ? (english ? "Generating a web-grounded detailed answer…" : "正在生成联网详细回答…") : (english ? "Adding a detailed answer from the available materials…" : "正在结合资料补充详细回答…")}</p>}</section> : null}</div>{webSearchNotice ? <div className="context-warning" role="status">{webSearchNotice}</div> : null}{unavailableSources.length ? <div className="context-warning" role="status">{english ? `${unavailableSources.length} selected source(s) were unavailable for this answer.` : `有 ${unavailableSources.length} 份已选资料本次未使用：${unavailableSources.map(source => source.displayName).join("、")}。请回到资料库重新处理后再确认本场资料。`}</div> : null}{webSources.length ? <div className="context-warning web-source-list" role="status"><strong>{english ? "Web sources" : "联网来源"}</strong>{webSources.map(source => <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a>)}</div> : null}<div className="advice-footer"><div className="source-pills"><small>{minimalSourceSummary}</small>{shown.advice.provenance.usedSources.map(source => <span key={`${source.sourceId}-${source.contextRole ?? "source"}`}>{english ? (source.contextRole === "retrieved" ? "Knowledge" : source.kind === "jd" ? "JD" : "Fixed") : (source.contextRole === "retrieved" ? "知识库" : source.kind === "jd" ? "JD" : "固定")} · {source.displayName} {source.sourceVersion}{source.truncated ? (english ? " · Truncated" : " · 已截断") : ""}</span>)}{webSources.map(source => <span key={`web-${source.url}`}>{english ? "Web" : "联网"} · {source.title}</span>)}</div><span>{english ? (shown.advice.uncertain ? "Use only experience you can verify." : "Keep the answer faithful to your real experience.") : (shown.advice.uncertain ? "资料不足时请只使用你能核对的真实经历" : "请按真实经历表达，避免补造细节")}</span></div></div> : null}
  </section>;
}
