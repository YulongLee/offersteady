import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { constants, copyFileSync, cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";
import * as asar from "@electron/asar";
import ts from "typescript";
import * as resedit from "resedit";

const desktop = resolve(import.meta.dirname, "..");
const repository = resolve(desktop, "../..");
const version = JSON.parse(readFileSync(join(desktop, "package.json"), "utf8")).version;
const [sourceArg, ...options] = process.argv.slice(2);
const prepareOnly = options.includes("--prepare-only");
const sevenZip = options.find(option => option !== "--prepare-only");
if (process.platform !== "darwin" || !sourceArg) {
  throw new Error("On macOS, pass a published CN 1.3.6 DMG or the published Windows installer and the 7zz path.");
}
const source = resolve(sourceArg);
const manifest = JSON.parse(readFileSync(join(repository, "docs/releases/companion-1.3.6-cn-20261102/desktop_release_manifest.json"), "utf8"));
const published = manifest.entries.find(entry => entry.fileName === basename(source));
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
if (!published || statSync(source).size !== published.fileSizeBytes || hash(readFileSync(source)) !== published.sha256) {
  throw new Error("Published package baseline does not match the sealed manifest.");
}
const mac = published.platform === "macos";
if (!mac && !sevenZip) throw new Error("The Windows installer requires the 7zz path.");
if (!mac && prepareOnly) throw new Error("prepare-only applies to Mac only");

const label = mac ? `macOS-${published.architecture}` : "Windows-x64";
if (version !== "2.0.0") throw new Error("Unexpected version");
const name = mac ? `OfferSteady-Companion-${version}-${label}` : `OfferSteady-Companion-Setup-${version}-Windows-x64`;
const macDmg = mac && !prepareOnly;
const output = join(repository, "artifacts", "cn-companion-2.0.0-candidate-r2");
const artifactPath = join(output, prepareOnly ? `${name}-Signed-Not-Notarized.zip` : `${name}.${mac ? "dmg" : "exe"}`);
if (existsSync(artifactPath)) throw new Error(`Refusing to overwrite ${artifactPath}`);
const temp = mkdtempSync(join(tmpdir(), "offersteady-floating-preview-"));
const root = join(temp, name);
const bundleId = "com.offersteady.companion";
const signingIdentity = "Developer ID Application: Yulong li (8Y5FAR3TF3)";
const notaryProfile = process.env.APPLE_KEYCHAIN_PROFILE || "OfferSteady-Notary";

function command(command, args, options = {}) {
  return spawnSync(command, args, { encoding: "utf8", ...options });
}
function run(executable, args, options) {
  const result = command(executable, args, options);
  if (result.status !== 0) throw new Error(`${executable} failed: ${result.error ?? result.stderr ?? result.stdout}`);
  return result.stdout?.trim() ?? "";
}

function makeIndexPatch() {
  const config = ts.readConfigFile(join(desktop, "tsconfig.main.json"), ts.sys.readFile);
  const { options } = ts.parseJsonConfigFileContent(config.config, ts.sys, desktop);
  const baseline = run("git", ["show", "f18dfecf:apps/desktop/src/main/index.ts"], { cwd: repository }) + "\n";
  const compiled = ts.transpileModule(baseline, { fileName: join(desktop, "src/main/index.ts"), compilerOptions: options }).outputText;
  if (hash(compiled) !== "2b1e666f9b05b8669f82e1521f4728b86e326b3401596893a10ef56208661d3d") {
    throw new Error("Unexpected compiled baseline for the desktop menu patch.");
  }
  const baselinePath = join(temp, "baseline.js");
  writeFileSync(baselinePath, compiled);
  const diff = command("diff", ["-U", "1", baselinePath, join(desktop, "dist/main/index.js")]);
  if (diff.status !== 1 || !diff.stdout.includes("桌面浮窗")) throw new Error("The expected menu patch was not built.");
  return diff.stdout;
}

function setPlist(plist, key, value) {
  const executable = "/usr/libexec/PlistBuddy";
  run(executable, ["-c", `Set :${key} ${value}`, plist]);
}

function designatedRequirement(app) {
  const result = command("codesign", ["-d", "-r-", app]);
  const requirement = result.stdout?.match(/^designated => (.+)$/m)?.[1];
  if (result.status !== 0 || !requirement) throw new Error("Could not read the original app permission identity.");
  return requirement;
}

function notarize(submission, stapleTarget) {
  const args = [
    "notarytool", "submit", submission, "--keychain-profile", notaryProfile, "--wait", "--output-format", "json",
  ];
  let response = command("xcrun", args);
  if (response.status !== 0 && /abortedUpload.*connectTimeout/s.test(response.stderr ?? "")) {
    console.log(`Retrying Apple upload without S3 acceleration: ${basename(submission)}`);
    response = command("xcrun", [...args, "--no-s3-acceleration"]);
  }
  if (response.status !== 0) {
    throw new Error(`Apple notarization did not complete for ${basename(submission)}. Check the notarization history.`);
  }
  const result = JSON.parse(response.stdout);
  if (result.status !== "Accepted") {
    throw new Error(`Apple notarization did not accept ${basename(submission)} (${result.status}, ${result.id}).`);
  }
  run("xcrun", ["stapler", "staple", stapleTarget]);
  console.log(`Apple notarization accepted: ${basename(submission)}`);
}

async function patchCompanion(resources, patch) {
  if (existsSync(join(resources, "local-test-runtime.json")) || existsSync(join(resources, "global-runtime-config.json"))) throw new Error("Unexpected runtime configuration");
  writeFileSync(join(resources, "cn-floating-production"), "cn-floating-production-2.0.0\n", { flag: "wx" });
  const archive = join(resources, "app.asar");
  const app = existsSync(archive) ? join(temp, "extracted-app") : join(resources, "app");
  const originalFiles = new Map();
  if (existsSync(archive)) {
    const unpacked = asar.listPackage(archive, { isPack: true }).filter(entry => entry.startsWith("unpack"));
    if (unpacked.length) throw new Error("Unexpected unpacked ASAR layout for this published baseline.");
    asar.extractAll(archive, app);
  }
  const dist = join(app, "dist");
  for (const file of readdirSync(app, { recursive: true, withFileTypes: true })) {
    if (file.isFile()) {
      const relative = join(file.parentPath.slice(app.length + 1), file.name);
      originalFiles.set(relative, hash(readFileSync(join(app, relative))));
    }
  }
  const rendererCount = [...originalFiles.keys()].filter(file => file.startsWith("dist/renderer/")).length;
  if (!rendererCount) throw new Error("Missing original companion renderer.");
  const index = join(dist, "main", "index.js");
  const publishedIndex = readFileSync(index);
  if (hash(publishedIndex) !== "c14038b72525987e5924bee173955ad29f4e8d97cbf757ce9fbde84bdb6b4f59") {
    throw new Error("Unexpected main process input in the sealed CN package.");
  }
  run("patch", ["-s", "-F", "0", index], { input: patch });
  rmSync(`${index}.orig`, { force: true });
  const reverse = join(temp, "reverse.js");
  cpSync(index, reverse);
  run("patch", ["-s", "-R", "-F", "0", reverse], { input: patch });
  if (!readFileSync(reverse).equals(publishedIndex)) throw new Error("Original main process could not be recovered exactly.");

  for (const file of [
    "floating-interview.js", "floating-preview-preload.js", "floating-screen-capture.js", "floating-release-data.js",
  ]) {
    cpSync(join(desktop, "dist/main", file), join(dist, "main", file));
  }
  cpSync(join(desktop, "dist/floating-preview"), join(dist, "floating-preview"), { recursive: true });
  const packagePath = join(app, "package.json");
  const metadata = JSON.parse(readFileSync(packagePath, "utf8"));
  if (metadata.version !== "1.3.6" || metadata.main !== "dist/main/index.js") throw new Error("Unexpected original app entry.");
  writeFileSync(packagePath, JSON.stringify({ ...metadata, version }, null, 2) + "\n");

  if (existsSync(archive)) {
    await asar.createPackage(app, archive);
    asar.uncache(archive);
  }
  for (const [file, expected] of originalFiles) {
    if (file === "dist/main/index.js" || file === "package.json") continue;
    const bytes = existsSync(archive) ? asar.extractFile(archive, file) : readFileSync(join(app, file));
    if (hash(bytes) !== expected) throw new Error(`Original companion file changed: ${file}`);
  }
  console.log(`${originalFiles.size - 2} original companion app files verified byte-for-byte, including all ${rendererCount} renderer files`);
}

try {
  mkdirSync(root, { recursive: true });
  mkdirSync(output, { recursive: true });
  const patch = makeIndexPatch();
  const program = mac ? "面试稳伴随程序.app" : "OfferSteady.exe";
  const app = join(root, program);

  if (mac) {
    const mount = join(temp, "source-dmg");
    mkdirSync(mount);
    run("hdiutil", ["attach", source, "-readonly", "-nobrowse", "-mountpoint", mount]);
    try {
      run("ditto", [join(mount, program), app]);
    } finally {
      run("hdiutil", ["detach", mount]);
    }
    const plist = join(app, "Contents/Info.plist");
    if (run("plutil", ["-extract", "CFBundleIdentifier", "raw", "-o", "-", plist]) !== bundleId) {
      throw new Error("The sealed macOS package does not have the official CN permission identity.");
    }
    const originalRequirement = designatedRequirement(app);
    setPlist(plist, "CFBundleShortVersionString", version);
    setPlist(plist, "CFBundleVersion", version);
    await patchCompanion(join(app, "Contents/Resources"), patch);
    const targetArch = published.architecture === "x64" ? "x86_64" : "arm64";
    const helper = join(app, "Contents/Resources/app/native/macos-capture/OfferSteadyFilteredScreenshot");
    run("swiftc", [
      join(desktop, "native/macos-capture", "OfferSteadyFilteredScreenshot.swift"),
      "-target", `${targetArch}-apple-macos14.2`, "-parse-as-library", "-O", "-o", helper,
    ]);
    run("codesign", [
      "--force", "--sign", signingIdentity, "--timestamp", "--options", "runtime",
      "--identifier", `${bundleId}.filtered-screenshot`, helper,
    ]);
    if (run("lipo", ["-archs", helper]) !== targetArch) throw new Error("Unexpected filtered screenshot helper architecture.");
    // Keep the published audio and renderer helpers' original signatures.
    run("codesign", [
      "--force", "--sign", signingIdentity, "--timestamp", "--options", "runtime",
      "--preserve-metadata=identifier,requirements,entitlements", app,
    ]);
    if (designatedRequirement(app) !== originalRequirement) {
      throw new Error("The Mac candidate changed the official app permission identity.");
    }
    run("codesign", ["--verify", "--deep", "--strict", `-R=${originalRequirement}`, app]);
    const binary = run("/usr/libexec/PlistBuddy", ["-c", "Print :CFBundleExecutable", plist]);
    const expectedArch = published.architecture === "x64" ? "x86_64" : published.architecture;
    if (run("lipo", ["-archs", join(app, "Contents/MacOS", binary)]) !== expectedArch) {
      throw new Error("Unexpected macOS executable architecture.");
    }
    if (macDmg) {
      const submission = join(temp, `${name}-App.zip`);
      run("ditto", ["-c", "-k", "--keepParent", app, submission]);
      notarize(submission, app);
      rmSync(submission);
    }
  } else {
    const seven = resolve(sevenZip);
    run(seven, ["e", "-y", `-o${temp}`, source, "$PLUGINSDIR/app-64.7z"]);
    run(seven, ["x", "-y", `-o${root}`, join(temp, "app-64.7z")]);
    const executable = readFileSync(join(root, program));
    const pe = executable.readUInt32LE(0x3c);
    if (executable.toString("ascii", pe, pe + 4) !== "PE\0\0" || executable.readUInt16LE(pe + 4) !== 0x8664) {
      throw new Error("Unexpected Windows executable architecture.");
    }
    await patchCompanion(join(root, "resources"), patch);
  }

  const staged = join(temp, prepareOnly ? `${name}-Signed-Not-Notarized.zip` : `${name}.${macDmg ? "dmg" : "exe"}`);
  if (macDmg) {
    run("hdiutil", ["create", "-srcfolder", root, "-volname", `面试稳伴随程序 ${version}`, "-format", "UDZO", staged]);
    run("codesign", ["--force", "--sign", signingIdentity, "--timestamp", staged]);
    notarize(staged, staged);
    run(process.execPath, [join(desktop, "scripts/verify-release-mac.mjs"), "--app", app, "--dmg", staged]);
  } else if (prepareOnly) {
    run(process.execPath, [join(desktop, "scripts/verify-release-mac.mjs"), "--app", app, "--allow-unnotarized"]);
    run("ditto", ["-c", "-k", "--keepParent", root, staged]);
    run("unzip", ["-tq", staged]);
  } else {
    const executablePath = join(root, "OfferSteady.exe");
    const executable = resedit.NtExecutable.from(readFileSync(executablePath));
    const resources = resedit.NtExecutableResource.from(executable);
    const versions = resedit.Resource.VersionInfo.fromEntries(resources.entries);
    if (versions.length !== 1) throw new Error("Unexpected Windows version resource");
    versions[0].setFileVersion(2, 0, 0, 0, 1033);
    versions[0].setProductVersion(2, 0, 0, 0, 1033);
    versions[0].outputToResourceEntries(resources.entries);
    resources.outputResource(executable);
    writeFileSync(executablePath, Buffer.from(executable.generate()));
    const stageOutput = join(temp, "installer");
    mkdirSync(stageOutput);
    run(process.execPath, [join(repository, "node_modules/electron-builder/out/cli/cli.js"), "--prepackaged", root,
      "--win", "nsis", "--x64", "--config", join(desktop, "electron-builder.yml"),
      `--config.directories.output=${stageOutput}`, "--config.win.signAndEditExecutable=false"],
      { cwd: desktop, env: { ...process.env, CSC_IDENTITY_AUTO_DISCOVERY: "false" }, stdio: "inherit" });
    const generated = join(stageOutput, `${name}.exe`);
    if (!existsSync(generated)) throw new Error("Expected Windows installer was not produced");
    const verify = join(temp, "verified-windows");
    rmSync(join(temp, "app-64.7z"));
    run(resolve(sevenZip), ["e", "-y", `-o${temp}`, generated, "$PLUGINSDIR/app-64.7z"]);
    run(resolve(sevenZip), ["x", "-y", `-o${verify}`, join(temp, "app-64.7z")]);
    for (const entry of readdirSync(root, { withFileTypes: true, recursive: true })) {
      if (!entry.isFile()) continue;
      const file = join(entry.parentPath, entry.name);
      if (hash(readFileSync(file)) !== hash(readFileSync(join(verify, file.slice(root.length + 1))))) throw new Error("Installer payload mismatch");
    }
    cpSync(generated, staged, { errorOnExist: true });
  }
  const artifact = artifactPath;
  copyFileSync(staged, artifact, constants.COPYFILE_EXCL);
  writeFileSync(`${artifact}.sha256`, `${hash(readFileSync(artifact))}  ${basename(artifact)}\n`, "utf8");
  console.log(artifact);
} finally {
  rmSync(temp, { recursive: true, force: true });
}
