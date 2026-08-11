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
    throw new Error(detail || `请求失败 (${response.status})`);
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
  growthReferralSettings: () => request<{ enabled: boolean; rewardPoints: number; configVersion: number; updatedAtMs: number }>("/api/v1/admin/growth/referrals"),
  saveGrowthReferralSettings: (payload: { enabled: boolean; rewardPoints: number; confirmed: boolean; reason: string }) =>
    request<{ enabled: boolean; rewardPoints: number; configVersion: number; updatedAtMs: number }>("/api/v1/admin/growth/referrals", { method: "PUT", body: JSON.stringify(payload) }),
  serverHealth: () => request<ServerHealthResponse>("/api/v1/admin/server-health"),
  observability: () => request<Record<string, unknown>>("/api/v1/admin/observability"),
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
