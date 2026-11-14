import path from "node:path";
import os from "node:os";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { floatingReleaseDataDirectory } from "../src/main/floating-release-data";
import { migrateLegacyCompanionState } from "../src/main/user-data-bootstrap";

describe("floating companion data identity", () => {
  it("keeps the published domestic data directory in production", () => {
    expect(floatingReleaseDataDirectory("/synthetic", "2.0.0", true, true, false, false))
      .toBe(path.join("/synthetic", "@offersteady", "desktop"));
  });
  it("keeps unmarked test builds separate from production identity", () => {
    expect(floatingReleaseDataDirectory("/synthetic", "2.0.0", true, false, false, false))
      .toBe(path.join("/synthetic", "@offersteady", "desktop", "local-test", "floating-2.0.0"));
  });
  it("preserves existing production pairing and credential during an upgrade", async () => {
    const root = await mkdtemp(path.join(os.tmpdir(), "offersteady-floating-upgrade-"));
    try {
      const stable = floatingReleaseDataDirectory(root, "2.0.0", true, true, false, false);
      const legacy = path.join(root, "legacy");
      await mkdir(stable, { recursive: true });
      await mkdir(legacy, { recursive: true });
      const identity = JSON.stringify({ deviceId: "synthetic-stable", displayName: "synthetic" });
      await writeFile(path.join(stable, "device-pairing.json"), identity);
      await writeFile(path.join(stable, "device-credential.bin"), "synthetic-existing-credential");
      await writeFile(path.join(legacy, "device-pairing.json"), JSON.stringify({ deviceId: "synthetic-old", displayName: "synthetic" }));
      await writeFile(path.join(legacy, "device-credential.bin"), "synthetic-old-credential");
      await migrateLegacyCompanionState({ stableDirectory: stable, legacyDirectories: [legacy] });
      expect(await readFile(path.join(stable, "device-pairing.json"), "utf8")).toBe(identity);
      expect(await readFile(path.join(stable, "device-credential.bin"), "utf8")).toBe("synthetic-existing-credential");
    } finally { await rm(root, { recursive: true, force: true }); }
  });
  it("preserves the local test and international directories outside floating builds", () => {
    expect(floatingReleaseDataDirectory("/synthetic", "2.0.0", false, true, true, false))
      .toBe(path.join("/synthetic", "@offersteady", "desktop", "local-test"));
    expect(floatingReleaseDataDirectory("/synthetic", "2.0.0", false, true, false, true))
      .toBe(path.join("/synthetic", "@offersteady", "desktop", "global"));
  });
});
