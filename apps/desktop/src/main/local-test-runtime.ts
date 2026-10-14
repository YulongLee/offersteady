import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export interface LocalTestRuntime {
  readonly apiBaseUrl: string;
  readonly webWorkspaceUrl: string;
}

const loopbackUrl = (value: unknown): string => {
  if (typeof value !== "string") throw new Error("Local test runtime requires loopback URLs.");
  const parsed = new URL(value);
  if (parsed.protocol !== "http:"
    || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)
    || parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error("Local test runtime requires plain HTTP loopback URLs without credentials.");
  }
  return parsed.toString().replace(/\/$/, "");
};

/** Packaged, explicit local builds only. Invalid configuration fails closed. */
export const loadLocalTestRuntime = (isPackaged: boolean, resourcesDirectory: string): LocalTestRuntime | null => {
  const configPath = path.join(resourcesDirectory, "local-test-runtime.json");
  if (!isPackaged || !existsSync(configPath)) return null;
  const parsed = JSON.parse(readFileSync(configPath, "utf8")) as Record<string, unknown>;
  return { apiBaseUrl: loopbackUrl(parsed.apiBaseUrl), webWorkspaceUrl: loopbackUrl(parsed.webWorkspaceUrl) };
};

export const localTestUserDataDirectory = (appDataDirectory: string) =>
  path.join(appDataDirectory, "@offersteady", "desktop", "local-test");
