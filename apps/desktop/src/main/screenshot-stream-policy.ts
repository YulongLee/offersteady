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
