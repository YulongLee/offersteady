import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const source = join(desktopDir, "native/macos-capture/OfferSteadyCaptureRuntime.swift");
const buildDir = join(desktopDir, "native/macos-capture/build");
const output = join(buildDir, "OfferSteadyCaptureRuntime");
const distDir = join(desktopDir, "dist/native/macos-capture");

if (process.platform !== "darwin") {
  console.log("Skipping macOS native capture runtime build on non-macOS host.");
  process.exit(0);
}

if (!existsSync(source)) {
  throw new Error(`Native runtime source not found: ${source}`);
}

rmSync(buildDir, { recursive: true, force: true });
mkdirSync(buildDir, { recursive: true });

const result = spawnSync("swiftc", [
  source,
  "-O",
  "-framework", "AVFoundation",
  "-framework", "CoreGraphics",
  "-framework", "ScreenCaptureKit",
  "-o", output,
], { encoding: "utf8" });

if (result.status !== 0) {
  throw new Error(`Failed to build macOS native capture runtime:\n${result.stderr || result.stdout}`);
}

rmSync(distDir, { recursive: true, force: true });
mkdirSync(distDir, { recursive: true });
cpSync(output, join(distDir, "OfferSteadyCaptureRuntime"));

console.log(`Built native capture runtime: ${output}`);
