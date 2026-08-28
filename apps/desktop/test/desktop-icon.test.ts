import { readFileSync } from "node:fs";
import path from "node:path";
import { inflateSync } from "node:zlib";
import { describe, expect, it } from "vitest";

const pngMetadata = (relativePath: string) => {
  const desktopRoot = path.resolve(import.meta.dirname, "..");
  const bytes = readFileSync(path.join(desktopRoot, relativePath));
  return {
    signature: bytes.subarray(1, 4).toString("ascii"),
    width: bytes.readUInt32BE(16),
    height: bytes.readUInt32BE(20),
    bitDepth: bytes.readUInt8(24),
    colorType: bytes.readUInt8(25),
    interlace: bytes.readUInt8(28),
  };
};

const rgbaAt = (relativePath: string, x: number, y: number) => {
  const desktopRoot = path.resolve(import.meta.dirname, "..");
  const bytes = readFileSync(path.join(desktopRoot, relativePath));
  const width = bytes.readUInt32BE(16);
  const height = bytes.readUInt32BE(20);
  const idat: Buffer[] = [];
  for (let offset = 8; offset < bytes.length;) {
    const length = bytes.readUInt32BE(offset);
    const kind = bytes.subarray(offset + 4, offset + 8).toString("ascii");
    if (kind === "IDAT") idat.push(bytes.subarray(offset + 8, offset + 8 + length));
    offset += 12 + length;
  }
  const inflated = inflateSync(Buffer.concat(idat));
  const stride = width * 4;
  const decoded = Buffer.alloc(stride * height);
  const paeth = (a: number, b: number, c: number) => {
    const estimate = a + b - c;
    const distanceA = Math.abs(estimate - a);
    const distanceB = Math.abs(estimate - b);
    const distanceC = Math.abs(estimate - c);
    return distanceA <= distanceB && distanceA <= distanceC ? a : distanceB <= distanceC ? b : c;
  };
  for (let row = 0; row < height; row += 1) {
    const filter = inflated[row * (stride + 1)];
    const sourceOffset = row * (stride + 1) + 1;
    const targetOffset = row * stride;
    for (let column = 0; column < stride; column += 1) {
      const raw = inflated[sourceOffset + column] ?? 0;
      const left = column >= 4 ? decoded[targetOffset + column - 4] ?? 0 : 0;
      const above = row > 0 ? decoded[targetOffset - stride + column] ?? 0 : 0;
      const upperLeft = row > 0 && column >= 4 ? decoded[targetOffset - stride + column - 4] ?? 0 : 0;
      const prediction = filter === 0 ? 0
        : filter === 1 ? left
          : filter === 2 ? above
            : filter === 3 ? Math.floor((left + above) / 2)
              : paeth(left, above, upperLeft);
      decoded[targetOffset + column] = (raw + prediction) & 0xff;
    }
  }
  const offset = y * stride + x * 4;
  return [...decoded.subarray(offset, offset + 4)];
};

describe("desktop application icon", () => {
  it("uses a high-resolution RGBA packaging icon with transparent corners", () => {
    expect(pngMetadata("resources/app-icon.png")).toEqual({
      signature: "PNG",
      width: 1024,
      height: 1024,
      bitDepth: 8,
      colorType: 6,
      interlace: 0,
    });
    expect(rgbaAt("resources/app-icon.png", 0, 0)[3]).toBe(0);
    expect(rgbaAt("resources/app-icon.png", 512, 512)[3]).toBeGreaterThanOrEqual(250);
  });

  it("keeps the renderer icon in the same transparent visual family", () => {
    expect(pngMetadata("src/renderer/assets/app-icon.png")).toEqual({
      signature: "PNG",
      width: 256,
      height: 256,
      bitDepth: 8,
      colorType: 6,
      interlace: 0,
    });
    expect(rgbaAt("src/renderer/assets/app-icon.png", 0, 0)[3]).toBe(0);
    expect(rgbaAt("src/renderer/assets/app-icon.png", 128, 128)[3]).toBeGreaterThanOrEqual(250);
    const packageCenter = rgbaAt("resources/app-icon.png", 512, 512);
    const rendererCenter = rgbaAt("src/renderer/assets/app-icon.png", 128, 128);
    expect(packageCenter.slice(0, 3).every((value, index) => Math.abs(value - (rendererCenter[index] ?? 0)) <= 2)).toBe(true);
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
