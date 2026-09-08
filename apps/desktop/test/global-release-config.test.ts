import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const desktopRoot = path.resolve(import.meta.dirname, "..");
const readDesktop = (relativePath: string) => readFileSync(path.join(desktopRoot, relativePath), "utf8");

describe("isolated Global companion release", () => {
  it("uses a distinct application identity, artifact directory, and executable", () => {
    const config = readDesktop("electron-builder.global.yml");
    expect(config).toContain("appId: com.offersteady.companion.global");
    expect(config).toContain("productName: OfferSteady Companion Global");
    expect(config).toContain("output: release/global");
    expect(config).toContain("executableName: OfferSteadyGlobal");
    expect(config).toContain("OfferSteady-Companion-Global-${version}");
  });

  it("requires HTTPS Global endpoints and rejects every domestic hostname", () => {
    const generator = readDesktop("scripts/prepare-global-runtime-config.mjs");
    expect(generator).toContain("OFFERSTEADY_GLOBAL_WEB_URL");
    expect(generator).toContain("OFFERSTEADY_GLOBAL_API_BASE_URL");
    expect(generator).toContain('parsed.protocol !== "https:"');
    expect(generator).toContain('"mianshiwen.cn", "www.mianshiwen.cn", "beta.mianshiwen.cn"');
    expect(generator).toContain('!== "/api/v1"');
  });

  it("does not migrate domestic pairing credentials into the Global profile", () => {
    const main = readDesktop("src/main/index.ts");
    expect(main).toContain("app.isPackaged && existsSync(packagedGlobalRuntimeConfigPath())");
    expect(main).toContain("isGlobalRelease() ? [] : legacyUserDataDirectories");
    expect(main).toContain('releaseChannel: isGlobalRelease() ? "global"');
    expect(main).toContain("global-runtime-config.json");
    expect(main).toContain('desktopCopy("稳", "O")');
    expect(main).toContain("isGlobalRelease()\n    ? defaultWebWorkspaceUrl()");
    expect(main).toContain("isGlobalRelease()\n    ? defaultApiBaseUrl()");
  });

  it("contains only English values in the generated Global companion catalogue", () => {
    const generated = readDesktop("src/renderer/global-copy.generated.ts");
    const values = [...generated.matchAll(/:[ \t]*"([^"]*)"/g)].map((match) => match[1]);
    expect(values.length).toBeGreaterThan(100);
    expect(values.join("\n")).not.toMatch(/[\u3400-\u9fff]/);
    expect(values.join("\n")).not.toContain("Additional companion information is available for this step.");
  });

  it("fails the Global copy build when new Chinese companion copy has no explicit translation", () => {
    const generator = readDesktop("scripts/generate-global-companion-copy.mjs");
    expect(generator).toContain("Global companion copy is incomplete");
    expect(generator).toContain("Missing exact translation");
    expect(generator).toContain("Missing template translation");
  });

  it("leaves the domestic release identity and artifact names intact", () => {
    const domestic = readDesktop("electron-builder.yml");
    expect(domestic).toContain("appId: com.offersteady.companion");
    expect(domestic).toContain("productName: 面试稳伴随程序");
    expect(domestic).not.toContain("com.offersteady.companion.global");
  });
});
