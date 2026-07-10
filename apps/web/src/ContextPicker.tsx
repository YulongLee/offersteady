import { useMemo, useState } from "react";
import type { ContextLibrarySource, SessionContextSelection } from "@offersteady/protocol";
import { Link } from "react-router-dom";
import { contextLevel, contextSourceStatusLabel, eligibleSource, reviseSelection, selectionValidity } from "./context-selection";
import { routes } from "./routes";

export interface ContextPickerProps {
  readonly sources: readonly ContextLibrarySource[];
  readonly selection: SessionContextSelection;
  readonly onSave: (selection: SessionContextSelection) => void | Promise<void>;
  readonly onCancel?: () => void;
}

const dateLabel = (value: number) => new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(value);

export function ContextPicker({ sources, selection, onSave, onCancel }: ContextPickerProps) {
  const [resumeSourceId, setResume] = useState(selection.resumeSourceId);
  const [jobDescriptionSourceId, setJd] = useState(selection.jobDescriptionSourceId);
  const [knowledgeSourceIds, setKnowledge] = useState<string[]>([...selection.knowledgeSourceIds]);
  const [query, setQuery] = useState("");
  const resumes = sources.filter(source => source.kind === "resume");
  const jds = sources.filter(source => source.kind === "jd");
  const knowledge = useMemo(() => sources.filter(source => source.kind === "knowledge" && source.displayName.toLowerCase().includes(query.trim().toLowerCase())), [sources, query]);
  const draft = reviseSelection(selection, { resumeSourceId, jobDescriptionSourceId, knowledgeSourceIds });
  const valid = selectionValidity(sources, draft) === "valid";
  const level = contextLevel(draft);
  const toggleKnowledge = (id: string) => setKnowledge(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id]);
  const selectAll = () => setKnowledge(knowledge.filter(eligibleSource).map(source => source.id));

  const group = (title: string, items: readonly ContextLibrarySource[], kind: "resume" | "jd") => <fieldset className="context-group"><legend>{title} <small>可选 · 单选</small></legend><label className={`context-option context-none ${!(kind === "resume" ? resumeSourceId : jobDescriptionSourceId) ? "selected" : ""}`}><input type="radio" name={`${selection.sessionId}-${kind}`} checked={!(kind === "resume" ? resumeSourceId : jobDescriptionSourceId)} onChange={() => kind === "resume" ? setResume(null) : setJd(null)} /><span><strong>本场不使用{title}</strong><small>仍可开始面试，回答不会引用这类资料</small></span></label>{items.map((source, index) => {
    const disabled = !eligibleSource(source); const checked = (kind === "resume" ? resumeSourceId : jobDescriptionSourceId) === source.id;
    return <label className={`context-option ${checked ? "selected" : ""} ${disabled ? "disabled" : ""}`} key={source.id}><input type="radio" name={`${selection.sessionId}-${kind}`} checked={checked} disabled={disabled} onChange={() => kind === "resume" ? setResume(source.id) : setJd(source.id)} /><span><strong>{source.displayName}</strong><small>{source.version} · {dateLabel(source.updatedAtMs)} · {contextSourceStatusLabel[source.status]}{kind === "resume" && index === 0 ? " · 最近使用建议" : ""}</small></span>{checked ? <b>✓</b> : null}</label>;
  })}</fieldset>;

  return <div className="context-picker"><div className="context-picker-head"><div><h2>本场使用的资料</h2><p>与“面试资料”页面使用同一份资料清单；三类都可以为空。</p></div><span>{knowledgeSourceIds.length + (resumeSourceId ? 1 : 0) + (jobDescriptionSourceId ? 1 : 0)} 项 · {level === "none" ? "无个人资料" : level === "personalized" ? "个性化" : "部分资料"}</span></div>
    {group("简历", resumes, "resume")}{group("职位 JD", jds, "jd")}
    <fieldset className="context-group"><legend>知识材料 <small>多选 · 默认不全选</small></legend><div className="context-tools"><input aria-label="搜索知识材料" value={query} onChange={event => setQuery(event.target.value)} placeholder="搜索资料名称" /><button type="button" onClick={selectAll}>全选可用</button><button type="button" onClick={() => setKnowledge([])}>全部取消</button></div>{knowledge.map(source => { const disabled = !eligibleSource(source); const checked = knowledgeSourceIds.includes(source.id); return <label className={`context-option ${checked ? "selected" : ""} ${disabled ? "disabled" : ""}`} key={source.id}><input type="checkbox" checked={checked} disabled={disabled} onChange={() => toggleKnowledge(source.id)} /><span><strong>{source.displayName}</strong><small>{source.version} · {contextSourceStatusLabel[source.status]} · {source.summary}</small></span>{checked ? <b>✓</b> : null}</label>; })}</fieldset>
    {!valid ? <div className="context-warning" role="alert">已选资料已失效或不再可用，请取消选择或<Link to={routes.library}>前往面试资料处理</Link>后重新确认。</div> : knowledgeSourceIds.length > 5 ? <div className="context-warning">选择过多材料可能引入无关内容，检索仍会执行相关性过滤。</div> : null}
    <div className="context-picker-actions"><button className="button ghost" type="button" onClick={() => { setResume(null); setJd(null); setKnowledge([]); }}>本场不使用资料</button>{onCancel ? <button className="button ghost" onClick={onCancel}>取消</button> : null}<button className="button primary" disabled={!valid} title={valid ? undefined : "所选资料不可用，请取消选择或更换资料"} onClick={() => { void onSave(draft); }}>{level === "none" ? "确认空资料并继续" : "确认本场资料"}</button></div>
  </div>;
}
