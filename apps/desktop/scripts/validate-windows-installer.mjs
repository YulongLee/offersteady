import { access, open, readFile, stat } from "node:fs/promises";
import path from "node:path";

const desktopRoot = path.resolve(import.meta.dirname, "..");
const packageJson = JSON.parse(
  await readFile(path.join(desktopRoot, "package.json"), "utf8"),
);
const builderConfig = await readFile(
  path.join(desktopRoot, "electron-builder.yml"),
  "utf8",
);
const executableNameMatch = builderConfig.match(
  /^\s*executableName:\s*([^\s#]+)\s*$/m,
);

if (!executableNameMatch) {
  throw new Error("electron-builder.yml must define win.executableName");
}

const executableName = executableNameMatch[1];
const releaseRoot = path.join(desktopRoot, "release");
const appDirectory = path.join(
  releaseRoot,
  "win-x64",
  `OfferSteady-Companion-${packageJson.version}-Windows-x64`,
);
const executablePath = path.join(appDirectory, `${executableName}.exe`);
const installerPath = path.join(
  releaseRoot,
  `OfferSteady-Companion-Setup-${packageJson.version}-Windows-x64.exe`,
);

await access(executablePath);
const installer = await stat(installerPath);
if (installer.size < 10 * 1024 * 1024) {
  throw new Error(`Windows installer is unexpectedly small: ${installer.size}`);
}

const installerHandle = await open(installerPath, "r");
const signature = Buffer.alloc(2);
await installerHandle.read(signature, 0, signature.length, 0);
await installerHandle.close();
if (signature[0] !== 0x4d || signature[1] !== 0x5a) {
  throw new Error("Windows installer does not have a valid PE signature");
}

console.log(
  `Windows installer validated: ${path.basename(installerPath)} -> ${executableName}.exe`,
);
