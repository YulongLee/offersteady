export const SCREENSHOT_LIVE_POLL_MS = 1_200;
// Binding state is a control-plane signal, not the media transport itself.
// Keep the normal path low-frequency; failures still use the bounded backoff
// below and visibility changes can trigger an immediate refresh.
export const BINDING_LIVE_POLL_MS = 10_000;
// Waiting for a binding is still a control-plane state. The first check runs
// immediately; subsequent checks use the same 10-second budget as live state.
export const BINDING_WAITING_POLL_MS = 10_000;
export const BINDING_WAITING_MAX_POLL_MS = 10_000;
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
  serverSuggestedMs?: number,
) => {
  if (state === "failure") return desktopFailureBackoffMs(consecutiveFailures);
  if (state === "idle") {
    if (channel !== "binding") return DESKTOP_IDLE_POLL_MS;
    if (typeof serverSuggestedMs !== "number" || !Number.isFinite(serverSuggestedMs)) return BINDING_WAITING_POLL_MS;
    return Math.max(BINDING_WAITING_POLL_MS, Math.min(BINDING_WAITING_MAX_POLL_MS, Math.round(serverSuggestedMs)));
  }
  return channel === "binding" ? BINDING_LIVE_POLL_MS : SCREENSHOT_LIVE_POLL_MS;
};
