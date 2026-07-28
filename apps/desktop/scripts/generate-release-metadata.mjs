import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const desktopPackage = JSON.parse(readFileSync(join(desktopDir, "package.json"), "utf8"));
const [platform, architecture, artifactArgument] = process.argv.slice(2);

if (!["macos", "windows"].includes(platform) || architecture !== "x64") {
  throw new Error("Usage: generate-release-metadata.mjs <macos|windows> x64 [artifact]");
}

const platformLabel = platform === "macos" ? "macOS" : "Windows";
const extension = platform === "macos" ? "zip" : "zip";
const artifact = resolve(
  artifactArgument || join(
    desktopDir,
    "release",
    `OfferSteady-Companion-${desktopPackage.version}-${platformLabel}-${architecture}.${extension}`,
  ),
);
if (!existsSync(artifact)) throw new Error(`Release artifact not found: ${artifact}`);

const bytes = readFileSync(artifact);
const metadata = {
  id: `${platform === "macos" ? "mac" : "win"}-${architecture}-local-dev`,
  platform,
  architecture,
  displayName: platform === "macos" ? "macOS Intel 测试版" : artifact.endsWith(".exe") ? "Windows 10/11 安装版" : "Windows 10/11 便携测试版",
  version: desktopPackage.version,
  minimumOs: platform === "macos" ? "macOS 14.2+" : "Windows 10 22H2+",
  artifactPath: artifact,
  ...(artifact.endsWith(".zip") ? { zipPath: artifact } : {}),
  fileName: basename(artifact),
  fileSizeBytes: statSync(artifact).size,
  sha256: createHash("sha256").update(bytes).digest("hex"),
  signingStatus: "local-development",
  installerType: platform === "windows" && artifact.endsWith(".exe") ? "nsis" : "archive",
  notarized: false,
  protocolVersion: "2.0",
  captureRuntime: platform === "macos" ? "electron-single-owner" : "electron-wasapi-loopback",
  generatedAtMs: Date.now(),
  developmentOnly: true,
  capabilities: {
    microphone: true,
    systemAudio: true,
    screenCapture: true,
    manualInputFallback: true,
    screenshotFallback: true,
  },
};
const metadataPath = join(desktopDir, "release", `OfferSteady-Companion-${desktopPackage.version}-${platformLabel}-${architecture}.json`);
writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
console.log(`Created ${metadataPath}`);
console.log(`SHA-256 ${metadata.sha256}`);
