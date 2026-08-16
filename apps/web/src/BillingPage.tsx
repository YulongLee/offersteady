import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from "react";
import type {
  BillingProduct,
  OfficialCheckoutOrder,
  PointsLedgerEntry,
  PointsRedemptionResult,
} from "@offersteady/protocol";
import { Link } from "react-router-dom";
import type { ReferralStatus, WebAppState } from "./domain";
import { routes } from "./routes";
import { interviewAppAdapter } from "./app-adapter";
import { runAdapterOperation } from "./api-client";
import { assetUrl } from "./assets";
import QRCode from "qrcode";

interface Props {
  readonly state: WebAppState;
  readonly setState: Dispatch<SetStateAction<WebAppState>>;
}
const money = (cents: number) => `¥${(cents / 100).toFixed(2)}`;
const officialStatus: Record<OfficialCheckoutOrder["status"], string> = {
  created: "订单已创建",
  payment_pending: "等待官方支付确认",
  paid: "支付成功",
  failed: "支付失败",
  closed: "订单已关闭",
  refund_pending: "退款处理中",
  refunded: "已退款",
};
const minuteMs = 60_000;
export const referralCopyFeedbackMs = 1_600;

export const formatMembershipDuration = (durationMs: number) => {
  if (durationMs <= 0) return "0 小时 0 分钟";
  const totalMinutes = Math.ceil(durationMs / minuteMs);
  if (totalMinutes >= 24 * 60) {
    const days = Math.floor(totalMinutes / (24 * 60));
    const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
    return `${days} 天 ${hours} 小时`;
  }
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours} 小时 ${minutes} 分钟`;
};

export const formatMembershipRemaining = (endsAtMs: number, nowMs: number) =>
  endsAtMs <= nowMs ? "已到期" : formatMembershipDuration(endsAtMs - nowMs);

export const successfulOfficialOrders = (
  orders: readonly OfficialCheckoutOrder[],
) => orders.filter((order) => order.status === "paid");

const referralCodePattern = /^[A-Za-z0-9_-]{12,48}$/;

export function parseReferralActivationInput(value: string): string | null {
  const input = value.trim();
  if (!input) return null;

  let candidate = input;
  if (input.includes("/") || input.includes(":")) {
    try {
      const url = new URL(input, window.location.origin);
      const match = url.pathname.match(/^\/invite\/([^/]+)\/?$/);
      if (!match) return null;
      candidate = decodeURIComponent(match[1]!);
    } catch {
      return null;
    }
  }

  return referralCodePattern.test(candidate) ? candidate : null;
}

export async function copyTextWithFallback(value: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    // Some browsers expose Clipboard API but deny it outside a permitted context.
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.readOnly = true;
  textarea.setAttribute("aria-hidden", "true");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  textarea.style.pointerEvents = "none";
  document.body.appendChild(textarea);
  textarea.select();
  textarea.setSelectionRange(0, value.length);
  try {
    return (
      typeof document.execCommand === "function" && document.execCommand("copy")
    );
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}

const membershipDateTime = (value: number) =>
  new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

interface PointsLedgerDisplayEntry {
  readonly id: string;
  readonly kind: string;
  readonly points: number;
  readonly createdAtMs: number;
  readonly description: string;
  readonly count: number;
  readonly isConsumption: boolean;
}

const consumptionCategory = (entry: PointsLedgerEntry) => {
  if (entry.points >= 0) return null;
  const marker = `${entry.kind} ${entry.description}`.toLowerCase();
  if (marker.includes("screenshot") || marker.includes("截图"))
    return "screenshot-answer";
  if (
    marker.includes("knowledge") ||
    marker.includes("index") ||
    marker.includes("知识")
  )
    return "knowledge-index";
  if (marker.includes("refund") || marker.includes("退款")) return "refund";
  if (marker.includes("redemption") || marker.includes("兑换"))
    return "redemption-reversal";
  if (
    marker.includes("answer") ||
    marker.includes("回答") ||
    marker.includes("usage")
  )
    return "answer";
  return `other:${entry.kind}`;
};

const consumptionDescription = (category: string, fallback: string) => {
  if (category === "answer") return "普通回答消费";
  if (category === "screenshot-answer") return "截图回答消费";
  if (category === "knowledge-index") return "知识材料制作消费";
  if (category === "refund") return "退款积分扣回";
  if (category === "redemption-reversal") return "兑换积分撤回";
  return fallback;
};

export function summarizePointsLedger(
  entries: readonly PointsLedgerEntry[],
): readonly PointsLedgerDisplayEntry[] {
  const displayEntries: Array<
    PointsLedgerDisplayEntry & {
      points: number;
      count: number;
      createdAtMs: number;
    }
  > = [];
  const consumptionGroups = new Map<
    string,
    PointsLedgerDisplayEntry & {
      points: number;
      count: number;
      createdAtMs: number;
    }
  >();
  const seenReferences = new Set<string>();

  for (const entry of entries) {
    if (seenReferences.has(entry.referenceId)) continue;
    seenReferences.add(entry.referenceId);
    const category = consumptionCategory(entry);
    if (!category) {
      displayEntries.push({ ...entry, count: 1, isConsumption: false });
      continue;
    }
    const existing = consumptionGroups.get(category);
    if (existing) {
      existing.points += entry.points;
      existing.count += 1;
      existing.createdAtMs = Math.max(existing.createdAtMs, entry.createdAtMs);
      continue;
    }
    const summary = {
      id: `consumption-${category}`,
      kind: entry.kind,
      points: entry.points,
      createdAtMs: entry.createdAtMs,
      description: consumptionDescription(category, entry.description),
      count: 1,
      isConsumption: true,
    };
    consumptionGroups.set(category, summary);
    displayEntries.push(summary);
  }

  return displayEntries.sort(
    (left, right) => right.createdAtMs - left.createdAtMs,
  );
}

export function BillingPage({ state, setState }: Props) {
  const [product, setProduct] = useState<BillingProduct | null>(null);
  const [checkout, setCheckout] = useState<OfficialCheckoutOrder | null>(null);
  const [notice, setNotice] = useState("");
  const [checkoutPending, setCheckoutPending] = useState(false);
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [clockMs, setClockMs] = useState(() => Date.now());
  const [entitlementSync, setEntitlementSync] = useState<
    "idle" | "syncing" | "error"
  >("idle");
  const [referral, setReferral] = useState<ReferralStatus | null>(null);
  const [referralError, setReferralError] = useState("");
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">(
    "idle",
  );
  const [referralActivationInput, setReferralActivationInput] = useState("");
  const [referralActivationPending, setReferralActivationPending] =
    useState(false);
  const [referralActivationResult, setReferralActivationResult] = useState("");
  const [redemptionCode, setRedemptionCode] = useState("");
  const [redemptionPending, setRedemptionPending] = useState(false);
  const [redemptionResult, setRedemptionResult] =
    useState<PointsRedemptionResult | null>(null);
  const paidOfficialOrders = useMemo(
    () => successfulOfficialOrders(state.billing.officialOrders),
    [state.billing.officialOrders],
  );
  const inviterRewardPoints = referral?.inviterRewardPoints ?? referral?.rewardPoints ?? 0;
  const inviteeRewardPoints = referral?.inviteeRewardPoints ?? referral?.rewardPoints ?? 0;
  const activationDeadlineMs = referral?.activationDeadlineMs ?? null;
  const referralEligible = Boolean(
    referral &&
      !referral.hasActivatedReferral &&
      referral.enabled &&
      (referral.eligibleToActivate ?? true) &&
      (activationDeadlineMs === null || clockMs <= activationDeadlineMs),
  );
  const redemptionController = useRef<AbortController | null>(null);
  const referralCopyTimer = useRef<number | null>(null);
  const refreshBillingState = useCallback(async () => {
    setEntitlementSync("syncing");
    try {
      const billing = await runAdapterOperation((signal) =>
        interviewAppAdapter.getBillingState(signal),
      );
      setState((current) => ({ ...current, billing }));
      setClockMs(Date.now());
      setEntitlementSync("idle");
      return true;
    } catch {
      setEntitlementSync("error");
      return false;
    }
  }, [setState]);
  useEffect(
    () => () => {
      redemptionController.current?.abort();
      if (referralCopyTimer.current !== null)
        window.clearTimeout(referralCopyTimer.current);
    },
    [],
  );
  const refreshReferralStatus = useCallback(async (signal?: AbortSignal) => {
    setReferralError("");
    try {
      const status = await runAdapterOperation(
        (operationSignal) =>
          interviewAppAdapter.getReferralStatus(operationSignal),
        signal,
      );
      setReferral(status);
      return status;
    } catch (error) {
      if (!signal?.aborted)
        setReferralError(
          error instanceof Error ? error.message : "邀请信息暂时无法读取",
        );
      return null;
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void refreshReferralStatus(controller.signal);
    return () => controller.abort();
  }, [refreshReferralStatus]);
  useEffect(() => {
    const timer = window.setInterval(() => setClockMs(Date.now()), minuteMs);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    const onFocus = () => {
      void refreshBillingState();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refreshBillingState]);
  useEffect(() => {
    if (checkout?.action.kind !== "dynamic_qr") {
      setQrDataUrl("");
      return;
    }
    void QRCode.toDataURL(checkout.action.value, { width: 240, margin: 2 })
      .then(setQrDataUrl)
      .catch(() => setQrDataUrl(""));
  }, [checkout]);
  useEffect(() => {
    if (!checkout || checkout.status !== "payment_pending") return undefined;
    const controller = new AbortController();
    const timer = window.setInterval(() => {
      void runAdapterOperation(
        (signal) => interviewAppAdapter.getCheckoutOrder(checkout.id, signal),
        controller.signal,
      )
        .then(async (order) => {
          setCheckout(order);
          setState((current) => ({
            ...current,
            billing: {
              ...current.billing,
              officialOrders: current.billing.officialOrders.some(
                (item) => item.id === order.id,
              )
                ? current.billing.officialOrders.map((item) =>
                    item.id === order.id ? order : item,
                  )
                : [order, ...current.billing.officialOrders],
            },
          }));
          if (order.status === "paid") {
            const refreshed = await refreshBillingState();
            setNotice(
              refreshed
                ? "支付已由服务端验签确认，权益已到账"
                : "支付已确认，会员权益正在同步，请稍后重试。",
            );
          }
        })
        .catch(() => undefined);
    }, 3000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [checkout, refreshBillingState, setState]);
  const redeem = async (event: FormEvent) => {
    event.preventDefault();
    if (!redemptionCode.replace(/[\s-]/g, "") || redemptionPending) return;
    setRedemptionPending(true);
    setRedemptionResult(null);
    const controller = new AbortController();
    redemptionController.current = controller;
    try {
      const idempotencyKey =
        globalThis.crypto?.randomUUID?.() ??
        `redeem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const result = await runAdapterOperation(
        (signal) =>
          interviewAppAdapter.redeemPoints(
            { code: redemptionCode, idempotencyKey },
            signal,
          ),
        controller.signal,
      );
      setRedemptionResult(result);
      if (
        result.outcome === "redeemed" ||
        result.outcome === "already-redeemed-by-you"
      ) {
        const data = result.data;
        setRedemptionCode("");
        setState((current) => ({
          ...current,
          billing: {
            ...current.billing,
            balance: data.newBalance,
            ledger: current.billing.ledger.some(
              (entry) =>
                entry.id === data.ledgerEntry.id ||
                entry.referenceId === data.ledgerEntry.referenceId,
            )
              ? current.billing.ledger
              : [data.ledgerEntry, ...current.billing.ledger],
          },
        }));
      }
    } catch {
      if (!controller.signal.aborted)
        setRedemptionResult({ outcome: "temporarily-unavailable" });
    } finally {
      if (!controller.signal.aborted) setRedemptionPending(false);
    }
  };
  const startCheckout = async (
    selectedProduct: BillingProduct,
    channel: "wechat" | "alipay",
  ) => {
    if (checkoutPending) return;
    setProduct(selectedProduct);
    setCheckout(null);
    setCheckoutPending(true);
    try {
      const idempotencyKey =
        globalThis.crypto?.randomUUID?.() ??
        `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const order = await runAdapterOperation((signal) =>
        interviewAppAdapter.createCheckoutOrder(
          { productId: selectedProduct.id, channel, idempotencyKey },
          signal,
        ),
      );
      setCheckout(order);
      setState((current) => ({
        ...current,
        billing: {
          ...current.billing,
          officialOrders: current.billing.officialOrders.some(
            (item) => item.id === order.id,
          )
            ? current.billing.officialOrders.map((item) =>
                item.id === order.id ? order : item,
              )
            : [order, ...current.billing.officialOrders],
        },
      }));
      if (order.action.kind === "redirect")
        window.open(order.action.url, "_blank", "noopener,noreferrer");
      setNotice(
        order.provider === "alipay"
          ? "支付宝官方订单已创建，已为你打开官方收银台；到账以服务端验签通知为准。"
          : "微信支付订单已创建，请扫描订单专属二维码；到账以服务端验签通知为准。",
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "创建支付订单失败，请稍后重试",
      );
    } finally {
      setCheckoutPending(false);
    }
  };
  const passes = state.billing.catalog.filter(
    (item) => item.kind === "time_pass" && item.published,
  );
  const points = state.billing.catalog.filter(
    (item) => item.kind === "points_pack" && item.published,
  );
  const ledgerEntries = summarizePointsLedger(state.billing.ledger);
  const uniqueLedgerCount = new Set(
    state.billing.ledger.map((entry) => entry.referenceId),
  ).size;
  const knowledgeIndexPointsPer5000Tokens =
    state.billing.rates.knowledgeIndexPointsPer1000Tokens * 5;
  const cards = (items: readonly BillingProduct[]) => (
    <div className="price-grid">
      {items.map((item) => (
        <article key={item.id} className="price-card">
          <span>
            {item.kind === "time_pass"
              ? "回答与截图不限次"
              : `¥${(item.priceCents / 100 / (item.points ?? 1)).toFixed(3)}/点`}
          </span>
          <h3>{item.displayName}</h3>
          <strong>{money(item.priceCents)}</strong>
          <small>
            {item.kind === "time_pass"
              ? `约 ¥${(item.priceCents / 100 / (item.durationDays ?? 1)).toFixed(2)}/天${item.knowledgeIndexAllowance ? ` · 含 ${item.knowledgeIndexAllowance} 份知识材料` : " · 知识材料按点"}`
              : `预计可回答 ${Math.floor((item.points ?? 0) / state.billing.rates.answerPoints)} 次`}
          </small>
          <button
            className="button primary"
            onClick={() => {
              setProduct(item);
              setCheckout(null);
            }}
            disabled={
              checkoutPending || !state.billing.availablePaymentChannels.length
            }
          >
            {state.billing.availablePaymentChannels.length
              ? "购买"
              : "支付暂未开放"}
          </button>
        </article>
      ))}
    </div>
  );
  const entitlements = useMemo(
    () =>
      [state.billing.activePass, ...state.billing.queuedPasses].filter(
        (item) => item !== null,
      ),
    [state.billing.activePass, state.billing.queuedPasses],
  );
  const activePass =
    entitlements.find(
      (item) => item.startsAtMs <= clockMs && clockMs < item.endsAtMs,
    ) ?? null;
  const queuedPasses = entitlements
    .filter((item) => item.startsAtMs > clockMs)
    .sort((left, right) => left.startsAtMs - right.startsAtMs);
  const nextPass = queuedPasses[0] ?? null;
  const finalPassEndMs = entitlements.reduce(
    (latest, item) => Math.max(latest, item.endsAtMs),
    0,
  );
  const queuedDurationMs = queuedPasses.reduce(
    (total, item) => total + Math.max(0, item.endsAtMs - item.startsAtMs),
    0,
  );
  const allowance = activePass
    ? Math.max(
        0,
        activePass.knowledgeAllowanceGranted -
          activePass.knowledgeAllowanceUsed -
          activePass.knowledgeAllowanceLocked,
      )
    : 0;
  useEffect(() => {
    const boundaryMs = activePass?.endsAtMs ?? nextPass?.startsAtMs;
    if (!boundaryMs) return undefined;
    const delay = Math.max(0, boundaryMs - Date.now()) + 50;
    const timer = window.setTimeout(
      () => {
        setClockMs(Date.now());
        void refreshBillingState();
      },
      Math.min(delay, 2_147_483_647),
    );
    return () => window.clearTimeout(timer);
  }, [activePass?.endsAtMs, nextPass?.startsAtMs, refreshBillingState]);
  const copyReferralLink = async () => {
    if (!referral) return;
    if (referralCopyTimer.current !== null) {
      window.clearTimeout(referralCopyTimer.current);
      referralCopyTimer.current = null;
    }
    const copied = await copyTextWithFallback(referral.shareUrl);
    if (!copied) {
      const input = document.querySelector<HTMLInputElement>(
        "#referral-share-url",
      );
      input?.focus();
      input?.select();
    }
    setCopyState(copied ? "copied" : "failed");
    if (copied) {
      referralCopyTimer.current = window.setTimeout(() => {
        setCopyState("idle");
        referralCopyTimer.current = null;
      }, referralCopyFeedbackMs);
    }
  };
  const activateReferral = async (event: FormEvent) => {
    event.preventDefault();
    if (
      !referral?.enabled ||
      referral.hasActivatedReferral ||
      !referralEligible ||
      referralActivationPending
    )
      return;
    const code = parseReferralActivationInput(referralActivationInput);
    if (!code) {
      setReferralActivationResult("请输入有效的邀请链接。");
      return;
    }
    setReferralActivationPending(true);
    setReferralActivationResult("");
    try {
      const activation = await runAdapterOperation((signal) =>
        interviewAppAdapter.activateReferral(code, signal),
      );
      const message =
        activation.outcome === "activated"
          ? activation.replayed
            ? "你已经激活过这个邀请，无需重复操作。"
            : `邀请已成功激活，你获得 ${activation.inviteeRewardPoints ?? inviteeRewardPoints} 点，好友获得 ${activation.inviterRewardPoints ?? activation.rewardPoints ?? inviterRewardPoints} 点。`
          : activation.outcome === "already-activated"
            ? "当前账号已经激活过其他邀请，每个账号只能激活一次。"
            : activation.outcome === "self-referral"
              ? "不能激活自己的邀请链接。"
              : activation.outcome === "disabled"
                ? "邀请活动目前已暂停。"
                : activation.outcome === "activation-window-expired"
                  ? "邀请链接仅限新用户注册后 3 天内激活，你的激活期限已过。"
                  : activation.outcome === "registration-time-unavailable"
                    ? "暂时无法确认账号注册时间，请联系客服处理。"
                    : "邀请链接无效或已撤销。";
      setReferralActivationResult(message);
      if (activation.outcome === "activated") {
        setNotice(message);
        setReferralActivationInput("");
        await Promise.all([refreshReferralStatus(), refreshBillingState()]);
      }
    } catch (error) {
      setReferralActivationResult(
        error instanceof Error ? error.message : "激活失败，请稍后重试。",
      );
    } finally {
      setReferralActivationPending(false);
    }
  };
  return (
    <main className="app-page billing-page">
      <header className="billing-hero">
        <div>
          <span className="kicker">
            PRICING & POINTS · 目录 v{state.billing.rates.catalogVersion}
          </span>
          <h1>按你的面试节奏付费</h1>
          <p>
            新用户赠送 200
            点体验额度。低频按点，高频选择按天会员；商品与金额由服务端确认，到账以后端验签结果为准。
          </p>
        </div>
        <section
          className={`balance-card entitlement-card${activePass ? " active" : ""}`}
          aria-labelledby="entitlement-card-title"
        >
          <div className="entitlement-card-heading">
            <small id="entitlement-card-title">我的权益</small>
            <span
              className={`entitlement-badge${activePass ? " active" : nextPass ? " queued" : ""}`}
            >
              {activePass
                ? "会员使用中"
                : nextPass
                  ? "会员待生效"
                  : "当前未开通会员"}
            </span>
          </div>
          {activePass ? (
            <>
              <strong className="membership-remaining">
                剩余 {formatMembershipRemaining(activePass.endsAtMs, clockMs)}
              </strong>
              <span>有效期至 {membershipDateTime(activePass.endsAtMs)}</span>
              <span>会员期内回答与截图不扣积分</span>
              {activePass.knowledgeAllowanceGranted ? (
                <span>
                  知识材料额度 {allowance}/
                  {activePass.knowledgeAllowanceGranted}
                </span>
              ) : null}
            </>
          ) : nextPass ? (
            <>
              <strong className="membership-remaining">
                {membershipDateTime(nextPass.startsAtMs)} 生效
              </strong>
              <span>
                待生效会员共 {formatMembershipDuration(queuedDurationMs)}
              </span>
              <span>累计有效期至 {membershipDateTime(finalPassEndMs)}</span>
            </>
          ) : (
            <>
              <strong>{state.billing.balance} 点</strong>
              <span>
                回答 {state.billing.rates.answerPoints} 点 · 截图{" "}
                {state.billing.rates.screenshotAnswerPoints} 点 · 知识材料{" "}
                {state.billing.rates.knowledgeIndexMinimumPoints} 点起
              </span>
            </>
          )}
          {activePass || nextPass ? (
            <div className="entitlement-points">
              <small>积分余额 · 会员到期后继续使用</small>
              <b>{state.billing.balance} 点</b>
            </div>
          ) : null}
        </section>
      </header>
      {notice ? (
        <div className="billing-notice" role="status">
          {notice}
        </div>
      ) : null}
      {entitlementSync === "syncing" ? (
        <div className="billing-sync" role="status">
          正在同步最新会员权益…
        </div>
      ) : entitlementSync === "error" ? (
        <div className="billing-sync error" role="alert">
          <span>会员权益暂时未同步，请稍后重试。</span>
          <button type="button" onClick={() => void refreshBillingState()}>
            重新同步
          </button>
        </div>
      ) : null}
      <section
        className="panel referral-card"
        aria-labelledby="referral-card-title"
      >
        <div className="referral-card-copy">
          <span className="kicker">INVITE & EARN</span>
          <h2 id="referral-card-title">邀请好友，获得积分</h2>
          <p>
            把专属链接分享给其他用户。对方登录并首次激活后，积分会由服务端自动发放给你；每个账号只能激活一次，不能自邀。
          </p>
          {referral ? (
            <div className="referral-summary">
              <span>
                <b>{referral.inviteCount}</b>成功邀请
              </span>
              <span>
                <b>{referral.totalRewardPoints}</b>累计奖励积分
              </span>
              <span>
                <b>{inviterRewardPoints}</b>每次分享奖励
              </span>
              <span>
                <b>{inviteeRewardPoints}</b>新用户激活奖励
              </span>
            </div>
          ) : null}
        </div>
        <div className="referral-share-box">
          {referralError ? (
            <div className="inline-error" role="alert">
              {referralError}
            </div>
          ) : !referral ? (
            <span className="referral-loading">正在生成专属分享链接…</span>
          ) : (
            <>
              <div className="referral-status-row">
                <span
                  className={referral.enabled ? "success-text" : "muted-text"}
                >
                  ● {referral.enabled ? "邀请活动进行中" : "邀请活动暂时关闭"}
                </span>
                {referral.hasActivatedReferral ? (
                  <small>你已激活过一次邀请</small>
                ) : (
                  <small>你还可以激活一次其他用户邀请</small>
                )}
              </div>
              <label htmlFor="referral-share-url">你的专属链接</label>
              <div className="referral-link-controls">
                <input
                  id="referral-share-url"
                  readOnly
                  value={referral.shareUrl}
                  onFocus={(event) => event.currentTarget.select()}
                />
                <button
                  className="button primary"
                  type="button"
                  disabled={!referral.enabled}
                  onClick={() => void copyReferralLink()}
                >
                  {copyState === "copied" ? "已复制" : "复制链接"}
                </button>
              </div>
              <small>
                {copyState === "failed"
                  ? "浏览器没有允许自动复制，请选中链接并按 Ctrl/Cmd+C。"
                  : referral.enabled
                    ? `好友注册后 3 天内激活，你将获得 ${inviterRewardPoints} 点，对方获得 ${inviteeRewardPoints} 点。`
                    : "管理员重新开启活动后，这个链接仍可继续使用。"}
              </small>
              <div className="referral-activation-divider" />
              <div className="referral-activation-heading">
                <strong>激活其他用户邀请</strong>
                <small>
                  {referral.hasActivatedReferral
                    ? "每个账号只能激活一次"
                    : referralEligible
                      ? activationDeadlineMs
                        ? `请在 ${membershipDateTime(activationDeadlineMs)} 前激活`
                        : "请粘贴好友分享的完整链接"
                      : "新用户仅可在注册后 3 天内激活"}
                </small>
              </div>
              {referral.hasActivatedReferral ? (
                <div className="referral-activation-complete" role="status">
                  已激活过邀请，不能再次激活其他链接。
                  {referral.activatedReward
                    ? ` 本次你已获得 ${referral.activatedReward.inviteeRewardPoints} 点。`
                    : ""}
                </div>
              ) : !referralEligible ? (
                <div className="referral-activation-complete" role="status">
                  {referral.activationEligibilityReason === "activity-disabled"
                    ? "邀请活动目前暂停，暂时不能激活。"
                    : referral.activationEligibilityReason === "registration-time-unavailable"
                      ? "暂时无法确认账号注册时间，请联系客服处理。"
                      : "邀请链接仅限新用户注册后 3 天内激活，你的激活期限已过。"}
                </div>
              ) : (
                <form
                  className="referral-activation-form"
                  onSubmit={(event) => void activateReferral(event)}
                >
                  <label htmlFor="referral-activation-input">
                    邀请链接
                  </label>
                  <div className="referral-link-controls">
                    <input
                      id="referral-activation-input"
                      value={referralActivationInput}
                      onChange={(event) => {
                        setReferralActivationInput(event.target.value);
                        setReferralActivationResult("");
                      }}
                      disabled={!referralEligible || referralActivationPending}
                      autoComplete="off"
                      spellCheck={false}
                      placeholder="粘贴好友的邀请链接"
                    />
                    <button
                      className="button primary"
                      type="submit"
                      disabled={!referralEligible || referralActivationPending}
                    >
                      {referralActivationPending ? "激活中…" : "确认激活"}
                    </button>
                  </div>
                  {referralActivationResult ? (
                    <div
                      className="referral-activation-result"
                      role="status"
                      aria-live="polite"
                    >
                      {referralActivationResult}
                    </div>
                  ) : (
                    <small>
                      你将获得 {inviteeRewardPoints} 点，分享链接的好友将获得 {inviterRewardPoints} 点。
                    </small>
                  )}
                </form>
              )}
            </>
          )}
        </div>
      </section>
      <section
        className="panel redemption-card"
        aria-labelledby="redemption-title"
      >
        <div>
          <span className="kicker">POINTS CODE</span>
          <h2 id="redemption-title">兑换积分</h2>
          <p>
            兑换成功后，积分直接进入当前账号。兑换码属于一次性凭证，请勿转发给他人。
          </p>
        </div>
        <form onSubmit={(event) => void redeem(event)}>
          <label htmlFor="points-redemption-code">积分兑换码</label>
          <div className="redemption-controls">
            <input
              id="points-redemption-code"
              value={redemptionCode}
              onChange={(event) => setRedemptionCode(event.target.value)}
              disabled={redemptionPending}
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              placeholder="XXXX-XXXX-XXXX-XXXX"
              aria-describedby="redemption-format redemption-status"
            />
            <button
              className="button primary"
              disabled={
                redemptionPending || !redemptionCode.replace(/[\s-]/g, "")
              }
              type="submit"
            >
              {redemptionPending ? "兑换中…" : "立即兑换"}
            </button>
          </div>
          <small id="redemption-format">
            输入 16 位兑换码，可包含空格或连字符；旧版兑换码仍可使用。
          </small>
          <div
            id="redemption-status"
            className={`redemption-status ${redemptionResult?.outcome ?? "idle"}`}
            role="status"
            aria-live="polite"
          >
            {redemptionPending
              ? "正在安全校验兑换码，当前余额不会提前变化。"
              : redemptionResult?.outcome === "redeemed"
                ? `兑换成功：+${redemptionResult.data.points} 点，当前余额 ${redemptionResult.data.newBalance} 点 · ${redemptionResult.data.publicHint} · ${new Date(redemptionResult.data.redeemedAtMs).toLocaleString("zh-CN")}`
                : redemptionResult?.outcome === "already-redeemed-by-you"
                  ? `这枚兑换码已兑换至当前账号，余额 ${redemptionResult.data.newBalance} 点。`
                  : redemptionResult?.outcome === "code-unavailable"
                    ? "兑换码不可用，请检查输入；仍有问题可联系售后客服。"
                    : redemptionResult?.outcome === "rate-limited"
                      ? `尝试次数较多，请约 ${Math.ceil(redemptionResult.retryAfterMs / 1000)} 秒后重试。`
                      : redemptionResult?.outcome === "temporarily-unavailable"
                        ? "服务暂时不可用，请保留当前输入并稍后重试。"
                        : "输入兑换码后即可兑换；兑换点数由服务端确认。"}
          </div>
        </form>
      </section>
      {queuedPasses.length ? (
        <section className="panel queued-entitlements">
          <div className="panel-heading">
            <h2>待生效会员</h2>
            <span>
              {queuedPasses.length} 个 · 共{" "}
              {formatMembershipDuration(queuedDurationMs)}
            </span>
          </div>
          {queuedPasses.map((item) => (
            <p key={item.id}>
              <strong>{membershipDateTime(item.startsAtMs)} 生效</strong>，至{" "}
              {membershipDateTime(item.endsAtMs)}；含{" "}
              {item.knowledgeAllowanceGranted} 份知识材料额度。
            </p>
          ))}
          <small>累计会员有效期至 {membershipDateTime(finalPassEndMs)}</small>
        </section>
      ) : null}
      <section className="billing-section">
        <div className="panel-heading">
          <h2>按天会员</h2>
          <span>15 天与 30 天会员含 2 份知识材料额度</span>
        </div>
        {cards(passes)}
      </section>
      <section className="billing-section">
        <div className="panel-heading">
          <h2>积分包</h2>
          <span>积分长期有效，按成功结果扣除</span>
        </div>
        {cards(points)}
      </section>
      <section className="panel consumption-panel">
        <div className="panel-heading">
          <h2>点数消费说明</h2>
          <Link to={`${routes.guide}#billing`}>查看支付说明</Link>
        </div>
        <div className="consumption-grid">
          <article>
            <b>{state.billing.rates.answerPoints} 点</b>
            <strong>普通回答</strong>
            <p>成功生成可用回答后结算；会员期内为 0 点。</p>
          </article>
          <article>
            <b>{state.billing.rates.screenshotAnswerPoints} 点</b>
            <strong>截图回答</strong>
            <p>识别失败或取消会释放预留积分。</p>
          </article>
          <article>
            <b>{state.billing.rates.knowledgeIndexMinimumPoints} 点起</b>
            <strong>知识材料索引</strong>
            <p>
              每 5,000 Token {knowledgeIndexPointsPer5000Tokens} 点，最低{" "}
              {state.billing.rates.knowledgeIndexMinimumPoints} 点；15/30
              天会员含 2 份。
            </p>
          </article>
        </div>
      </section>
      <section className="panel points-history">
        <div className="panel-heading">
          <h2>积分明细</h2>
          <span>
            {ledgerEntries.length} 项 · {uniqueLedgerCount} 笔流水
          </span>
        </div>
        <div
          className="order-list points-ledger-scroll"
          role="region"
          aria-label="积分明细记录"
          tabIndex={ledgerEntries.length > 5 ? 0 : undefined}
        >
          {ledgerEntries.map((entry) => (
            <article key={entry.id}>
              <div>
                <strong>{entry.description}</strong>
                <small>
                  {entry.isConsumption
                    ? `共 ${entry.count} 次 · 最近 ${new Date(entry.createdAtMs).toLocaleString("zh-CN")}`
                    : `${new Date(entry.createdAtMs).toLocaleString("zh-CN")}${entry.kind === "redemption_credit" ? ` · ${entry.description.match(/••••-[0-9A-Z]+/)?.[0] ?? "兑换积分"}` : ""}`}
                </small>
              </div>
              <span className={entry.points >= 0 ? "success-text" : ""}>
                {entry.points >= 0 ? "+" : ""}
                {entry.points} 点
              </span>
            </article>
          ))}
        </div>
      </section>
      <div className="billing-bottom">
        <section
          className="panel billing-assurance-panel"
          aria-labelledby="billing-assurance-title"
        >
          <div className="billing-bottom-heading">
            <div>
              <span className="kicker">PAYMENT PROTECTION</span>
              <h2 id="billing-assurance-title">支付保障与售后</h2>
            </div>
            <span className="billing-trust-chip">
              <i /> 服务端验签
            </span>
          </div>
          <div className="billing-assurance-list">
            <article>
              <b>01</b>
              <div>
                <strong>服务端创建订单</strong>
                <p>商品与金额由服务端目录确认，避免前端参数被篡改。</p>
              </div>
            </article>
            <article>
              <b>02</b>
              <div>
                <strong>到账以后端通知为准</strong>
                <p>返回支付页不代表到账，系统会等待验签通知或主动查单。</p>
              </div>
            </article>
            <article>
              <b>03</b>
              <div>
                <strong>问题可追踪处理</strong>
                <p>咨询支付问题时请提供订单号，请勿发送密码或验证码。</p>
              </div>
            </article>
          </div>
          <div className="support-card">
            <div className="support-card-heading">
              <div>
                <strong>需要帮助？联系我们</strong>
                <small>{state.billing.support.serviceHours}</small>
              </div>
              <span>工作日响应</span>
            </div>
            <div className="billing-support-contacts">
              <article>
                <small>客服微信</small>
                <strong>{state.billing.support.wechatId}</strong>
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard?.writeText(
                      state.billing.support.wechatId,
                    );
                    setNotice("客服微信号已复制");
                  }}
                >
                  复制微信号
                </button>
              </article>
              <article>
                <small>联系邮箱</small>
                <strong>{state.billing.support.email}</strong>
                <a href={`mailto:${state.billing.support.email}`}>发送邮件</a>
              </article>
            </div>
          </div>
        </section>
        <section
          className="panel billing-orders-panel"
          aria-labelledby="official-orders-title"
        >
          <div className="panel-heading">
            <div>
              <span className="kicker">ORDER HISTORY</span>
              <h2 id="official-orders-title">官方订单</h2>
            </div>
            <span>{paidOfficialOrders.length} 笔</span>
          </div>
          {paidOfficialOrders.length ? (
            <div className="order-list">
              {paidOfficialOrders.map((order) => (
                <article key={order.id}>
                  <div>
                    <strong>{order.product.displayName}</strong>
                    <small>
                      {order.id} ·{" "}
                      {order.channel === "wechat" ? "微信支付" : "支付宝"}
                    </small>
                  </div>
                  <span>{officialStatus[order.status]}</span>
                </article>
              ))}
            </div>
          ) : (
            <div className="billing-orders-empty">
              <span>◇</span>
              <strong>暂无成功订单</strong>
              <p>支付成功并到账后，订单会显示在这里。</p>
            </div>
          )}
        </section>
      </div>
      {product ? (
        <div
          className="sheet-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="official-checkout-title"
        >
          <section className="sheet checkout-sheet">
            <button
              className="sheet-close"
              aria-label="关闭支付"
              onClick={() => setProduct(null)}
            >
              ×
            </button>
            <h2 id="official-checkout-title">购买 {product.displayName}</h2>
            <p>
              订单金额由服务端目录确认：
              <strong>{money(product.priceCents)}</strong>
            </p>
            {!checkout && !checkoutPending ? (
              <div className="checkout-channel-actions">
                {state.billing.availablePaymentChannels.includes("wechat") ? (
                  <button
                    className="checkout-channel-card wechat"
                    aria-label="微信支付"
                    onClick={() => void startCheckout(product, "wechat")}
                  >
                    <img src={assetUrl("payments.wechat")} alt="" />
                    <span>
                      <strong>微信支付</strong>
                      <small>打开微信，扫描订单二维码</small>
                    </span>
                    <i aria-hidden="true">→</i>
                  </button>
                ) : null}
                {state.billing.availablePaymentChannels.includes("alipay") ? (
                  <button
                    className="checkout-channel-card alipay"
                    aria-label="支付宝支付"
                    onClick={() => void startCheckout(product, "alipay")}
                  >
                    <img src={assetUrl("payments.alipay")} alt="" />
                    <span>
                      <strong>支付宝支付</strong>
                      <small>跳转支付宝官方收银台</small>
                    </span>
                    <i aria-hidden="true">→</i>
                  </button>
                ) : null}
              </div>
            ) : null}
            {checkoutPending && !checkout ? (
              <div className="payment-waiting">
                <i className="online-dot" />
                <span>正在创建安全支付订单…</span>
              </div>
            ) : null}
            {checkout ? (
              <>
                <div className="official-order-meta">
                  <span>订单号</span>
                  <strong>{checkout.id}</strong>
                  <span>金额</span>
                  <strong>{money(checkout.amountCents)}</strong>
                  <span>状态</span>
                  <strong>{officialStatus[checkout.status]}</strong>
                </div>
                {checkout.status === "payment_pending" ? (
                  checkout.action.kind === "dynamic_qr" ? (
                    <div className="dynamic-payment-qr">
                      {qrDataUrl ? (
                        <img src={qrDataUrl} alt="微信支付订单二维码" />
                      ) : null}
                      <span>订单专属动态支付二维码</span>
                      <small>有效期以内有效 · 请使用微信扫码</small>
                    </div>
                  ) : (
                    <a
                      className="button primary full"
                      href={checkout.action.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      打开支付宝官方收银台
                    </a>
                  )
                ) : null}
                {checkout.status === "payment_pending" ? (
                  <div className="payment-waiting">
                    <i className="online-dot" />
                    <span>正在等待服务端验签通知，请勿重复付款</span>
                  </div>
                ) : null}
              </>
            ) : null}
          </section>
        </div>
      ) : null}
    </main>
  );
}
