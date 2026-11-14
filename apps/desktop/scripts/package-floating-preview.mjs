import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";
import * as asar from "@electron/asar";
import ts from "typescript";

const desktop = resolve(import.meta.dirname, "..");
const repository = resolve(desktop, "../..");
const version = JSON.parse(readFileSync(join(desktop, "package.json"), "utf8")).version;
const [sourceArg, ...options] = process.argv.slice(2);
const signedLocal = options.includes("--signed-local");
const sevenZip = options.find(option => option !== "--signed-local");
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

const label = mac ? `macOS-${published.architecture}` : "Windows-x64";
const name = `OfferSteady-Companion-${version}-CN-Test-CaptureProtection-${label}`;
const macDmg = mac && !signedLocal;
const output = join(desktop, "release", "floating-preview");
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
  return result.stdout.trim();
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

  writeFileSync(join(root, "打开说明.txt"), [
    `面试稳伴随程序 ${version} · 桌面浮窗本地测试`,
    "",
    mac
      ? `1. 先退出旧助手，再将 ${program} 拷贝到独立的测试目录打开，避免覆盖正在使用的正式版。`
      : `1. 解压整个目录，先退出旧助手，再从解压目录打开 ${program}。`,
    "2. 从 macOS 菜单栏图标或 Windows 托盘图标菜单点击「桌面浮窗」。",
    "3. 浮窗加载国服官网。使用自己的面试稳账号登录并新建面试。准备页自动连接本机助手，无需填写机器码。",
    "4. 浮窗在普通窗口上方保持置顶。默认透明度为 0%（完全不透明），可用顶部滑块调节。拖标题栏移动，拖边缘缩放。",
    mac
      ? "5. 麦克风与电脑输出由主助手收音。如果系统提示授权，请检查「隐私与安全性」中的「麦克风」与「屏幕与系统音频录制」，授权后完全退出并重开候选版。"
      : "5. Windows 免安装。请从会议接收端验证整屏共享，分别测试 0% 和 20% 透明度。",
    mac
      ? "6. 在主助手点「预览」查看屏幕。预览、Control + Shift + 空格和网页截图回答默认排除所有助手窗口。"
      : "6. 正常开始会话或生成回答会使用国服权益。",
    ...(mac ? [
      "7. 助手启动时会请求系统窗口捕获保护。测试飞书时，保持浮窗打开，选择「共享整个桌面」，用另一台设备查看接收画面。",
      "8. 如果会议接收端仍能看到浮窗，可先点「收起」。如果主助手也打开了，用菜单栏的「隐藏助手」将它收起。停止共享后，从菜单栏选择「桌面浮窗」恢复原页面。",
    ] : []),
    ...(signedLocal && mac ? ["9. 此包采用正式签名，供本地验收。"] : []),
    "",
  ].join("\r\n"), "utf8");

  const staged = join(temp, `${name}.${macDmg ? "dmg" : "zip"}`);
  if (macDmg) {
    run("hdiutil", ["create", "-srcfolder", root, "-volname", `面试稳伴随程序 ${version} 测试版`, "-format", "UDZO", staged]);
    run("codesign", ["--force", "--sign", signingIdentity, "--timestamp", staged]);
    notarize(staged, staged);
    run(process.execPath, [join(desktop, "scripts/verify-release-mac.mjs"), "--app", app, "--dmg", staged]);
  } else {
    if (mac) {
      run(process.execPath, [join(desktop, "scripts/verify-release-mac.mjs"), "--app", app, "--allow-unnotarized"]);
    }
    run("ditto", ["-c", "-k", "--keepParent", ...(mac ? [] : ["--norsrc", "--noextattr"]), root, staged]);
    run("unzip", ["-tq", staged]);
  }
  const artifact = join(output, basename(staged));
  cpSync(staged, artifact);
  writeFileSync(`${artifact}.sha256`, `${hash(readFileSync(artifact))}  ${basename(artifact)}\n`, "utf8");
  console.log(artifact);
} finally {
  rmSync(temp, { recursive: true, force: true });
}
