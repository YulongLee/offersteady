const apiBase = (import.meta.env.VITE_ADMIN_API_BASE_URL || "").replace(/\/$/, "");
const adminTokenKey = "offersteady.admin.session";
import type { TrendResponse } from "./analytics";
import type { CapacityResponse } from "./capacity";
import type { PaymentRevenueSummary } from "./payment-monitoring";
import type { ServerHealthResponse } from "./server-health";

type Envelope<T> = { data: T };

export class AdminAuthenticationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AdminAuthenticationError";
  }
}

export function adminAuthenticationMessage(status: number, detail: unknown): string | null {
  if (status !== 401 && !/admin_session_invalid|admin_step_up_required/i.test(String(detail ?? ""))) return null;
  return /admin_step_up_required/i.test(String(detail ?? ""))
    ? "管理员安全验证已过期，请重新登录后继续操作。"
    : "管理员登录已过期，请重新登录后继续操作。";
}

export function isAdminAuthenticationError(error: unknown): error is AdminAuthenticationError {
  return error instanceof AdminAuthenticationError;
}

export function adminGatewayMessage(status: number): string | null {
  return [502, 503, 504].includes(status)
    ? "管理后台暂时无法连接后端服务，请稍后重试；无需重新输入手机号或获取新的验证码。"
    : null;
}

async function request<T>(path: string, init: RequestInit = {}, admin = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (admin) {
    const token = sessionStorage.getItem(adminTokenKey);
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${apiBase}${path}`, { ...init, headers, credentials: "omit" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || payload.error?.message;
    const authenticationMessage = admin ? adminAuthenticationMessage(response.status, detail) : null;
    if (authenticationMessage) {
      sessionStorage.removeItem(adminTokenKey);
      throw new AdminAuthenticationError(authenticationMessage);
    }
    throw new Error(adminGatewayMessage(response.status) || detail || `请求失败 (${response.status})`);
  }
  return (payload as Envelope<T>).data;
}

export const adminApi = {
  token(): string | null {
    return sessionStorage.getItem(adminTokenKey);
  },
  clear() {
    sessionStorage.removeItem(adminTokenKey);
  },
  async sendSms(phoneNumber: string) {
    return request<{ challengeId: string; cooldownSeconds: number }>("/api/v1/auth/sms/send-code", {
      method: "POST",
      body: JSON.stringify({ phoneNumber, clientLabel: "commercial-admin" }),
    }, false);
  },
  async verifySms(phoneNumber: string, challengeId: string, code: string) {
    return request<{ tokens: { accessToken: string } }>("/api/v1/auth/sms/verify-login", {
      method: "POST",
      body: JSON.stringify({ phoneNumber, challengeId, code, clientLabel: "commercial-admin" }),
    }, false);
  },
  async login(accessToken: string) {
    const result = await request<{ token: string; role: string; permissions: string[]; expiresAtMs: number }>(
      "/api/v1/admin/session",
      { method: "POST", body: JSON.stringify({ accessToken }) },
      false,
    );
    sessionStorage.setItem(adminTokenKey, result.token);
    return result;
  },
  session: () => request<{ role: string; permissions: string[] }>("/api/v1/admin/session"),
  dashboard: () => request<Record<string, number>>("/api/v1/admin/dashboard"),
  trends: (range: "7d" | "30d" | "90d") =>
    request<TrendResponse>(`/api/v1/admin/analytics/trends?range=${range}`),
  capacity: () => request<CapacityResponse>("/api/v1/admin/capacity"),
  paymentRevenue: () => request<PaymentRevenueSummary>("/api/v1/admin/payments/revenue-summary"),
  growthReferralSettings: () => request<{ enabled: boolean; rewardPoints: number; inviterRewardPoints: number; inviteeRewardPoints: number; activationWindowDays: number; configVersion: number; updatedAtMs: number }>("/api/v1/admin/growth/referrals"),
  saveGrowthReferralSettings: (payload: { enabled: boolean; rewardPoints: number; inviteeRewardPoints: number; confirmed: boolean; reason: string }) =>
    request<{ enabled: boolean; rewardPoints: number; inviterRewardPoints: number; inviteeRewardPoints: number; activationWindowDays: number; configVersion: number; updatedAtMs: number }>("/api/v1/admin/growth/referrals", { method: "PUT", body: JSON.stringify(payload) }),
  serverHealth: () => request<ServerHealthResponse>("/api/v1/admin/server-health"),
  observability: () => request<Record<string, unknown>>("/api/v1/admin/observability"),
  promotionOverview: (range = "30d", model = "last_non_direct_touch") => request<Record<string, unknown>>(`/api/v1/admin/promotion/overview?range=${encodeURIComponent(range)}&model=${encodeURIComponent(model)}`),
  promotionHealth: () => request<Record<string, unknown>>("/api/v1/admin/promotion/health"),
  promotionFunnel: (range = "30d", model = "last_non_direct_touch") => request<Record<string, unknown>>(`/api/v1/admin/promotion/funnel?range=${encodeURIComponent(range)}&model=${encodeURIComponent(model)}`),
  promotionReport: (dimension: "channel" | "campaign" | "link", range = "30d", model = "last_non_direct_touch") => request<{ items: Record<string, unknown>[]; metadata: Record<string, unknown> }>(`/api/v1/admin/promotion/reports/${dimension}?range=${encodeURIComponent(range)}&model=${encodeURIComponent(model)}`),
  promotionTrends: (range = "30d", model = "last_non_direct_touch") => request<{ items: Record<string, unknown>[]; metadata: Record<string, unknown> }>(`/api/v1/admin/promotion/trends?range=${encodeURIComponent(range)}&model=${encodeURIComponent(model)}`),
  promotionChannels: () => request<{ items: Record<string, unknown>[] }>("/api/v1/admin/promotion/channels"),
  createPromotionChannel: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/admin/promotion/channels", { method: "POST", body: JSON.stringify(payload) }),
  updatePromotionChannel: (channelId: string, payload: Record<string, unknown>) => request<Record<string, unknown>>(`/api/v1/admin/promotion/channels/${encodeURIComponent(channelId)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  promotionCampaigns: () => request<{ items: Record<string, unknown>[] }>("/api/v1/admin/promotion/campaigns?limit=100&offset=0"),
  createPromotionCampaign: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/admin/promotion/campaigns", { method: "POST", body: JSON.stringify(payload) }),
  updatePromotionCampaign: (campaignId: string, payload: Record<string, unknown>) => request<Record<string, unknown>>(`/api/v1/admin/promotion/campaigns/${encodeURIComponent(campaignId)}`, { method: "PUT", body: JSON.stringify(payload) }),
  promotionCampaignReport: (campaignId: string, range = "30d", model = "last_non_direct_touch") => request<Record<string, unknown>>(`/api/v1/admin/promotion/campaigns/${encodeURIComponent(campaignId)}/report?range=${encodeURIComponent(range)}&model=${encodeURIComponent(model)}`),
  promotionLinks: () => request<{ items: Record<string, unknown>[] }>("/api/v1/admin/promotion/links?limit=100&offset=0"),
  createPromotionLink: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/admin/promotion/links", { method: "POST", body: JSON.stringify(payload) }),
  updatePromotionLink: (linkId: string, payload: Record<string, unknown>) => request<Record<string, unknown>>(`/api/v1/admin/promotion/links/${encodeURIComponent(linkId)}`, { method: "PUT", body: JSON.stringify(payload) }),
  clonePromotionLink: (linkId: string, payload: Record<string, unknown>) => request<Record<string, unknown>>(`/api/v1/admin/promotion/links/${encodeURIComponent(linkId)}/clone`, { method: "POST", body: JSON.stringify(payload) }),
  addPromotionCost: (payload: Record<string, unknown>) => request<Record<string, unknown>>("/api/v1/admin/promotion/costs", { method: "POST", body: JSON.stringify(payload) }),
  promotionCosts: () => request<{ items: Record<string, unknown>[] }>("/api/v1/admin/promotion/costs?limit=100&offset=0"),
  reversePromotionCost: (costEntryId: string, reason: string) => request<Record<string, unknown>>(`/api/v1/admin/promotion/costs/${encodeURIComponent(costEntryId)}/reverse`, { method: "POST", body: JSON.stringify({ reason }) }),
  promotionPartners: () => request<{ items: Record<string, unknown>[] }>("/api/v1/admin/promotion/partners?limit=100"),
  partnerPayouts: () => request<{ items: Record<string, unknown>[] }>("/api/v1/admin/promotion/partner-payouts?limit=100"),
  projectPartnerCommissions: () => request<Record<string, unknown>>("/api/v1/admin/promotion/partners/project?limit=200", { method: "POST" }),
  recordPartnerRefund: (payload: { orderId: string; refundReference: string; refundedCents: number; reason: string }) => request<Record<string, unknown>>("/api/v1/admin/promotion/partner-refunds", { method: "POST", body: JSON.stringify(payload) }),
  transitionPartnerPayout: (payoutId: string, payload: { status: "approved" | "rejected" | "paid"; reason: string; paymentReference?: string }) => request<Record<string, unknown>>(`/api/v1/admin/promotion/partner-payouts/${encodeURIComponent(payoutId)}`, { method: "PATCH", body: JSON.stringify(payload) }),
  list: (resource: "users" | "orders" | "catalog-products" | "redemption-batches" | "payment-channels" | "materials" | "interviews" | "audit" | "admins", offset = 0) =>
    request<{ items: Record<string, unknown>[] }>(`/api/v1/admin/${resource}?limit=50&offset=${offset}`),
  listOrders: (offset = 0, status?: string) => request<{ items: Record<string, unknown>[] }>(
    `/api/v1/admin/orders?limit=50&offset=${offset}${status ? `&status=${encodeURIComponent(status)}` : ""}`,
  ),
  action: (path: string, payload: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/api/v1/admin${path}`, { method: "POST", body: JSON.stringify(payload) }),
  savePaymentChannel: (channel: string, payload: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/api/v1/admin/payment-channels/${channel}`, { method: "PUT", body: JSON.stringify(payload) }),
  async logout() {
    try {
      await request("/api/v1/admin/session", { method: "DELETE" });
    } finally {
      this.clear();
    }
  },
};
