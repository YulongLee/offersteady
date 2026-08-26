import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { describe, expect, it } from "vitest";

const pngMetadata = (relativePath: string) => {
  const desktopRoot = path.resolve(import.meta.dirname, "..");
  const bytes = readFileSync(path.join(desktopRoot, relativePath));
  return {
    signature: bytes.subarray(1, 4).toString("ascii"),
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    colorType: bytes.readUInt8(25),
  };
};

const sha256 = (relativePath: string) => {
  const desktopRoot = path.resolve(import.meta.dirname, "..");
  return createHash("sha256").update(readFileSync(path.join(desktopRoot, relativePath))).digest("hex");
};

describe("desktop application icon", () => {
  it("uses the approved high-resolution white-background packaging icon", () => {
    expect(pngMetadata("resources/app-icon.png")).toEqual({
      signature: "PNG",
      width: 1024,
      height: 1024,
      colorType: 2,
    });
    expect(sha256("resources/app-icon.png")).toBe("403b1f6d89a5ada0a153f018c27ef98e1eaf5675850ace041d7ac7096f8fed3d");
  });

  it("keeps the renderer icon on the same approved white-background brand family", () => {
    expect(pngMetadata("src/renderer/assets/app-icon.png")).toEqual({
      signature: "PNG",
      width: 256,
      height: 256,
      colorType: 2,
    });
    expect(sha256("src/renderer/assets/app-icon.png")).toBe("c92cf9662f80f8e8f75c5afa284e0d1c24852c6c3276e80ed88863cf384e19d2");
  });

  it("pins the same icon in both macOS and Windows package configuration", () => {
    const desktopRoot = path.resolve(import.meta.dirname, "..");
    const builderConfig = readFileSync(path.join(desktopRoot, "electron-builder.yml"), "utf8");
    expect(builderConfig.match(/icon: resources\/app-icon\.png/g)).toHaveLength(2);
    const macPackager = readFileSync(path.join(desktopRoot, "scripts/package-local-mac.mjs"), "utf8");
    expect(macPackager).toContain('join(desktopDir, "resources/app-icon.png")');
  });

  it("builds the Windows installer path from the current package version", () => {
    const desktopRoot = path.resolve(import.meta.dirname, "..");
    const desktopPackage = JSON.parse(readFileSync(path.join(desktopRoot, "package.json"), "utf8"));
    expect(desktopPackage.scripts["package:win:installer:x64"]).not.toContain("0.1.13");
    const installerScript = readFileSync(path.join(desktopRoot, "scripts/package-windows-installer.mjs"), "utf8");
    expect(installerScript).toContain("desktopPackage.version");
    expect(installerScript).toContain("electron-builder.yml");
  });
});
