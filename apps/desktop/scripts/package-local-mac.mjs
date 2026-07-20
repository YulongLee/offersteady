import { createHash } from "node:crypto";
import { copyFileSync, cpSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const repoRoot = resolve(desktopDir, "../..");
const desktopPackage = JSON.parse(readFileSync(join(desktopDir, "package.json"), "utf8"));
const arch = process.argv[2] || process.arch;

if (process.platform !== "darwin") {
  throw new Error("Local macOS app packaging must run on macOS.");
}

if (arch !== "arm64" && arch !== "x64") {
  throw new Error(`Unsupported macOS architecture: ${arch}`);
}

const electronApp = join(repoRoot, "node_modules/electron/dist/Electron.app");
if (!existsSync(electronApp)) {
  throw new Error(`Electron.app was not found at ${electronApp}. Run npm install first.`);
}

const releaseDir = join(desktopDir, "release");
const archDir = join(releaseDir, `mac-${arch}`);
const packageFolderName = `OfferSteady-Companion-${desktopPackage.version}-macOS-${arch}`;
const packageFolder = join(archDir, packageFolderName);
const appName = "面试稳伴随程序.app";
const appPath = join(packageFolder, appName);
const readmeName = "打开说明.txt";
const readmePath = join(packageFolder, readmeName);
const resourcesAppDir = join(appPath, "Contents/Resources/app");
const resourcesDir = join(appPath, "Contents/Resources");
const sourceIconPng = join(desktopDir, "build/app-icon.png");
const appIconIcns = join(resourcesDir, "offersteady.icns");
const zipName = `OfferSteady-Companion-${desktopPackage.version}-macOS-${arch}.zip`;
const zipPath = join(releaseDir, zipName);
const metadataPath = join(releaseDir, `OfferSteady-Companion-${desktopPackage.version}-macOS-${arch}.json`);

rmSync(archDir, { recursive: true, force: true });
rmSync(zipPath, { force: true });
rmSync(metadataPath, { force: true });
mkdirSync(archDir, { recursive: true });
mkdirSync(packageFolder, { recursive: true });

const copyBundle = spawnSync("ditto", [electronApp, appPath], { encoding: "utf8" });
if (copyBundle.status !== 0) {
  throw new Error(`Failed to copy Electron.app with ditto: ${copyBundle.stderr || copyBundle.stdout}`);
}
mkdirSync(resourcesAppDir, { recursive: true });
cpSync(join(desktopDir, "dist"), join(resourcesAppDir, "dist"), { recursive: true });
if (existsSync(sourceIconPng)) {
  const iconset = join(archDir, "offersteady.iconset");
  rmSync(iconset, { recursive: true, force: true });
  mkdirSync(iconset, { recursive: true });
  const iconSizes = [
    ["icon_16x16.png", 16],
    ["icon_16x16@2x.png", 32],
    ["icon_32x32.png", 32],
    ["icon_32x32@2x.png", 64],
    ["icon_128x128.png", 128],
    ["icon_128x128@2x.png", 256],
    ["icon_256x256.png", 256],
    ["icon_256x256@2x.png", 512],
    ["icon_512x512.png", 512],
    ["icon_512x512@2x.png", 1024],
  ];
  for (const [name, size] of iconSizes) {
    const result = spawnSync("sips", ["-z", String(size), String(size), sourceIconPng, "--out", join(iconset, name)], { encoding: "utf8" });
    if (result.status !== 0) {
      throw new Error(`Failed to generate app icon ${name}: ${result.stderr || result.stdout}`);
    }
  }
  const iconutil = spawnSync("iconutil", ["-c", "icns", iconset, "-o", appIconIcns], { encoding: "utf8" });
  if (iconutil.status !== 0) {
    throw new Error(`Failed to generate macOS icns: ${iconutil.stderr || iconutil.stdout}`);
  }
}
const nativeRuntimePath = join(desktopDir, "dist/native/macos-capture/OfferSteadyCaptureRuntime");
if (!existsSync(nativeRuntimePath)) {
  throw new Error("macOS native capture runtime is missing. Run npm run build:native -w @offersteady/desktop before packaging.");
}
mkdirSync(join(resourcesAppDir, "native/macos-capture"), { recursive: true });
copyFileSync(nativeRuntimePath, join(resourcesAppDir, "native/macos-capture/OfferSteadyCaptureRuntime"));
writeFileSync(
  join(resourcesAppDir, "package.json"),
  JSON.stringify(
    {
      name: desktopPackage.name,
      version: desktopPackage.version,
      productName: "面试稳伴随程序",
      main: "dist/main/index.js",
    },
    null,
    2,
  ),
);

const plistBuddy = "/usr/libexec/PlistBuddy";
const plistSet = (plistPath, key, value) => {
  const result = spawnSync(plistBuddy, ["-c", `Set :${key} ${value}`, plistPath], { encoding: "utf8" });
  if (result.status !== 0) {
    spawnSync(plistBuddy, ["-c", `Add :${key} string ${value}`, plistPath], { encoding: "utf8" });
  }
};
const plist = join(appPath, "Contents/Info.plist");
const appBundleId = "com.offersteady.companion.local";
const helperBundleIds = [
  ["Electron Helper.app/Contents/Info.plist", `${appBundleId}.helper`],
  ["Electron Helper (Renderer).app/Contents/Info.plist", `${appBundleId}.helper.renderer`],
  ["Electron Helper (Plugin).app/Contents/Info.plist", `${appBundleId}.helper.plugin`],
  ["Electron Helper (GPU).app/Contents/Info.plist", `${appBundleId}.helper.gpu`],
];

plistSet(plist, "CFBundleIdentifier", appBundleId);
plistSet(plist, "CFBundleName", "面试稳伴随程序");
plistSet(plist, "CFBundleDisplayName", "面试稳伴随程序");
plistSet(plist, "CFBundleShortVersionString", desktopPackage.version);
plistSet(plist, "CFBundleVersion", desktopPackage.version);
if (existsSync(appIconIcns)) plistSet(plist, "CFBundleIconFile", "offersteady.icns");
plistSet(plist, "LSMinimumSystemVersion", "14.2.0");
plistSet(plist, "NSMicrophoneUsageDescription", "面试稳仅在你明确开始后使用麦克风识别你的表达。");
plistSet(plist, "NSAudioCaptureUsageDescription", "面试稳仅在你明确开始后采集系统音频以识别面试问题。");
plistSet(plist, "NSScreenCaptureUsageDescription", "面试稳仅在你明确授权后使用屏幕视频权限进行屏幕监控和截屏回答，不保存屏幕录像。");
for (const [relativePlist, bundleId] of helperBundleIds) {
  const helperPlist = join(appPath, "Contents/Frameworks", relativePlist);
  if (existsSync(helperPlist)) {
    plistSet(helperPlist, "CFBundleIdentifier", bundleId);
  }
}

const entitlements = join(desktopDir, "build/entitlements.mac.plist");
const configuredSignIdentity = process.env.OFFERSTEADY_MAC_SIGN_IDENTITY?.trim();
const findCodesignIdentity = () => {
  if (configuredSignIdentity) return configuredSignIdentity;
  const result = spawnSync("security", ["find-identity", "-v", "-p", "codesigning"], { encoding: "utf8" });
  if (result.status !== 0) return "-";
  const preferred = result.stdout
    .split("\n")
    .map(line => line.match(/\) [A-F0-9]+ \"(.+)\"/)?.[1])
    .filter(Boolean)
    .find(name => name.includes("Developer ID Application") || name.includes("Apple Development") || name.includes("Mac Developer") || name.includes("OfferSteady Local Code Signing"));
  return preferred || "-";
};
const signIdentity = findCodesignIdentity();
const sign = spawnSync("codesign", ["--force", "--deep", "--sign", signIdentity, "--entitlements", entitlements, appPath], {
  encoding: "utf8",
});
if (sign.status !== 0) {
  throw new Error(`Failed to sign app with identity "${signIdentity}": ${sign.stderr || sign.stdout}`);
}
if (signIdentity === "-") {
  console.warn("OfferSteady local packaging used ad-hoc signing. macOS privacy permissions may need reset after each rebuild.");
}

const verifySignature = spawnSync("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appPath], {
  encoding: "utf8",
});
if (verifySignature.status !== 0) {
  throw new Error(`Generated app failed codesign verification: ${verifySignature.stderr || verifySignature.stdout}`);
}

writeFileSync(
  readmePath,
  [
    "面试稳伴随程序 · 本机开发版",
    "",
    "1. 解压 zip 后，将“面试稳伴随程序.app”拖到“应用程序”或直接双击打开。",
    "2. 如果 macOS 提示无法验证开发者，请右键 App 选择“打开”，或进入“系统设置 → 隐私与安全性”点击“仍要打开”。",
    "3. 首次使用需要按提示授权麦克风、屏幕/系统音频权限。",
    "4. 如果系统设置里已经授权，但程序内测试仍失败，请先退出 App，再到“系统设置 → 隐私与安全性”中移除旧授权后重新打开；也可以在项目根目录执行：",
    "   npm run desktop:reset-privacy-open",
    "5. 系统音频测试需要选择可共享音频的屏幕/窗口，并播放一段会议声音或网页声音；若提示没有系统音频轨道，说明屏幕流拿到了但系统音频没有被 macOS 提供。",
    signIdentity === "-"
      ? "6. 这是本机开发版，当前使用 ad-hoc 签名；每次重新构建后 macOS 隐私权限可能需要重置。"
      : `6. 这是本机开发版，当前使用代码签名身份：${signIdentity}`,
    "",
  ].join("\n"),
  "utf8",
);

const ditto = spawnSync("ditto", ["-c", "-k", "--sequesterRsrc", "--keepParent", packageFolderName, zipPath], {
  cwd: archDir,
  encoding: "utf8",
});
if (ditto.status !== 0) {
  throw new Error(`Failed to create zip with ditto: ${ditto.stderr || ditto.stdout}`);
}

const fileHash = (filePath) => {
  const hash = createHash("sha256");
  hash.update(readFileSync(filePath));
  return hash.digest("hex");
};

const metadata = {
  id: `mac-${arch}-local-dev`,
  platform: "macos",
  architecture: arch,
  displayName: arch === "arm64" ? "macOS Apple Silicon 本机开发版" : "macOS Intel 本机开发版",
  version: desktopPackage.version,
  minimumOs: "macOS 14.2+",
  appPath,
  zipPath,
  fileName: basename(zipPath),
  fileSizeBytes: statSync(zipPath).size,
  sha256: fileHash(zipPath),
  signingStatus: signIdentity === "-" ? "local-development-ad-hoc" : "local-development-signed",
  signingIdentity: signIdentity,
  notarized: false,
  protocolVersion: "2.0",
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

writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);

console.log(`Created ${appPath}`);
console.log(`Created ${zipPath}`);
console.log(`SHA-256 ${metadata.sha256}`);
