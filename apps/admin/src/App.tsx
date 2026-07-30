import { FormEvent, useEffect, useMemo, useState } from "react";

import { adminApi } from "./api";

type View = "dashboard" | "users" | "orders" | "materials" | "interviews" | "audit" | "admins";
type Row = Record<string, unknown>;

const views: { id: View; label: string; eyebrow: string }[] = [
  { id: "dashboard", label: "运营总览", eyebrow: "OVERVIEW" },
  { id: "users", label: "用户与权益", eyebrow: "CUSTOMERS" },
  { id: "orders", label: "订单与支付", eyebrow: "BILLING" },
  { id: "materials", label: "资料任务", eyebrow: "KNOWLEDGE" },
  { id: "interviews", label: "面试会话", eyebrow: "SESSIONS" },
  { id: "audit", label: "审计记录", eyebrow: "AUDIT" },
  { id: "admins", label: "管理员", eyebrow: "ACCESS" },
];

const labels: Record<string, string> = {
  users: "累计用户",
  active_sessions: "进行中面试",
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
  const [totpCode, setTotpCode] = useState("");
  const [message, setMessage] = useState("使用已授权的账号完成短信验证与动态口令验证。");
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
      await adminApi.login(user.tokens.accessToken, totpCode);
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
        <label>动态口令<input value={totpCode} onChange={event => setTotpCode(event.target.value)} placeholder="身份验证器中的 6 位口令" maxLength={6} /></label>
        <button className="primary" disabled={busy || !challengeId || smsCode.length !== 6 || totpCode.length !== 6}>进入运营中心</button>
        <p className="form-message">{message}</p>
      </form>
    </main>
  );
}

function Dashboard({ data }: { data: Row }) {
  const entries = Object.entries(data).filter(([key]) => key in labels);
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
    </>
  );
}

function Table({ rows }: { rows: Row[] }) {
  const keys = useMemo(() => Array.from(new Set(rows.flatMap(row => Object.keys(row)))).slice(0, 8), [rows]);
  if (!rows.length) return <div className="empty">当前范围内没有数据</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{keys.map(key => <th key={key}>{key.replaceAll("_", " ")}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={String(row.id || row.user_id || row.order_id || row.session_id || index)}>{keys.map(key => <td key={key}>{display(row[key])}</td>)}</tr>)}</tbody>
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
        const code = window.prompt("该操作需要近期 MFA 验证，请输入 6 位动态口令：");
        if (code?.length === 6) {
          try {
            await adminApi.stepUp(code);
            setMessage("MFA 验证成功，请再次确认操作。");
            return;
          } catch (stepError) {
            setMessage(stepError instanceof Error ? stepError.message : "MFA 验证失败");
            return;
          }
        }
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
  const [enrollment, setEnrollment] = useState<{ secret: string; uri: string } | null>(null);
  if (!permissions.includes("admins.manage")) return <div className="empty">当前角色无管理员管理权限</div>;

  const stepUpAndRetry = async (error: unknown) => {
    const text = error instanceof Error ? error.message : "操作失败";
    if (!text.includes("admin_step_up_required")) {
      setMessage(text);
      return false;
    }
    const code = window.prompt("管理员授权需要近期 MFA 验证，请输入 6 位动态口令：");
    if (!code || code.length !== 6) return false;
    await adminApi.stepUp(code);
    setMessage("MFA 验证成功，请再次提交操作。");
    return true;
  };

  const create = async () => {
    if (loginId.trim().length < 3 || reason.trim().length < 6) {
      setMessage("请输入已注册手机号或登录标识，并填写至少 6 个字的原因。");
      return;
    }
    if (!window.confirm(`确认授予 ${loginId} “${role}”管理员角色？`)) return;
    try {
      const result = await adminApi.action("/admins", {
        loginId: loginId.trim(),
        role,
        reason,
        confirmed: true,
        idempotencyKey: crypto.randomUUID(),
      });
      setEnrollment({
        secret: String(result.totp_secret),
        uri: String(result.provisioning_uri),
      });
      setMessage("管理员已创建。下方绑定信息只展示一次，请安全交给该管理员。");
      setLoginId("");
      onChanged();
    } catch (error) {
      await stepUpAndRetry(error);
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
            <button onClick={() => void create()}>添加管理员</button>
            {rows.filter(row => row.status === "active").map(row => (
              <button key={String(row.user_id)} onClick={() => void disable(String(row.user_id))}>
                停用 {String(row.masked_login || row.display_name || row.user_id)}
              </button>
            ))}
          </div>
          <small>{message}</small>
        </div>
      </section>
      {enrollment && <section className="enrollment-panel">
        <div><p className="eyebrow">DISPLAY ONCE</p><h3>TOTP 绑定信息</h3><p>请让新管理员立即添加到身份验证器。关闭后后台不再展示明文密钥。</p></div>
        <code>{enrollment.secret}</code>
        <textarea readOnly value={enrollment.uri} />
        <button onClick={() => setEnrollment(null)}>我已安全保存并关闭</button>
      </section>}
    </>
  );
}

export function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(adminApi.token()));
  const [view, setView] = useState<View>("dashboard");
  const [role, setRole] = useState("");
  const [permissions, setPermissions] = useState<string[]>([]);
  const [data, setData] = useState<Row | Row[]>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [offset, setOffset] = useState(0);

  const load = async (target: View) => {
    setLoading(true);
    setError("");
    try {
      const session = await adminApi.session();
      setRole(session.role);
      setPermissions(session.permissions);
      setData(target === "dashboard" ? await adminApi.dashboard() : (await adminApi.list(target, offset)).items);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "后台服务暂时不可用";
      setError(message);
      if (/session|required|401|invalid/i.test(message)) {
        adminApi.clear();
        setAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) void load(view);
  }, [authenticated, view, offset]);

  if (!authenticated) return <Login onReady={() => setAuthenticated(true)} />;
  const current = views.find(item => item.id === view)!;

  return (
    <div className="admin-shell">
      <aside>
        <div className="brand"><span className="brand-mark small">稳</span><div><strong>面试稳</strong><small>运营中心</small></div></div>
        <nav>{views.map(item => <button className={item.id === view ? "active" : ""} onClick={() => { setOffset(0); setView(item.id); }} key={item.id}><small>{item.eyebrow}</small>{item.label}</button>)}</nav>
        <div className="operator"><span className="online" /><div><small>当前角色</small><strong>{role || "验证中"}</strong></div></div>
      </aside>
      <main className="workspace">
        <header><div><p className="eyebrow">{current.eyebrow}</p><h1>{current.label}</h1></div><div className="header-actions"><span>{new Date().toLocaleDateString("zh-CN")}</span><button onClick={() => void load(view)}>刷新</button><button onClick={() => adminApi.logout().then(() => setAuthenticated(false))}>退出</button></div></header>
        {error && <div className="alert">{error}</div>}
        {loading ? <div className="loading">正在读取脱敏运营数据...</div> : view === "dashboard" ? <Dashboard data={data as Row} /> : view === "admins" ? <AdminPanel rows={data as Row[]} permissions={permissions} onChanged={() => void load(view)} /> : <>
          <Table rows={data as Row[]} />
          <div className="pagination"><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 50))}>上一页</button><span>第 {offset / 50 + 1} 页</span><button disabled={(data as Row[]).length < 50} onClick={() => setOffset(value => value + 50)}>下一页</button></div>
          <ActionPanel view={view} rows={data as Row[]} permissions={permissions} onChanged={() => void load(view)} />
        </>}
      </main>
    </div>
  );
}
