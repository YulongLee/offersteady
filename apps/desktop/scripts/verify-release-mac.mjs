import { existsSync, lstatSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const valueAfter = flag => {
  const index = process.argv.indexOf(flag);
  return index >= 0 ? process.argv[index + 1] : undefined;
};
const EXPECTED_BUNDLE_ID = valueAfter("--bundle-id") || "com.offersteady.companion";
const EXPECTED_IDENTITY = "Developer ID Application: Yulong li (8Y5FAR3TF3)";
const EXPECTED_TEAM_ID = "8Y5FAR3TF3";

const appPath = valueAfter("--app") ? resolve(valueAfter("--app")) : null;
const dmgPath = valueAfter("--dmg") ? resolve(valueAfter("--dmg")) : null;
const allowUnnotarized = process.argv.includes("--allow-unnotarized");

if (process.platform !== "darwin") throw new Error("macOS release verification must run on macOS.");
if (!appPath || !existsSync(appPath)) throw new Error("--app must point to an existing packaged .app.");
if (!allowUnnotarized && (!dmgPath || !existsSync(dmgPath))) throw new Error("Official verification requires an existing --dmg artifact.");

const execute = (command, args, { allowFailure = false } = {}) => {
  const result = spawnSync(command, args, { encoding: "utf8" });
  const output = `${result.stdout || ""}${result.stderr || ""}`.trim();
  if (!allowFailure && result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed (${result.status ?? "signal"}):\n${output}`);
  }
  return { status: result.status, output };
};

const signatureDetails = path => execute("codesign", ["-dv", "--verbose=4", path]).output;
const assertDeveloperIdSignature = (path, { requireRuntime = false } = {}) => {
  execute("codesign", ["--verify", "--strict", "--verbose=2", path]);
  const details = signatureDetails(path);
  if (!details.includes(`Authority=${EXPECTED_IDENTITY}`)) throw new Error(`Unexpected signing authority for ${path}`);
  if (!details.includes(`TeamIdentifier=${EXPECTED_TEAM_ID}`)) throw new Error(`Unexpected TeamIdentifier for ${path}`);
  if (requireRuntime && !/flags=.*\bruntime\b/.test(details)) throw new Error(`Hardened Runtime is missing for ${path}`);
  if (!details.includes("Timestamp=")) throw new Error(`Trusted timestamp is missing for ${path}`);
};

execute("codesign", ["--verify", "--deep", "--strict", "--verbose=2", appPath]);
const appDetails = signatureDetails(appPath);
if (!appDetails.includes(`Identifier=${EXPECTED_BUNDLE_ID}`)) throw new Error(`Bundle identifier changed from ${EXPECTED_BUNDLE_ID}.`);
assertDeveloperIdSignature(appPath, { requireRuntime: true });

const infoPlist = join(appPath, "Contents/Info.plist");
for (const usageKey of ["NSMicrophoneUsageDescription", "NSAudioCaptureUsageDescription", "NSScreenCaptureUsageDescription"]) {
  const usage = execute("plutil", ["-extract", usageKey, "raw", "-o", "-", infoPlist]).output;
  if (!usage.trim()) throw new Error(`Missing ${usageKey} in packaged Info.plist.`);
}
const entitlements = execute("codesign", ["-d", "--entitlements", ":-", appPath]).output;
if (!entitlements.includes("com.apple.security.cs.allow-jit")) throw new Error("Electron JIT entitlement is missing.");
for (const forbidden of ["com.apple.security.cs.allow-unsigned-executable-memory", "com.apple.security.app-sandbox"]) {
  if (entitlements.includes(forbidden)) throw new Error(`Unneeded release entitlement is present: ${forbidden}`);
}

const regularFiles = root => {
  const results = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) results.push(...regularFiles(path));
    else if (entry.isFile() && lstatSync(path).isFile()) results.push(path);
  }
  return results;
};
const machoFiles = regularFiles(join(appPath, "Contents")).filter(path => {
  const type = execute("file", ["-b", path], { allowFailure: true });
  return type.status === 0 && type.output.includes("Mach-O");
});
if (machoFiles.length === 0) throw new Error("No Mach-O components found in packaged application.");
for (const path of machoFiles) assertDeveloperIdSignature(path);

if (allowUnnotarized) {
  console.log(`codesign verification: PASS (${machoFiles.length} Mach-O components)`);
  console.log("Gatekeeper verification: PENDING (prepare-only build is not notarized)");
  console.log("stapler verification: PENDING (prepare-only build is not notarized)");
  process.exit(0);
}

execute("hdiutil", ["verify", dmgPath]);
assertDeveloperIdSignature(dmgPath);
const appGatekeeper = execute("spctl", ["--assess", "--type", "execute", "--verbose", appPath]);
const appStapler = execute("xcrun", ["stapler", "validate", appPath]);
const dmgGatekeeper = execute("spctl", ["--assess", "--type", "open", "--context", "context:primary-signature", "--verbose", dmgPath]);
const dmgStapler = execute("xcrun", ["stapler", "validate", dmgPath]);

console.log(`codesign verification: PASS (${machoFiles.length} Mach-O components)`);
console.log(`App Gatekeeper verification: PASS (${appGatekeeper.output || "accepted"})`);
console.log(`App stapler verification: PASS (${appStapler.output || "ticket valid"})`);
console.log(`DMG Gatekeeper verification: PASS (${dmgGatekeeper.output || "accepted"})`);
console.log(`DMG stapler verification: PASS (${dmgStapler.output || "ticket valid"})`);
console.log(`DMG verification: PASS (${dmgPath})`);
