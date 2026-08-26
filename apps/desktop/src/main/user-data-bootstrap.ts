import { constants, copyFile, mkdir, readFile, chmod } from "node:fs/promises";
import path from "node:path";

export const STABLE_USER_DATA_SEGMENTS = ["@offersteady", "desktop"] as const;
const IDENTITY_FILE = "device-pairing.json";
const CREDENTIAL_FILE = "device-credential.bin";
const INDEPENDENT_SETTINGS_FILES = ["screenshot-shortcut.json"] as const;

export const stableUserDataDirectory = (appDataDirectory: string) =>
  path.join(appDataDirectory, ...STABLE_USER_DATA_SEGMENTS);

export const legacyUserDataDirectories = (
  appDataDirectory: string,
  originalUserDataDirectory: string,
): readonly string[] => Array.from(new Set([
  originalUserDataDirectory,
  path.join(appDataDirectory, "面试稳伴随程序"),
])).filter((candidate) => path.resolve(candidate) !== path.resolve(stableUserDataDirectory(appDataDirectory)));

const containsValidPairingIdentity = async (directory: string) => {
  try {
    const parsed = JSON.parse(await readFile(path.join(directory, IDENTITY_FILE), "utf8")) as {
      deviceId?: unknown;
      displayName?: unknown;
    };
    return typeof parsed.deviceId === "string" && parsed.deviceId.length > 0
      && typeof parsed.displayName === "string" && parsed.displayName.length > 0;
  } catch {
    return false;
  }
};

const copyAbsentFile = async (source: string, destination: string) => {
  try {
    await copyFile(source, destination, constants.COPYFILE_EXCL);
    await chmod(destination, 0o600).catch(() => undefined);
    return true;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT" || code === "EEXIST") return false;
    throw error;
  }
};

export interface CompanionStateMigrationResult {
  readonly identitySource: string | null;
  readonly copiedFiles: readonly string[];
}

export const migrateLegacyCompanionState = async (input: {
  readonly stableDirectory: string;
  readonly legacyDirectories: readonly string[];
}): Promise<CompanionStateMigrationResult> => {
  await mkdir(input.stableDirectory, { recursive: true, mode: 0o700 });
  const copiedFiles: string[] = [];
  let identitySource: string | null = null;

  if (!(await containsValidPairingIdentity(input.stableDirectory))) {
    for (const legacyDirectory of input.legacyDirectories) {
      if (!(await containsValidPairingIdentity(legacyDirectory))) continue;
      if (await copyAbsentFile(
        path.join(legacyDirectory, IDENTITY_FILE),
        path.join(input.stableDirectory, IDENTITY_FILE),
      )) copiedFiles.push(IDENTITY_FILE);
      identitySource = legacyDirectory;
      if (await copyAbsentFile(
        path.join(legacyDirectory, CREDENTIAL_FILE),
        path.join(input.stableDirectory, CREDENTIAL_FILE),
      )) copiedFiles.push(CREDENTIAL_FILE);
      break;
    }
  }

  for (const settingsFile of INDEPENDENT_SETTINGS_FILES) {
    for (const legacyDirectory of input.legacyDirectories) {
      if (await copyAbsentFile(
        path.join(legacyDirectory, settingsFile),
        path.join(input.stableDirectory, settingsFile),
      )) {
        copiedFiles.push(settingsFile);
        break;
      }
    }
  }

  return { identitySource, copiedFiles };
};
