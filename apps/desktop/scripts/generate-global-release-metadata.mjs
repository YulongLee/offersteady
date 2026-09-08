import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";

const desktopRoot = resolve(import.meta.dirname, "..");
const desktopPackage = JSON.parse(readFileSync(join(desktopRoot, "package.json"), "utf8"));
const [platform, architecture, artifactArgument] = process.argv.slice(2);

if (!(["macos", "windows"].includes(platform) && ["arm64", "x64"].includes(architecture))) {
  throw new Error("Usage: generate-global-release-metadata.mjs <macos|windows> <arm64|x64> <artifact>");
}
if (platform === "windows" && architecture !== "x64") throw new Error("Only Windows x64 is supported.");

const artifact = resolve(artifactArgument || "");
if (!existsSync(artifact)) throw new Error(`Global release artifact not found: ${artifact}`);
if (platform === "macos" && !artifact.endsWith(".dmg")) throw new Error("Global macOS publication requires a DMG.");
if (platform === "windows" && !artifact.endsWith(".exe")) throw new Error("Global Windows publication requires an EXE installer.");

const bytes = readFileSync(artifact);
const metadata = {
  id: `${platform === "macos" ? "mac" : "win"}-${architecture}-${desktopPackage.version.replaceAll(".", "")}`,
  platform,
  architecture,
  displayName: platform === "macos"
    ? architecture === "arm64" ? "macOS Apple Silicon" : "macOS Intel"
    : "Windows 10/11 Installer",
  version: desktopPackage.version,
  minimumOs: platform === "macos" ? "macOS 14.2+" : "Windows 10 22H2+",
  artifactPath: artifact,
  fileName: basename(artifact),
  fileSizeBytes: statSync(artifact).size,
  sha256: createHash("sha256").update(bytes).digest("hex"),
  signingStatus: platform === "macos" ? "verified" : "unsigned",
  installerType: platform === "macos" ? "dmg" : "nsis",
  notarized: platform === "macos",
  protocolVersion: "2.0",
  captureRuntime: platform === "macos" ? "electron-single-owner" : "electron-wasapi-loopback",
  generatedAtMs: Date.now(),
  developmentOnly: false,
  capabilities: {
    microphone: true,
    systemAudio: true,
    screenCapture: true,
    manualInputFallback: true,
    screenshotFallback: true,
  },
};

const metadataPath = join(desktopRoot, "release/global", `${artifact.split("/").at(-1).replace(/\.(dmg|exe)$/, "")}.json`);
writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
console.log(metadataPath);
