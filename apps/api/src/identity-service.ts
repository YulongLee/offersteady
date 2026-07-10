import type { IdentityAuthorizationState, SafeAccountSummary, SafeIdentityBinding, WechatAuthorizationResult } from "@offersteady/protocol";

export interface WechatIdentityProviderAdapter {
  exchangeCode(code: string): Promise<{ subjectId: string; displayName: string }>;
}

export class IdentityError extends Error {
  constructor(readonly code: "invalid-state" | "collision" | "forbidden" | "not-found" | "provider-error", message: string) { super(message); }
}

interface InternalAccount { id: string; displayName: string; createdAtMs: number; bindings: Map<string, SafeIdentityBinding> }

export class IdentityService {
  private states = new Map<string, IdentityAuthorizationState>();
  private accounts = new Map<string, InternalAccount>();
  private subjectOwners = new Map<string, string>();
  private counter = 0;

  constructor(private readonly provider: WechatIdentityProviderAdapter) {}

  createWechatState(nowMs = Date.now(), ttlMs = 5 * 60_000) {
    const state: IdentityAuthorizationState = { id: `wechat-state-${++this.counter}`, provider: "wechat", expiresAtMs: nowMs + ttlMs };
    this.states.set(state.id, state); return state;
  }

  async completeWechat(stateId: string, code: string, nowMs = Date.now()): Promise<WechatAuthorizationResult> {
    const state = this.consumeState(stateId, nowMs);
    let identity: { subjectId: string; displayName: string };
    try { identity = await this.provider.exchangeCode(code); } catch { throw new IdentityError("provider-error", "微信授权暂时不可用"); }
    const ownerId = this.subjectOwners.get(identity.subjectId);
    if (ownerId) return { account: this.safeAccount(this.account(ownerId)), sessionId: `session-${state.id}`, createdAccount: false };
    const account: InternalAccount = { id: `account-${++this.counter}`, displayName: identity.displayName || "微信用户", createdAtMs: nowMs, bindings: new Map() };
    const binding = this.binding(identity.displayName, nowMs, account.bindings.size === 0);
    account.bindings.set(binding.id, binding); this.accounts.set(account.id, account); this.subjectOwners.set(identity.subjectId, account.id);
    return { account: this.safeAccount(account), sessionId: `session-${state.id}`, createdAccount: true };
  }

  async bindWechat(accountId: string, stateId: string, code: string, reauthenticated: boolean, nowMs = Date.now()) {
    if (!reauthenticated) throw new IdentityError("forbidden", "需要重新验证当前账号");
    this.consumeState(stateId, nowMs);
    const identity = await this.provider.exchangeCode(code);
    const owner = this.subjectOwners.get(identity.subjectId);
    if (owner && owner !== accountId) throw new IdentityError("collision", "该微信身份已绑定其他账号");
    const account = this.account(accountId);
    const existing = [...account.bindings.values()].find(item => item.provider === "wechat" && item.status === "active"); if (existing) return existing;
    const binding = this.binding(identity.displayName, nowMs, false); account.bindings.set(binding.id, binding); this.subjectOwners.set(identity.subjectId, accountId); return binding;
  }

  unbind(accountId: string, bindingId: string) {
    const account = this.account(accountId); const binding = account.bindings.get(bindingId); if (!binding) throw new IdentityError("not-found", "登录方式不存在");
    const active = [...account.bindings.values()].filter(item => item.status === "active");
    if (active.length <= 1) throw new IdentityError("forbidden", "请先添加其他恢复方式");
    account.bindings.set(bindingId, { ...binding, status: "revoked", canUnbind: false });
  }

  private consumeState(id: string, nowMs: number) {
    const state = this.states.get(id); if (!state || state.expiresAtMs <= nowMs || state.consumedAtMs) throw new IdentityError("invalid-state", "授权状态已失效");
    const consumed = { ...state, consumedAtMs: nowMs }; this.states.set(id, consumed); return consumed;
  }
  private binding(displayName: string, nowMs: number, only: boolean): SafeIdentityBinding { return { id: `binding-${++this.counter}`, provider: "wechat", displayName: displayName || "微信账号", status: "active", boundAtMs: nowMs, canUnbind: !only }; }
  private account(id: string) { const value = this.accounts.get(id); if (!value) throw new IdentityError("not-found", "账号不存在"); return value; }
  private safeAccount(account: InternalAccount): SafeAccountSummary { return { id: account.id, displayName: account.displayName, bindings: [...account.bindings.values()], createdAtMs: account.createdAtMs }; }
}
