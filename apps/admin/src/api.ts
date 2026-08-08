const apiBase = (import.meta.env.VITE_ADMIN_API_BASE_URL || "").replace(/\/$/, "");
const adminTokenKey = "offersteady.admin.session";
import type { TrendResponse } from "./analytics";
import type { CapacityResponse } from "./capacity";

type Envelope<T> = { data: T };

async function request<T>(path: string, init: RequestInit = {}, admin = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (admin) {
    const token = sessionStorage.getItem(adminTokenKey);
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${apiBase}${path}`, { ...init, headers, credentials: "omit" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.error?.message || `请求失败 (${response.status})`);
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
  observability: () => request<Record<string, unknown>>("/api/v1/admin/observability"),
  list: (resource: "users" | "orders" | "catalog-products" | "redemption-batches" | "payment-channels" | "materials" | "interviews" | "audit" | "admins", offset = 0) =>
    request<{ items: Record<string, unknown>[] }>(`/api/v1/admin/${resource}?limit=50&offset=${offset}`),
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
