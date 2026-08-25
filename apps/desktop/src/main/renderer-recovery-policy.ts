export interface RendererRecoveryDecision {
  readonly allowed: boolean;
  readonly attempts: readonly number[];
}

export const decideRendererRecovery = (
  previousAttempts: readonly number[],
  nowMs: number,
  maximumAttempts = 3,
  windowMs = 60_000,
): RendererRecoveryDecision => {
  const recentAttempts = previousAttempts.filter((attemptAtMs) => nowMs - attemptAtMs < windowMs);
  if (recentAttempts.length >= maximumAttempts) {
    return { allowed: false, attempts: recentAttempts };
  }
  return { allowed: true, attempts: [...recentAttempts, nowMs] };
};
