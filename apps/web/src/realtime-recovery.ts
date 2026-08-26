export const INVALID_REALTIME_SESSION_RETRY_MS = 60_000;

export const realtimeRetryDelayMs = (status: number | null, attempt: number) => {
  if (isInvalidRealtimeSessionStatus(status)) return INVALID_REALTIME_SESSION_RETRY_MS;
  if (attempt <= 0) return 0;
  return [2_000, 4_000, 8_000, 15_000][Math.min(attempt - 1, 3)]!;
};

export const realtimeReconnectAttemptAfterRecovery = (
  attempt: number,
  source: "stream-snapshot" | "fallback-snapshot",
) => source === "stream-snapshot" ? 0 : Math.max(0, attempt);

export const isInvalidRealtimeSessionStatus = (status: number | null) =>
  status === 401 || status === 403 || status === 404 || status === 409 || status === 410;
