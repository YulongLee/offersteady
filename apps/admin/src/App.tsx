import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { adminApi } from "./api";
import { buildLinePath, chartDomain, formatTrendChange, formatTrendValue, type TrendMetric, type TrendResponse } from "./analytics";

type View = "dashboard" | "users" | "orders" | "redemptions" | "materials" | "interviews" | "audit" | "admins";
type Row = Record<string, unknown>;

const views: { id: View; label: string; eyebrow: string; permission: string }[] = [
  { id: "dashboard", label: "运营总览", eyebrow: "OVERVIEW", permission: "observability.read" },
  { id: "users", label: "用户与权益", eyebrow: "CUSTOMERS", permission: "users.read" },
  { id: "orders", label: "订单与支付", eyebrow: "BILLING", permission: "billing.read" },
  { id: "redemptions", label: "兑换码", eyebrow: "BENEFITS", permission: "billing.read" },
  { id: "materials", label: "资料任务", eyebrow: "KNOWLEDGE", permission: "materials.read" },
  { id: "interviews", label: "面试会话", eyebrow: "SESSIONS", permission: "sessions.read" },
  { id: "audit", label: "审计记录", eyebrow: "AUDIT", permission: "audit.read" },
  { id: "admins", label: "管理员", eyebrow: "ACCESS", permission: "admins.manage" },
];

const labels: Record<string, string> = {
  users: "累计用户",
  active_sessions: "进行中面试",
  idle_sessions: "空闲待关闭",
  pending_orders: "待确认订单",
  failed_materials: "待处理资料",
  ai_calls_24h: "24h AI 调用",
  ai_errors_24h: "24h AI 异常",
};

const display = (value: unknown) => {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "number" && value > 1_000_000_000_000) return new Date(value).toLocaleString("zh-CN");
  return String(value);
};

function Login({ onReady }: { onReady: () => void }) {
  const [phone, setPhone] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [smsCode, setSmsCode] = useState("");
  const [message, setMessage] = useState("使用已授权的管理员手机号和短信验证码登录。");
  const [busy, setBusy] = useState(false);

  const send = async () => {
    setBusy(true);
    try {
      const result = await adminApi.sendSms(phone);
      setChallengeId(result.challengeId);
      setMessage(`验证码已发送，${result.cooldownSeconds} 秒后可重新获取。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "验证码发送失败");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      const user = await adminApi.verifySms(phone, challengeId, smsCode);
      await adminApi.login(user.tokens.accessToken);
      onReady();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "管理身份验证失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-shell">
      <section className="login-story">
        <span className="brand-mark">稳</span>
        <p className="eyebrow">OFFERSTEADY OPERATIONS</p>
        <h1>把复杂留在后台，<br />把稳定交给用户。</h1>
        <p className="story-copy">独立运营控制面，仅展示脱敏信息。所有财务、账号和任务操作都会写入不可修改的审计记录。</p>
        <div className="security-note"><span /> 管理入口与用户端完全隔离</div>
      </section>
      <form className="login-card" onSubmit={submit}>
        <p className="eyebrow">SECURE ACCESS</p>
        <h2>管理员验证</h2>
        <label>手机号<input value={phone} onChange={event => setPhone(event.target.value)} placeholder="请输入已授权手机号" /></label>
        <button className="secondary" type="button" onClick={send} disabled={busy || phone.length < 11}>获取短信验证码</button>
        <label>短信验证码<input value={smsCode} onChange={event => setSmsCode(event.target.value)} placeholder="6 位验证码" maxLength={6} /></label>
        <button className="primary" disabled={busy || !challengeId || smsCode.length !== 6}>进入运营中心</button>
        <p className="form-message">{message}</p>
      </form>
    </main>
  );
}

function Dashboard({ data }: { data: Row }) {
  const entries = Object.entries(data).filter(([key]) => key in labels);
  const [range, setRange] = useState<"7d" | "30d" | "90d">("30d");
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [trendError, setTrendError] = useState("");
  const [trendLoading, setTrendLoading] = useState(true);
  const loadTrends = async () => {
    setTrendLoading(true);
    setTrendError("");
    try {
      setTrends(await adminApi.trends(range));
    } catch (error) {
      setTrendError(error instanceof Error ? error.message : "趋势数据暂时不可用");
    } finally {
      setTrendLoading(false);
    }
  };
  useEffect(() => { void loadTrends(); }, [range]);
  return (
    <>
      <div className="metric-grid">
        {entries.map(([key, value], index) => (
          <article className="metric" key={key}>
            <span>0{index + 1}</span>
            <strong>{display(value)}</strong>
            <p>{labels[key]}</p>
          </article>
        ))}
      </div>
      <section className="signal-panel">
        <div><p className="eyebrow">SYSTEM SIGNAL</p><h3>今日运行信号</h3></div>
        <p>后台查询使用独立时间窗、分页与超时预算。用户资料原文、音频、截图及密钥不会在这里出现。</p>
      </section>
      <section className="trend-section">
        <div className="trend-heading">
          <div><p className="eyebrow">HISTORICAL SIGNAL</p><h2>运营趋势</h2><p>每日聚合永久保存。缺失历史不会被绘制为零。</p></div>
          <div className="range-switch">{(["7d", "30d", "90d"] as const).map(item => <button className={range === item ? "active" : ""} onClick={() => setRange(item)} key={item}>{item.replace("d", " 天")}</button>)}</div>
        </div>
        {trendLoading ? <div className="trend-state">正在读取历史运营快照...</div> : trendError ? <div className="trend-state error"><span>{trendError}</span><button onClick={() => void loadTrends()}>重新加载</button></div> : trends && <>
          <div className="trend-health">
            <span className={trends.health.lastSuccessAtMs ? "healthy" : "delayed"} />
            <strong>{trends.health.lastSuccessAtMs ? "聚合正常" : "等待首次聚合"}</strong>
            <small>{trends.health.lastSuccessAtMs ? `最近更新 ${new Date(trends.health.lastSuccessAtMs).toLocaleString("zh-CN")}` : "部署后将自动生成历史快照"}</small>
          </div>
          <div className="trend-grid">{trends.metrics.map(metric => <TrendCard metric={metric} key={metric.key} />)}</div>
        </>}
      </section>
    </>
  );
}

function TrendCard({ metric }: { metric: TrendMetric }) {
  const path = buildLinePath(metric.points);
  const domain = chartDomain(metric.points);
  const missing = metric.points.filter(point => point.value === null).length;
  const middle = domain ? (domain.minimum + domain.maximum) / 2 : null;
  const dateLabel = (value: string | undefined) => value ? value.slice(5) : "—";
  const middlePoint = metric.points[Math.floor((metric.points.length - 1) / 2)];
  return (
    <article className="trend-card">
      <div className="trend-card-title"><div><small>{metric.group.toUpperCase()}</small><h3>{metric.label}</h3></div><span>{formatTrendChange(metric.summary.changePercent)}</span></div>
      <strong>{formatTrendValue(metric.summary.current, metric.unit)}</strong>
      <div className="chart-wrap">
        {path && domain ? <svg viewBox="0 0 560 190" role="img" aria-label={`${metric.label}趋势`}>
          {[10, 85, 160].map(y => <line className="chart-grid" x1="52" x2="550" y1={y} y2={y} key={y} />)}
          <line className="chart-axis" x1="52" x2="52" y1="10" y2="160" />
          <line className="chart-axis" x1="52" x2="550" y1="160" y2="160" />
          <text className="chart-label y" x="45" y="14">{formatTrendValue(domain.maximum, metric.unit)}</text>
          <text className="chart-label y" x="45" y="89">{formatTrendValue(middle, metric.unit)}</text>
          <text className="chart-label y" x="45" y="164">{formatTrendValue(domain.minimum, metric.unit)}</text>
          <text className="chart-label x" x="52" y="184">{dateLabel(metric.points.at(0)?.date)}</text>
          <text className="chart-label x middle" x="301" y="184">{dateLabel(middlePoint?.date)}</text>
          <text className="chart-label x end" x="550" y="184">{dateLabel(metric.points.at(-1)?.date)}</text>
          <text className="chart-unit" x="52" y="8">单位：{metric.unit}</text>
          <path className="chart-glow" d={path} />
          <path className="chart-line" d={path} />
        </svg> : <div className="chart-empty">该区间暂无可用数据</div>}
      </div>
      <div className="trend-card-foot"><span>{metric.points.at(0)?.date} - {metric.points.at(-1)?.date}</span><span>{missing ? `${missing} 天无覆盖` : "数据完整"}</span></div>
      <p>{metric.description}</p>
    </article>
  );
}

function Table({ rows }: { rows: Row[] }) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const keys = useMemo(() => Array.from(new Set(safeRows.flatMap(row => Object.keys(row)))).slice(0, 8), [safeRows]);
  if (!safeRows.length) return <div className="empty">当前范围内没有数据</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{keys.map(key => <th key={key}>{key.replaceAll("_", " ")}</th>)}</tr></thead>
        <tbody>{safeRows.map((row, index) => <tr key={String(row.id || row.user_id || row.order_id || row.session_id || index)}>{keys.map(key => <td key={key}>{display(row[key])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function ActionPanel({ view, rows, permissions, onChanged }: { view: View; rows: Row[]; permissions: string[]; onChanged: () => void }) {
  const [selected, setSelected] = useState("");
  const [reason, setReason] = useState("");
  const [amount, setAmount] = useState("");
  const [message, setMessage] = useState("");
  const options = rows.map(row => {
    const value = String(row.user_id || row.order_id || row.task_id || row.session_id || "");
    return { value, label: `${value} · ${String(row.display_name || row.title || row.status || "")}` };
  }).filter(item => item.value);
  const requiredPermission: Partial<Record<View, string>> = {
    users: "users.suspend",
    orders: "payments.reconcile",
    materials: "materials.retry",
    interviews: "sessions.terminate",
  };
  const canOperate = requiredPermission[view] ? permissions.includes(requiredPermission[view]!) : false;
  if (!["users", "orders", "materials", "interviews"].includes(view) || !options.length || !canOperate) return null;

  const run = async (kind: string) => {
    if (!selected || reason.trim().length < 6) {
      setMessage("请选择目标并填写至少 6 个字的操作原因。");
      return;
    }
    if (!window.confirm(`确认执行“${kind}”？该操作会记录到审计日志。`)) return;
    const payload: Record<string, unknown> = {
      reason,
      confirmed: true,
      idempotencyKey: crypto.randomUUID(),
    };
    let path = "";
    if (kind === "suspend") path = `/users/${selected}/suspend`;
    if (kind === "restore") path = `/users/${selected}/restore`;
    if (kind === "points") {
      path = `/users/${selected}/points`;
      payload.points = Number(amount);
    }
    if (kind === "time") {
      path = `/users/${selected}/time`;
      payload.days = Number(amount);
    }
    if (kind === "reconcile") path = `/orders/${selected}/reconcile`;
    if (kind === "retry") path = `/materials/tasks/${selected}/retry`;
    if (kind === "terminate") path = `/interviews/${selected}/terminate`;
    try {
      const result = await adminApi.action(path, payload);
      setMessage(`操作已受理：${display(result.status || result.order_status || "success")}`);
      onChanged();
    } catch (error) {
      const text = error instanceof Error ? error.message : "操作失败";
      if (text.includes("admin_step_up_required")) {
        setMessage("短信安全验证已过期，即将返回登录页，请重新获取短信验证码。");
        adminApi.clear();
        window.location.reload();
        return;
      }
      setMessage(text);
    }
  };

  return (
    <section className="action-panel">
      <div><p className="eyebrow">CONTROLLED ACTION</p><h3>受控运营操作</h3><p>操作原因、操作者、结果和请求编号将写入不可修改的审计记录。</p></div>
      <div className="action-form">
        <select value={selected} onChange={event => setSelected(event.target.value)}><option value="">选择操作目标</option>{options.map(item => <option value={item.value} key={item.value}>{item.label}</option>)}</select>
        <input value={reason} onChange={event => setReason(event.target.value)} placeholder="填写操作原因（必填）" />
        {view === "users" && <input value={amount} onChange={event => setAmount(event.target.value)} type="number" placeholder="积分增减值或增加天数" />}
        <div className="action-buttons">
          {view === "users" && <><button onClick={() => void run("suspend")}>封禁账号</button><button onClick={() => void run("restore")}>恢复账号</button><button onClick={() => void run("points")}>调整积分</button><button onClick={() => void run("time")}>增加时长</button></>}
          {view === "orders" && <button onClick={() => void run("reconcile")}>渠道对账检查</button>}
          {view === "materials" && <button onClick={() => void run("retry")}>重试失败任务</button>}
          {view === "interviews" && <button onClick={() => void run("terminate")}>结束异常会话</button>}
        </div>
        <small>{message}</small>
      </div>
    </section>
  );
}

function AdminPanel({ rows, permissions, onChanged }: { rows: Row[]; permissions: string[]; onChanged: () => void }) {
  const [loginId, setLoginId] = useState("");
  const [role, setRole] = useState("operations");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  if (!permissions.includes("admins.manage")) return <div className="empty">当前角色无管理员管理权限</div>;

  const stepUpAndRetry = async (error: unknown) => {
    const text = error instanceof Error ? error.message : "操作失败";
    if (!text.includes("admin_step_up_required")) {
      setMessage(text);
      return false;
    }
    setMessage("短信安全验证已过期，即将返回登录页，请重新获取短信验证码。");
    adminApi.clear();
    window.location.reload();
    return false;
  };

  const create = async () => {
    if (busy) return;
    if (loginId.trim().length < 3 || reason.trim().length < 6) {
      setMessage("请输入已注册手机号或登录标识，并填写至少 6 个字的原因。");
      return;
    }
    if (!window.confirm(`确认授予 ${loginId} “${role}”管理员角色？`)) return;
    setBusy(true);
    try {
      await adminApi.action("/admins", {
        loginId: loginId.trim(),
        role,
        reason,
        confirmed: true,
        idempotencyKey: crypto.randomUUID(),
      });
      setMessage("管理员已创建，可直接使用授权手机号和短信验证码登录。");
      setLoginId("");
      onChanged();
    } catch (error) {
      await stepUpAndRetry(error);
    } finally {
      setBusy(false);
    }
  };

  const disable = async (userId: string) => {
    if (reason.trim().length < 6) {
      setMessage("停用管理员前请填写至少 6 个字的原因。");
      return;
    }
    if (!window.confirm("确认停用该管理员并立即撤销其管理会话？")) return;
    try {
      await adminApi.action(`/admins/${userId}/disable`, {
        reason,
        confirmed: true,
        idempotencyKey: crypto.randomUUID(),
      });
      setMessage("管理员已停用，现有管理会话已撤销。");
      onChanged();
    } catch (error) {
      await stepUpAndRetry(error);
    }
  };

  return (
    <>
      <Table rows={rows} />
      <section className="action-panel">
        <div><p className="eyebrow">ADMIN ACCESS</p><h3>管理员授权</h3><p>只能添加已经注册的用户。权限使用预设角色，所有变更都会审计。</p></div>
        <div className="action-form">
          <input value={loginId} onChange={event => setLoginId(event.target.value)} placeholder="已注册手机号或登录标识" />
          <select value={role} onChange={event => setRole(event.target.value)}>
            <option value="operations">运营管理员</option>
            <option value="support">客服管理员</option>
            <option value="finance">财务管理员</option>
            <option value="technical_auditor">技术审计员</option>
            <option value="super_admin">超级管理员</option>
          </select>
          <input value={reason} onChange={event => setReason(event.target.value)} placeholder="授权或停用原因（必填）" />
          <div className="action-buttons">
            <button disabled={busy} onClick={() => void create()}>{busy ? "正在添加..." : "添加管理员"}</button>
            {rows.filter(row => row.status === "active").map(row => (
              <button key={String(row.user_id)} onClick={() => void disable(String(row.user_id))}>
                停用 {String(row.masked_login || row.display_name || row.user_id)}
              </button>
            ))}
          </div>
          <small>{message}</small>
        </div>
      </section>
    </>
  );
}

function RedemptionPanel({ rows, permissions, onChanged }: { rows: Row[]; permissions: string[]; onChanged: () => void }) {
  const [campaign, setCampaign] = useState("");
  const [points, setPoints] = useState("2000");
  const [quantity, setQuantity] = useState("100");
  const [expiresInDays, setExpiresInDays] = useState("30");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [codes, setCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const canGenerate = permissions.includes("redemptions.generate");

  const generate = async () => {
    if (busy) return;
    if (!canGenerate) return;
    if (campaign.trim().length < 2 || reason.trim().length < 6) {
      setMessage("请填写活动名称和至少 6 个字的生成原因。");
      return;
    }
    if (!window.confirm(`确认生成 ${quantity} 个、每个 ${points} 积分的一次性兑换码？`)) return;
    setBusy(true);
    try {
      const result = await adminApi.action("/redemption-batches", {
        campaign: campaign.trim(),
        points: Number(points),
        quantity: Number(quantity),
        expiresInDays: Number(expiresInDays),
        reason,
        confirmed: true,
        idempotencyKey: crypto.randomUUID(),
      });
      const generated = Array.isArray(result.codes) ? result.codes.map(String) : [];
      setCodes(generated);
      setMessage(generated.length
        ? "兑换码已生成。明文只展示这一次，请立即下载并安全分发。"
        : "该请求已处理过，出于安全原因不会再次展示明文兑换码。");
      onChanged();
    } catch (error) {
      const text = error instanceof Error ? error.message : "生成失败";
      if (text.includes("admin_step_up_required")) {
        setMessage("短信安全验证已过期，即将返回登录页，请重新获取短信验证码。");
        adminApi.clear();
        window.location.reload();
        return;
      }
      setMessage(text);
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    const blob = new Blob([codes.join("\n") + "\n"], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `offersteady-${campaign.trim() || "redemption-codes"}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <Table rows={rows} />
      <section className="action-panel">
        <div><p className="eyebrow">SINGLE-USE CODES</p><h3>创建兑换码批次</h3><p>每个兑换码仅可成功兑换一次。后台只保存不可逆摘要，明文不会进入数据库或审计日志。</p></div>
        <div className="action-form">
          <input value={campaign} onChange={event => setCampaign(event.target.value)} placeholder="活动名称，例如：首批内测用户" />
          <div className="field-grid">
            <label>每码积分<input type="number" min="1" max="100000" value={points} onChange={event => setPoints(event.target.value)} /></label>
            <label>生成数量<input type="number" min="1" max="500" value={quantity} onChange={event => setQuantity(event.target.value)} /></label>
            <label>有效天数<input type="number" min="1" max="365" value={expiresInDays} onChange={event => setExpiresInDays(event.target.value)} /></label>
          </div>
          <input value={reason} onChange={event => setReason(event.target.value)} placeholder="生成原因（必填）" />
          <div className="action-buttons"><button disabled={!canGenerate || busy} onClick={() => void generate()}>{busy ? "正在生成..." : "生成一次性兑换码"}</button></div>
          <small>{canGenerate ? message : "当前角色无兑换码生成权限"}</small>
        </div>
      </section>
      {codes.length > 0 && <section className="redemption-output">
        <div><p className="eyebrow">DISPLAY ONCE</p><h3>本批兑换码</h3><p>关闭或刷新页面后无法恢复明文，请立即下载。</p></div>
        <textarea readOnly value={codes.join("\n")} />
        <div><button onClick={download}>下载 TXT</button><button onClick={() => setCodes([])}>我已保存并关闭</button></div>
      </section>}
    </>
  );
}

export function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(adminApi.token()));
  const [view, setView] = useState<View>("dashboard");
  const [role, setRole] = useState("");
  const [permissions, setPermissions] = useState<string[]>([]);
  const [dashboardData, setDashboardData] = useState<Row>({});
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const loadSequence = useRef(0);
  const sessionRequest = useRef<ReturnType<typeof adminApi.session> | null>(null);

  const load = async (target: View, background = false) => {
    const sequence = ++loadSequence.current;
    if (!background) setLoading(true);
    setError("");
    try {
      if (!sessionRequest.current) sessionRequest.current = adminApi.session();
      const session = await sessionRequest.current;
      if (sequence !== loadSequence.current) return;
      setRole(session.role);
      setPermissions(session.permissions);
      const targetView = views.find(item => item.id === target);
      if (targetView && !session.permissions.includes(targetView.permission)) {
        const fallback = views.find(item => session.permissions.includes(item.permission));
        if (!fallback) throw new Error("当前管理员角色没有可访问的后台页面");
        if (fallback.id !== target) setView(fallback.id);
        return;
      }
      if (target === "dashboard") {
        const nextDashboard = await adminApi.dashboard();
        if (sequence === loadSequence.current) setDashboardData(nextDashboard);
      } else {
        const resource = target === "redemptions" ? "redemption-batches" : target;
        const nextRows = (await adminApi.list(resource, offset)).items;
        if (sequence === loadSequence.current) setRows(Array.isArray(nextRows) ? nextRows : []);
      }
    } catch (reason) {
      if (sequence !== loadSequence.current) return;
      const message = reason instanceof Error ? reason.message : "后台服务暂时不可用";
      setError(message);
      if (/session|required|401|invalid/i.test(message)) {
        sessionRequest.current = null;
        adminApi.clear();
        setAuthenticated(false);
      }
    } finally {
      if (sequence === loadSequence.current && !background) setLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) void load(view);
  }, [authenticated, view, offset]);

  if (!authenticated) return <Login onReady={() => setAuthenticated(true)} />;
  const current = views.find(item => item.id === view)!;
  const visibleViews = views.filter(item => permissions.length === 0 || permissions.includes(item.permission));

  return (
    <div className="admin-shell">
      <aside>
        <div className="brand"><span className="brand-mark small">稳</span><div><strong>面试稳</strong><small>运营中心</small></div></div>
        <nav>{visibleViews.map(item => <button type="button" className={item.id === view ? "active" : ""} onClick={() => { setOffset(0); setRows([]); setView(item.id); }} key={item.id}><small>{item.eyebrow}</small>{item.label}</button>)}</nav>
        <div className="operator"><span className="online" /><div><small>当前角色</small><strong>{role || "验证中"}</strong></div></div>
      </aside>
      <main className="workspace">
        <header><div><p className="eyebrow">{current.eyebrow}</p><h1>{current.label}</h1></div><div className="header-actions"><span>{new Date().toLocaleDateString("zh-CN")}</span><button onClick={() => void load(view)}>刷新</button><button onClick={() => adminApi.logout().then(() => { sessionRequest.current = null; setAuthenticated(false); })}>退出</button></div></header>
        {error && <div className="alert">{error}</div>}
        {loading ? <div className="loading">正在读取生产运营数据...</div> : view === "dashboard" ? <Dashboard data={dashboardData} /> : view === "admins" ? <AdminPanel rows={rows} permissions={permissions} onChanged={() => void load(view, true)} /> : view === "redemptions" ? <RedemptionPanel rows={rows} permissions={permissions} onChanged={() => void load(view, true)} /> : <>
          <Table rows={rows} />
          <div className="pagination"><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 50))}>上一页</button><span>第 {offset / 50 + 1} 页</span><button disabled={rows.length < 50} onClick={() => setOffset(value => value + 50)}>下一页</button></div>
          <ActionPanel view={view} rows={rows} permissions={permissions} onChanged={() => void load(view, true)} />
        </>}
      </main>
    </div>
  );
}
