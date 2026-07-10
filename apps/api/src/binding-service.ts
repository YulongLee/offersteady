import { createHash, randomBytes, randomInt } from "node:crypto";
import type {
  BindingToken,
  DesktopBindingExchangeRequest,
  DesktopBindingExchangeResult,
} from "@offersteady/protocol";

const BINDING_TTL_MS = 10 * 60 * 1_000;
const DEVICE_CREDENTIAL_TTL_MS = 12 * 60 * 60 * 1_000;

interface BindingRecord {
  readonly tokenHash: string;
  readonly manualCode: string;
  readonly sessionId: string;
  readonly userId: string;
  readonly expiresAtMs: number;
  used: boolean;
}

interface DeviceCredentialRecord {
  readonly credentialHash: string;
  readonly sessionId: string;
  readonly userId: string;
  readonly deviceId: string;
  readonly expiresAtMs: number;
  revoked: boolean;
}

export type BindingErrorCode =
  | "binding-invalid"
  | "binding-expired"
  | "binding-used"
  | "binding-scope-mismatch"
  | "device-credential-invalid"
  | "device-credential-expired"
  | "device-revoked";

export class BindingError extends Error {
  constructor(readonly code: BindingErrorCode) {
    super(code);
  }
}

const hashSecret = (value: string): string => createHash("sha256").update(value).digest("hex");
const secureToken = (): string => randomBytes(32).toString("base64url");
const secureManualCode = (): string => randomInt(0, 1_000_000).toString().padStart(6, "0");

export class DesktopBindingService {
  private readonly bindingsByToken = new Map<string, BindingRecord>();
  private readonly bindingTokenByCode = new Map<string, string>();
  private readonly devicesByCredential = new Map<string, DeviceCredentialRecord>();
  private readonly credentialHashByDevice = new Map<string, string>();

  createBinding(sessionId: string, userId: string, nowMs = Date.now()): BindingToken {
    const token = secureToken();
    let manualCode = secureManualCode();
    while (this.bindingTokenByCode.has(manualCode)) manualCode = secureManualCode();
    const tokenHash = hashSecret(token);
    const expiresAtMs = nowMs + BINDING_TTL_MS;
    const record: BindingRecord = {
      tokenHash,
      manualCode,
      sessionId,
      userId,
      expiresAtMs,
      used: false,
    };
    this.bindingsByToken.set(tokenHash, record);
    this.bindingTokenByCode.set(manualCode, tokenHash);
    return {
      token,
      sessionId,
      expiresAtMs,
      deepLink: `offersteady://bind?token=${encodeURIComponent(token)}&session=${encodeURIComponent(sessionId)}`,
      manualCode,
    };
  }

  exchange(request: DesktopBindingExchangeRequest, nowMs = Date.now()): DesktopBindingExchangeResult {
    const tokenHash = this.resolveTokenHash(request.tokenOrCode);
    const binding = tokenHash ? this.bindingsByToken.get(tokenHash) : undefined;
    if (!binding) throw new BindingError("binding-invalid");
    if (binding.used) throw new BindingError("binding-used");
    if (binding.expiresAtMs <= nowMs) throw new BindingError("binding-expired");
    if (binding.sessionId !== request.sessionId || binding.userId !== request.userId) {
      throw new BindingError("binding-scope-mismatch");
    }

    binding.used = true;
    this.bindingTokenByCode.delete(binding.manualCode);
    const credential = secureToken();
    const credentialHash = hashSecret(credential);
    const expiresAtMs = nowMs + DEVICE_CREDENTIAL_TTL_MS;
    this.devicesByCredential.set(credentialHash, {
      credentialHash,
      sessionId: request.sessionId,
      userId: request.userId,
      deviceId: request.deviceId,
      expiresAtMs,
      revoked: false,
    });
    this.credentialHashByDevice.set(request.deviceId, credentialHash);

    return {
      deviceCredential: credential,
      expiresAtMs,
      deviceStatus: {
        deviceId: request.deviceId,
        displayName: request.displayName,
        captureState: "permission-required",
        connected: true,
        activeSourceIds: [],
        capabilities: request.capabilities,
        lastSeenAtMs: nowMs,
      },
    };
  }

  authorize(
    credential: string,
    expectedSessionId: string,
    nowMs = Date.now(),
  ): { readonly userId: string; readonly deviceId: string } {
    const record = this.devicesByCredential.get(hashSecret(credential));
    if (!record || record.sessionId !== expectedSessionId) {
      throw new BindingError("device-credential-invalid");
    }
    if (record.revoked) throw new BindingError("device-revoked");
    if (record.expiresAtMs <= nowMs) throw new BindingError("device-credential-expired");
    return { userId: record.userId, deviceId: record.deviceId };
  }

  revoke(deviceId: string): boolean {
    const credentialHash = this.credentialHashByDevice.get(deviceId);
    if (!credentialHash) return false;
    const record = this.devicesByCredential.get(credentialHash);
    if (!record) return false;
    record.revoked = true;
    return true;
  }

  private resolveTokenHash(tokenOrCode: string): string | undefined {
    if (/^\d{6}$/.test(tokenOrCode)) return this.bindingTokenByCode.get(tokenOrCode);
    return hashSecret(tokenOrCode);
  }
}
