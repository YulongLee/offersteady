import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { adminApi, isAdminAuthenticationError } from "./api";
import { buildLinePath, chartDomain, formatTrendChange, formatTrendValue, type TrendMetric, type TrendResponse } from "./analytics";
import { capacityLevelLabel, formatCapacityValue, hasRequestBreakdownData, requestClassLabels, type CapacityMetric, type CapacityResponse, type RequestBreakdown } from "./capacity";
import { paymentAcceptanceOutcomeLabel, paymentChannelStatus } from "./payment-channel-status";
import { diagnosticLabel, formatCny, type PaymentRevenueSummary } from "./payment-monitoring";
import { formatUptime, type ServerHealthResponse } from "./server-health";
import { validateGrowthSettings } from "./growth-settings";
import { PromotionCenter } from "./PromotionCenter";
import {
  clearRememberedAdminPhone,
  isValidAdminPhone,
  normalizeAdminPhone,
  readRememberedAdminPhone,
  saveRememberedAdminPhone,
} from "./login-preferences";

export type View = "dashboard" | "server" | "seo" | "promotion" | "users" | "orders" | "payments" | "globalCommerce" | "globalMembers" | "growth" | "pricing" | "redemptions" | "materials" | "interviews" | "audit" | "admins";
type Row = Record<string, unknown>;
const globalEdition = import.meta.env.VITE_PRODUCT_EDITION === "global";

export type AdminViewDefinition = { id: View; label: string; eyebrow: string; permission: string };

const commonCoreViews: AdminViewDefinition[] = [
  { id: "dashboard", label: "运营总览", eyebrow: "OVERVIEW", permission: "observability.read" },
  { id: "server", label: "服务器监控", eyebrow: "SERVER", permission: "observability.read" },
  { id: "seo", label: "搜索排名", eyebrow: "SEO", permission: "seo.read" },
  { id: "users", label: "用户与权益", eyebrow: "CUSTOMERS", permission: "users.read" },
];

const commonOperationsViews: AdminViewDefinition[] = [
  { id: "materials", label: "资料任务", eyebrow: "KNOWLEDGE", permission: "materials.read" },
  { id: "interviews", label: "面试会话", eyebrow: "SESSIONS", permission: "sessions.read" },
  { id: "audit", label: "审计记录", eyebrow: "AUDIT", permission: "audit.read" },
  { id: "admins", label: "管理员", eyebrow: "ACCESS", permission: "admins.manage" },
];

const chinaViews: AdminViewDefinition[] = [
  ...commonCoreViews,
  { id: "promotion", label: "推广中心", eyebrow: "ACQUISITION", permission: "promotion.read" },
  { id: "orders", label: "订单与支付", eyebrow: "BILLING", permission: "billing.read" },
  { id: "payments", label: "支付设置", eyebrow: "PAYMENTS", permission: "payments.manage" },
  { id: "growth", label: "增长设置", eyebrow: "GROWTH", permission: "growth.manage" },
  { id: "pricing", label: "商品定价", eyebrow: "CATALOG", permission: "billing.read" },
  { id: "redemptions", label: "兑换码", eyebrow: "BENEFITS", permission: "billing.read" },
  ...commonOperationsViews,
];

const globalViews: AdminViewDefinition[] = [
  ...commonCoreViews.slice(0, 2),
  { id: "globalMembers", label: "用户与会员", eyebrow: "CUSTOMERS", permission: "users.read" },
  { id: "globalCommerce", label: "国际商业化", eyebrow: "CREEM", permission: "payments.manage" },
  ...commonOperationsViews,
];

export function adminViewsForEdition(edition: "cn" | "global"): readonly AdminViewDefinition[] {
  return edition === "global" ? globalViews : chinaViews;
}

const views = adminViewsForEdition(globalEdition ? "global" : "cn");

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

export function GlobalCommercePanel({ row }: { row: Row | undefined; onChanged: () => void }) {
  const mode = "live" as const;
  const [data, setData] = useState<Row | undefined>(row);
  const [products, setProducts] = useState<Row[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [apiKey, setApiKey] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [reason, setReason] = useState("配置 Creem 支付环境");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => { if (row) setData(row); }, [row]);
  const reload = async (selectedMode = mode) => {
    const [overview, operations] = await Promise.all([adminApi.globalCommerceOverview(selectedMode), adminApi.globalCommerceOperations(selectedMode)]);
    setData({ ...overview, operations });
  };
  if (!data) return <div className="loading">国际商业化配置暂不可用</div>;
  const blockers = Array.isArray(data.blockers) ? data.blockers.map(String) : [];
  const mappings = Array.isArray(data.mappings) ? data.mappings as Row[] : [];
  const credentials = data.credentials as Record<string, Row> | undefined;
  const metrics = data.metrics as Row | undefined;
  const operations = data.operations as Row | undefined;
  const urls = data.urls as Row | undefined;
  const orders = Array.isArray(operations?.orders) ? operations.orders as Row[] : [];
  const subscriptions = Array.isArray(operations?.subscriptions) ? operations.subscriptions as Row[] : [];
  const events = Array.isArray(operations?.events) ? operations.events as Row[] : [];
  const formatProduct = (product: Row) => `${display(product.name)} · $${(Number(product.priceCents ?? 0) / 100).toFixed(2)} ${display(product.currency)} · ${product.billingMode === "recurring" ? "订阅" : "一次性"}`;
  const saveCredentials = async () => {
    if (!apiKey.trim() && !webhookSecret.trim()) { setMessage("请填写需要更新的 API Key 或 Webhook Secret。"); return; }
    setBusy("credentials"); setMessage("");
    try { await adminApi.saveGlobalCommerceCredentials(mode, apiKey.trim(), webhookSecret.trim(), reason); setApiKey(""); setWebhookSecret(""); setProducts([]); await reload(); setMessage("密钥已加密保存。当前环境的新结账保持关闭，请继续读取商品并完成映射。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "密钥保存失败"); }
    finally { setBusy(""); }
  };
  const syncProducts = async () => {
    setBusy("products"); setMessage("");
    try { const result = await adminApi.globalCommerceProducts(mode); setProducts(result.items); setMessage(`Creem 正式环境连接成功，读取到 ${result.items.length} 个商品。`); await reload(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Creem 商品读取失败"); }
    finally { setBusy(""); }
  };
  const saveMapping = async (offerCode: string) => {
    const productId = (drafts[offerCode] || "").trim();
    if (!productId) { setMessage("请从 Creem 商品列表中选择对应商品。"); return; }
    setBusy(offerCode); setMessage("");
    try { await adminApi.saveGlobalCommerceMapping(mode, offerCode, productId, reason); await reload(); setMessage("商品匹配及校验已通过；新结账仍保持关闭，需全部完成后单独启用。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "商品映射验证失败"); }
    finally { setBusy(""); }
  };
  const activate = async (enabled: boolean) => {
    setBusy("activation"); setMessage("");
    try { await adminApi.activateGlobalCommerce(mode, enabled, reason); await reload(); setMessage(enabled ? "正式环境的新结账已启用。" : "新结账已关闭，历史回调不受影响。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "启用检查失败"); }
    finally { setBusy(""); }
  };
  const reconcile = async (orderId: string) => {
    setBusy(`reconcile:${orderId}`); setMessage("");
    try { await adminApi.reconcileGlobalCommerceOrder(orderId, reason); await reload(); setMessage(`订单 ${orderId} 已完成对账。`); }
    catch (error) { setMessage(error instanceof Error ? error.message : "订单对账失败"); }
    finally { setBusy(""); }
  };
  const reconcilableOrders = orders.filter(order => ["checkout_created", "confirming"].includes(String(order.status)) && order.id && order.providerCheckoutId);
  const active = Boolean(data.providerActivated);
  // A mode can only become the runtime mode by being enabled. Requiring the
  // selected mode to already be active made the Live switch impossible to use.
  const activationAllowed = Boolean(data.configurationReady) && Boolean(data.masterSwitchEnabled);
  return <div className="global-commerce-admin">
    <section className="signal-panel"><div><p className="eyebrow">CREEM PAYMENT</p><h3>正式环境配置</h3></div><span className="status-badge ready">LIVE · 正式</span></section>
    <section className={active ? "signal-panel" : "alert"}><strong>{active ? "正式支付已允许创建结账" : "正式支付尚未启用"}</strong><span>服务器当前运行：Live 正式；正式支付需完成配置校验后启用。</span></section>
    {message ? <section className="alert">{message}</section> : null}
    <section className="panel"><p className="eyebrow">01 · CONNECTION</p><h2>连接 Creem 正式环境</h2><p>已保存的密钥不会回显；留空表示保留原值。保存新密钥会自动关闭正式支付。</p>
      <div className="payment-grid"><label>API Key <small>{credentials?.apiKey?.configured ? `已配置 · 指纹 ${display(credentials.apiKey.fingerprint)}` : "未配置"}</small><input type="password" autoComplete="new-password" value={apiKey} placeholder={credentials?.apiKey?.configured ? "留空保留原 API Key" : "creem_…"} onChange={event => setApiKey(event.target.value)} /></label><label>Webhook Secret <small>{credentials?.webhookSecret?.configured ? `已配置 · 指纹 ${display(credentials.webhookSecret.fingerprint)}` : "未配置"}</small><input type="password" autoComplete="new-password" value={webhookSecret} placeholder={credentials?.webhookSecret?.configured ? "留空保留原 Webhook Secret" : "填写 Creem Webhook Secret"} onChange={event => setWebhookSecret(event.target.value)} /></label></div>
      <label>操作说明<input value={reason} onChange={event => setReason(event.target.value)} /></label>
      <div className="page-actions"><button className="secondary" disabled={Boolean(busy)} onClick={() => void saveCredentials()}>{busy === "credentials" ? "加密保存中…" : "保存密钥"}</button><button className="primary" disabled={Boolean(busy) || !credentials?.apiKey?.configured} onClick={() => void syncProducts()}>{busy === "products" ? "连接中…" : "测试连接并读取商品"}</button></div>
      <div className="signal-panel"><div><strong>Webhook URL</strong><p>{display(urls?.webhookUrl)}</p></div><button className="secondary" onClick={() => void navigator.clipboard.writeText(String(urls?.webhookUrl ?? ""))}>复制地址</button></div>
    </section>
    <section className="panel"><p className="eyebrow">02 · PLAN MAPPING</p><h2>套餐与 Creem 商品关联</h2><p>Free 是免费权益，不需要 Creem 商品。下面只显示4个需要收款的套餐，不再展示内部技术字段。</p>
      {!products.length ? <div className="empty">先点击“测试连接并读取商品”，系统会显示 Creem 中的真实商品供你选择。</div> : null}
      <div className="payment-grid">{mappings.map(mapping => { const code = String(mapping.offerCode); const selected = drafts[code] ?? String(mapping.providerProductId ?? ""); return <article className="payment-card" key={code}><strong>{display(mapping.displayName)}</strong><small>${(Number(mapping.priceCents ?? 0) / 100).toFixed(2)} {display(mapping.currency)} · {mapping.billingMode === "recurring" ? "每月订阅" : "一次性购买"} · {mapping.validationStatus === "ready" ? "已匹配" : "待匹配"}</small><label>对应的 Creem 商品<select value={selected} disabled={!products.length || Boolean(busy)} onChange={event => setDrafts(current => ({ ...current, [code]: event.target.value }))}><option value="">请选择 Creem 商品</option>{products.map(product => <option key={String(product.id)} value={String(product.id)}>{formatProduct(product)}</option>)}</select></label><button className="payment-save" disabled={Boolean(busy) || !selected} onClick={() => void saveMapping(code)}>{busy === code ? "校验中…" : "保存并校验"}</button></article>; })}</div>
    </section>
    {blockers.length ? <section className="alert"><strong>启用前还需完成：</strong> {blockers.join("；")}</section> : <section className="signal-panel"><strong>配置校验已完成</strong><span>仍需手动点击启用，不会自动开放支付。</span></section>}
    <div className="page-actions"><button className="secondary" disabled={Boolean(busy) || !active} onClick={() => void activate(false)}>关闭正式支付</button><button className="primary" disabled={Boolean(busy) || active || !activationAllowed} onClick={() => void activate(true)}>{busy === "activation" ? "最终检查中…" : "启用 Live 正式支付"}</button></div>
    <div className="metric-grid"><article className="metric"><span>01</span><strong>{display(metrics?.paidOrders ?? 0)}</strong><p>正式已支付订单</p></article><article className="metric"><span>02</span><strong>${(Number(metrics?.grossRevenueCents ?? 0) / 100).toFixed(2)}</strong><p>确认收入</p></article><article className="metric"><span>03</span><strong>${(Number(metrics?.estimatedNetBeforeServiceCostCents ?? 0) / 100).toFixed(2)}</strong><p>估算渠道费后收入</p></article></div>
    <section><p className="eyebrow">ORDERS</p><h2>最近订单</h2><Table rows={orders} />{reconcilableOrders.length ? <div className="page-actions">{reconcilableOrders.slice(0, 8).map(order => { const orderId = String(order.id); return <button className="secondary" key={orderId} disabled={Boolean(busy)} onClick={() => void reconcile(orderId)}>{busy === `reconcile:${orderId}` ? "对账中…" : `对账 ${orderId}`}</button>; })}</div> : null}</section>
    <section><p className="eyebrow">SUBSCRIPTIONS</p><h2>订阅状态</h2><Table rows={subscriptions} /></section>
    <section><p className="eyebrow">WEBHOOKS</p><h2>回调记录</h2><Table rows={events} /></section>
  </div>;
}

const globalMemberOffers = [
  ["global-interview-pass", "Interview Day Pass · 24 小时 / 180 分钟"],
  ["global-pro-weekly", "Pro Weekly · 7 天无限使用"],
  ["global-pro-monthly", "Pro Monthly · 人工赠送 30 天（不自动续费）"],
  ["global-job-hunt", "Job Hunt · 90 天无限使用"],
] as const;

export function GlobalMembersPanel() {
  const [search, setSearch] = useState("");
  const [members, setMembers] = useState<Row[]>([]);
  const [detail, setDetail] = useState<Row | null>(null);
  const [offerCode, setOfferCode] = useState(globalMemberOffers[0][0]);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  const runSearch = async () => {
    setBusy("search"); setMessage("");
    try { const result = await adminApi.globalMembers(search.trim()); setMembers(result.items); if (!result.items.length) setMessage("没有找到匹配的国际版用户。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "用户搜索失败"); }
    finally { setBusy(""); }
  };
  useEffect(() => { void runSearch(); }, []);
  const openMember = async (userId: string) => {
    setBusy(`member:${userId}`); setMessage("");
    try { setDetail(await adminApi.globalMember(userId)); }
    catch (error) { setMessage(error instanceof Error ? error.message : "会员详情读取失败"); }
    finally { setBusy(""); }
  };
  const refreshDetail = async () => {
    const userId = String((detail?.identity as Row | undefined)?.user_id ?? "");
    if (userId) setDetail(await adminApi.globalMember(userId));
  };
  const grant = async () => {
    const identity = detail?.identity as Row | undefined; const userId = String(identity?.user_id ?? "");
    if (!userId || reason.trim().length < 3) { setMessage("请选择用户并填写操作原因。"); return; }
    if (!window.confirm("确认人工赠送该套餐？本操作不会创建 Creem 订单或自动续费。")) return;
    setBusy("grant"); setMessage("");
    try { await adminApi.grantGlobalMemberPlan(userId, offerCode, reason.trim(), crypto.randomUUID()); await refreshDetail(); setMessage("会员权益已赠送并记录审计日志。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "会员赠送失败"); }
    finally { setBusy(""); }
  };
  const revoke = async (entitlementId: string) => {
    const identity = detail?.identity as Row | undefined; const userId = String(identity?.user_id ?? "");
    if (!userId || reason.trim().length < 3) { setMessage("撤销前请填写操作原因。"); return; }
    if (!window.confirm("确认仅撤销这条会员权益？订单与订阅历史会保留。")) return;
    setBusy(`revoke:${entitlementId}`); setMessage("");
    try { await adminApi.revokeGlobalMemberEntitlement(userId, entitlementId, reason.trim(), crypto.randomUUID()); await refreshDetail(); setMessage("指定会员权益已撤销，其他有效权益不受影响。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "会员撤销失败"); }
    finally { setBusy(""); }
  };
  const identity = detail?.identity as Row | undefined;
  const state = detail?.state as Row | undefined;
  const usage = state?.usage as Row | undefined;
  const features = state?.features as Row | undefined;
  const entitlements = Array.isArray(detail?.entitlements) ? detail.entitlements as Row[] : [];
  const orders = Array.isArray(detail?.orders) ? detail.orders as Row[] : [];
  const subscriptions = Array.isArray(detail?.subscriptions) ? detail.subscriptions as Row[] : [];
  return <div className="global-members-admin">
    <section className="member-search"><div><p className="eyebrow">GLOBAL MEMBER SEARCH</p><h2>查找国际版用户</h2><p>支持邮箱、昵称或用户 ID；查询有分页与数量限制，不扫描面试内容。</p><p>国际版后台只管理会员套餐与会员权益；国服的积分和增加时长操作不适用于这里。</p></div><div><input aria-label="搜索国际版用户" value={search} onChange={event => setSearch(event.target.value)} onKeyDown={event => { if (event.key === "Enter") void runSearch(); }} placeholder="输入邮箱、昵称或用户 ID" /><button className="primary" disabled={busy === "search"} onClick={() => void runSearch()}>{busy === "search" ? "查询中…" : "搜索用户"}</button></div></section>
    {message ? <section className="alert" role="status">{message}</section> : null}
    <div className="member-layout"><section className="member-results"><h3>搜索结果</h3>{members.length ? members.map(member => <button key={String(member.user_id)} onClick={() => void openMember(String(member.user_id))} className={identity?.user_id === member.user_id ? "active" : ""}><strong>{display(member.email)}</strong><span>{display(member.display_name)} · {display(member.current_plan_name || "Free / 未激活")}</span><small>{member.current_ends_at_ms ? `有效至 ${display(member.current_ends_at_ms)}` : "无固定到期时间"}</small></button>) : <div className="empty">输入邮箱或用户信息开始查询</div>}</section>
      <section className="member-detail">{identity ? <><div className="member-identity"><div><p className="eyebrow">MEMBER DETAIL</p><h2>{display(identity.email)}</h2><p>{display(identity.display_name)} · 注册于 {display(identity.created_at_ms)}</p></div><span className="status-badge active">国际版账号</span></div>
        <div className="member-usage"><article><small>Copilot</small><strong>{usage?.copilotUnlimited ? "Unlimited" : `${display(usage?.copilotMinutesRemaining ?? 0)} 分钟`}</strong></article><article><small>Screen Assist</small><strong>{usage?.screenAssistUnlimited ? "Unlimited" : `${display(usage?.screenAssistUsesRemaining ?? 0)} 次`}</strong></article><article><small>资料能力</small><strong>{features?.resumeJd ? "Resume / JD" : "未包含"}</strong></article><article><small>知识库 / 笔试</small><strong>{features?.knowledgeBase || features?.writtenExam ? "已包含" : "未包含"}</strong></article></div>
        <section className="member-adjust"><div><h3>人工会员管理</h3><p>按当前套餐权益与期限赠送；不会生成支付订单，Pro Monthly 人工赠送也不会自动续费。</p></div><select aria-label="选择赠送套餐" value={offerCode} onChange={event => setOfferCode(event.target.value as typeof offerCode)}>{globalMemberOffers.map(([code, label]) => <option value={code} key={code}>{label}</option>)}</select><input aria-label="会员操作原因" value={reason} onChange={event => setReason(event.target.value)} placeholder="填写赠送或撤销原因" /><button className="primary" disabled={Boolean(busy)} onClick={() => void grant()}>{busy === "grant" ? "处理中…" : "确认赠送"}</button></section>
        <section><p className="eyebrow">ENTITLEMENTS</p><h3>会员权益记录</h3>{entitlements.length ? <div className="entitlement-list">{entitlements.map(item => <article key={String(item.id)}><div><strong>{globalMemberOffers.find(([code]) => code === item.offerCode)?.[1] ?? (item.offerCode === "global-free" ? "Free" : display(item.offerCode))}</strong><span>{display(item.status)} · {display(item.sourceKind)} · {item.endsAtMs ? `至 ${display(item.endsAtMs)}` : "长期 / 用完为止"}</span></div>{item.status === "active" && item.sourceKind !== "free_grant" ? <button disabled={Boolean(busy)} onClick={() => void revoke(String(item.id))}>{busy === `revoke:${item.id}` ? "撤销中…" : "撤销此权益"}</button> : null}</article>)}</div> : <div className="empty">暂无权益记录</div>}</section>
        <section><p className="eyebrow">ORDERS & SUBSCRIPTIONS</p><h3>订单与订阅</h3><Table rows={orders} /><Table rows={subscriptions} /></section></> : <div className="empty">从左侧搜索结果选择一名用户查看详情</div>}</section></div>
  </div>;
}

type AdminLoginMode = "phone" | "email";

export function Login({ onReady, initialMessage = "", mode = globalEdition ? "email" : "phone" }: { onReady: () => void; initialMessage?: string; mode?: AdminLoginMode }) {
  const rememberedPhone = useMemo(() => readRememberedAdminPhone(), []);
  const [phone, setPhone] = useState(rememberedPhone);
  const [email, setEmail] = useState("");
  const [rememberPhone, setRememberPhone] = useState(Boolean(rememberedPhone));
  const [challengeId, setChallengeId] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [message, setMessage] = useState(initialMessage || (mode === "email" ? "使用已授权的管理员邮箱和邮件验证码登录。" : "使用已授权的管理员手机号和短信验证码登录。"));
  const [busy, setBusy] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);
  const normalizedPhone = normalizeAdminPhone(phone);
  const phoneValid = isValidAdminPhone(normalizedPhone);
  const normalizedEmail = email.trim().toLowerCase();
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail);
  const identityValid = mode === "email" ? emailValid : phoneValid;

  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const timer = window.setInterval(() => {
      setCooldownSeconds(current => Math.max(0, current - 1));
    }, 1_000);
    return () => window.clearInterval(timer);
  }, [cooldownSeconds > 0]);

  const updatePhone = (value: string) => {
    setPhone(value);
    if (challengeId) {
      setChallengeId("");
      setVerificationCode("");
    }
    setCooldownSeconds(0);
  };

  const updateEmail = (value: string) => {
    setEmail(value);
    if (challengeId) {
      setChallengeId("");
      setVerificationCode("");
    }
    setCooldownSeconds(0);
  };

  const updateRememberPhone = (checked: boolean) => {
    setRememberPhone(checked);
    if (checked && phoneValid) saveRememberedAdminPhone(normalizedPhone);
    if (!checked) clearRememberedAdminPhone();
  };

  const send = async () => {
    if (!identityValid) {
      setMessage(mode === "email" ? "请输入有效的邮箱地址。" : "请输入有效的 11 位中国大陆手机号。");
      return;
    }
    setBusy(true);
    try {
      const result = mode === "email"
        ? await adminApi.sendEmailCode(normalizedEmail)
        : await adminApi.sendSms(normalizedPhone);
      setChallengeId(result.challengeId);
      const seconds = Math.max(0, Math.ceil(result.cooldownSeconds));
      setCooldownSeconds(seconds);
      if (mode === "phone" && rememberPhone) saveRememberedAdminPhone(normalizedPhone);
      setMessage(mode === "email" && "maskedEmail" in result
        ? `验证码已发送至 ${result.maskedEmail}，${seconds} 秒后可重新获取。`
        : `验证码已发送，${seconds} 秒后可重新获取。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : (mode === "email" ? "邮件验证码发送失败" : "短信验证码发送失败"));
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!identityValid) {
      setMessage(mode === "email" ? "请输入有效的邮箱地址。" : "请输入有效的 11 位中国大陆手机号。");
      return;
    }
    setBusy(true);
    try {
      const user = mode === "email"
        ? await adminApi.verifyEmailLogin(normalizedEmail, challengeId, verificationCode)
        : await adminApi.verifySms(normalizedPhone, challengeId, verificationCode);
      await adminApi.login(user.tokens.accessToken);
      if (mode === "phone" && rememberPhone) saveRememberedAdminPhone(normalizedPhone);
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
        {mode === "email" ? (
          <label>管理员邮箱<input value={email} onChange={event => updateEmail(event.target.value)} placeholder="请输入已授权邮箱" inputMode="email" autoComplete="email" /></label>
        ) : <>
          <label>手机号<input value={phone} onChange={event => updatePhone(event.target.value)} placeholder="请输入已授权手机号" inputMode="tel" autoComplete="tel" /></label>
          <label className="remember-phone"><input type="checkbox" checked={rememberPhone} onChange={event => updateRememberPhone(event.target.checked)} /><span>在这台浏览器记住手机号</span></label>
        </>}
        <button className="secondary" type="button" onClick={send} disabled={busy || !identityValid || cooldownSeconds > 0}>{cooldownSeconds > 0 ? `${cooldownSeconds} 秒后重新获取` : mode === "email" ? "获取邮件验证码" : "获取短信验证码"}</button>
        <label>{mode === "email" ? "邮件验证码" : "短信验证码"}<input value={verificationCode} onChange={event => setVerificationCode(event.target.value.replace(/\D/g, "").slice(0, 8))} placeholder="请输入验证码" inputMode="numeric" autoComplete="one-time-code" maxLength={8} /></label>
        <button className="primary" disabled={busy || !challengeId || verificationCode.length < 6}>进入运营中心</button>
        <p className="form-message">{message}</p>
      </form>
    </main>
  );
}

function Dashboard({ data, onAuthenticationExpired }: { data: Row; onAuthenticationExpired: (message: string) => void }) {
  const entries = Object.entries(data).filter(([key]) => key in labels);
  const [range, setRange] = useState<"7d" | "30d" | "90d">("30d");
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [trendError, setTrendError] = useState("");
  const [trendLoading, setTrendLoading] = useState(true);
  const [capacity, setCapacity] = useState<CapacityResponse | null>(null);
  const [capacityError, setCapacityError] = useState("");
  const [revenue, setRevenue] = useState<PaymentRevenueSummary | null>(null);
  const [revenueError, setRevenueError] = useState("");
  const loadTrends = async () => {
    setTrendLoading(true);
    setTrendError("");
    try {
      setTrends(await adminApi.trends(range));
    } catch (error) {
      if (isAdminAuthenticationError(error)) {
        onAuthenticationExpired(error.message);
        return;
      }
      setTrendError(error instanceof Error ? error.message : "趋势数据暂时不可用");
    } finally {
      setTrendLoading(false);
    }
  };
  useEffect(() => { void loadTrends(); }, [range]);
  useEffect(() => {
    let active = true;
    const loadCapacity = async () => {
      try {
        const response = await adminApi.capacity();
        if (active) {
          setCapacity(response);
          setCapacityError("");
        }
      } catch (error) {
        if (isAdminAuthenticationError(error)) {
          active = false;
          onAuthenticationExpired(error.message);
          return;
        }
        if (active) setCapacityError(error instanceof Error ? error.message : "容量监控暂时不可用");
      }
    };
    void loadCapacity();
    const timer = window.setInterval(() => void loadCapacity(), 15_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    let active = true;
    const loadRevenue = async () => {
      try { const response = await adminApi.paymentRevenue(); if (active) { setRevenue(response); setRevenueError(""); } }
      catch (error) {
        if (isAdminAuthenticationError(error)) {
          active = false;
          onAuthenticationExpired(error.message);
          return;
        }
        if (active) { setRevenue(null); setRevenueError(error instanceof Error ? error.message : "支付实况暂不可用"); }
      }
    };
    void loadRevenue();
    const timer = window.setInterval(() => void loadRevenue(), 15_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  return (
    <>
      <section className="revenue-section">
        <div className="trend-heading"><div><p className="eyebrow">LIVE SETTLEMENT</p><h2>今日支付实况</h2><p>按 Asia/Shanghai 自然日直接读取订单，不使用延迟聚合。</p></div><small>{revenue ? `更新于 ${new Date(revenue.generatedAtMs).toLocaleTimeString("zh-CN")}` : "正在读取"}</small></div>
        {revenueError && <div className="revenue-error">{revenueError}，请使用页面右上角“刷新”重试。</div>}
        <div className="revenue-grid">{(["paid", "pending", "anomalous", "closed"] as const).map(key => {
          const names = { paid: "实收金额", pending: "待支付", anomalous: "支付异常", closed: "已关闭" };
          return <article className={`revenue-card ${key}`} key={key}><small>{names[key]}</small><strong>{revenue ? formatCny(revenue[key].amountCents) : "—"}</strong><span>{revenue ? `${revenue[key].count} 笔` : "数据不可用"}</span></article>;
        })}</div>
      </section>
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
      <section className="capacity-section">
        <div className="trend-heading">
          <div><p className="eyebrow">LIVE CAPACITY</p><h2>实时容量监控</h2><p>最近 60 分钟 · 每 30 秒采样。关注阈值用于预警，不代表压测确认的绝对上限。</p></div>
          <div className="capacity-summary">
            <span>活跃用户 {display(capacity?.supporting.activeUsers)}</span>
            <span>请求速率 {display(capacity?.supporting.requestsPerMinute)} / min</span>
          </div>
        </div>
        {capacityError && !capacity ? <div className="trend-state error">{capacityError}</div> : capacity ? <>
          <div className="trend-health">
            <span className={capacity.metrics.some(metric => metric.level === "critical") ? "delayed" : "healthy"} />
            <strong>{capacity.metrics.some(metric => metric.level === "critical") ? "存在容量风险" : "容量采集正常"}</strong>
            <small>更新于 {new Date(capacity.generatedAtMs).toLocaleString("zh-CN")}</small>
          </div>
          <div className="capacity-grid">{capacity.metrics.map(metric => <CapacityCard metric={metric} key={metric.key} />)}</div>
          {hasRequestBreakdownData(capacity.supporting.requestBreakdown) && <RequestBreakdownPanel breakdown={capacity.supporting.requestBreakdown} />}
        </> : <div className="trend-state">正在读取实时容量...</div>}
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

function RequestBreakdownPanel({ breakdown }: { breakdown: RequestBreakdown }) {
  const summaries = Object.entries(breakdown.classes).filter((entry): entry is [keyof typeof requestClassLabels, NonNullable<typeof entry[1]>] => Boolean(entry[1]?.requestCount));
  const series = breakdown.series || [];
  return (
    <section className="request-breakdown" aria-label="请求链路诊断">
      <div className="request-breakdown-heading"><div><p className="eyebrow">REQUEST DIAGNOSTICS</p><h3>请求链路诊断</h3></div><small>仅保留最近窗口的脱敏统计</small></div>
      <div className="request-breakdown-summary">
        {summaries.map(([key, item]) => <article key={key}><span>{requestClassLabels[key]}</span><strong>{formatCapacityValue(item.p95Ms, "ms")}</strong><small>{item.requestCount} 次 · 5xx {item.errorCount} 次</small></article>)}
      </div>
      {summaries.length === 0 && breakdown.slowRoutes.length === 0 && <div className="trend-state">当前窗口暂无请求数据，产生请求后会显示分类 P95 和慢路由。</div>}
      {series.length > 0 && <div className="request-breakdown-charts">{(Object.keys(requestClassLabels) as Array<keyof typeof requestClassLabels>).map(key => <RequestClassChart key={key} label={requestClassLabels[key]} points={series.map(point => ({ date: String(point.atMs), value: point.classes[key] ?? 0, coverage: "complete" }))} />)}</div>}
      {breakdown.slowRoutes.length > 0 && <div className="slow-route-list"><div className="slow-route-title"><span>慢请求路由</span><small>按 P95 降序</small></div>{breakdown.slowRoutes.map(item => <div className="slow-route-row" key={`${item.class}:${item.route}`}><code>{item.route}</code><span>{requestClassLabels[item.class]}</span><strong>{formatCapacityValue(item.p95Ms, "ms")}</strong><small>{item.requestCount} 次 · 5xx {item.errorCount}</small></div>)}</div>}
    </section>
  );
}

function RequestClassChart({ label, points }: { label: string; points: { date: string; value: number; coverage: string }[] }) {
  const path = buildLinePath(points, 360, 120);
  const domain = chartDomain(points);
  const first = points.at(0);
  const last = points.at(-1);
  const timeLabel = (value: string | undefined) => value ? new Date(Number(value)).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "—";
  return <article className="request-breakdown-chart"><div><span>{label} P95</span><strong>{formatCapacityValue(last?.value ?? null, "ms")}</strong></div>{path && domain ? <svg viewBox="0 0 360 120" role="img" aria-label={`${label} P95 最近 60 分钟趋势`}><line className="chart-grid" x1="52" x2="350" y1="10" y2="10" /><line className="chart-grid" x1="52" x2="350" y1="50" y2="50" /><line className="chart-grid" x1="52" x2="350" y1="90" y2="90" /><line className="chart-axis" x1="52" x2="52" y1="10" y2="90" /><line className="chart-axis" x1="52" x2="350" y1="90" y2="90" /><text className="chart-label y" x="45" y="14">{formatCapacityValue(domain.maximum, "ms")}</text><text className="chart-label y" x="45" y="94">{formatCapacityValue(domain.minimum, "ms")}</text><text className="chart-label x" x="52" y="114">{timeLabel(first?.date)}</text><text className="chart-label x end" x="350" y="114">{timeLabel(last?.date)}</text><path className="chart-glow" d={path} /><path className="chart-line" d={path} /></svg> : <div className="capacity-empty">等待形成分钟曲线</div>}</article>;
}

function OrdersPanel({ rows, permissions, onChanged }: { rows: Row[]; permissions: string[]; onChanged: () => void }) {
  return <>
    <section className="orders-intro"><div><p className="eyebrow">PAYMENT DIAGNOSTICS</p><h3>订单与回调诊断</h3><p>待支付订单可执行渠道权威查单；只有订单号、金额与支付状态全部匹配后才会发放权益。</p></div><div className="diagnostic-legend"><span>签名</span><span>应用</span><span>商户</span><span>订单</span><span>金额</span></div></section>
    {rows.length ? <div className="table-wrap"><table><thead><tr><th>订单</th><th>金额</th><th>渠道 / 状态</th><th>回调结果</th><th>签名</th><th>应用</th><th>商户</th><th>订单</th><th>金额</th><th>创建时间</th></tr></thead><tbody>{rows.map(row => <tr key={String(row.order_id)}><td>{String(row.order_id)}</td><td>{formatCny(Number(row.amount_cents))}</td><td>{display(row.channel)} / {display(row.status)}</td><td>{display(row.callback_outcome)}</td>{["signature_verified", "app_identity_verified", "seller_identity_verified", "order_known", "amount_matches"].map(key => <td className={row[key] === false ? "diagnostic-failed" : row[key] === true ? "diagnostic-passed" : ""} key={key}>{diagnosticLabel(row[key])}</td>)}<td>{row.created_at_ms ? new Date(Number(row.created_at_ms)).toLocaleString("zh-CN") : "—"}</td></tr>)}</tbody></table></div> : <div className="empty">当前范围内没有订单</div>}
    <ActionPanel view="orders" rows={rows} permissions={permissions} onChanged={onChanged} />
  </>;
}

function ServerMonitor({ onAuthenticationExpired }: { onAuthenticationExpired: (message: string) => void }) {
  const [health, setHealth] = useState<ServerHealthResponse | null>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const response = await adminApi.serverHealth();
        if (active) { setHealth(response); setError(""); }
      } catch (reason) {
        if (isAdminAuthenticationError(reason)) {
          active = false;
          onAuthenticationExpired(reason.message);
          return;
        }
        if (active) setError(reason instanceof Error ? reason.message : "服务器状态暂不可用");
      }
    };
    void load(); const timer = window.setInterval(() => void load(), 15_000);
    return () => { active = false; window.clearInterval(timer); };
  }, [reloadKey]);
  if (!health) return error ? <div className="monitor-error"><span>{error}</span><button onClick={() => setReloadKey(value => value + 1)}>重新加载</button></div> : <div className="loading">正在读取服务器状态...</div>;
  return <>
    <section className="server-hero"><div><p className="eyebrow">INFRASTRUCTURE HEALTH</p><h2>服务状态：{health.overall === "healthy" ? "正常" : health.overall === "warning" ? "需关注" : "异常"}</h2><p>每 15 秒刷新，只展示只读运行指标，不暴露密钥、连接串或用户内容。</p></div><div><strong>{formatUptime(health.supporting.uptimeSeconds)}</strong><small>主机运行时长</small><span>{display(health.supporting.requestsPerMinute)} 请求/分钟</span></div></section>
    <section className="capacity-section"><div className="trend-heading"><div><p className="eyebrow">HOST RESOURCES</p><h2>主机资源</h2></div><small>更新于 {new Date(health.generatedAtMs).toLocaleString("zh-CN")}</small></div><div className="capacity-grid server-resources">{health.resources.map(metric => <CapacityCard metric={metric} key={metric.key} />)}</div>{hasRequestBreakdownData(health.supporting.requestBreakdown) && <RequestBreakdownPanel breakdown={health.supporting.requestBreakdown} />}</section>
    <section className="dependency-section"><p className="eyebrow">DEPENDENCIES</p><h2>依赖服务</h2><div className="dependency-grid">{health.dependencies.map(item => <article className={item.status} key={item.key}><span className="status-dot" /><div><strong>{item.label}</strong><p>{item.detail}</p></div><small>{item.latencyMs === null ? "—" : `${item.latencyMs} ms`}</small></article>)}</div></section>
  </>;
}

function CapacityCard({ metric }: { metric: CapacityMetric }) {
  const points = metric.points.map(point => ({ date: String(point.atMs), value: point.value, coverage: point.value === null ? "unavailable" : "complete" }));
  const path = buildLinePath(points, 360, 120);
  const domain = chartDomain(points);
  const middle = domain ? (domain.minimum + domain.maximum) / 2 : null;
  const first = metric.points.at(0);
  const last = metric.points.at(-1);
  const timeLabel = (value: number | undefined) => value ? new Date(value).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "—";
  return (
    <article className={`capacity-card ${metric.level}`}>
      <div className="capacity-card-head"><div><small>{capacityLevelLabel[metric.level]}</small><h3>{metric.label}</h3></div><strong>{formatCapacityValue(metric.value, metric.unit)}</strong></div>
      <div className="capacity-chart">
        {path && domain ? <svg viewBox="0 0 360 120" role="img" aria-label={`${metric.label}最近 60 分钟趋势`}>
          {[10, 50, 90].map(y => <line className="chart-grid" x1="52" x2="350" y1={y} y2={y} key={y} />)}
          <line className="chart-axis" x1="52" x2="52" y1="10" y2="90" />
          <line className="chart-axis" x1="52" x2="350" y1="90" y2="90" />
          <text className="chart-label y" x="45" y="14">{formatCapacityValue(domain.maximum, metric.unit)}</text>
          <text className="chart-label y" x="45" y="54">{formatCapacityValue(middle, metric.unit)}</text>
          <text className="chart-label y" x="45" y="94">{formatCapacityValue(domain.minimum, metric.unit)}</text>
          <text className="chart-label x" x="52" y="114">{timeLabel(first?.atMs)}</text>
          <text className="chart-label x end" x="350" y="114">{timeLabel(last?.atMs)}</text>
          <path className="chart-glow" d={path} />
          <path className="chart-line" d={path} />
        </svg> : <div className="capacity-empty">等待形成分钟曲线</div>}
      </div>
      <p>{metric.description}</p>
      <small className="capacity-threshold">{metric.warning === null ? "状态观测指标" : `关注 ${formatCapacityValue(metric.warning, metric.unit)} · 严重 ${formatCapacityValue(metric.critical, metric.unit)}`}</small>
    </article>
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

type PricingDraft = { productId: string; kind: string; displayName: string; priceYuan: string; points: number | null; durationDays: number | null; knowledgeIndexAllowance: number; published: boolean; catalogVersion: number };

function PricingPanel({ rows, permissions, onChanged }: { rows: Row[]; permissions: string[]; onChanged: () => void }) {
  const [drafts, setDrafts] = useState<PricingDraft[]>([]);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState("");
  const canManage = permissions.includes("catalog.manage");
  useEffect(() => { setDrafts(rows.map(row => ({
    productId: String(row.product_id), kind: String(row.kind), displayName: String(row.display_name),
    priceYuan: (Number(row.price_cents) / 100).toFixed(2),
    points: row.points == null ? null : Number(row.points), durationDays: row.duration_days == null ? null : Number(row.duration_days),
    knowledgeIndexAllowance: Number(row.knowledge_index_allowance || 0), published: Boolean(row.published), catalogVersion: Number(row.catalog_version),
  }))); }, [rows]);
  const change = (productId: string, values: Partial<PricingDraft>) => setDrafts(current => current.map(item => item.productId === productId ? { ...item, ...values } : item));
  const save = async (draft: PricingDraft) => {
    const priceCents = Math.round(Number(draft.priceYuan) * 100);
    if (!canManage || !Number.isFinite(priceCents) || priceCents < 1 || draft.displayName.trim().length < 2) { setMessage("请填写有效的商品名称和价格。"); return; }
    if (reason.trim().length < 6) { setMessage("调价前请填写至少 6 个字的变更原因。"); return; }
    if (!window.confirm(`确认将“${draft.displayName}”价格设为 ¥${draft.priceYuan}，并${draft.published ? "上架" : "下架"}？`)) return;
    setSaving(draft.productId);
    try {
      await adminApi.action(`/catalog-products/${draft.productId}`, { displayName: draft.displayName.trim(), priceCents, published: draft.published, reason: reason.trim(), confirmed: true, idempotencyKey: crypto.randomUUID() });
      setMessage("商品目录已更新，新订单将立即使用新价格；历史订单不受影响。"); onChanged();
    } catch (error) {
      const text = error instanceof Error ? error.message : "目录更新失败";
      if (text.includes("admin_step_up_required")) { adminApi.clear(); window.location.reload(); return; }
      setMessage(text);
    } finally { setSaving(""); }
  };
  return <>
    <section className="pricing-intro"><div><p className="eyebrow">SERVER CATALOG</p><h3>商品目录与价格</h3><p>权益档位由系统固定，避免误操作改变已售商品含义。这里只调整名称、价格与上下架状态。</p></div><label>本次变更原因<input value={reason} onChange={event => setReason(event.target.value)} placeholder="例如：正式版首发价格调整" /></label></section>
    <div className="pricing-grid">{drafts.map(draft => <article className={`pricing-card ${draft.published ? "published" : "unpublished"}`} key={draft.productId}>
      <div className="pricing-card-head"><span>{draft.kind === "time_pass" ? "时长会员" : "积分包"}</span><small>目录 v{draft.catalogVersion}</small></div>
      <strong>{draft.kind === "time_pass" ? `${draft.durationDays} 天` : `${draft.points?.toLocaleString("zh-CN")} 积分`}</strong>
      <p>{draft.kind === "time_pass" ? `回答与截图不限次${draft.knowledgeIndexAllowance ? ` · 含 ${draft.knowledgeIndexAllowance} 份知识材料` : ""}` : "积分长期有效，按成功结果扣除"}</p>
      <label>展示名称<input value={draft.displayName} disabled={!canManage} onChange={event => change(draft.productId, { displayName: event.target.value })} /></label>
      <label>售价（人民币元）<input type="number" min="0.01" step="0.01" value={draft.priceYuan} disabled={!canManage} onChange={event => change(draft.productId, { priceYuan: event.target.value })} /></label>
      <label className="publish-switch"><input type="checkbox" checked={draft.published} disabled={!canManage} onChange={event => change(draft.productId, { published: event.target.checked })} /><span>{draft.published ? "已上架" : "已下架"}</span></label>
      <button disabled={!canManage || saving === draft.productId} onClick={() => void save(draft)}>{saving === draft.productId ? "保存中..." : "保存商品"}</button>
    </article>)}</div><small className="pricing-message">{canManage ? message : "当前角色可查看目录，但只有财务管理员和超级管理员可以调价。"}</small>
  </>;
}

const paymentFields = {
  wechat: { public: ["mchId", "appId", "merchantSerialNo", "nativeUrl", "notifyUrl"], secret: ["merchantPrivateKey", "platformPublicKey", "apiV3Key"] },
  alipay: { public: ["appId", "sellerId", "gatewayUrl", "notifyUrl", "returnUrl"], secret: ["appPrivateKey", "alipayPublicKey"] },
} as const;
const paymentLabels: Record<string, string> = { mchId: "微信商户号", appId: "应用 ID", merchantSerialNo: "商户证书序列号", nativeUrl: "Native API 地址", notifyUrl: "异步通知地址", returnUrl: "支付返回地址", sellerId: "支付宝卖家 ID", gatewayUrl: "支付宝网关", merchantPrivateKey: "商户 API 私钥（PEM）", platformPublicKey: "微信支付平台公钥（PEM）", apiV3Key: "APIv3 密钥", appPrivateKey: "应用私钥（支持直接复制或 PEM）", alipayPublicKey: "支付宝公钥（支持直接复制或 PEM）" };

function PaymentPanel({ rows, onChanged, onAuthenticationExpired }: { rows: Row[]; onChanged: () => void; onAuthenticationExpired: (message: string) => void }) {
  const [drafts, setDrafts] = useState<Record<string, { publicConfig: Record<string, string>; secrets: Record<string, string> }>>({});
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => {
    setDrafts(Object.fromEntries(rows.map(row => [String(row.channel), { publicConfig: { ...(row.publicConfig as Record<string, string> || {}) }, secrets: {} }])));
  }, [rows]);
  const updatePublic = (channel: string, key: string, value: string) => setDrafts(current => {
    const existing = current[channel] || { publicConfig: {}, secrets: {} };
    return { ...current, [channel]: { ...existing, publicConfig: { ...existing.publicConfig, [key]: value } } };
  });
  const updateSecret = (channel: string, key: string, value: string) => setDrafts(current => {
    const existing = current[channel] || { publicConfig: {}, secrets: {} };
    return { ...current, [channel]: { ...existing, secrets: { ...existing.secrets, [key]: value } } };
  });
  const save = async (channel: "wechat" | "alipay") => {
    if (reason.trim().length < 3) { setMessage("请填写本次配置变更原因。"); return; }
    setBusy(channel);
    try {
      await adminApi.savePaymentChannel(channel, { ...drafts[channel], reason: reason.trim() });
      setMessage("配置已加密保存。出于安全考虑，修改配置后渠道会自动关闭，请校验后再开启。"); onChanged();
    } catch (error) {
      if (isAdminAuthenticationError(error)) { onAuthenticationExpired(error.message); return; }
      setMessage(error instanceof Error ? error.message : "保存失败");
    }
    finally { setBusy(""); }
  };
  const activate = async (channel: "wechat" | "alipay", enabled: boolean) => {
    if (reason.trim().length < 3 || !window.confirm(`确认${enabled ? "开启" : "关闭"}${channel === "wechat" ? "微信支付" : "支付宝"}？`)) return;
    setBusy(channel);
    try { await adminApi.action(`/payment-channels/${channel}/activation`, { enabled, confirmed: true, reason: reason.trim() }); setMessage(enabled ? "渠道已开启，新订单可以选择该方式。" : "渠道已关闭，历史订单回调仍会继续处理。"); onChanged(); }
    catch (error) {
      if (isAdminAuthenticationError(error)) { onAuthenticationExpired(error.message); return; }
      setMessage(error instanceof Error ? error.message : "操作失败");
    }
    finally { setBusy(""); }
  };
  return <>
    <section className="pricing-intro"><div><p className="eyebrow">ENCRYPTED CHANNEL CONFIG</p><h3>官方支付渠道</h3><p>微信与支付宝可独立配置和启停。私钥只允许替换，保存后不会再次显示原文。</p></div><label>本次变更原因<input value={reason} onChange={event => setReason(event.target.value)} placeholder="例如：录入正式商户配置" /></label></section>
    <div className="payment-grid">{rows.map(row => { const channel = String(row.channel) as "wechat" | "alipay"; const fields = paymentFields[channel]; const draft = drafts[channel]; const secretState = row.secretFields as Record<string, { configured: boolean }> || {}; const status = paymentChannelStatus(row); return <article className={`payment-card ${status.active ? "active" : "inactive"}`} key={channel}>
      <div className="payment-card-head"><div><span>{channel === "wechat" ? "微信支付" : "支付宝"}</span><small>配置 v{String(row.configVersion)} · 更新于 {status.updatedAtLabel}</small></div><span className={`status-badge ${status.active ? "active" : "inactive"}`}>{status.usageLabel}</span></div>
      <section className={`payment-usage ${status.active ? "active" : "inactive"}`} aria-live="polite"><span className="status-dot" /><div><strong>{status.usageLabel}</strong><p>{status.usageDescription}</p></div></section>
      <div className="payment-readiness"><div><span className={`status-badge ${status.ready ? "ready" : "draft"}`}>{status.readinessLabel}</span><p>{status.readinessDescription}</p></div><label className="payment-toggle"><span>允许用户使用</span><input type="checkbox" role="switch" aria-label={`${channel === "wechat" ? "微信支付" : "支付宝"}用户端使用开关`} checked={status.active} disabled={busy === channel || (!row.enabled && !status.ready)} onChange={event => void activate(channel, event.target.checked)} /><span className="toggle-track" aria-hidden="true"><span /></span></label></div>
      <div className="acceptance-panel"><strong>链路验收状态</strong>{(["notification", "authoritativeQuery"] as const).map(key => { const item = (row.acceptance as Record<string, Record<string, unknown> | null> | undefined)?.[key]; return <div key={key}><span>{key === "notification" ? "异步通知" : "权威查单"}</span><b className={String(item?.status || "unknown")}>{item ? (item.status === "passed" ? "通过" : "失败") : "尚未验证"}</b><small>{item?.atMs ? `${new Date(Number(item.atMs)).toLocaleString("zh-CN")} · ${paymentAcceptanceOutcomeLabel(item.outcome)}` : "完成一次真实链路后显示"}</small></div>; })}</div>
      {status.validationErrors.length > 0 ? <div className="payment-errors"><strong>需要修正</strong><ul>{status.validationErrors.map(error => <li key={error}>{error}</li>)}</ul></div> : null}
      {draft ? fields.public.map(key => <label key={key}>{paymentLabels[key]}<input value={draft.publicConfig[key] || ""} inputMode={channel === "alipay" && ["appId", "sellerId"].includes(key) ? "numeric" : undefined} placeholder={channel === "alipay" && key === "sellerId" ? "以 2088 开头的 16 位签约商户 PID" : undefined} onChange={event => updatePublic(channel, key, event.target.value)} />{channel === "alipay" && key === "sellerId" ? <small>请填写支付宝商户平台显示的签约 PID，不是应用 ID、登录账号或订单号。</small> : null}</label>) : null}
      {draft ? fields.secret.map(key => <label key={key}>{paymentLabels[key]}<textarea value={draft.secrets[key] || ""} placeholder={secretState[key]?.configured ? "已安全配置；留空保持不变" : "尚未配置"} onChange={event => updateSecret(channel, key, event.target.value)} /></label>) : null}
      <button className="payment-save" disabled={busy === channel} onClick={() => void save(channel)}>保存配置并校验</button>
      <small className="payment-save-note">保存或修改配置会自动关闭此渠道；确认状态为“配置可启用”后，再打开上方使用开关。</small>
    </article>; })}</div><small className="pricing-message">{message}</small>
  </>;
}

function GrowthPanel({ row, onChanged, onAuthenticationExpired }: { row: Row | undefined; onChanged: () => void; onAuthenticationExpired: (message: string) => void }) {
  const [enabled, setEnabled] = useState(Boolean(row?.enabled));
  const [rewardPoints, setRewardPoints] = useState(String(row?.rewardPoints ?? 500));
  const [inviteeRewardPoints, setInviteeRewardPoints] = useState(String(row?.inviteeRewardPoints ?? 500));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    setEnabled(Boolean(row?.enabled));
    setRewardPoints(String(row?.rewardPoints ?? 500));
    setInviteeRewardPoints(String(row?.inviteeRewardPoints ?? 500));
  }, [row?.enabled, row?.rewardPoints, row?.inviteeRewardPoints]);
  const save = async () => {
    const points = Number(rewardPoints);
    const inviteePoints = Number(inviteeRewardPoints);
    const validation = validateGrowthSettings(rewardPoints, inviteeRewardPoints, reason);
    if (!validation.valid) { setMessage(validation.message); return; }
    setBusy(true); setMessage("");
    try {
      const result = await adminApi.saveGrowthReferralSettings({ enabled, rewardPoints: points, inviteeRewardPoints: inviteePoints, confirmed: true, reason: reason.trim() });
      setMessage(result.enabled ? `邀请奖励已开启：分享者 ${result.inviterRewardPoints} 点，新用户 ${result.inviteeRewardPoints} 点。` : "邀请奖励已关闭，历史关系和已发积分不会撤销。");
      setReason("");
      onChanged();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "保存失败";
      setMessage(errorMessage);
      if (isAdminAuthenticationError(error)) onAuthenticationExpired(errorMessage);
    } finally { setBusy(false); }
  };
  return <section className="growth-settings-card"><div className="growth-settings-head"><div><p className="eyebrow">REFERRAL PROGRAM</p><h3>邀请拉新奖励</h3><p>新用户仅可在注册后 3 天内激活好友链接；成功后分享者与新用户分别获得积分。每个账号只能激活一次，禁止自邀。</p></div><span className={`status-badge ${enabled ? "active" : "inactive"}`}>{enabled ? "当前已启用" : "当前已关闭"}</span></div><div className="growth-setting-grid"><label><span>允许新邀请激活</span><small>固定注册后 3 天内可激活；关闭后仅停止新的激活和奖励</small><input type="checkbox" role="switch" aria-label="允许新邀请激活" checked={enabled} onChange={event => setEnabled(event.target.checked)} /></label><label><span>分享者奖励</span><small>好友在有效期内激活后发放</small><div className="points-input"><input aria-label="分享者奖励积分" type="number" min="1" max="100000" step="1" value={rewardPoints} onChange={event => setRewardPoints(event.target.value)} /><b>积分</b></div></label><label><span>新用户奖励</span><small>新用户成功激活后同步发放</small><div className="points-input"><input aria-label="新用户奖励积分" type="number" min="1" max="100000" step="1" value={inviteeRewardPoints} onChange={event => setInviteeRewardPoints(event.target.value)} /><b>积分</b></div></label></div><label className="growth-reason">配置变更原因<input value={reason} onChange={event => setReason(event.target.value)} placeholder="例如：上线双向邀请奖励" /></label><div className="growth-settings-footer"><div><strong>配置版本 v{String(row?.configVersion ?? 1)}</strong><small>{Number(row?.updatedAtMs) > 0 ? `最近更新：${new Date(Number(row?.updatedAtMs)).toLocaleString("zh-CN")}` : "尚未进行运营配置"}</small></div><button className="primary" disabled={busy} onClick={() => void save()}>{busy ? "保存中…" : "保存并立即生效"}</button></div>{message ? <div className="form-message" role="status">{message}</div> : null}</section>;
}

function BaiduRankingPanel({ data, onChanged }: { data: Row; onChanged: () => void }) {
  const [reason, setReason] = useState("查看百度关键词排名");
  const [keyword, setKeyword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const items = Array.isArray(data.items) ? data.items as Row[] : [];
  const refresh = async () => { if (reason.trim().length < 3) { setMessage("请填写刷新原因。"); return; } setBusy(true); try { await adminApi.refreshBaiduRanking(reason.trim()); setMessage("排名已刷新。"); onChanged(); } catch (error) { setMessage(error instanceof Error ? error.message : "刷新失败"); } finally { setBusy(false); } };
  const add = async () => { if (!keyword.trim() || reason.trim().length < 3) { setMessage("请输入关键词并填写原因。"); return; } setBusy(true); try { await adminApi.addBaiduKeyword(keyword.trim(), reason.trim()); setKeyword(""); setMessage("关键词已添加。"); onChanged(); } catch (error) { setMessage(error instanceof Error ? error.message : "添加失败"); } finally { setBusy(false); } };
  return <div className="seo-ranking"><section className="signal-panel"><div><p className="eyebrow">BAIDU PC RANKING</p><h2>{display(data.domain)}</h2><span>每日同步一次 · 最近同步 {display(data.lastSyncAtMs)}</span></div><button className="primary" disabled={busy} onClick={() => void refresh()}>{busy ? "处理中…" : "立即刷新"}</button></section><section className="panel"><div className="page-actions"><input aria-label="新增关键词" placeholder="新增关键词" value={keyword} onChange={event => setKeyword(event.target.value)} /><input aria-label="排名操作原因" value={reason} onChange={event => setReason(event.target.value)} /><button className="secondary" disabled={busy} onClick={() => void add()}>添加关键词</button></div>{message ? <div className="form-message" role="status">{message}</div> : null}</section>{items.map(item => { const latest = item.latest as Row | undefined; const results = Array.isArray(latest?.results_json) ? latest.results_json as Row[] : []; return <section className="panel" key={String(item.keyword_id)}><div className="payment-card-head"><div><h3>{display(item.keyword)}</h3><small>{item.status === "active" ? "监控中" : "已停用"} · 观察日 {display(latest?.observed_date)}</small></div><strong>{latest?.status === "ranked" ? `第 ${display(latest.top_rank)} 名` : latest?.status === "not_found" ? "未进入前 50" : display(latest?.status || "尚未同步")}</strong></div>{results.length ? <div className="table-wrap"><table><thead><tr><th>排名</th><th>标题</th><th>链接</th></tr></thead><tbody>{results.slice(0, 50).map((result, index) => <tr key={`${String(result.url)}-${index}`}><td>{display(result.rank)}</td><td>{display(result.title)}</td><td>{display(result.url)}</td></tr>)}</tbody></table></div> : <div className="empty">暂无今日结果</div>}</section>; })}</div>;
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
  const [loginMessage, setLoginMessage] = useState("");
  const [offset, setOffset] = useState(0);
  const loadSequence = useRef(0);
  const sessionRequest = useRef<ReturnType<typeof adminApi.session> | null>(null);

  const requireNewAdminLogin = (message: string) => {
    adminApi.clear();
    sessionRequest.current = null;
    setLoginMessage(message);
    setAuthenticated(false);
  };

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
      if (!targetView || !session.permissions.includes(targetView.permission)) {
        const fallback = views.find(item => session.permissions.includes(item.permission));
        if (!fallback) throw new Error("当前管理员角色没有可访问的后台页面");
        if (fallback.id !== target) setView(fallback.id);
        return;
      }
      if (target === "dashboard") {
        const nextDashboard = await adminApi.dashboard();
        if (sequence === loadSequence.current) setDashboardData(nextDashboard);
      } else if (target === "growth") {
        const settings = await adminApi.growthReferralSettings();
        if (sequence === loadSequence.current) setRows([settings]);
      } else if (target === "globalCommerce") {
        const [overview, operations] = await Promise.all([adminApi.globalCommerceOverview(), adminApi.globalCommerceOperations()]);
        if (sequence === loadSequence.current) setRows([{ ...overview, operations }]);
      } else if (target === "globalMembers") {
        if (sequence === loadSequence.current) setRows([]);
      } else if (target === "seo") {
        const result = await adminApi.baiduRanking();
        if (sequence === loadSequence.current) setRows([result]);
      } else if (target !== "server" && target !== "promotion") {
        const resource = target === "redemptions" ? "redemption-batches" : target === "pricing" ? "catalog-products" : target === "payments" ? "payment-channels" : target;
        const nextRows = (await adminApi.list(resource, offset)).items;
        if (sequence === loadSequence.current) setRows(Array.isArray(nextRows) ? nextRows : []);
      }
    } catch (reason) {
      if (sequence !== loadSequence.current) return;
      const message = reason instanceof Error ? reason.message : "后台服务暂时不可用";
      setError(message);
      if (isAdminAuthenticationError(reason) || /session|required|401|invalid/i.test(message)) requireNewAdminLogin(message);
    } finally {
      if (sequence === loadSequence.current && !background) setLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) void load(view);
  }, [authenticated, view, offset]);

  if (!authenticated) return <Login initialMessage={loginMessage} onReady={() => { setLoginMessage(""); setAuthenticated(true); }} />;
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
        {loading ? <div className="loading">正在读取生产运营数据...</div> : view === "dashboard" ? <Dashboard data={dashboardData} onAuthenticationExpired={requireNewAdminLogin} /> : view === "server" ? <ServerMonitor onAuthenticationExpired={requireNewAdminLogin} /> : view === "seo" ? <BaiduRankingPanel data={rows[0] || {}} onChanged={() => void load(view, true)} /> : view === "promotion" ? <PromotionCenter permissions={permissions} onAuthenticationExpired={requireNewAdminLogin} /> : view === "globalMembers" ? <GlobalMembersPanel /> : view === "globalCommerce" ? <GlobalCommercePanel row={rows[0]} onChanged={() => void load(view, true)} /> : view === "admins" ? <AdminPanel rows={rows} permissions={permissions} onChanged={() => void load(view, true)} /> : view === "redemptions" ? <RedemptionPanel rows={rows} permissions={permissions} onChanged={() => void load(view, true)} /> : view === "pricing" ? <PricingPanel rows={rows} permissions={permissions} onChanged={() => void load(view, true)} /> : view === "payments" ? <PaymentPanel rows={rows} onChanged={() => void load(view, true)} onAuthenticationExpired={requireNewAdminLogin} /> : view === "growth" ? <GrowthPanel row={rows[0]} onChanged={() => void load(view, true)} onAuthenticationExpired={requireNewAdminLogin} /> : view === "orders" ? <OrdersPanel rows={rows} permissions={permissions} onChanged={() => void load(view, true)} /> : <>
          <Table rows={rows} />
          <div className="pagination"><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 50))}>上一页</button><span>第 {offset / 50 + 1} 页</span><button disabled={rows.length < 50} onClick={() => setOffset(value => value + 50)}>下一页</button></div>
          <ActionPanel view={view} rows={rows} permissions={permissions} onChanged={() => void load(view, true)} />
        </>}
      </main>
    </div>
  );
}
