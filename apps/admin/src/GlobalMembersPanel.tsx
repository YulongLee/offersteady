import { useEffect, useRef, useState, type ReactNode } from "react";
import { adminApi } from "./api";
import "./global-members.css";

type Row = Record<string, unknown>;
const offers = [
  ["global-interview-pass", "Interview Day Pass · 24 小时 / 180 分钟"],
  ["global-pro-weekly", "Pro Weekly · 7 天无限使用"],
  ["global-pro-monthly", "Pro Monthly · 人工赠送 30 天（不自动续费）"],
  ["global-job-hunt", "Job Hunt · 90 天无限使用"],
] as const;
const label = (value: unknown) => value == null || value === "" ? "—" : String(value);
export function memberTime(value: unknown): string {
  if ((typeof value !== "number" && typeof value !== "string") || String(value).trim() === "") return "—";
  const ms = Number(value);
  if (!Number.isSafeInteger(ms) || ms <= 0 || ms > 8.64e15) return "—";
  return new Date(ms).toISOString().replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
}

export function GlobalMembersContent({ renderTable }: { renderTable: (rows: Row[]) => ReactNode }) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [members, setMembers] = useState<Row[]>([]);
  const [detail, setDetail] = useState<Row | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [offerCode, setOfferCode] = useState<string>(offers[0][0]);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  const [listValid, setListValid] = useState(false);
  const searchRevision = useRef(0);
  const detailRevision = useRef(0);
  const writing = useRef(false);
  const retryKeys = useRef(new Map<string, string>());
  const mounted = useRef(true);
  const pageSize = 30;

  function clearSelection() {
    detailRevision.current += 1;
    setDetail(null); setSelectedId(""); setReason("");
  }
  async function runSearch(nextQuery = search.trim(), nextOffset = 0) {
    if (writing.current) return;
    const revision = ++searchRevision.current;
    clearSelection(); setMembers([]); setListValid(false); setBusy("search"); setMessage("");
    setQuery(nextQuery); setOffset(nextOffset);
    try {
      const result = await adminApi.globalMembers(nextQuery, nextOffset);
      if (!mounted.current || revision !== searchRevision.current) return;
      setMembers(result.items); setListValid(true);
      if (!result.items.length) setMessage("没有找到匹配的国际版用户。");
    } catch (error) {
      if (mounted.current && revision === searchRevision.current) setMessage(error instanceof Error ? error.message : "用户搜索失败，请重试。");
    } finally {
      if (mounted.current && revision === searchRevision.current) setBusy("");
    }
  }
  useEffect(() => {
    mounted.current = true;
    void runSearch("", 0);
    return () => { mounted.current = false; searchRevision.current += 1; detailRevision.current += 1; };
  }, []);

  async function openMember(userId: string) {
    if (writing.current) return;
    const revision = ++detailRevision.current;
    setSelectedId(userId); setDetail(null); setReason(""); setBusy(`member:${userId}`); setMessage("");
    try {
      const result = await adminApi.globalMember(userId);
      if (mounted.current && revision === detailRevision.current) {
        if ((result.identity as Row | undefined)?.user_id !== userId) throw new Error("返回的用户身份不匹配，请重新选择。");
        setDetail(result);
      }
    } catch (error) {
      if (mounted.current && revision === detailRevision.current) setMessage(error instanceof Error ? error.message : "会员详情读取失败，请重试。");
    } finally {
      if (mounted.current && revision === detailRevision.current) setBusy("");
    }
  }

  async function mutate(kind: "grant" | "revoke", entitlement?: Row) {
    if (writing.current || busy) return;
    const identity = detail?.identity as Row | undefined;
    const userId = String(identity?.user_id ?? "");
    const normalizedReason = reason.trim();
    if (!userId || userId !== selectedId || normalizedReason.length < 3) {
      setMessage("请选择用户并填写至少 3 个字符的操作原因。"); return;
    }
    const target = kind === "grant" ? offerCode : String(entitlement?.id ?? "");
    if (kind === "revoke" && (!target || entitlement?.status !== "active" || entitlement?.sourceKind === "free_grant")) return;
    const actionLabel = kind === "grant" ? `赠送 ${offers.find(([code]) => code === target)?.[1] ?? target}` : `撤销权益 ${target}`;
    if (!window.confirm(`确认${actionLabel}？\n邮箱：${label(identity?.email)}\n用户 ID：${userId}\n原因：${normalizedReason}\n不会创建 Creem 订单、自动续费或修改其他用户。`)) return;
    writing.current = true; setBusy(kind); setMessage("");
    const signature = JSON.stringify([kind, userId, target, normalizedReason]);
    const key = retryKeys.current.get(signature) ?? crypto.randomUUID();
    retryKeys.current.set(signature, key);
    try {
      if (kind === "grant") await adminApi.grantGlobalMemberPlan(userId, target, normalizedReason, key);
      else await adminApi.revokeGlobalMemberEntitlement(userId, target, normalizedReason, key);
      retryKeys.current.delete(signature);
      if (!mounted.current) return;
      setReason("");
      // A successful write is final even if the subsequent read fails.
      setDetail(null);
      try {
        const result = await adminApi.globalMember(userId);
        if (!mounted.current) return;
        if ((result.identity as Row | undefined)?.user_id !== userId) throw new Error("身份不匹配");
        setDetail(result); setMessage("会员权益操作已成功并记录审计日志。");
      } catch {
        if (mounted.current) setMessage("权益操作已成功，但详情刷新失败。请刷新用户详情，不要重复提交。");
      }
    } catch (error) {
      if (mounted.current) setMessage(`${error instanceof Error ? error.message : "权益操作失败"}；保持用户、操作和原因不变重试，不会重复执行同一请求。`);
    } finally {
      writing.current = false;
      if (mounted.current) setBusy("");
    }
  }

  const identity = detail?.identity as Row | undefined;
  const state = detail?.state as Row | undefined;
  const usage = state?.usage as Row | undefined;
  const features = state?.features as Row | undefined;
  const entitlements = Array.isArray(detail?.entitlements) ? detail.entitlements as Row[] : [];
  const orders = Array.isArray(detail?.orders) ? detail.orders as Row[] : [];
  const subscriptions = Array.isArray(detail?.subscriptions) ? detail.subscriptions as Row[] : [];
  const writingNow = busy === "grant" || busy === "revoke";
  return <div className="global-members-admin">
    <section className="member-search"><div><p className="eyebrow">GLOBAL MEMBER SEARCH</p><h2>查找国际版用户</h2><p>支持邮箱、昵称或用户 ID，每页 30 条。注册时间统一显示 UTC。</p><p>这里只管理国际版会员套餐与权益，不使用国服积分规则。</p></div>
      <form onSubmit={event => { event.preventDefault(); void runSearch(); }}><input aria-label="搜索国际版用户" disabled={writingNow} value={search} onChange={event => { setSearch(event.target.value); searchRevision.current += 1; clearSelection(); setMembers([]); setListValid(false); setBusy(""); setMessage(""); }} placeholder="输入邮箱、昵称或用户 ID" /><button className="primary" disabled={writingNow || busy === "search"}>{busy === "search" ? "查询中…" : "搜索用户"}</button></form>
    </section>
    {message ? <section className="alert" role="status">{message}</section> : null}
    <div className="member-layout"><section className="member-results" aria-label="用户搜索结果"><h3>搜索结果</h3>
      {members.length ? members.map(member => <button disabled={writingNow} key={String(member.user_id)} onClick={() => void openMember(String(member.user_id))} className={selectedId === member.user_id ? "active" : ""}>
        <strong>{label(member.email)}</strong><span>{label(member.display_name)} · {label(member.current_plan_name || "Free / 未激活")}</span>
        <small>用户 ID：{label(member.user_id)}</small><small>注册时间：{memberTime(member.created_at_ms)}</small><small>{member.current_ends_at_ms ? `有效至 ${memberTime(member.current_ends_at_ms)}` : "无固定到期时间"}</small>
      </button>) : <div className="empty">{busy === "search" ? "正在查询…" : "当前没有搜索结果"}</div>}
      <nav className="member-pagination" aria-label="用户分页"><button className="secondary" disabled={writingNow || busy === "search" || offset === 0} onClick={() => void runSearch(query, Math.max(0, offset - pageSize))}>上一页</button><span>第 {Math.floor(offset / pageSize) + 1} 页</span><button className="secondary" disabled={Boolean(busy) || !listValid || members.length < pageSize} onClick={() => void runSearch(query, offset + pageSize)}>下一页</button></nav>
    </section>
    <section className="member-detail" aria-label="会员详情">{identity ? <>
      <div className="member-identity"><div><p className="eyebrow">MEMBER DETAIL</p><h2>{label(identity.email)}</h2><p>{label(identity.display_name)}</p><p>用户 ID：{label(identity.user_id)}</p><p>注册时间：{memberTime(identity.created_at_ms)}</p></div><span className="status-badge active">国际版账号</span></div>
      <div className="member-usage"><article><small>Copilot</small><strong>{usage?.copilotUnlimited ? "Unlimited" : `${label(usage?.copilotMinutesRemaining ?? 0)} 分钟`}</strong></article><article><small>Screen Assist</small><strong>{usage?.screenAssistUnlimited ? "Unlimited" : `${label(usage?.screenAssistUsesRemaining ?? 0)} 次`}</strong></article><article><small>资料能力</small><strong>{features?.resumeJd ? "Resume / JD" : "未包含"}</strong></article><article><small>知识库 / 笔试</small><strong>{features?.knowledgeBase || features?.writtenExam ? "已包含" : "未包含"}</strong></article></div>
      <section className="member-adjust"><div><h3>人工会员管理</h3><p>按现有套餐赠送，不创建支付订单或自动续费。</p></div><select aria-label="选择赠送套餐" disabled={Boolean(busy)} value={offerCode} onChange={event => setOfferCode(event.target.value)}>{offers.map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select><input aria-label="会员操作原因" disabled={Boolean(busy)} value={reason} onChange={event => setReason(event.target.value)} placeholder="填写赠送或撤销原因" /><button className="primary" disabled={Boolean(busy)} onClick={() => void mutate("grant")}>{writingNow ? "处理中…" : "确认赠送"}</button></section>
      <section><p className="eyebrow">ENTITLEMENTS</p><h3>会员权益记录</h3>{entitlements.length ? <div className="entitlement-list">{entitlements.map(item => <article key={String(item.id)}><div><strong>{offers.find(([code]) => code === item.offerCode)?.[1] ?? (item.offerCode === "global-free" ? "Free" : label(item.offerCode))}</strong><span>{label(item.status)} · {label(item.sourceKind)} · {item.endsAtMs ? `至 ${memberTime(item.endsAtMs)}` : "长期 / 用完为止"}</span></div>{item.status === "active" && item.sourceKind !== "free_grant" ? <button disabled={Boolean(busy)} onClick={() => void mutate("revoke", item)}>撤销此权益</button> : null}</article>)}</div> : <div className="empty">暂无权益记录</div>}</section>
      <section><p className="eyebrow">ORDERS &amp; SUBSCRIPTIONS</p><h3>订单与订阅</h3>{renderTable(orders)}{renderTable(subscriptions)}</section>
    </> : <div className="empty">{busy.startsWith("member:") ? "正在读取会员详情…" : selectedId ? <button className="secondary" disabled={Boolean(busy)} onClick={() => void openMember(selectedId)}>刷新用户详情</button> : "从左侧搜索结果选择一名用户查看详情"}</div>}</section></div>
  </div>;
}
