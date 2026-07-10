import { mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { DevicePairingIdentityStore } from "../src/main/device-pairing";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })));
});

describe("DevicePairingIdentityStore", () => {
  it("keeps one stable manual code for one local machine identity", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "offersteady-pairing-"));
    directories.push(directory);
    const store = new DevicePairingIdentityStore(directory);

    const first = await store.loadOrCreate("面试稳伴随程序 · Mac");
    const second = await new DevicePairingIdentityStore(directory).loadOrCreate("ignored");

    expect(first.deviceId).toMatch(/^device-/);
    expect(first.manualCode).toMatch(/^[0-9]{6}$/);
    expect(second).toEqual(first);
  });

  it("returns null for an empty pairing store", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "offersteady-pairing-"));
    directories.push(directory);
    const store = new DevicePairingIdentityStore(directory);

    await expect(store.load()).resolves.toBeNull();
  });
});
