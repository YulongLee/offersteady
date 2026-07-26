export const INVALID_REALTIME_SESSION_RETRY_MS = 60_000;

export const realtimeRetryDelayMs = (status: number | null, attempt: number) => {
  if (status === 401 || status === 403 || status === 404) return INVALID_REALTIME_SESSION_RETRY_MS;
  return Math.min(15_000, 1_000 * 2 ** Math.min(attempt, 4));
};

export const isInvalidRealtimeSessionStatus = (status: number | null) =>
  status === 401 || status === 403 || status === 404;
