import { useEffect, useRef, useState, type Dispatch, type FormEvent, type SetStateAction } from "react";
import type { BillingProduct, OfficialCheckoutOrder, PointsRedemptionResult } from "@offersteady/protocol";
import { Link } from "react-router-dom";
import type { WebAppState } from "./domain";
import { assetUrl } from "./assets";
import { routes } from "./routes";
import { interviewAppAdapter } from "./app-adapter";
import { runAdapterOperation } from "./api-client";

interface Props { readonly state: WebAppState; readonly setState: Dispatch<SetStateAction<WebAppState>> }
const money = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
const officialStatus: Record<OfficialCheckoutOrder["status"], string> = { created: "订单已创建", payment_pending: "等待官方支付确认", paid: "支付成功", failed: "支付失败", closed: "订单已关闭", refund_pending: "退款处理中", refunded: "已退款" };

export function BillingPage({ state, setState }: Props) {
  const [product, setProduct] = useState<BillingProduct | null>(null); const [checkout, setCheckout] = useState<OfficialCheckoutOrder | null>(null); const [notice, setNotice] = useState("");
  const [checkoutPending, setCheckoutPending] = useState(false);
  const [redemptionCode, setRedemptionCode] = useState(""); const [redemptionPending, setRedemptionPending] = useState(false); const [redemptionResult, setRedemptionResult] = useState<PointsRedemptionResult | null>(null); const redemptionController = useRef<AbortController | null>(null);
  useEffect(() => () => { redemptionController.current?.abort(); }, []);
  useEffect(() => {
    if (!checkout || checkout.status !== "payment_pending") return undefined;
    const controller = new AbortController();
    const timer = window.setInterval(() => {
      void runAdapterOperation(signal => interviewAppAdapter.getCheckoutOrder(checkout.id, signal), controller.signal).then(order => {
        setCheckout(order);
        setState(current => ({ ...current, billing: { ...current.billing, officialOrders: current.billing.officialOrders.some(item => item.id === order.id) ? current.billing.officialOrders.map(item => item.id === order.id ? order : item) : [order, ...current.billing.officialOrders] } }));
        if (order.status === "paid") setNotice("支付已由服务端验签确认，权益已到账");
      }).catch(() => undefined);
    }, 3000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [checkout, setState]);
  const redeem = async (event: FormEvent) => {
    event.preventDefault(); if (!redemptionCode.replace(/[\s-]/g, "") || redemptionPending) return;
    setRedemptionPending(true); setRedemptionResult(null); const controller = new AbortController(); redemptionController.current = controller;
    try {
      const idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `redeem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const result = await runAdapterOperation(signal => interviewAppAdapter.redeemPoints({ code: redemptionCode, idempotencyKey }, signal), controller.signal);
      setRedemptionResult(result);
      if (result.outcome === "redeemed" || result.outcome === "already-redeemed-by-you") {
        const data = result.data; setRedemptionCode("");
        setState(current => ({ ...current, billing: { ...current.billing, balance: data.newBalance, ledger: current.billing.ledger.some(entry => entry.kind === "redemption_credit" && entry.referenceId === data.redemptionId) ? current.billing.ledger : [data.ledgerEntry, ...current.billing.ledger] } }));
      }
    } catch { if (!controller.signal.aborted) setRedemptionResult({ outcome: "temporarily-unavailable" }); }
    finally { if (!controller.signal.aborted) setRedemptionPending(false); }
  };
  const startCheckout = async (selectedProduct: BillingProduct) => {
    if (checkoutPending) return;
    setProduct(selectedProduct);
    setCheckout(null);
    setCheckoutPending(true);
    try {
      const idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const order = await runAdapterOperation(signal => interviewAppAdapter.createCheckoutOrder({ productId: selectedProduct.id, channel: "alipay", idempotencyKey }, signal));
      setCheckout(order);
      setState(current => ({ ...current, billing: { ...current.billing, officialOrders: current.billing.officialOrders.some(item => item.id === order.id) ? current.billing.officialOrders.map(item => item.id === order.id ? order : item) : [order, ...current.billing.officialOrders] } }));
      const paymentUrl = order.action.kind === "redirect" ? order.action.url : order.action.value;
      window.open(paymentUrl, "_blank", "noopener,noreferrer");
      setNotice("码支付订单已创建，已为你打开支付页面；到账以服务端验签通知为准。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "创建支付订单失败，请稍后重试");
    } finally {
      setCheckoutPending(false);
    }
  };
  const passes = state.billing.catalog.filter(item => item.kind === "time_pass" && item.published); const points = state.billing.catalog.filter(item => item.kind === "points_pack" && item.published);
  const knowledgeIndexPointsPer5000Tokens = state.billing.rates.knowledgeIndexPointsPer1000Tokens * 5;
  const cards = (items: readonly BillingProduct[]) => <div className="price-grid">{items.map(item => <article key={item.id} className="price-card"><span>{item.kind === "time_pass" ? "回答与截图不限次" : `¥${(item.priceCents / 100 / (item.points ?? 1)).toFixed(3)}/点`}</span><h3>{item.displayName}</h3><strong>{money(item.priceCents)}</strong><small>{item.kind === "time_pass" ? `约 ¥${(item.priceCents / 100 / (item.durationDays ?? 1)).toFixed(2)}/天${item.knowledgeIndexAllowance ? ` · 含 ${item.knowledgeIndexAllowance} 份知识材料` : " · 知识材料按点"}` : `预计可回答 ${Math.floor((item.points ?? 0) / state.billing.rates.answerPoints)} 次`}</small><button className="button primary" onClick={() => void startCheckout(item)} disabled={checkoutPending}>{checkoutPending && product?.id === item.id ? "跳转中…" : "购买"}</button></article>)}</div>;
  const allowance = state.billing.activePass ? Math.max(0, state.billing.activePass.knowledgeAllowanceGranted - state.billing.activePass.knowledgeAllowanceUsed - state.billing.activePass.knowledgeAllowanceLocked) : 0;
  return <main className="app-page billing-page"><header className="billing-hero"><div><span className="kicker">PRICING & POINTS · 目录 v{state.billing.rates.catalogVersion}</span><h1>按你的面试节奏付费</h1><p>新用户赠送 200 点体验额度。低频按点，高频选择按天会员；支付由微信和支付宝官方订单完成。</p></div><div className="balance-card"><small>{state.billing.activePass ? "会员有效期内回答与截图不限次" : "当前可用"}</small><strong>{state.billing.balance} 点</strong><span>回答 {state.billing.rates.answerPoints} 点 · 截图 {state.billing.rates.screenshotAnswerPoints} 点 · 知识材料 {state.billing.rates.knowledgeIndexMinimumPoints} 点起</span>{state.billing.activePass ? <span>知识材料额度 {allowance}/{state.billing.activePass.knowledgeAllowanceGranted} · {new Date(state.billing.activePass.endsAtMs).toLocaleDateString("zh-CN")} 到期</span> : null}</div></header>{notice ? <div className="billing-notice" role="status">{notice}</div> : null}
    <section className="panel redemption-card" aria-labelledby="redemption-title"><div><span className="kicker">POINTS CODE</span><h2 id="redemption-title">兑换积分</h2><p>兑换成功后，积分直接进入当前账号。兑换码属于一次性凭证，请勿转发给他人。</p></div><form onSubmit={event => void redeem(event)}><label htmlFor="points-redemption-code">积分兑换码</label><div className="redemption-controls"><input id="points-redemption-code" value={redemptionCode} onChange={event => setRedemptionCode(event.target.value)} disabled={redemptionPending} autoComplete="off" autoCapitalize="characters" spellCheck={false} placeholder="4 组，每组 4 位" aria-describedby="redemption-format redemption-status" /><button className="button primary" disabled={redemptionPending || !redemptionCode.replace(/[\s-]/g, "")} type="submit">{redemptionPending ? "兑换中…" : "立即兑换"}</button></div><small id="redemption-format">输入 16 位兑换码，可包含空格或连字符。原型演示可输入 SYNTHETIC-DEMO。</small><div id="redemption-status" className={`redemption-status ${redemptionResult?.outcome ?? "idle"}`} role="status" aria-live="polite">{redemptionPending ? "正在安全校验兑换码，当前余额不会提前变化。" : redemptionResult?.outcome === "redeemed" ? `兑换成功：+${redemptionResult.data.points} 点，当前余额 ${redemptionResult.data.newBalance} 点 · ${redemptionResult.data.publicHint} · ${new Date(redemptionResult.data.redeemedAtMs).toLocaleString("zh-CN")}` : redemptionResult?.outcome === "already-redeemed-by-you" ? `这枚兑换码已兑换至当前账号，余额 ${redemptionResult.data.newBalance} 点。` : redemptionResult?.outcome === "code-unavailable" ? "兑换码不可用，请检查输入；仍有问题可联系售后客服。" : redemptionResult?.outcome === "rate-limited" ? `尝试次数较多，请约 ${Math.ceil(redemptionResult.retryAfterMs / 1000)} 秒后重试。` : redemptionResult?.outcome === "temporarily-unavailable" ? "服务暂时不可用，请保留当前输入并稍后重试。" : "输入兑换码后即可兑换；兑换点数由服务端确认。"}</div></form></section>
    {state.billing.queuedPasses.length ? <section className="panel queued-entitlements"><div className="panel-heading"><h2>待生效会员</h2><span>{state.billing.queuedPasses.length} 个</span></div>{state.billing.queuedPasses.map(item => <p key={item.id}><strong>{new Date(item.startsAtMs).toLocaleString("zh-CN")} 生效</strong>，至 {new Date(item.endsAtMs).toLocaleString("zh-CN")}；含 {item.knowledgeAllowanceGranted} 份知识材料额度。</p>)}</section> : null}<section className="billing-section"><div className="panel-heading"><h2>按天会员</h2><span>15 天与 30 天会员含 2 份知识材料额度</span></div>{cards(passes)}</section><section className="billing-section"><div className="panel-heading"><h2>积分包</h2><span>积分长期有效，按成功结果扣除</span></div>{cards(points)}</section><section className="panel consumption-panel"><div className="panel-heading"><h2>点数消费说明</h2><Link to={`${routes.guide}#billing`}>查看支付说明</Link></div><div className="consumption-grid"><article><b>{state.billing.rates.answerPoints} 点</b><strong>普通回答</strong><p>成功生成可用回答后结算；会员期内为 0 点。</p></article><article><b>{state.billing.rates.screenshotAnswerPoints} 点</b><strong>截图回答</strong><p>识别失败或取消会释放预留积分。</p></article><article><b>{state.billing.rates.knowledgeIndexMinimumPoints} 点起</b><strong>知识材料索引</strong><p>每 5,000 Token {knowledgeIndexPointsPer5000Tokens} 点，最低 {state.billing.rates.knowledgeIndexMinimumPoints} 点；15/30 天会员含 2 份。</p></article></div></section><section className="panel points-history"><div className="panel-heading"><h2>积分明细</h2><span>{state.billing.ledger.length} 条</span></div><div className="order-list">{state.billing.ledger.map(entry => <article key={entry.id}><div><strong>{entry.description}</strong><small>{new Date(entry.createdAtMs).toLocaleString("zh-CN")}{entry.kind === "redemption_credit" ? ` · ${entry.description.match(/••••-[0-9A-Z]+/)?.[0] ?? "兑换积分"}` : ""}</small></div><span className={entry.points >= 0 ? "success-text" : ""}>{entry.points >= 0 ? "+" : ""}{entry.points} 点</span></article>)}</div></section><div className="billing-bottom"><section className="panel"><h2>官方支付与售后</h2><ul className="billing-rules"><li>每笔支付由服务端创建微信或支付宝官方订单。</li><li>浏览器返回不代表到账，必须等待服务端验签通知或主动查单。</li><li>无需填写交易单号，也无需上传付款截图。</li></ul><div className="support-card"><img src={assetUrl("support.customer-service")} alt="客服微信二维码合成占位图" /><div><strong>{state.billing.support.wechatId}</strong><small>{state.billing.support.serviceHours}</small><button onClick={() => { void navigator.clipboard?.writeText(state.billing.support.wechatId); setNotice("客服微信号已复制"); }}>复制微信号</button></div></div></section><section className="panel"><div className="panel-heading"><h2>官方订单</h2><span>{state.billing.officialOrders.length} 笔</span></div>{state.billing.officialOrders.length ? <div className="order-list">{state.billing.officialOrders.map(order => <article key={order.id}><div><strong>{order.product.displayName}</strong><small>{order.id} · {order.channel === "wechat" ? "微信支付" : "支付宝"}</small></div><span>{officialStatus[order.status]}</span></article>)}</div> : <p className="muted-copy">还没有官方支付订单。</p>}</section></div>
    {product ? <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="official-checkout-title"><section className="sheet checkout-sheet"><button className="sheet-close" aria-label="关闭支付" onClick={() => setProduct(null)}>×</button><h2 id="official-checkout-title">购买 {product.displayName}</h2><p>订单金额由服务端目录确认：<strong>{money(product.priceCents)}</strong></p>{checkoutPending && !checkout ? <div className="payment-waiting"><i className="online-dot" /><span>正在创建码支付订单并跳转支付页面…</span></div> : null}{checkout ? <><div className="official-order-meta"><span>订单号</span><strong>{checkout.id}</strong><span>金额</span><strong>{money(checkout.amountCents)}</strong><span>状态</span><strong>{officialStatus[checkout.status]}</strong></div>{checkout.status === "payment_pending" ? checkout.action.kind === "dynamic_qr" ? <div className="dynamic-payment-qr"><span>订单专属动态支付二维码</span><small>5 分钟内有效 · 不属于静态图片资产</small></div> : <a className="button primary full" href={checkout.action.url} target="_blank" rel="noreferrer">打开码支付收银台</a> : null}{checkout.status === "payment_pending" ? <div className="payment-waiting"><i className="online-dot" /><span>正在等待服务端验签通知，请勿重复付款</span></div> : null}</> : null}</section></div> : null}
  </main>;
}
