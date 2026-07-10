import type { WechatAuthorizationSession } from "@offersteady/protocol";

export interface OfficialWechatAuthorizationAdapter { createAuthorizationUrl(state: string): Promise<string> }
export class AuthorizationEntryError extends Error { constructor(readonly code: "rate-limited" | "invalid-state" | "provider-unavailable", message: string) { super(message); } }
export class AuthorizationEntryService {
  private sessions = new Map<string, WechatAuthorizationSession>();
  private attempts = new Map<string, number[]>();
  private counter = 0;
  constructor(private readonly provider: OfficialWechatAuthorizationAdapter, private readonly limit = 5) {}
  async create(userKey: string, nowMs = Date.now()) {
    const recent = (this.attempts.get(userKey) ?? []).filter(value => value > nowMs - 60_000); if (recent.length >= this.limit) throw new AuthorizationEntryError("rate-limited", "登录请求过于频繁"); this.attempts.set(userKey, [...recent, nowMs]);
    const id = `wechat-auth-${++this.counter}`; const state = `state-${id}-${nowMs}`; let authorizeUrl: string; try { authorizeUrl = await this.provider.createAuthorizationUrl(state); } catch { throw new AuthorizationEntryError("provider-unavailable", "微信授权暂时不可用"); }
    const session: WechatAuthorizationSession = { id, state, status: "waiting", authorizeUrl, expiresAtMs: nowMs + 5 * 60_000 }; this.sessions.set(id, session); return session;
  }
  status(id: string, nowMs = Date.now()) { const value = this.sessions.get(id); if (!value) throw new AuthorizationEntryError("invalid-state", "授权会话不存在"); if (value.expiresAtMs <= nowMs && value.status !== "authorized") { const expired = { ...value, status: "expired" as const }; this.sessions.set(id, expired); return expired; } return value; }
  markAuthorized(id: string, state: string, nowMs = Date.now()) { const value = this.status(id, nowMs); if (value.state !== state || value.status !== "waiting") throw new AuthorizationEntryError("invalid-state", "授权状态无效"); const next = { ...value, status: "authorized" as const }; this.sessions.set(id, next); return next; }
  close(id: string) { const value = this.status(id); const next = { ...value, status: "closed" as const }; this.sessions.set(id, next); return next; }
}
