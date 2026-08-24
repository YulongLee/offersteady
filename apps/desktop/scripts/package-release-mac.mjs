import { existsSync, readdirSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const EXPECTED_IDENTITY = "Developer ID Application: Yulong li (8Y5FAR3TF3)";
const SIGNING_QUALIFIER = "Yulong li (8Y5FAR3TF3)";
const EXPECTED_TEAM_ID = "8Y5FAR3TF3";
const scriptDir = resolve(fileURLToPath(new URL(".", import.meta.url)));
const desktopDir = resolve(scriptDir, "..");
const repoRoot = resolve(desktopDir, "../..");
const outputDir = join(desktopDir, "release/macos-production");
const arch = process.argv[2] || process.arch;
const prepareOnly = process.argv.includes("--prepare-only");

if (process.platform !== "darwin") throw new Error("macOS release packaging must run on macOS.");
if (arch !== "arm64" && arch !== "x64") throw new Error(`Unsupported macOS architecture: ${arch}`);

const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, { cwd: desktopDir, encoding: "utf8", stdio: "inherit", ...options });
  if (result.status !== 0) throw new Error(`Command failed (${result.status ?? "signal"}): ${command} ${args.join(" ")}`);
};

const identityResult = spawnSync("security", ["find-identity", "-v", "-p", "codesigning"], { encoding: "utf8" });
if (identityResult.status !== 0 || !identityResult.stdout.includes(`"${EXPECTED_IDENTITY}"`)) {
  throw new Error(`Required signing identity is unavailable: ${EXPECTED_IDENTITY}`);
}

const completeNotaryCredentials = () => {
  const apiValues = [process.env.APPLE_API_KEY, process.env.APPLE_API_KEY_ID, process.env.APPLE_API_ISSUER];
  const appleIdValues = [process.env.APPLE_ID, process.env.APPLE_APP_SPECIFIC_PASSWORD, process.env.APPLE_TEAM_ID];
  const hasApiValue = apiValues.some(Boolean);
  const hasAppleIdValue = appleIdValues.some(Boolean);
  if (hasApiValue && !apiValues.every(Boolean)) throw new Error("Incomplete API key credentials: set APPLE_API_KEY, APPLE_API_KEY_ID, and APPLE_API_ISSUER together.");
  if (hasAppleIdValue && !appleIdValues.every(Boolean)) throw new Error("Incomplete Apple ID credentials: set APPLE_ID, APPLE_APP_SPECIFIC_PASSWORD, and APPLE_TEAM_ID together.");
  if (apiValues.every(Boolean) && !existsSync(resolve(process.env.APPLE_API_KEY))) {
    throw new Error("APPLE_API_KEY must be an absolute path to an existing .p8 file outside the repository.");
  }
  return apiValues.every(Boolean) || appleIdValues.every(Boolean) || Boolean(process.env.APPLE_KEYCHAIN_PROFILE);
};

const notarytoolCredentialArgs = () => {
  if (process.env.APPLE_KEYCHAIN_PROFILE) {
    return [
      ...(process.env.APPLE_KEYCHAIN ? ["--keychain", process.env.APPLE_KEYCHAIN] : []),
      "--keychain-profile", process.env.APPLE_KEYCHAIN_PROFILE,
    ];
  }
  if (process.env.APPLE_API_KEY && process.env.APPLE_API_KEY_ID && process.env.APPLE_API_ISSUER) {
    return [
      "--key", resolve(process.env.APPLE_API_KEY),
      "--key-id", process.env.APPLE_API_KEY_ID,
      "--issuer", process.env.APPLE_API_ISSUER,
    ];
  }
  if (process.env.APPLE_ID && process.env.APPLE_APP_SPECIFIC_PASSWORD && process.env.APPLE_TEAM_ID) {
    return [
      "--apple-id", process.env.APPLE_ID,
      "--password", process.env.APPLE_APP_SPECIFIC_PASSWORD,
      "--team-id", process.env.APPLE_TEAM_ID,
    ];
  }
  throw new Error("No complete notarization credentials are available for the final DMG.");
};

const notarizeAndStapleDmg = dmgPath => {
  console.log(`Submitting final DMG for notarization: ${dmgPath}`);
  const result = spawnSync("xcrun", [
    "notarytool", "submit", dmgPath,
    ...notarytoolCredentialArgs(),
    "--wait",
    "--output-format", "json",
  ], { cwd: desktopDir, encoding: "utf8" });
  const output = `${result.stdout || ""}${result.stderr || ""}`.trim();
  if (output) console.log(output);
  if (result.status !== 0) {
    throw new Error(`Final DMG notarization command failed (${result.status ?? "signal"}).`);
  }
  let submission;
  try {
    submission = JSON.parse(result.stdout);
  } catch {
    throw new Error("Final DMG notarization did not return valid JSON status.");
  }
  if (submission.status !== "Accepted") {
    throw new Error(`Final DMG notarization was not accepted (status: ${submission.status || "unknown"}, id: ${submission.id || "unknown"}).`);
  }
  console.log(`Final DMG notarization accepted: ${submission.id}`);
  run("xcrun", ["stapler", "staple", dmgPath]);
};

if (!prepareOnly && !completeNotaryCredentials()) {
  throw new Error(
    "Production notarization credentials are missing. Configure APPLE_API_KEY + APPLE_API_KEY_ID + APPLE_API_ISSUER, " +
    "or APPLE_KEYCHAIN_PROFILE, before creating the official DMG.",
  );
}

if (existsSync(outputDir)) {
  const architectureDirectories = arch === "arm64" ? new Set(["mac-arm64"]) : new Set(["mac", "mac-x64"]);
  for (const entry of readdirSync(outputDir, { withFileTypes: true })) {
    if (architectureDirectories.has(entry.name) || entry.name.includes(`-macOS-${arch}.`)) {
      rmSync(join(outputDir, entry.name), { recursive: true, force: true });
    }
  }
}
run(process.execPath, [join(desktopDir, "scripts/build-native-runtime.mjs"), arch]);
run("npm", ["run", "build"]);

const electronBuilderCli = join(repoRoot, "node_modules/electron-builder/out/cli/cli.js");
const localElectronDist = join(repoRoot, "node_modules/electron/dist");
const localElectronExecutable = join(localElectronDist, "Electron.app/Contents/MacOS/Electron");
const localElectronType = existsSync(localElectronExecutable)
  ? spawnSync("file", ["-b", localElectronExecutable], { encoding: "utf8" }).stdout
  : "";
const localElectronMatchesTarget = arch === "arm64"
  ? localElectronType.includes("arm64")
  : localElectronType.includes("x86_64");
const builderArgs = [
  electronBuilderCli,
  "--mac",
  prepareOnly ? "dir" : "dmg",
  `--${arch}`,
  "--config",
  "electron-builder.release.mac.yml",
];
if (localElectronMatchesTarget) builderArgs.push(`--config.electronDist=${localElectronDist}`);
if (prepareOnly) builderArgs.push("--config.mac.notarize=false");
run(process.execPath, builderArgs, {
  env: {
    ...process.env,
    CSC_NAME: SIGNING_QUALIFIER,
    CSC_IDENTITY_AUTO_DISCOVERY: "true",
  },
});

const findByExtension = (root, extension) => {
  if (!existsSync(root)) return [];
  const found = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isDirectory()) {
      if (entry.name.endsWith(extension)) found.push(path);
      else found.push(...findByExtension(path, extension));
    } else if (entry.name.endsWith(extension)) found.push(path);
  }
  return found;
};

const isTargetArchitecture = path => {
  const executable = join(path, "Contents/MacOS/面试稳伴随程序");
  if (!existsSync(executable)) return false;
  const type = spawnSync("file", ["-b", executable], { encoding: "utf8" }).stdout;
  return arch === "arm64" ? type.includes("arm64") : type.includes("x86_64");
};
const apps = findByExtension(outputDir, ".app")
  .filter(path => path.endsWith("面试稳伴随程序.app"))
  .filter(isTargetArchitecture);
if (apps.length !== 1) throw new Error(`Expected exactly one packaged app, found ${apps.length}.`);
const dmgs = prepareOnly ? [] : findByExtension(outputDir, ".dmg").filter(path => path.endsWith(`-macOS-${arch}.dmg`));
if (!prepareOnly && dmgs.length !== 1) throw new Error(`Expected exactly one official DMG, found ${dmgs.length}.`);

if (!prepareOnly) {
  run("codesign", ["--sign", EXPECTED_IDENTITY, "--force", "--timestamp", dmgs[0]]);
  notarizeAndStapleDmg(dmgs[0]);
}

run(process.execPath, [
  join(desktopDir, "scripts/verify-release-mac.mjs"),
  "--app", apps[0],
  ...(prepareOnly ? ["--allow-unnotarized"] : ["--dmg", dmgs[0]]),
]);

if (!prepareOnly) {
  run(process.execPath, [
    join(desktopDir, "scripts/generate-production-mac-metadata.mjs"),
    arch,
    dmgs[0],
  ]);
}

console.log(`Signing identity: ${EXPECTED_IDENTITY}`);
console.log(`Team identifier: ${EXPECTED_TEAM_ID}`);
console.log(`Application: ${apps[0]}`);
console.log(prepareOnly ? "Prepare build only: notarization and DMG generation intentionally skipped." : `Official DMG: ${dmgs[0]}`);
