import type { SafeAccountSummary } from "@offersteady/protocol";

import { createJsonClient } from "./api-client";
import { AppError } from "./domain";
import { readRuntimeConfig } from "./runtime-config";

const runtimeConfig = readRuntimeConfig(import.meta.env);
const client = createJsonClient({ baseUrl: runtimeConfig.apiBaseUrl });

const accessTokenKey = "offersteady.auth.access_token";
const refreshTokenKey = "offersteady.auth.refresh_token";
const accountKey = "offersteady.auth.account";

export const adminPrototypeAccount: SafeAccountSummary = {
  id: "admin",
  displayName: "admin",
  createdAtMs: 1_719_000_000_000,
  bindings: [{
    id: "prototype-admin-binding",
    provider: "prototype",
    displayName: "本地 admin 身份",
    status: "active",
    boundAtMs: 1_719_000_000_000,
    canUnbind: false,
  }],
};

const storage = () => window.localStorage;
const prototypeAuthEnabled = () => import.meta.env.MODE === "test" || import.meta.env.VITE_ENABLE_PROTOTYPE_AUTH === "true";
const readStorageItem = (key: string) => {
  const store = storage();
  return typeof store?.getItem === "function" ? store.getItem(key) : null;
};
const writeStorageItem = (key: string, value: string) => {
  const store = storage();
  if (typeof store?.setItem === "function") store.setItem(key, value);
};
const removeStorageItem = (key: string) => {
  const store = storage();
  if (typeof store?.removeItem === "function") store.removeItem(key);
};

const persistPrototypeAccount = (account: SafeAccountSummary) => {
  writeStorageItem(accountKey, JSON.stringify(account));
  writeStorageItem("offersteady.prototype.auth", "true");
};

const normalizePrototypeAccount = (account: SafeAccountSummary | null): SafeAccountSummary => {
  if (account && account.id !== adminPrototypeAccount.id) return account;
  if (account?.id === adminPrototypeAccount.id) return account;
  if (!prototypeAuthEnabled()) throw new AppError("validation", "当前没有登录态");
  removeStorageItem(accessTokenKey);
  removeStorageItem(refreshTokenKey);
  persistPrototypeAccount(adminPrototypeAccount);
  return adminPrototypeAccount;
};

export interface StoredAuthSession {
  readonly accessToken: string;
  readonly refreshToken: string;
  readonly account: SafeAccountSummary;
}

interface AuthTokensResponse {
  readonly accessToken: string;
  readonly refreshToken: string;
}

interface CurrentUserResponse {
  readonly userId: string;
  readonly displayName: string;
  readonly createdAtMs: number;
  readonly bindings: readonly {
    readonly bindingId: string;
    readonly provider: "wechat" | "sms" | "password" | "prototype" | "other";
    readonly displayName?: string | null;
    readonly status: "active" | "recovery-required" | "revoked";
    readonly boundAtMs: number;
  }[];
}

export interface AuthResultResponse {
  readonly user: CurrentUserResponse;
  readonly tokens: AuthTokensResponse;
}

export interface SmsSendCodeResponse {
  readonly challengeId: string;
  readonly status: string;
  readonly provider: string;
  readonly expiresAtMs: number;
  readonly cooldownSeconds: number;
  readonly maskedPhone: string;
}

export interface WechatAuthorizationSessionResponse {
  readonly authRequestId: string;
  readonly status: "creating" | "waiting" | "scanned" | "authorized" | "expired" | "failed";
  readonly authorizationUrl: string;
  readonly qrCodeText: string;
  readonly expiresAtMs: number;
  readonly errorCode?: string | null;
  readonly errorMessage?: string | null;
  readonly result?: AuthResultResponse | null;
}

const toSafeAccountSummary = (user: CurrentUserResponse): SafeAccountSummary => ({
  id: user.userId,
  displayName: user.displayName,
  createdAtMs: user.createdAtMs,
  bindings: user.bindings.map(item => ({
    id: item.bindingId,
    provider: item.provider === "wechat" ? "wechat" : item.provider === "sms" ? "sms" : "prototype",
    displayName: item.displayName ?? (item.provider === "wechat" ? "微信账号" : item.provider === "sms" ? "手机号" : "账号"),
    status: item.status === "active" ? "active" : item.status === "revoked" ? "revoked" : "recovery-required",
    boundAtMs: item.boundAtMs,
    canUnbind: false,
  })),
});

const storeSession = (result: AuthResultResponse): StoredAuthSession => {
  const session = {
    accessToken: result.tokens.accessToken,
    refreshToken: result.tokens.refreshToken,
    account: toSafeAccountSummary(result.user),
  } satisfies StoredAuthSession;
  writeStorageItem(accessTokenKey, session.accessToken);
  writeStorageItem(refreshTokenKey, session.refreshToken);
  writeStorageItem(accountKey, JSON.stringify(session.account));
  writeStorageItem("offersteady.prototype.auth", "true");
  return session;
};

const authorizationHeaders = (accessToken: string) => ({ Authorization: `Bearer ${accessToken}` });

export const authClient = {
  readStoredAccount(): SafeAccountSummary | null {
    try {
      const accountRaw = readStorageItem(accountKey);
      if (!accountRaw) return null;
      return normalizePrototypeAccount(JSON.parse(accountRaw) as SafeAccountSummary);
    } catch {
      return null;
    }
  },

  readStoredSession(): StoredAuthSession | null {
    try {
      const accessToken = readStorageItem(accessTokenKey);
      const refreshToken = readStorageItem(refreshTokenKey);
      const accountRaw = readStorageItem(accountKey);
      if (!accessToken || !refreshToken || !accountRaw) return null;
      const account = JSON.parse(accountRaw) as SafeAccountSummary;
      return { accessToken, refreshToken, account };
    } catch {
      return null;
    }
  },

  clear() {
    removeStorageItem(accessTokenKey);
    removeStorageItem(refreshTokenKey);
    removeStorageItem(accountKey);
    removeStorageItem("offersteady.prototype.auth");
  },

  bootstrapPrototypeIdentity(account: SafeAccountSummary) {
    if (!prototypeAuthEnabled()) return;
    persistPrototypeAccount(normalizePrototypeAccount(account));
  },

  async sendSmsCode(phoneNumber: string, signal?: AbortSignal) {
    return client.request<SmsSendCodeResponse>("/api/v1/auth/sms/send-code", {
      method: "POST",
      body: JSON.stringify({ phoneNumber, clientLabel: "web" }),
    }, signal);
  },

  async verifySmsLogin(input: { phoneNumber: string; challengeId: string; code: string }, signal?: AbortSignal): Promise<StoredAuthSession> {
    const result = await client.request<AuthResultResponse>("/api/v1/auth/sms/verify-login", {
      method: "POST",
      body: JSON.stringify({ phoneNumber: input.phoneNumber, challengeId: input.challengeId, code: input.code, clientLabel: "web" }),
    }, signal);
    return storeSession(result);
  },

  async createWechatAuthorizationSession(signal?: AbortSignal) {
    return client.request<WechatAuthorizationSessionResponse>("/api/v1/auth/wechat/authorization-sessions", {
      method: "POST",
      body: JSON.stringify({ clientLabel: "web" }),
    }, signal);
  },

  async getWechatAuthorizationSession(authRequestId: string, signal?: AbortSignal) {
    return client.request<WechatAuthorizationSessionResponse>(`/api/v1/auth/wechat/authorization-sessions/${authRequestId}`, undefined, signal);
  },

  async simulateScan(authRequestId: string, signal?: AbortSignal) {
    return client.request<WechatAuthorizationSessionResponse>(`/api/v1/auth/wechat/authorization-sessions/${authRequestId}/scan`, { method: "POST" }, signal);
  },

  async simulateAuthorize(authRequestId: string, signal?: AbortSignal) {
    return client.request<WechatAuthorizationSessionResponse>(`/api/v1/auth/wechat/authorization-sessions/${authRequestId}/authorize`, { method: "POST" }, signal);
  },

  acceptAuthorizedResult(result: AuthResultResponse): StoredAuthSession {
    return storeSession(result);
  },

  async refresh(signal?: AbortSignal): Promise<StoredAuthSession> {
    const existing = this.readStoredSession();
    if (!existing) throw new AppError("validation", "当前没有可恢复的登录会话");
    const refreshed = await client.request<AuthResultResponse>("/api/v1/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refreshToken: existing.refreshToken }),
    }, signal);
    return storeSession(refreshed);
  },

  async currentUser(signal?: AbortSignal): Promise<SafeAccountSummary> {
    const existing = this.readStoredSession();
    if (!existing) throw new AppError("validation", "当前没有登录态");
    const user = await client.request<CurrentUserResponse>("/api/v1/auth/me", {
      headers: authorizationHeaders(existing.accessToken),
    }, signal);
    const account = toSafeAccountSummary(user);
    writeStorageItem(accountKey, JSON.stringify(account));
    return account;
  },

  async restore(signal?: AbortSignal): Promise<StoredAuthSession> {
    try {
      const current = await this.currentUser(signal);
      const existing = this.readStoredSession();
      if (!existing) throw new AppError("validation", "当前没有登录态");
      return { ...existing, account: current };
    } catch {
      return this.refresh(signal);
    }
  },

  async logout(signal?: AbortSignal) {
    const existing = this.readStoredSession();
    if (!existing) {
      this.clear();
      return;
    }
    try {
      await client.request("/api/v1/auth/logout", {
        method: "POST",
        headers: authorizationHeaders(existing.accessToken),
        body: JSON.stringify({ logoutAllDevices: false }),
      }, signal);
    } finally {
      this.clear();
    }
  },
};
