import type { DesktopArchitecture, DesktopPlatform, DesktopReleaseEntry, DesktopReleaseManifest } from "@offersteady/protocol";

interface ParsedVersion {
  readonly numbers: readonly number[];
  readonly suffix: string | null;
}

export interface CompanionUpdate {
  readonly currentVersion: string;
  readonly release: DesktopReleaseEntry;
}

export interface CompanionVersionRequirement {
  readonly status: "current" | "update-required";
  readonly currentVersion: string | null;
  readonly release: DesktopReleaseEntry | null;
}

const parseVersion = (value: unknown): ParsedVersion | null => {
  if (typeof value !== "string") return null;
  const match = value.trim().match(/^v?(\d+(?:\.\d+)*)([a-z][0-9a-z.-]*)?$/i);
  if (!match?.[1]) return null;
  const numbers = match[1].split(".").map(Number);
  if (numbers.some(part => !Number.isSafeInteger(part))) return null;
  return { numbers, suffix: match[2]?.toLowerCase() ?? null };
};

export const compareDesktopVersions = (left: unknown, right: unknown): number | null => {
  const a = parseVersion(left);
  const b = parseVersion(right);
  if (!a || !b) return null;
  const length = Math.max(a.numbers.length, b.numbers.length);
  for (let index = 0; index < length; index += 1) {
    const difference = (a.numbers[index] ?? 0) - (b.numbers[index] ?? 0);
    if (difference !== 0) return difference < 0 ? -1 : 1;
  }
  if (a.suffix === b.suffix) return 0;
  if (a.suffix === null) return 1;
  if (b.suffix === null) return -1;
  return a.suffix.localeCompare(b.suffix, "en", { numeric: true });
};

const normalizedPlatform = (value: unknown): Exclude<DesktopPlatform, "unsupported"> | null => {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toLowerCase();
  if (["macos", "darwin", "mac"].includes(normalized)) return "macos";
  if (["windows", "win32", "win"].includes(normalized)) return "windows";
  return null;
};

const normalizedArchitecture = (value: unknown): DesktopArchitecture | null => {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toLowerCase();
  if (["arm64", "aarch64"].includes(normalized)) return "arm64";
  if (["x64", "x86_64", "amd64"].includes(normalized)) return "x64";
  if (normalized === "universal") return "universal";
  return null;
};

export const detectDesktopPlatform = (userAgent: string): DesktopPlatform => {
  const normalized = userAgent.toLowerCase();
  if (normalized.includes("windows")) return "windows";
  if (normalized.includes("macintosh") || normalized.includes("mac os")) return "macos";
  return "unsupported";
};

export const detectArchitecture = (userAgent: string, platform = navigator.platform): DesktopArchitecture | null => {
  const text = `${userAgent} ${platform}`.toLowerCase();
  if (text.includes("arm64") || text.includes("aarch64")) return "arm64";
  if (text.includes("x86_64") || text.includes("x64") || text.includes("win64")) return "x64";
  return null;
};

export const downloadableRelease = (entry: DesktopReleaseEntry) => {
  const published = entry.distributionStatus === "published" || entry.signingStatus === "verified";
  const withdrawn = entry.distributionStatus === "withdrawn" || entry.signingStatus === "withdrawn";
  return published && !withdrawn && Boolean(entry.downloadUrl) && /^[a-f0-9]{64}$/i.test(entry.sha256);
};

export const recommendedRelease = (manifest: DesktopReleaseManifest, userAgent: string, platform = navigator.platform) => {
  const os = detectDesktopPlatform(userAgent); const architecture = detectArchitecture(userAgent, platform);
  return manifest.entries.find(entry => entry.platform === os && (!architecture || entry.architecture === architecture) && downloadableRelease(entry)) ?? null;
};

export const companionUpdate = (
  capabilities: Record<string, unknown> | null | undefined,
  manifest: DesktopReleaseManifest,
): CompanionUpdate | null => {
  const requirement = companionVersionRequirement(capabilities, manifest);
  if (requirement.status !== "update-required" || !requirement.currentVersion || !requirement.release) return null;
  if (compareDesktopVersions(requirement.currentVersion, requirement.release.version) !== -1) return null;
  return { currentVersion: requirement.currentVersion, release: requirement.release };
};

export const companionVersionRequirement = (
  capabilities: Record<string, unknown> | null | undefined,
  manifest: DesktopReleaseManifest,
): CompanionVersionRequirement => {
  const currentVersion = typeof capabilities?.appVersion === "string" ? capabilities.appVersion.trim() : "";
  const platform = normalizedPlatform(capabilities?.platform);
  const architecture = normalizedArchitecture(capabilities?.architecture);
  const release = platform && architecture ? manifest.entries
    .filter(entry => entry.platform === platform && entry.architecture === architecture && downloadableRelease(entry) && parseVersion(entry.version))
    .reduce<DesktopReleaseEntry | null>((latest, entry) => {
      if (!latest) return entry;
      const comparison = compareDesktopVersions(entry.version, latest.version);
      if (comparison === null || comparison < 0) return latest;
      if (comparison > 0) return entry;
      return entry.publishedAtMs > latest.publishedAtMs ? entry : latest;
    }, null) : null;
  const comparison = release ? compareDesktopVersions(currentVersion, release.version) : null;
  return {
    status: comparison !== null && comparison >= 0 ? "current" : "update-required",
    currentVersion: currentVersion || null,
    release,
  };
};
