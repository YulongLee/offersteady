import type { AudioSourceHealth, AudioSourceKind } from "@offersteady/protocol";

export const AUDIO_READINESS_TTL_MS = 120_000;

export const sourceSignalVerificationThreshold = (sourceKind: AudioSourceKind): number =>
  sourceKind === "system" ? 0.00045 : 0.0012;

export const signalEvidenceIsFresh = (
  lastSignalAtMs: number | undefined,
  nowMs = Date.now(),
  ttlMs = AUDIO_READINESS_TTL_MS,
): boolean => Boolean(lastSignalAtMs && nowMs >= lastSignalAtMs && nowMs - lastSignalAtMs <= ttlMs);

export const sourceHealthIsAudioReady = (
  health: AudioSourceHealth | undefined,
  nowMs = Date.now(),
): boolean => Boolean(
  health
  && (health.state === "receiving" || health.state === "silent")
  && signalEvidenceIsFresh(health.lastSignalAtMs, nowMs),
);

export const readinessFields = (
  lastSignalAtMs: number | undefined,
  nowMs = Date.now(),
): Pick<AudioSourceHealth, "lastSignalAtMs" | "readinessState" | "readinessExpiresAtMs"> => {
  if (!lastSignalAtMs) return { readinessState: "unchecked" };
  const readinessExpiresAtMs = lastSignalAtMs + AUDIO_READINESS_TTL_MS;
  return {
    lastSignalAtMs,
    readinessExpiresAtMs,
    readinessState: signalEvidenceIsFresh(lastSignalAtMs, nowMs) ? "ready" : "stale",
  };
};
