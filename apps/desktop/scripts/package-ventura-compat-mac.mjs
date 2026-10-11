import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const desktopDir = resolve(fileURLToPath(new URL("..", import.meta.url)));
const repoRoot = resolve(desktopDir, "../..");
const desktopPackage = JSON.parse(readFileSync(join(desktopDir, "package.json"), "utf8"));
const arch = "arm64";
const minimumSystemVersion = "13.4.0";
const releaseDir = join(desktopDir, "release/macos-compat-13.4-arm64");
const baseBuilderConfig = join(desktopDir, "electron-builder.release.mac.yml");
const temporaryConfig = join(tmpdir(), `offersteady-ventura13.4-${process.pid}.yml`);
const artifactSuffix = "-Ventura13.4";
const signingIdentity = "Developer ID Application: Yulong li (8Y5FAR3TF3)";
let downloadedElectronDir = null;

if (process.platform !== "darwin") {
  throw new Error("The Ventura compatibility package must be built on macOS.");
}

const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, {
    cwd: desktopDir,
    encoding: "utf8",
    stdio: "inherit",
    ...options,
  });
  if (result.status !== 0) {
    throw new Error(`Command failed (${result.status ?? "signal"}): ${command} ${args.join(" ")}`);
  }
};

const temporaryBuilderConfigText = readFileSync(baseBuilderConfig, "utf8")
  .replace("output: release/macos-production", "output: release/macos-compat-13.4-arm64")
  .replace("minimumSystemVersion: 14.2.0", `minimumSystemVersion: ${minimumSystemVersion}`)
  .replace("notarize: true", "notarize: false")
  .replace(
    "artifactName: OfferSteady-Companion-${version}-macOS-${arch}.${ext}",
    `artifactName: OfferSteady-Companion-\${version}-macOS-\${arch}${artifactSuffix}.\${ext}`,
  );
writeFileSync(temporaryConfig, temporaryBuilderConfigText, "utf8");

const buildEnv = {
  ...process.env,
  OFFERSTEADY_MACOS_MIN_VERSION: minimumSystemVersion,
  CSC_IDENTITY_AUTO_DISCOVERY: "true",
  CSC_NAME: "Yulong li (8Y5FAR3TF3)",
};

try {
  rmSync(releaseDir, { recursive: true, force: true });
  mkdirSync(releaseDir, { recursive: true });

  run(process.execPath, [join(desktopDir, "scripts/build-native-runtime.mjs"), arch], { env: buildEnv });
  run("npm", ["run", "build"], { env: buildEnv });

  const electronBuilderCli = join(repoRoot, "node_modules/electron-builder/out/cli/cli.js");
  if (!existsSync(electronBuilderCli)) {
    throw new Error(`electron-builder was not found at ${electronBuilderCli}`);
  }
  let electronDist = join(repoRoot, "node_modules/electron/dist");
  if (!existsSync(join(electronDist, "Electron.app"))) {
    const expectedArchive = `electron-v${desktopPackage.devDependencies.electron}-darwin-${arch}.zip`;
    const cacheResult = spawnSync(
      "find",
      [join(homedir(), "Library/Caches/electron"), "-type", "f", "-name", expectedArchive],
      { encoding: "utf8" },
    );
    let archive = cacheResult.status === 0 ? cacheResult.stdout.trim().split("\n").filter(Boolean)[0] : null;
    if (!archive) {
      const { downloadArtifact } = await import("@electron/get");
      archive = await downloadArtifact({
        version: desktopPackage.devDependencies.electron,
        artifactName: "electron",
        platform: "darwin",
        arch,
      });
    }
    downloadedElectronDir = mkdtempSync(join(tmpdir(), "offersteady-electron-ventura-"));
    const extract = spawnSync("ditto", ["-x", "-k", archive, downloadedElectronDir], { encoding: "utf8" });
    if (extract.status !== 0) {
      throw new Error(`Failed to extract arm64 Electron: ${extract.stderr || extract.stdout}`);
    }
    electronDist = downloadedElectronDir;
  }
  const electronExecutable = join(electronDist, "Electron.app/Contents/MacOS/Electron");
  if (!existsSync(electronExecutable)) {
    throw new Error(`arm64 Electron distribution was not found at ${electronDist}`);
  }
  const electronType = spawnSync("file", ["-b", electronExecutable], { encoding: "utf8" }).stdout || "";
  if (!electronType.includes("arm64")) {
    throw new Error(`Expected an arm64 Electron distribution, got: ${electronType.trim()}`);
  }
  run(
    process.execPath,
    [electronBuilderCli, "--mac", "--arm64", "--config", temporaryConfig, `--config.electronDist=${electronDist}`],
    { env: buildEnv },
  );

  const dmgs = readdirSync(releaseDir)
    .filter(name => name.endsWith(`${artifactSuffix}.dmg`))
    .map(name => join(releaseDir, name));
  if (dmgs.length !== 1) {
    throw new Error(`Expected exactly one Ventura compatibility DMG, found ${dmgs.length}.`);
  }

  const dmgPath = dmgs[0];
  run("codesign", ["--sign", signingIdentity, "--force", "--timestamp", dmgPath], { env: buildEnv });
  const sha256 = createHash("sha256").update(readFileSync(dmgPath)).digest("hex");
  const metadata = {
    id: "mac-arm64-132-ventura134-compat",
    platform: "macos",
    architecture: arch,
    displayName: "macOS Apple Silicon Ventura 13.4 兼容版（专用）",
    version: desktopPackage.version,
    minimumOs: "macOS 13.4+",
    compatibilityBuild: true,
    baseReleaseVersion: "1.3.2",
    artifactPath: dmgPath,
    fileName: basename(dmgPath),
    fileSizeBytes: statSync(dmgPath).size,
    sha256,
    signingStatus: "app-and-dmg-developer-id-signed",
    dmgSigned: true,
    notarized: false,
    installerType: "dmg",
    protocolVersion: "2.0",
    captureRuntime: "electron-single-owner",
    generatedAtMs: Date.now(),
    developmentOnly: true,
    onlinePublicationEligible: false,
    capabilities: {
      microphone: true,
      systemAudio: true,
      screenCapture: true,
      manualInputFallback: true,
      screenshotFallback: true,
    },
  };
  const metadataPath = join(releaseDir, `${basename(dmgPath, ".dmg")}.json`);
  writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`, "utf8");
  writeFileSync(
    join(releaseDir, "使用说明.txt"),
    [
      "面试稳伴随程序 1.3.2 · macOS Ventura 13.4 专用兼容版",
      "",
      "适用设备：Apple Silicon（M1/M2/M3 等），macOS Ventura 13.4 及以上。",
      "本包仅供指定用户验证，不会更新官网线上下载版本。",
      "App 和 DMG 均已使用 Developer ID 签名，但未提交 Apple 公证；首次打开如被拦截，请右键 App 选择“打开”。",
      "首次进入面试时，请按系统提示授权麦克风、屏幕与系统音频录制权限。",
      "兼容包需要在真实 macOS Ventura 13.4 设备上继续验收音频和屏幕采集。",
      "",
    ].join("\n"),
    "utf8",
  );

  console.log(`Created Ventura compatibility DMG: ${dmgPath}`);
  console.log(`Created compatibility metadata: ${metadataPath}`);
  console.log(`SHA-256: ${sha256}`);
} finally {
  rmSync(temporaryConfig, { force: true });
  if (downloadedElectronDir) rmSync(downloadedElectronDir, { recursive: true, force: true });
}
