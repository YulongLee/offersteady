import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { createHash, randomUUID } from "node:crypto";

export interface DevicePairingIdentity {
  readonly deviceId: string;
  readonly manualCode: string;
  readonly displayName: string;
}

interface DevicePairingFile {
  readonly deviceId: string;
  readonly displayName: string;
}

const codeFromDeviceId = (deviceId: string): string => {
  const digest = createHash("sha256").update(deviceId).digest();
  const number = digest.readUInt32BE(0);
  return String(100000 + (number % 900000));
};

const isDevicePairingFile = (value: unknown): value is DevicePairingFile => {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<DevicePairingFile>;
  return typeof candidate.deviceId === "string" && candidate.deviceId.length > 0
    && typeof candidate.displayName === "string" && candidate.displayName.length > 0;
};

export class DevicePairingIdentityStore {
  private readonly identityPath: string;

  constructor(userDataDirectory: string) {
    this.identityPath = path.join(userDataDirectory, "device-pairing.json");
  }

  async loadOrCreate(defaultDisplayName: string): Promise<DevicePairingIdentity> {
    const existing = await this.load();
    if (existing) return existing;
    const identityFile: DevicePairingFile = {
      deviceId: `device-${randomUUID()}`,
      displayName: defaultDisplayName,
    };
    await mkdir(path.dirname(this.identityPath), { recursive: true });
    await writeFile(this.identityPath, `${JSON.stringify(identityFile, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
    return this.toIdentity(identityFile);
  }

  async load(): Promise<DevicePairingIdentity | null> {
    try {
      const raw = await readFile(this.identityPath, "utf8");
      const parsed: unknown = JSON.parse(raw);
      if (!isDevicePairingFile(parsed)) return null;
      return this.toIdentity(parsed);
    } catch {
      return null;
    }
  }

  async reset(): Promise<void> {
    try {
      await unlink(this.identityPath);
    } catch {
      return;
    }
  }

  private toIdentity(file: DevicePairingFile): DevicePairingIdentity {
    return {
      deviceId: file.deviceId,
      displayName: file.displayName,
      manualCode: codeFromDeviceId(file.deviceId),
    };
  }
}
