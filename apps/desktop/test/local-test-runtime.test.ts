import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { loadLocalTestRuntime, localTestUserDataDirectory } from "../src/main/local-test-runtime";
import { stableUserDataDirectory } from "../src/main/user-data-bootstrap";

const directories: string[] = [];
const configDirectory = (config: unknown) => {
  const directory = mkdtempSync(path.join(os.tmpdir(), "offersteady-local-runtime-"));
  directories.push(directory);
  writeFileSync(path.join(directory, "local-test-runtime.json"), JSON.stringify(config));
  return directory;
};
afterEach(() => { for (const directory of directories.splice(0)) rmSync(directory, { force: true, recursive: true }); });

describe("packaged local test runtime", () => {
  it("uses explicitly packaged loopback endpoints and a profile separate from production", () => {
    const config = { apiBaseUrl: "http://127.0.0.1:8015/api/v1", webWorkspaceUrl: "http://127.0.0.1:5175/app" };
    expect(loadLocalTestRuntime(true, configDirectory(config))).toEqual(config);
    expect(localTestUserDataDirectory("synthetic")).toBe(path.join("synthetic", "@offersteady", "desktop", "local-test"));
    expect(localTestUserDataDirectory("synthetic")).not.toBe(stableUserDataDirectory("synthetic"));
  });

  it("does not affect development or ordinary packaged launches", () => {
    expect(loadLocalTestRuntime(false, configDirectory({ apiBaseUrl: "https://invalid.example", webWorkspaceUrl: "invalid" }))).toBeNull();
    expect(loadLocalTestRuntime(true, path.join(os.tmpdir(), "absent-synthetic-local-runtime"))).toBeNull();
  });

  it.each(["https://127.0.0.1/app", "http://mianshiwen.cn/app", "http://127.0.0.1.evil.example/app", "http://user:secret@127.0.0.1/app", "http://127.0.0.1/app?token=synthetic", "http://192.168.1.2/app"])("rejects a nonlocal or credential-bearing endpoint: %s", endpoint => {
    expect(() => loadLocalTestRuntime(true, configDirectory({ apiBaseUrl: "http://127.0.0.1:8015/api/v1", webWorkspaceUrl: endpoint }))).toThrow();
  });

  it("does not fall back to production when a packaged local configuration is incomplete", () => {
    expect(() => loadLocalTestRuntime(true, configDirectory({ apiBaseUrl: "http://127.0.0.1:8015/api/v1" }))).toThrow();
  });
});
