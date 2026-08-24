export const INVALID_REALTIME_SESSION_RETRY_MS = 60_000;
export const REALTIME_FALLBACK_INITIAL_DELAY_MS = 5_000;
export const REALTIME_FALLBACK_MAX_DELAY_MS = 15_000;

export const realtimeRetryDelayMs = (status: number | null, attempt: number) => {
  if (isInvalidRealtimeSessionStatus(status)) return INVALID_REALTIME_SESSION_RETRY_MS;
  return Math.min(15_000, 1_000 * 2 ** Math.min(attempt, 4));
};

export const realtimeFallbackDelayMs = (attempt: number) =>
  Math.min(REALTIME_FALLBACK_MAX_DELAY_MS, REALTIME_FALLBACK_INITIAL_DELAY_MS * 2 ** Math.min(attempt, 2));

export const isInvalidRealtimeSessionStatus = (status: number | null) =>
  status === 401 || status === 403 || status === 404 || status === 409 || status === 410;
