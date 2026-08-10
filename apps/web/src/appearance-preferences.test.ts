import { afterEach, describe, expect, it } from "vitest";

import {
  appearancePreferencesStorageKey,
  applyAppearancePreferences,
  defaultAppearancePreferences,
  parseAppearancePreferences,
  persistAppearancePreferences,
  readAppearancePreferences,
} from "./appearance-preferences";

afterEach(() => {
  document.documentElement.removeAttribute("data-answer-font-size");
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.style.removeProperty("color-scheme");
});

describe("appearance preferences", () => {
  it("accepts only supported font sizes and themes", () => {
    expect(parseAppearancePreferences('{"answerFontSize":"large","theme":"bright"}')).toEqual({ answerFontSize: "large", theme: "bright" });
    expect(parseAppearancePreferences('{"answerFontSize":"huge","theme":"neon"}')).toEqual(defaultAppearancePreferences);
    expect(parseAppearancePreferences("not-json")).toEqual(defaultAppearancePreferences);
  });

  it("falls back safely when storage is unavailable or malformed", () => {
    expect(readAppearancePreferences({ getItem: () => { throw new Error("blocked"); } })).toEqual(defaultAppearancePreferences);
    expect(readAppearancePreferences({ getItem: () => "{" })).toEqual(defaultAppearancePreferences);
    expect(persistAppearancePreferences(defaultAppearancePreferences, { setItem: () => { throw new Error("full"); } })).toBe(false);
  });

  it("persists preferences and applies root attributes", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => { values.set(key, value); },
    };
    const preferences = { answerFontSize: "large", theme: "bright" } as const;
    expect(persistAppearancePreferences(preferences, storage)).toBe(true);
    expect(values.get(appearancePreferencesStorageKey)).toBe(JSON.stringify(preferences));
    expect(readAppearancePreferences(storage)).toEqual(preferences);
    applyAppearancePreferences(preferences);
    expect(document.documentElement).toHaveAttribute("data-answer-font-size", "large");
    expect(document.documentElement).toHaveAttribute("data-theme", "bright");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });
});
