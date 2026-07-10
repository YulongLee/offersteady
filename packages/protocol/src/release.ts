import type { DesktopArchitecture, DesktopPlatform } from "./audio.js";

export type ReleaseSigningStatus = "verified" | "pending" | "failed" | "withdrawn" | "local-development";

export interface DesktopReleaseCapabilities {
  readonly microphone: boolean;
  readonly systemAudio: boolean;
  readonly manualInputFallback: boolean;
  readonly screenshotFallback: boolean;
}

export interface DesktopReleaseEntry {
  readonly id: string;
  readonly platform: Exclude<DesktopPlatform, "unsupported">;
  readonly architecture: DesktopArchitecture;
  readonly displayName: string;
  readonly version: string;
  readonly minimumOs: string;
  readonly fileSizeBytes: number;
  readonly sha256: string;
  readonly signingStatus: ReleaseSigningStatus;
  readonly notarized: boolean;
  readonly publishedAtMs: number;
  readonly protocolVersion: string;
  readonly downloadUrl?: string;
  readonly localPath?: string;
  readonly buildCommand?: string;
  readonly developmentOnly?: boolean;
  readonly capabilities: DesktopReleaseCapabilities;
}

export interface DesktopReleaseManifest {
  readonly version: number;
  readonly generatedAtMs: number;
  readonly entries: readonly DesktopReleaseEntry[];
}
