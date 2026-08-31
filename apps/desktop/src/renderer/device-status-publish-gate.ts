export const DEVICE_STATUS_KEEPALIVE_MS = 15_000;

const stableValue = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, entry]) => [key, stableValue(entry)]),
    );
  }
  return value;
};

export const deviceStatusFingerprint = (payload: unknown) => JSON.stringify(stableValue(payload));

export class DeviceStatusPublishGate {
  private lastSuccessfulFingerprint: string | null = null;
  private lastSuccessfulAtMs = 0;

  constructor(private readonly keepaliveMs = DEVICE_STATUS_KEEPALIVE_MS) {}

  shouldPublish(payload: unknown, nowMs = Date.now()) {
    const fingerprint = deviceStatusFingerprint(payload);
    return {
      fingerprint,
      publish: fingerprint !== this.lastSuccessfulFingerprint
        || nowMs - this.lastSuccessfulAtMs >= this.keepaliveMs,
    };
  }

  markSuccessful(fingerprint: string, nowMs = Date.now()) {
    this.lastSuccessfulFingerprint = fingerprint;
    this.lastSuccessfulAtMs = nowMs;
  }
}
