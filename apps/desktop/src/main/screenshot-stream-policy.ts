import type { CaptureState } from "@offersteady/protocol" with { "resolution-mode": "import" };

export const screenshotStreamEligible = (state: CaptureState) =>
  state === "capturing" || state === "error" || state === "reconnecting" || state === "paused";

export const screenshotStreamTransition = (previous: CaptureState, next: CaptureState) => {
  const wasEligible = screenshotStreamEligible(previous);
  const isEligible = screenshotStreamEligible(next);
  if (wasEligible === isEligible) return "preserve" as const;
  return isEligible ? "start" as const : "stop" as const;
};
