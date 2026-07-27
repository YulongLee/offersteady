import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const LEGACY_SCREENSHOT_SHORTCUT = "CommandOrControl+Shift+Space";
export const DEFAULT_SCREENSHOT_SHORTCUT = "Control+Shift+Space";

export const SCREENSHOT_SHORTCUT_OPTIONS = [
  { accelerator: DEFAULT_SCREENSHOT_SHORTCUT, label: "Control + Shift + Space" },
  { accelerator: "CommandOrControl+Option+S", label: "⌘/Ctrl + Option + S" },
  { accelerator: "CommandOrControl+Shift+S", label: "⌘/Ctrl + Shift + S" },
  { accelerator: "", label: "关闭快捷键" },
] as const;

export const isSupportedScreenshotShortcut = (value: unknown): value is string =>
  typeof value === "string" && SCREENSHOT_SHORTCUT_OPTIONS.some(option => option.accelerator === value);

export class ScreenshotShortcutStore {
  private readonly settingsPath: string;

  constructor(userDataDirectory: string) {
    this.settingsPath = path.join(userDataDirectory, "screenshot-shortcut.json");
  }

  async load(): Promise<string> {
    try {
      const parsed = JSON.parse(await readFile(this.settingsPath, "utf8")) as { accelerator?: unknown };
      if (parsed.accelerator === LEGACY_SCREENSHOT_SHORTCUT) return DEFAULT_SCREENSHOT_SHORTCUT;
      return isSupportedScreenshotShortcut(parsed.accelerator) ? parsed.accelerator : DEFAULT_SCREENSHOT_SHORTCUT;
    } catch {
      return DEFAULT_SCREENSHOT_SHORTCUT;
    }
  }

  async save(accelerator: string): Promise<void> {
    if (!isSupportedScreenshotShortcut(accelerator)) throw new Error("unsupported_screenshot_shortcut");
    await mkdir(path.dirname(this.settingsPath), { recursive: true });
    await writeFile(this.settingsPath, `${JSON.stringify({ accelerator }, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  }
}
