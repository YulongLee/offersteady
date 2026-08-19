import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(scriptDir, "..");
const repositoryDir = resolve(desktopDir, "../..");
const desktopPackage = JSON.parse(readFileSync(join(desktopDir, "package.json"), "utf8"));
const packageDir = join(desktopDir, "release", "win-x64", `OfferSteady-Companion-${desktopPackage.version}-Windows-x64`);
const installer = join(desktopDir, "release", `OfferSteady-Companion-Setup-${desktopPackage.version}-Windows-x64.exe`);
const electronBuilderCli = join(repositoryDir, "node_modules", "electron-builder", "out", "cli", "cli.js");

const run = (command, args, environment = process.env) => {
  const result = spawnSync(command, args, { cwd: desktopDir, env: environment, encoding: "utf8", stdio: "inherit" });
  if (result.status !== 0) throw new Error(`${command} failed with exit code ${result.status ?? "unknown"}`);
};

run(process.execPath, [electronBuilderCli, "--prepackaged", packageDir, "--win", "nsis", "--x64", "--config", "electron-builder.yml"], {
  ...process.env,
  CSC_IDENTITY_AUTO_DISCOVERY: "false",
});
run(process.execPath, [join(scriptDir, "validate-windows-installer.mjs")]);
run(process.execPath, [join(scriptDir, "generate-release-metadata.mjs"), "windows", "x64", installer]);
