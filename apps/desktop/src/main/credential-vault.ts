import { chmod, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";

export interface SecureStorageAdapter {
  isEncryptionAvailable: () => boolean;
  encryptString: (value: string) => Buffer;
  decryptString: (value: Buffer) => string;
}

export class DeviceCredentialVault {
  private readonly credentialPath: string;

  constructor(
    userDataDirectory: string,
    private readonly secureStorage: SecureStorageAdapter,
  ) {
    this.credentialPath = path.join(userDataDirectory, "device-credential.bin");
  }

  async save(credential: string): Promise<void> {
    if (!credential) throw new Error("credential-required");
    if (!this.secureStorage.isEncryptionAvailable()) throw new Error("secure-storage-unavailable");
    await mkdir(path.dirname(this.credentialPath), { recursive: true });
    const encrypted = this.secureStorage.encryptString(credential);
    await writeFile(this.credentialPath, encrypted, { mode: 0o600 });
    await chmod(this.credentialPath, 0o600);
  }

  async load(): Promise<string | null> {
    try {
      const encrypted = await readFile(this.credentialPath);
      if (!this.secureStorage.isEncryptionAvailable()) return null;
      return this.secureStorage.decryptString(encrypted);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
      throw error;
    }
  }

  async clear(): Promise<void> {
    await rm(this.credentialPath, { force: true });
  }
}
