export const appearancePreferencesStorageKey = "offersteady:web-appearance";

export type AnswerFontSize = "normal" | "large";
export type AppearanceTheme = "dark" | "bright";

export interface AppearancePreferences {
  readonly answerFontSize: AnswerFontSize;
  readonly theme: AppearanceTheme;
}

export const defaultAppearancePreferences: AppearancePreferences = Object.freeze({
  answerFontSize: "normal",
  theme: "dark",
});

const isAnswerFontSize = (value: unknown): value is AnswerFontSize => value === "normal" || value === "large";
const isAppearanceTheme = (value: unknown): value is AppearanceTheme => value === "dark" || value === "bright";

export function parseAppearancePreferences(value: unknown): AppearancePreferences {
  let parsed: unknown = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch {
      return defaultAppearancePreferences;
    }
  }
  if (!parsed || typeof parsed !== "object") return defaultAppearancePreferences;
  const candidate = parsed as Record<string, unknown>;
  return {
    answerFontSize: isAnswerFontSize(candidate.answerFontSize) ? candidate.answerFontSize : defaultAppearancePreferences.answerFontSize,
    theme: isAppearanceTheme(candidate.theme) ? candidate.theme : defaultAppearancePreferences.theme,
  };
}

function browserStorage(): Pick<Storage, "getItem" | "setItem"> | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readAppearancePreferences(storage: Pick<Storage, "getItem"> | null = browserStorage()): AppearancePreferences {
  if (!storage) return defaultAppearancePreferences;
  try {
    return parseAppearancePreferences(storage.getItem(appearancePreferencesStorageKey));
  } catch {
    return defaultAppearancePreferences;
  }
}

export function applyAppearancePreferences(
  preferences: AppearancePreferences,
  root: HTMLElement | null = typeof document === "undefined" ? null : document.documentElement,
): void {
  if (!root) return;
  root.dataset.answerFontSize = preferences.answerFontSize;
  root.dataset.theme = preferences.theme;
  root.style.colorScheme = preferences.theme === "bright" ? "light" : "dark";
}

export function persistAppearancePreferences(
  preferences: AppearancePreferences,
  storage: Pick<Storage, "setItem"> | null = browserStorage(),
): boolean {
  if (!storage) return false;
  try {
    storage.setItem(appearancePreferencesStorageKey, JSON.stringify(preferences));
    return true;
  } catch {
    return false;
  }
}

export function applyStoredAppearancePreferences(): AppearancePreferences {
  const preferences = readAppearancePreferences();
  applyAppearancePreferences(preferences);
  return preferences;
}
