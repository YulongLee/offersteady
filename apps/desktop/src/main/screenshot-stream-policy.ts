import type { CaptureState } from "@offersteady/protocol" with { "resolution-mode": "import" };

export const screenshotStreamEligible = (state: CaptureState) =>
  state === "capturing" || state === "error" || state === "reconnecting" || state === "paused";

export const screenshotStreamTransition = (previous: CaptureState, next: CaptureState) => {
  const wasEligible = screenshotStreamEligible(previous);
  const isEligible = screenshotStreamEligible(next);
  if (wasEligible === isEligible) return "preserve" as const;
  return isEligible ? "start" as const : "stop" as const;
};

export const screenshotStreamAdmissionAction = (status: number | null) =>
  status === 404 || status === 409 ? "suspend" as const : "retry" as const;

export const screenshotStreamSuspensionTransition = (previous: CaptureState, next: CaptureState) =>
  previous !== next && next !== "reconnecting" && screenshotStreamEligible(next)
    ? "resume" as const
    : "preserve" as const;

export interface ScreenshotBindingIdentity {
  readonly sessionId: string;
  readonly bindingId: string;
}

export const screenshotBindingKey = (binding: ScreenshotBindingIdentity | null) =>
  binding?.sessionId && binding.bindingId ? `${binding.sessionId}:${binding.bindingId}` : null;

export const screenshotBindingTransition = (
  previousKey: string | null,
  nextKey: string | null,
  suspended: boolean,
) => {
  if (!nextKey) return previousKey ? "stop" as const : "preserve" as const;
  if (suspended || nextKey !== previousKey) return "restart" as const;
  return "preserve" as const;
};
