import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";

import {
  legacyUserDataDirectories,
  migrateLegacyCompanionState,
  stableUserDataDirectory,
} from "../src/main/user-data-bootstrap";

describe("stable companion user data", () => {
  it("uses one product-owned directory regardless of the original launch directory", () => {
    const appData = path.join("tmp", "Application Support");
    expect(stableUserDataDirectory(appData)).toBe(path.join(appData, "@offersteady", "desktop"));
    expect(legacyUserDataDirectories(appData, path.join(appData, "面试稳伴随程序")))
      .toEqual([path.join(appData, "面试稳伴随程序")]);
  });

  it("migrates only the allowlisted identity bundle and settings", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "offersteady-user-data-"));
    const legacy = path.join(root, "面试稳伴随程序");
    const stable = stableUserDataDirectory(root);
    await mkdir(legacy, { recursive: true });
    await writeFile(path.join(legacy, "device-pairing.json"), JSON.stringify({ deviceId: "device-legacy", displayName: "Legacy Mac" }));
    await writeFile(path.join(legacy, "device-credential.bin"), "encrypted");
    await writeFile(path.join(legacy, "screenshot-shortcut.json"), JSON.stringify({ accelerator: "Control+Shift+Space" }));
    await writeFile(path.join(legacy, "realtime-audio-transport-diagnostics.ndjson"), "must-not-copy");
    await mkdir(path.join(legacy, "Cache"));

    const result = await migrateLegacyCompanionState({ stableDirectory: stable, legacyDirectories: [legacy] });

    expect(result.identitySource).toBe(legacy);
    expect(result.copiedFiles).toEqual([
      "device-pairing.json",
      "device-credential.bin",
      "screenshot-shortcut.json",
    ]);
    expect(await readFile(path.join(stable, "device-pairing.json"), "utf8")).toContain("device-legacy");
    await expect(readFile(path.join(stable, "realtime-audio-transport-diagnostics.ndjson"), "utf8")).rejects.toMatchObject({ code: "ENOENT" });
    await expect(readFile(path.join(stable, "Cache"), "utf8")).rejects.toMatchObject({ code: "ENOENT" });
  });

  it("never overwrites an existing stable identity with a legacy identity", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "offersteady-user-data-existing-"));
    const legacy = path.join(root, "面试稳伴随程序");
    const stable = stableUserDataDirectory(root);
    await mkdir(legacy, { recursive: true });
    await mkdir(stable, { recursive: true });
    await writeFile(path.join(legacy, "device-pairing.json"), JSON.stringify({ deviceId: "device-legacy", displayName: "Legacy Mac" }));
    await writeFile(path.join(stable, "device-pairing.json"), JSON.stringify({ deviceId: "device-stable", displayName: "Stable Mac" }));

    const result = await migrateLegacyCompanionState({ stableDirectory: stable, legacyDirectories: [legacy] });

    expect(result.identitySource).toBeNull();
    expect(await readFile(path.join(stable, "device-pairing.json"), "utf8")).toContain("device-stable");
  });
});
