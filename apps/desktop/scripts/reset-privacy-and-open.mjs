import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const packagePath = join(desktopDir, "package.json");
const desktopPackage = JSON.parse(readFileSync(packagePath, "utf8"));
const arch = process.argv[2] || process.arch;
const bundleId = "com.offersteady.companion";
const appPath = join(
  desktopDir,
  "release",
  `mac-${arch}`,
  `OfferSteady-Companion-${desktopPackage.version}-macOS-${arch}`,
  "面试稳伴随程序.app",
);

if (process.platform !== "darwin") {
  throw new Error("macOS privacy reset can only run on macOS.");
}

if (!existsSync(appPath)) {
  throw new Error(`Packaged app was not found at ${appPath}. Run npm run package:mac:${arch} -w @offersteady/desktop first.`);
}

const run = (command, args, options = {}) => spawnSync(command, args, { encoding: "utf8", stdio: "inherit", ...options });
const desktopLaunchEnv = { ...process.env };
delete desktopLaunchEnv.ELECTRON_RUN_AS_NODE;

run("osascript", ["-e", 'tell application "面试稳伴随程序" to quit']);
run("pkill", ["-f", "面试稳伴随程序"]);
run("pkill", ["-f", "OfferSteadyCaptureRuntime"]);

const bundleIds = [
  bundleId,
  `${bundleId}.helper`,
  `${bundleId}.helper.renderer`,
  `${bundleId}.helper.plugin`,
  `${bundleId}.helper.gpu`,
  "com.github.Electron.helper",
];

for (const id of bundleIds) {
  for (const service of ["Microphone", "ScreenCapture", "AudioCapture", "SystemPolicyAllFiles"]) {
    const result = spawnSync("tccutil", ["reset", service, id], { encoding: "utf8" });
    if (result.status === 0) {
      console.log(`Reset ${service} permission for ${id}`);
    } else {
      const message = result.stderr || result.stdout || "";
      console.warn(`Skipped ${service} reset for ${id}: ${message.trim() || "service not available on this macOS version"}`);
    }
  }
}

const opened = run("open", ["-n", appPath], { env: desktopLaunchEnv });
if (opened.status !== 0) {
  throw new Error(`Failed to open ${appPath}`);
}

console.log(`Opened ${appPath}`);
