export const SCREENSHOT_LIVE_POLL_MS = 1_200;
export const BINDING_LIVE_POLL_MS = 5_000;
export const DESKTOP_IDLE_POLL_MS = 10_000;
export const DESKTOP_FAILURE_MIN_POLL_MS = 5_000;
export const DESKTOP_FAILURE_MAX_POLL_MS = 30_000;

export const desktopFailureBackoffMs = (consecutiveFailures: number) => {
  const exponent = Math.max(0, Math.min(consecutiveFailures - 1, 3));
  return Math.min(DESKTOP_FAILURE_MAX_POLL_MS, DESKTOP_FAILURE_MIN_POLL_MS * (2 ** exponent));
};

export const desktopPollDelayMs = (
  state: "live" | "idle" | "failure",
  consecutiveFailures = 0,
  channel: "screenshot" | "binding" = "screenshot",
) => {
  if (state === "failure") return desktopFailureBackoffMs(consecutiveFailures);
  if (state === "idle") return DESKTOP_IDLE_POLL_MS;
  return channel === "binding" ? BINDING_LIVE_POLL_MS : SCREENSHOT_LIVE_POLL_MS;
};
