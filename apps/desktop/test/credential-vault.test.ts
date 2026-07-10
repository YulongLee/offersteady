import { mkdtemp, readFile, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { rm } from "node:fs/promises";

import { DeviceCredentialVault, type SecureStorageAdapter } from "../src/main/credential-vault";

const directories: string[] = [];
const fakeSecureStorage: SecureStorageAdapter = {
  isEncryptionAvailable: () => true,
  encryptString: (value) => Buffer.from(`encrypted:${value}`, "utf8"),
  decryptString: (value) => value.toString("utf8").replace(/^encrypted:/, ""),
};

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })));
});

describe("DeviceCredentialVault", () => {
  it("stores only encrypted bytes with owner-only permissions", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "offersteady-vault-"));
    directories.push(directory);
    const vault = new DeviceCredentialVault(directory, fakeSecureStorage);
    await vault.save("raw-secret");
    const filePath = path.join(directory, "device-credential.bin");
    expect((await readFile(filePath, "utf8"))).toBe("encrypted:raw-secret");
    expect((await stat(filePath)).mode & 0o777).toBe(0o600);
    await expect(vault.load()).resolves.toBe("raw-secret");
  });

  it("clears a credential and handles an empty vault", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "offersteady-vault-"));
    directories.push(directory);
    const vault = new DeviceCredentialVault(directory, fakeSecureStorage);
    await vault.save("raw-secret");
    await vault.clear();
    await expect(vault.load()).resolves.toBeNull();
  });

  it("refuses plaintext fallback when OS encryption is unavailable", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "offersteady-vault-"));
    directories.push(directory);
    const vault = new DeviceCredentialVault(directory, {
      ...fakeSecureStorage,
      isEncryptionAvailable: () => false,
    });
    await expect(vault.save("raw-secret")).rejects.toThrow("secure-storage-unavailable");
  });
});
