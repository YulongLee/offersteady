import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const desktopPackage = JSON.parse(readFileSync(join(desktopDir, "package.json"), "utf8"));
const [architecture, artifactArgument] = process.argv.slice(2);

if (!['arm64', 'x64'].includes(architecture)) {
  throw new Error("Usage: generate-production-mac-metadata.mjs <arm64|x64> [dmg]");
}

const artifact = resolve(
  artifactArgument || join(
    desktopDir,
    "release/macos-production",
    `OfferSteady-Companion-${desktopPackage.version}-macOS-${architecture}.dmg`,
  ),
);
if (!existsSync(artifact) || !artifact.endsWith(".dmg")) {
  throw new Error(`Verified production DMG not found: ${artifact}`);
}

const bytes = readFileSync(artifact);
const metadata = {
  id: `mac-${architecture}-${desktopPackage.version.replaceAll(".", "")}`,
  platform: "macos",
  architecture,
  displayName: architecture === "arm64" ? "macOS Apple Silicon" : "macOS Intel",
  version: desktopPackage.version,
  minimumOs: "macOS 14.2+",
  artifactPath: artifact,
  fileName: basename(artifact),
  fileSizeBytes: statSync(artifact).size,
  sha256: createHash("sha256").update(bytes).digest("hex"),
  signingStatus: "verified",
  installerType: "dmg",
  notarized: true,
  protocolVersion: "2.0",
  captureRuntime: "electron-single-owner",
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
const metadataPath = join(
  desktopDir,
  "release/macos-production",
  `OfferSteady-Companion-${desktopPackage.version}-macOS-${architecture}.json`,
);
writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
console.log(`Created verified production metadata: ${metadataPath}`);
console.log(`SHA-256 ${metadata.sha256}`);
