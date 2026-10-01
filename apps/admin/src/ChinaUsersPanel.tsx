import { useEffect, useRef, useState } from "react";
import { adminApi, isAdminAuthenticationError } from "./api";
import "./china-users.css";

type UserRow = Record<string, unknown> & { user_id: string };
type Action = "points" | "time" | "suspend" | "restore";
const actionLabels: Record<Action, string> = { points: "调整积分", time: "增加时长", suspend: "封禁账号", restore: "恢复账号" };
const label = (value: unknown) => value == null || value === "" ? "—" : String(value);
const registrationFormatter = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});
const registrationTime = (value: unknown): string => {
  const timestamp = typeof value === "number" ? value
    : typeof value === "string" && /^\d+$/.test(value) ? Number(value) : NaN;
  if (!Number.isSafeInteger(timestamp) || timestamp <= 0) return "—";
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime())) return "—";
  const parts = Object.fromEntries(registrationFormatter.formatToParts(date).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`;
};

export function ChinaUsersPanel({ permissions, refreshKey = 0, onAuthenticationExpired }: {
  permissions: string[];
  refreshKey?: number;
  onAuthenticationExpired: (message: string) => void;
}) {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState({ search: "", offset: 0, revision: 0 });
  const [rows, setRows] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState<UserRow | null>(null);
  const [action, setAction] = useState<Action>("points");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const mounted = useRef(false);
  const sequence = useRef(0);
  const pendingCommand = useRef<{ signature: string; key: string } | null>(null);
  const form = useRef<HTMLElement>(null);
  const authExpired = useRef(onAuthenticationExpired);
  authExpired.current = onAuthenticationExpired;
  const canAdjust = permissions.includes("billing.adjust");
  const canSuspend = permissions.includes("users.suspend");
  const allowed = (kind: Action) => kind === "points" || kind === "time" ? canAdjust : canSuspend;

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const requestId = ++sequence.current;
    let active = true;
    setLoading(true); setError(""); setRows([]); setSelected(null);
    void adminApi.listUsers(query.search, query.offset).then(result => {
      if (!active || requestId !== sequence.current) return;
      setRows(Array.isArray(result.items) ? result.items.filter((row): row is UserRow => typeof row.user_id === "string") : []);
    }).catch(failure => {
      if (!active || requestId !== sequence.current) return;
      const text = failure instanceof Error ? failure.message : "用户查询失败，请重试。";
      setError(text);
      if (isAdminAuthenticationError(failure)) authExpired.current(text);
    }).finally(() => { if (active && requestId === sequence.current) setLoading(false); });
    return () => { active = false; };
  }, [query, refreshKey]);

  const clearSelection = () => { setSelected(null); setAmount(""); setReason(""); setMessage(""); };
  const search = (text: string, offset = 0, keepNotice = false) => {
    if (submitting.current) return;
    ++sequence.current;
    clearSelection(); setRows([]); setLoading(true); setError("");
    if (!keepNotice) setNotice("");
    setQuery(previous => ({ search: text.trim(), offset, revision: previous.revision + 1 }));
  };
  const choose = (row: UserRow, kind: Action) => {
    if (submitting.current || !allowed(kind)) return;
    clearSelection(); setNotice(""); setSelected(row); setAction(kind);
  };
  useEffect(() => {
    if (selected) form.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [selected]);

  const submit = async () => {
    if (submitting.current || !selected || !allowed(action)) return;
    const value = Number(amount);
    const safeReason = reason.trim();
    if (safeReason.length < 6 || safeReason.length > 500) { setMessage("请填写 6–500 字的操作原因。"); return; }
    if (action === "points" && (!Number.isSafeInteger(value) || value === 0 || Math.abs(value) > 1_000_000)) {
      setMessage("积分必须为非零整数，范围为 -1000000 至 1000000。"); return;
    }
    if (action === "time" && (!Number.isSafeInteger(value) || value < 1 || value > 365)) {
      setMessage("增加时长必须为 1–365 的整数天数。"); return;
    }
    const adjustment = action === "points" ? `${value > 0 ? "+" : ""}${value} 积分` : action === "time" ? `+${value} 天` : actionLabels[action];
    const identity = `${label(selected.display_name)}\n用户 ID：${selected.user_id}\n手机号：${label(selected.phone_hint)}`;
    if (!window.confirm(`${actionLabels[action]}\n${identity}\n本次操作：${adjustment}\n原因：${safeReason}\n确认后将记录审计，请核对操作对象。`)) return;
    submitting.current = true; setBusy(true); setMessage("");
    const target = selected.user_id;
    const payload = { reason: safeReason, confirmed: true, ...(action === "points" ? { points: value } : action === "time" ? { days: value } : {}) };
    const path = `/users/${encodeURIComponent(target)}/${action}`;
    const signature = JSON.stringify([path, payload]);
    if (pendingCommand.current?.signature !== signature) pendingCommand.current = { signature, key: crypto.randomUUID() };
    try {
      await adminApi.action(path, { ...payload, idempotencyKey: pendingCommand.current.key });
      pendingCommand.current = null;
      if (!mounted.current) return;
      setNotice(`已完成：${label(selected.display_name)}（${target}）${adjustment}。操作已记录，请勿重复提交。`);
      submitting.current = false;
      search(query.search, query.offset, true);
    } catch (failure) {
      if (!mounted.current) return;
      const text = failure instanceof Error ? failure.message : "请求失败，请核查后重试。";
      setMessage(`${text} 相同内容重试将复用请求编号，避免重复处理。`);
      if (isAdminAuthenticationError(failure)) authExpired.current(text);
    } finally {
      submitting.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  return <div className="cn-users-panel">
    <section className="cn-users-search">
      <div><p className="eyebrow">CUSTOMER SEARCH</p><h2>查找用户</h2><p>输入用户名或用户 ID，搜索全部用户；选中结果后直接调整权益。</p></div>
      <form onSubmit={event => { event.preventDefault(); search(draft); }}>
        <label htmlFor="cn-user-query">用户名 / 用户 ID</label>
        <div className="cn-users-search-controls"><input id="cn-user-query" type="search" maxLength={100} value={draft} disabled={busy} placeholder="输入用户名或用户 ID" onChange={event => setDraft(event.target.value)} />
          <button className="primary" disabled={busy} type="submit">搜索</button>
          <button type="button" disabled={busy} onClick={() => { setDraft(""); search(""); }}>重置</button></div>
      </form>
    </section>
    {notice && <div className="cn-users-notice" role="status">{notice}</div>}
    {error && <div className="alert" role="alert">{error}<button disabled={busy} onClick={() => search(query.search, query.offset, true)}>重新查询</button></div>}
    {loading ? <div className="loading" role="status">正在查询用户…</div> : !error && <>
      <div className="cn-users-result-meta"><span>{query.search ? `搜索“${query.search}”` : "全部用户"}</span><span>本页 {rows.length} 位用户</span></div>
      {rows.length ? <div className="table-wrap"><table><thead><tr><th>用户名 / 用户 ID</th><th>手机号</th><th>注册时间（北京时间）</th><th>积分余额</th><th>账号状态</th><th>操作</th></tr></thead><tbody>{rows.map(row => <tr key={row.user_id} className={selected?.user_id === row.user_id ? "cn-user-selected" : ""}>
        <td><strong>{label(row.display_name)}</strong><small className="cn-user-id">{row.user_id}</small></td><td>{label(row.phone_hint)}</td><td className="cn-user-registration">{registrationTime(row.created_at_ms)}</td><td>{label(row.points_balance)}</td><td>{row.account_status === "active" ? "正常" : label(row.account_status)}</td>
        <td><div className="cn-user-actions">{canAdjust && <><button disabled={busy} onClick={() => choose(row, "points")}>调整积分</button><button disabled={busy} onClick={() => choose(row, "time")}>增加时长</button></>}{canSuspend && <><button disabled={busy} onClick={() => choose(row, "suspend")}>封禁账号</button><button disabled={busy} onClick={() => choose(row, "restore")}>恢复账号</button></>}{!canAdjust && !canSuspend && <span>只读</span>}</div></td>
      </tr>)}</tbody></table></div> : <div className="empty">没有找到匹配用户，请修改用户名或用户 ID 后重试。</div>}
      <div className="pagination"><button disabled={busy || query.offset === 0} onClick={() => search(query.search, Math.max(0, query.offset - 50))}>上一页</button><span>第 {query.offset / 50 + 1} 页</span><button disabled={busy || rows.length < 50} onClick={() => search(query.search, query.offset + 50)}>下一页</button></div>
    </>}
    {selected && !loading && !error && allowed(action) && <section ref={form} className="cn-user-editor" aria-label="用户权益操作">
      <div className="cn-user-editor-heading"><div><p className="eyebrow">CONFIRM CUSTOMER</p><h3>{actionLabels[action]}</h3></div><button disabled={busy} onClick={clearSelection}>取消选择</button></div>
      <div className="cn-user-identity"><strong>{label(selected.display_name)}</strong><span>用户 ID：{selected.user_id}</span><span>手机号：{label(selected.phone_hint)}</span><span>注册时间（北京时间）：{registrationTime(selected.created_at_ms)}</span></div>
      <form onSubmit={event => { event.preventDefault(); void submit(); }}>
        {(action === "points" || action === "time") && <label>{action === "points" ? "积分增减值" : "增加天数"}<input aria-label={action === "points" ? "积分增减值" : "增加天数"} disabled={busy} type="number" step="1" min={action === "points" ? -1000000 : 1} max={action === "points" ? 1000000 : 365} value={amount} onChange={event => setAmount(event.target.value)} placeholder={action === "points" ? "正数增加，负数扣减，例如 100 或 -100" : "输入 1–365 天"} /></label>}
        <label>操作原因<input aria-label="操作原因" disabled={busy} maxLength={500} value={reason} onChange={event => setReason(event.target.value)} placeholder="填写至少 6 个字的操作原因" /></label>
        <p>提交前会再次核对用户和调整内容；操作权限、积分账本与审计规则保持不变。</p>
        <button className="primary" disabled={busy} type="submit">{busy ? "正在提交…" : `确认${actionLabels[action]}`}</button>
      </form>
      {message && <p role="alert">{message}</p>}
    </section>}
  </div>;
}
