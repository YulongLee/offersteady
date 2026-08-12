import type { DesktopArchitecture, DesktopPlatform, DesktopReleaseEntry, DesktopReleaseManifest } from "@offersteady/protocol";

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
