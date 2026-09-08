import { CheckCircleIcon, CreditCardIcon, ShieldCheckIcon, SparkleIcon } from "@phosphor-icons/react";
import type { GlobalPlanVersion } from "@offersteady/protocol";
import { useEffect, useState } from "react";

import { authClient } from "./auth-client";
import { createJsonClient } from "./api-client";
import type { WebAppState } from "./domain";
import { readRuntimeConfig } from "./runtime-config";

interface Props { readonly state: WebAppState }
interface AccountCommerceState {
  readonly entitlement: { readonly offerCode: string; readonly endsAtMs: number | null } | null;
  readonly usage: { readonly copilotMinutesRemaining: number | null; readonly screenAssistUsesRemaining: number | null; readonly copilotUnlimited: boolean; readonly screenAssistUnlimited: boolean };
  readonly orders: readonly { readonly id: string; readonly offerCode: string; readonly status: string; readonly amountCents: number; readonly createdAtMs: number }[];
  readonly subscription: { readonly status: "active" | "canceling" | "canceled" | "paused" | "expired"; readonly currentPeriodEndMs: number; readonly canceledAtMs?: number | null } | null;
}

const fallbackPlans: readonly GlobalPlanVersion[] = [
  { offerCode: "global-free", version: 1, displayName: "Free", description: "Try the live interview copilot before you buy.", currency: "USD", priceCents: 0, billingMode: "free", durationDays: null, benefits: { copilotMinutes: 15, screenAssistUses: 3, resumeAndJobDescription: false, knowledgeBase: false, writtenExam: false, fullProduct: false }, published: true, featured: false, displayOrder: 0, createdAtMs: 0 },
  { offerCode: "global-interview-pass", version: 2, displayName: "Interview Day Pass", description: "Focused access for your interview day.", currency: "USD", priceCents: 999, billingMode: "one_time", durationDays: 1, benefits: { copilotMinutes: 180, screenAssistUses: null, resumeAndJobDescription: true, knowledgeBase: false, writtenExam: true, fullProduct: false }, published: true, featured: false, displayOrder: 1, createdAtMs: 0 },
  { offerCode: "global-pro-weekly", version: 2, displayName: "Pro Weekly", description: "Unlimited full-product access for interview week.", currency: "USD", priceCents: 4999, billingMode: "one_time", durationDays: 7, benefits: { copilotMinutes: null, screenAssistUses: null, resumeAndJobDescription: true, knowledgeBase: true, writtenExam: true, fullProduct: true }, published: true, featured: true, displayOrder: 2, createdAtMs: 0 },
  { offerCode: "global-pro-monthly", version: 2, displayName: "Pro Monthly", description: "Unlimited access throughout your job search.", currency: "USD", priceCents: 9999, billingMode: "recurring", durationDays: 30, benefits: { copilotMinutes: null, screenAssistUses: null, resumeAndJobDescription: true, knowledgeBase: true, writtenExam: true, fullProduct: true }, published: true, featured: false, displayOrder: 3, createdAtMs: 0 },
  { offerCode: "global-job-hunt", version: 2, displayName: "Job Hunt", description: "Unlimited access for a focused three-month search.", currency: "USD", priceCents: 19999, billingMode: "one_time", durationDays: 90, benefits: { copilotMinutes: null, screenAssistUses: null, resumeAndJobDescription: true, knowledgeBase: true, writtenExam: true, fullProduct: true }, published: true, featured: false, displayOrder: 4, createdAtMs: 0 },
];

const money = (cents: number) => cents === 0 ? "$0" : `$${(cents / 100).toFixed(2)}`;
const pendingOrderKey = "offersteady.global.checkout.pending_order";
const term = (plan: GlobalPlanVersion) => plan.billingMode === "recurring" ? "/ month" : plan.durationDays === 1 ? "/ 24 hours" : plan.durationDays ? `/ ${plan.durationDays} days` : "forever";
const benefits = (plan: GlobalPlanVersion) => {
  const items = [
    plan.benefits.copilotMinutes == null ? "Unlimited live Copilot" : `${plan.benefits.copilotMinutes} live Copilot minutes`,
    plan.benefits.screenAssistUses == null ? "Unlimited Screen Assist" : `${plan.benefits.screenAssistUses} Screen Assist uses`,
  ];
  if (plan.benefits.resumeAndJobDescription) items.push("Resume and job-description context");
  if (plan.benefits.knowledgeBase) items.push("Knowledge base");
  if (plan.benefits.writtenExam) items.push("Written-exam mode");
  return items;
};

export function BillingPage({ state: _state }: Props) {
  const runtime = readRuntimeConfig(import.meta.env);
  const [plans, setPlans] = useState<readonly GlobalPlanVersion[]>(fallbackPlans);
  const [catalogueStatus, setCatalogueStatus] = useState<"loading" | "ready" | "fallback">("loading");
  const [checkoutMessage, setCheckoutMessage] = useState("");
  const [checkoutBusy, setCheckoutBusy] = useState<string | null>(null);
  const [account, setAccount] = useState<AccountCommerceState | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const client = createJsonClient({ baseUrl: runtime.apiBaseUrl });
    void client.request<{ plans: readonly GlobalPlanVersion[] }>("/api/v1/global-commerce/catalogue", undefined, controller.signal)
      .then(result => { setPlans(result.plans); setCatalogueStatus("ready"); })
      .catch(() => setCatalogueStatus("fallback"));
    return () => controller.abort();
  }, [runtime.apiBaseUrl]);

  useEffect(() => {
    const orderId = window.localStorage.getItem(pendingOrderKey);
    const session = authClient.readStoredSession();
    if (!orderId || !session) return;
    let stopped = false;
    let attempt = 0;
    let timer = 0;
    const poll = async () => {
      attempt += 1;
      try {
        const client = createJsonClient({ baseUrl: runtime.apiBaseUrl });
        const order = await client.request<{ status: string }>(`/api/v1/global-commerce/orders/${encodeURIComponent(orderId)}`, { headers: { Authorization: `Bearer ${session.accessToken}` } });
        if (stopped) return;
        if (order.status === "paid") { window.localStorage.removeItem(pendingOrderKey); setCheckoutMessage("Payment confirmed. Your access is now active."); return; }
        if (["failed", "expired", "refunded", "disputed"].includes(order.status)) { window.localStorage.removeItem(pendingOrderKey); setCheckoutMessage("This payment was not completed. No new entitlement was granted."); return; }
      } catch { /* Retry only within the bounded return window. */ }
      if (!stopped && attempt < 12) timer = window.setTimeout(() => void poll(), 1_500);
      else if (!stopped) setCheckoutMessage("Payment confirmation is taking longer than expected. Your order is safe; contact support if it does not update shortly.");
    };
    void poll();
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [runtime.apiBaseUrl]);

  useEffect(() => {
    const session = authClient.readStoredSession();
    if (!session) return;
    const controller = new AbortController();
    const client = createJsonClient({ baseUrl: runtime.apiBaseUrl });
    void client.request<AccountCommerceState>("/api/v1/global-commerce/state", { headers: { Authorization: `Bearer ${session.accessToken}` } }, controller.signal).then(setAccount).catch(() => undefined);
    return () => controller.abort();
  }, [runtime.apiBaseUrl]);

  const beginCheckout = async (plan: GlobalPlanVersion) => {
    if (plan.offerCode === "global-free") {
      setCheckoutMessage("Your one-time Free allowance is added automatically after verified email sign-in.");
      return;
    }
    if (!authClient.readStoredSession()) {
      setCheckoutMessage("Sign in with your verified email before choosing a paid plan.");
      return;
    }
    if (!runtime.commerceEnabled || runtime.commerceProvider !== "creem") {
      setCheckoutMessage("Secure checkout is being prepared. Your current access is unchanged.");
      return;
    }
    if (checkoutBusy) return;
    const session = authClient.readStoredSession();
    if (!session) return;
    setCheckoutBusy(plan.offerCode);
    setCheckoutMessage("");
    try {
      const client = createJsonClient({ baseUrl: runtime.apiBaseUrl });
      const result = await client.request<{ id: string; checkoutUrl?: string; status: string }>("/api/v1/global-commerce/checkout", {
        method: "POST",
        headers: { Authorization: `Bearer ${session.accessToken}` },
        body: JSON.stringify({ offerCode: plan.offerCode, idempotencyKey: crypto.randomUUID() }),
      });
      if (!result.checkoutUrl) throw new Error("Checkout URL was not returned.");
      const target = new URL(result.checkoutUrl);
      if (target.protocol !== "https:") throw new Error("Checkout URL is not secure.");
      window.localStorage.setItem(pendingOrderKey, result.id);
      window.location.assign(target.toString());
    } catch (error) {
      setCheckoutMessage(error instanceof Error ? error.message : "Secure checkout could not be opened. Please try again.");
    } finally {
      setCheckoutBusy(null);
    }
  };

  const openBillingPortal = async () => {
    const session = authClient.readStoredSession();
    if (!session || checkoutBusy) return;
    setCheckoutBusy("portal"); setCheckoutMessage("");
    try {
      const client = createJsonClient({ baseUrl: runtime.apiBaseUrl });
      const result = await client.request<{ portalUrl: string }>("/api/v1/global-commerce/customer-portal", { method: "POST", headers: { Authorization: `Bearer ${session.accessToken}` } });
      const target = new URL(result.portalUrl);
      if (target.protocol !== "https:") throw new Error("Billing portal URL is not secure.");
      window.location.assign(target.toString());
    } catch (error) { setCheckoutMessage(error instanceof Error ? error.message : "Billing management is temporarily unavailable."); }
    finally { setCheckoutBusy(null); }
  };

  return <main className="app-page global-billing-page">
    <header className="global-pricing-hero"><span className="kicker">PLANS &amp; BILLING</span><h1>Choose access that matches your interview schedule.</h1><p>Start free without a card. Short passes are one-time purchases; only Pro Monthly renews automatically.</p></header>
    {account ? <section className="global-current-access panel"><div><span className="kicker">CURRENT ACCESS</span><h2>{account.entitlement?.offerCode ?? "Free"}</h2><p>{account.entitlement?.endsAtMs ? `Access through ${new Date(account.entitlement.endsAtMs).toLocaleDateString("en-US")}` : "Your one-time Free allowance stays available until used."}</p>{account.subscription ? <p className="global-subscription-state">Subscription: {account.subscription.status}{account.subscription.status === "canceling" || account.subscription.status === "canceled" ? ` · access through ${new Date(account.subscription.currentPeriodEndMs).toLocaleDateString("en-US")}` : ""}</p> : null}{account.entitlement?.offerCode === "global-pro-monthly" ? <button className="text-link" type="button" disabled={checkoutBusy !== null} onClick={() => void openBillingPortal()}>Manage subscription and billing</button> : null}</div><div><strong>{account.usage.copilotUnlimited ? "Unlimited" : account.usage.copilotMinutesRemaining ?? 0}</strong><span>Copilot minutes</span></div><div><strong>{account.usage.screenAssistUnlimited ? "Unlimited" : account.usage.screenAssistUsesRemaining ?? 0}</strong><span>Screen Assist uses</span></div></section> : null}
    {checkoutMessage ? <div className="global-checkout-message" role="status"><ShieldCheckIcon size={18} /><span>{checkoutMessage}</span><button type="button" onClick={() => setCheckoutMessage("")}>Dismiss</button></div> : null}
    <section className="global-pricing-grid" aria-label="OfferSteady plans" aria-busy={catalogueStatus === "loading"}>
      {plans.map(plan => <article key={`${plan.offerCode}:${plan.version}`} className={`global-plan-card${plan.featured ? " featured" : ""}`}>
        {plan.featured ? <span className="global-featured-label"><SparkleIcon size={14} weight="fill" /> Most popular</span> : null}
        <div className="global-plan-heading"><div><h2>{plan.displayName}</h2><p>{plan.description}</p></div><CreditCardIcon size={22} weight="duotone" /></div>
        <div className="global-plan-price"><strong>{money(plan.priceCents)}</strong><span>{term(plan)}</span></div>
        <span className="global-plan-renewal">{plan.billingMode === "recurring" ? "Renews monthly until canceled" : plan.priceCents === 0 ? "One-time account allowance" : "One-time payment · no auto-renewal"}</span>
        <ul>{benefits(plan).map(item => <li key={item}><CheckCircleIcon size={16} weight="fill" />{item}</li>)}</ul>
        <button className={`button full ${plan.featured ? "primary" : "ghost"}`} type="button" disabled={checkoutBusy !== null} onClick={() => void beginCheckout(plan)}>{checkoutBusy === plan.offerCode ? "Opening secure checkout…" : plan.priceCents === 0 ? "Use Free" : "Choose plan"}</button>
      </article>)}
    </section>
    <section className="global-pricing-disclosure panel"><ShieldCheckIcon size={24} weight="duotone" /><div><h2>Clear billing, before checkout</h2><p>Prices above are USD base prices. Creem will show the final local currency and applicable taxes before payment. Unlimited plans are subject to a published Fair Use Policy and do not carry hidden ordinary-user minute caps.</p></div></section>
    {account?.orders.length ? <section className="panel global-order-history"><span className="kicker">BILLING HISTORY</span><h2>Your orders</h2>{account.orders.map(order => <article key={order.id}><div><strong>{order.offerCode}</strong><small>{new Date(order.createdAtMs).toLocaleDateString("en-US")}</small></div><span>{order.status}</span><b>{money(order.amountCents)}</b></article>)}</section> : null}
    <p className="global-billing-support">Questions about billing or refunds? <a href="mailto:contact@oneshowailab.com">contact@oneshowailab.com</a></p>
  </main>;
}
