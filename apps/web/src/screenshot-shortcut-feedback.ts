export const SHORTCUT_SCREENSHOT_RECOVERY_POLL_INTERVAL_MS = 1_500;

export const isFreshShortcutScreenshotAcceptance = (acceptedAtMs: number | undefined, mountedAtMs: number) =>
  (acceptedAtMs ?? 0) >= mountedAtMs - 5_000;
