export type IdentityProvider = "wechat" | "sms" | "prototype";
export type IdentityBindingStatus = "active" | "recovery-required" | "revoked";

export interface IdentityAuthorizationState {
  readonly id: string;
  readonly provider: IdentityProvider;
  readonly expiresAtMs: number;
  readonly consumedAtMs?: number;
}

export interface SafeIdentityBinding {
  readonly id: string;
  readonly provider: IdentityProvider;
  readonly displayName: string;
  readonly status: IdentityBindingStatus;
  readonly boundAtMs: number;
  readonly canUnbind: boolean;
}

export interface SafeAccountSummary {
  readonly id: string;
  readonly displayName: string;
  readonly bindings: readonly SafeIdentityBinding[];
  readonly createdAtMs: number;
}

export interface WechatAuthorizationResult {
  readonly account: SafeAccountSummary;
  readonly sessionId: string;
  readonly createdAccount: boolean;
}
