export const SHORTCUT_SCREENSHOT_RECOVERY_POLL_INTERVAL_MS = 15_000;

export const isFreshShortcutScreenshotAcceptance = (acceptedAtMs: number | undefined, mountedAtMs: number) =>
  (acceptedAtMs ?? 0) >= mountedAtMs - 5_000;
