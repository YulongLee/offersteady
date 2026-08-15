import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { downloadArtifact } from "@electron/get";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const desktopPackage = JSON.parse(readFileSync(join(desktopDir, "package.json"), "utf8"));
const releaseDir = join(desktopDir, "release");
const packageName = `OfferSteady-Companion-${desktopPackage.version}-Windows-x64`;
const packageDir = join(releaseDir, "win-x64", packageName);
const zipPath = join(releaseDir, `${packageName}.zip`);
const metadataPath = join(releaseDir, `${packageName}.json`);
const configuredElectronDir = process.env.OFFERSTEADY_WINDOWS_ELECTRON_DIR?.trim();
const downloadDir = configuredElectronDir ? null : mkdtempSync(join(tmpdir(), "offersteady-electron-win-x64-"));

if (downloadDir) {
  const archive = await downloadArtifact({
    version: desktopPackage.devDependencies.electron,
    artifactName: "electron",
    platform: "win32",
    arch: "x64",
  });
  const extract = spawnSync("ditto", ["-x", "-k", archive, downloadDir], { encoding: "utf8" });
  if (extract.status !== 0) throw new Error(`Failed to extract Windows x64 Electron: ${extract.stderr || extract.stdout}`);
}

rmSync(packageDir, { recursive: true, force: true });
rmSync(zipPath, { force: true });
rmSync(metadataPath, { force: true });
mkdirSync(dirname(packageDir), { recursive: true });
if (configuredElectronDir) {
  cpSync(resolve(configuredElectronDir), packageDir, { recursive: true });
} else if (downloadDir) {
  cpSync(downloadDir, packageDir, { recursive: true });
}
renameSync(join(packageDir, "electron.exe"), join(packageDir, "OfferSteady.exe"));

const resourcesAppDir = join(packageDir, "resources/app");
rmSync(resourcesAppDir, { recursive: true, force: true });
mkdirSync(resourcesAppDir, { recursive: true });
cpSync(join(desktopDir, "dist"), join(resourcesAppDir, "dist"), { recursive: true });
rmSync(join(resourcesAppDir, "dist/native"), { recursive: true, force: true });
writeFileSync(join(resourcesAppDir, "package.json"), JSON.stringify({
  name: desktopPackage.name,
  version: desktopPackage.version,
  productName: "面试稳伴随程序",
  main: "dist/main/index.js",
}, null, 2));
writeFileSync(join(packageDir, "打开说明.txt"), [
  "面试稳伴随程序 · Windows x64 测试版",
  "",
  "1. 解压整个 zip，不要只单独拖出 OfferSteady.exe。",
  "2. 双击 OfferSteady.exe 启动。",
  "3. 如果 Windows SmartScreen 提示未知发布者，请先核对下载页 SHA-256，再选择“更多信息 → 仍要运行”。",
  "4. 首次使用请允许麦克风和屏幕捕捉；电脑输出通过 Windows 系统回环音频采集。",
  "5. 当前为未签名测试包，正式发行前仍需 Windows Authenticode 代码签名。",
  "",
].join("\r\n"), "utf8");

const zip = spawnSync("ditto", ["-c", "-k", "--keepParent", basename(packageDir), zipPath], {
  cwd: dirname(packageDir),
  encoding: "utf8",
});
if (zip.status !== 0) throw new Error(`Failed to create Windows x64 zip: ${zip.stderr || zip.stdout}`);

const bytes = readFileSync(zipPath);
const metadata = {
  id: "win-x64-local-dev",
  platform: "windows",
  architecture: "x64",
  displayName: "Windows 10/11 测试版",
  version: desktopPackage.version,
  minimumOs: "Windows 10 22H2+",
  artifactPath: zipPath,
  zipPath,
  fileName: basename(zipPath),
  fileSizeBytes: statSync(zipPath).size,
  sha256: createHash("sha256").update(bytes).digest("hex"),
  signingStatus: "local-development",
  notarized: false,
  protocolVersion: "2.0",
  captureRuntime: "electron-wasapi-loopback",
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
if (downloadDir) rmSync(downloadDir, { recursive: true, force: true });
console.log(`Created ${zipPath}`);
console.log(`Created ${metadataPath}`);
console.log(`SHA-256 ${metadata.sha256}`);
