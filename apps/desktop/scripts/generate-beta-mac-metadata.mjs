import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const desktopPackage = JSON.parse(readFileSync(join(desktopDir, "package.json"), "utf8"));
const [architecture, artifactArgument] = process.argv.slice(2);

if (!['arm64', 'x64'].includes(architecture) || !artifactArgument) {
  throw new Error("Usage: generate-beta-mac-metadata.mjs <arm64|x64> <verified-dmg>");
}
const artifact = resolve(artifactArgument);
if (!existsSync(artifact) || !artifact.endsWith(".dmg") || !basename(artifact).includes("-Beta-")) {
  throw new Error(`Verified Beta DMG not found: ${artifact}`);
}

const manifestPath = join(desktopDir, "release/macos-beta/manifest.beta.json");
const previous = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, "utf8")) : { version: 1, entries: [] };
const entry = {
  id: `mac-${architecture}-commercial-realtime-beta`,
  releaseChannel: "beta",
  platform: "macos",
  architecture,
  displayName: architecture === "arm64" ? "macOS Apple 芯片 Beta" : "macOS Intel Beta",
  version: desktopPackage.version,
  bundleId: "com.offersteady.companion.beta",
  applicationName: "面试稳伴随程序 Beta",
  apiOrigin: "https://beta.mianshiwen.cn/api/v1",
  webOrigin: "https://beta.mianshiwen.cn/app",
  fileName: basename(artifact),
  fileSizeBytes: statSync(artifact).size,
  sha256: createHash("sha256").update(readFileSync(artifact)).digest("hex"),
  signingStatus: "verified-developer-id",
  notarized: true,
  stapled: true,
  developmentOnly: true,
  productionManifestEligible: false,
  generatedAtMs: Date.now(),
};
const entries = [...(Array.isArray(previous.entries) ? previous.entries : []).filter(item => item.id !== entry.id), entry]
  .sort((left, right) => left.id.localeCompare(right.id));
writeFileSync(manifestPath, `${JSON.stringify({ version: 1, releaseChannel: "beta", entries }, null, 2)}\n`);
console.log(`Created ${manifestPath}`);
console.log(`SHA-256 ${entry.sha256}`);
